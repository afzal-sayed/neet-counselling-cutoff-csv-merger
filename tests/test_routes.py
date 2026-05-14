import io, json, time
import pytest
from openpyxl import Workbook
from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c

def make_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.title = 'CUTOFF'
    ws.append(['Quota', 'Institute Name', 'Course', 'Category', 'AIR'])
    ws.append(['AI', 'Test College, City, Madhya Pradesh, 462001', 'MD', 'Open', '100'])
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()

def test_index_returns_html(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'html' in resp.data.lower()

def test_process_returns_job_id(client):
    data = {f'round{i}': (io.BytesIO(make_xlsx()), f'r{i}.xlsx') for i in range(1, 5)}
    resp = client.post('/process', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    assert 'job_id' in json.loads(resp.data)

def test_process_no_files_returns_400(client):
    resp = client.post('/process', data={}, content_type='multipart/form-data')
    assert resp.status_code == 400

def test_status_404_on_unknown_job(client):
    assert client.get('/status/bad-id').status_code == 404

def test_status_reaches_review(client):
    data = {'round1': (io.BytesIO(make_xlsx()), 'r1.xlsx')}
    job_id = json.loads(client.post('/process', data=data,
                                    content_type='multipart/form-data').data)['job_id']
    for _ in range(20):
        time.sleep(0.3)
        s = json.loads(client.get(f'/status/{job_id}').data)['status']
        if s in ('review', 'error'):
            break
    assert s in ('review', 'error')

def test_finalize_and_download(client):
    data = {'round1': (io.BytesIO(make_xlsx()), 'r1.xlsx')}
    job_id = json.loads(client.post('/process', data=data,
                                    content_type='multipart/form-data').data)['job_id']
    for _ in range(20):
        time.sleep(0.3)
        if json.loads(client.get(f'/status/{job_id}').data)['status'] == 'review':
            break
    fr = client.post(f'/finalize/{job_id}',
                     data=json.dumps({'confirmed_matches': []}),
                     content_type='application/json')
    assert json.loads(fr.data)['status'] == 'complete'
    xlsx_resp = client.get(f'/download/{job_id}?format=xlsx')
    assert xlsx_resp.status_code == 200
    assert xlsx_resp.data[:2] == b'PK'   # XLSX is ZIP-based
    csv_resp = client.get(f'/download/{job_id}?format=csv')
    assert csv_resp.status_code == 200
    assert b'Allotted Quota' in csv_resp.data
