import uuid
import threading
from io import BytesIO
from flask import Flask, request, jsonify, render_template, send_file

from services.parser import read_file
from services.normalizer import normalize_columns, extract_state
from services.matcher import build_fuzzy_mapping, apply_mapping
from services.exporter import merge_rounds, build_xlsx, build_csv

app = Flask(__name__)
jobs: dict = {}

ROUND_LABELS = {
    1: 'Round 1', 2: 'Round 2', 3: 'Round 3',
    4: 'Stray Vacancy', 5: 'Sp.Stray Vacancy',
}


def _process_job(job_id: str, files_data: dict) -> None:
    job = jobs[job_id]

    def upd(p, s):
        job['progress'], job['stage'] = p, s

    try:
        upd(5, 'Reading files...')
        dfs = []
        for round_num, (filename, fb) in sorted(files_data.items()):
            dfs.append(read_file(BytesIO(fb), filename, round_num))

        upd(20, 'Normalizing columns...')
        normalized = [normalize_columns(df) for df in dfs]

        upd(40, 'Extracting states...')
        for df in normalized:
            df['State'] = df['Allotted Institute'].apply(extract_state)

        upd(60, 'Fuzzy matching colleges...')
        mapping, match_log = build_fuzzy_mapping(normalized)

        # Write all fields before setting status='review' so polling threads
        # never see status=review with fuzzy_matches still empty.
        job['dfs'] = normalized
        job['mapping'] = mapping
        job['match_log'] = match_log
        job['fuzzy_matches'] = match_log
        job['progress'] = 100
        job['stage'] = 'Ready for review'
        job['status'] = 'review'  # written last — acts as the visibility barrier
    except Exception as exc:
        job.update({'status': 'error', 'error': str(exc), 'stage': 'Error'})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process():
    files_data = {}
    for i in range(1, 6):
        f = request.files.get(f'round{i}')
        if f and f.filename:
            files_data[i] = (f.filename, f.read())
    if not files_data:
        return jsonify({'error': 'No files provided'}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'status': 'processing', 'progress': 0,
        'stage': 'Starting...', 'fuzzy_matches': [],
    }
    threading.Thread(target=_process_job, args=(job_id, files_data), daemon=True).start()
    return jsonify({'job_id': job_id})


@app.route('/status/<job_id>')
def status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    resp = {'status': job['status'], 'progress': job['progress'], 'stage': job['stage']}
    if job['status'] == 'review':
        resp['fuzzy_matches'] = job['fuzzy_matches']
    if job['status'] == 'error':
        resp['error'] = job.get('error', 'Unknown error')
    return jsonify(resp)


@app.route('/finalize/<job_id>', methods=['POST'])
def finalize(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    confirmed = request.get_json(force=True).get('confirmed_matches', [])
    approved = {m['original']: m['canonical'] for m in confirmed}

    dfs = [apply_mapping(df, approved) for df in job['dfs']]
    approved_log = [m for m in job['match_log']
                    if approved.get(m['original']) == m['matched']]

    merged = merge_rounds(dfs)
    job.update({
        'bytes_xlsx': build_xlsx(merged, approved_log),
        'bytes_csv':  build_csv(merged),
        'status':     'complete',
    })
    return jsonify({'status': 'complete'})


@app.route('/download/<job_id>')
def download(job_id: str):
    job = jobs.get(job_id)
    if not job or job['status'] != 'complete':
        return jsonify({'error': 'Not ready'}), 404

    fmt = request.args.get('format', 'xlsx')
    if fmt == 'csv':
        return send_file(BytesIO(job['bytes_csv']), mimetype='text/csv',
                         as_attachment=True, download_name='neet_pg_2025_all_rounds.csv')
    return send_file(
        BytesIO(job['bytes_xlsx']),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='neet_pg_2025_all_rounds.xlsx',
    )


if __name__ == '__main__':
    app.run(debug=True)
