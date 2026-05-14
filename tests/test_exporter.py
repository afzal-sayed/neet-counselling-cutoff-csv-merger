import io
import pandas as pd
from services.exporter import merge_rounds, build_xlsx, build_csv

STATE = 'Madhya Pradesh'
COLLEGE = 'Government Medical College'

def make_round(rows, round_num):
    df = pd.DataFrame(rows, columns=[
        'Allotted Quota', 'Allotted Institute', 'Alloted Course',
        'Alloted Category', 'rank', '_round', 'State'
    ])
    df['_round'] = round_num
    return df

def test_merge_fills_na_for_missing_rounds():
    r1 = make_round([['AI', COLLEGE, 'MD', 'Open', '100', 1, STATE]], 1)
    merged = merge_rounds([r1])
    assert merged['Round 1'].iloc[0] == '100'
    assert merged['Round 2'].iloc[0] == 'N/A'
    assert merged['Stray Vacancy'].iloc[0] == 'N/A'

def test_merge_combines_matching_rows():
    r1 = make_round([['AI', COLLEGE, 'MD', 'Open', '100', 1, STATE]], 1)
    r2 = make_round([['AI', COLLEGE, 'MD', 'Open', '120', 2, STATE]], 2)
    merged = merge_rounds([r1, r2])
    assert len(merged) == 1
    assert merged['Round 1'].iloc[0] == '100'
    assert merged['Round 2'].iloc[0] == '120'

def test_merge_creates_separate_rows_for_different_colleges():
    r1 = make_round([['AI', 'College A', 'MD', 'Open', '100', 1, STATE]], 1)
    r2 = make_round([['AI', 'College B', 'MD', 'Open', '120', 2, STATE]], 2)
    merged = merge_rounds([r1, r2])
    assert len(merged) == 2

def test_merge_output_columns_match_2024_format():
    r1 = make_round([['AI', COLLEGE, 'MD', 'Open', '100', 1, STATE]], 1)
    merged = merge_rounds([r1])
    expected = ['Allotted Quota', 'Allotted Institute', 'State', 'Alloted Category',
                'Alloted Course', 'Round 1', 'Round 2', 'Round 3', 'Stray Vacancy', 'Sp.Stray Vacancy']
    assert list(merged.columns) == expected

def test_build_xlsx_returns_bytes():
    r1 = make_round([['AI', COLLEGE, 'MD', 'Open', '100', 1, STATE]], 1)
    merged = merge_rounds([r1])
    data = build_xlsx(merged, [])
    assert isinstance(data, bytes) and len(data) > 0

def test_build_xlsx_has_match_report_sheet():
    r1 = make_round([['AI', COLLEGE, 'MD', 'Open', '100', 1, STATE]], 1)
    merged = merge_rounds([r1])
    log = [{'original': 'X', 'matched': 'Y', 'score': 95, 'round': 'Round 1', 'state': STATE}]
    xf = pd.ExcelFile(io.BytesIO(build_xlsx(merged, log)))
    assert 'Match Report' in xf.sheet_names

def test_build_csv_handles_comma_in_college_name():
    r1 = make_round([['AI', 'College, With Comma', 'MD', 'Open', '100', 1, STATE]], 1)
    merged = merge_rounds([r1])
    text = build_csv(merged).decode('utf-8-sig')
    df = pd.read_csv(io.StringIO(text))
    assert len(df) == 1
    assert 'College, With Comma' in df['Allotted Institute'].iloc[0]
