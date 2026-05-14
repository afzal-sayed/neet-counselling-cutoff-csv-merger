import io
import pytest
import pandas as pd
from openpyxl import Workbook
from services.parser import read_file, _detect_header_row

def make_xlsx_bytes(rows, sheet_name='CUTOFF'):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()

def make_csv_bytes(rows):
    lines = [','.join(str(c) for c in r) for r in rows]
    return '\n'.join(lines).encode('utf-8-sig')

def test_read_xlsx_returns_dataframe():
    data = make_xlsx_bytes([
        ['Quota', 'Institute Name', 'Course', 'Category', 'AIR'],
        ['AI', 'Test College, City, State, 123456', 'MD', 'Open', '100'],
    ])
    df = read_file(io.BytesIO(data), 'round1.xlsx', 1)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df['_round'].iloc[0] == 1

def test_read_csv_returns_dataframe():
    data = make_csv_bytes([
        ['QUOTA', 'COLLEGE', 'COURSE', 'CATEGORY', 'AIR'],
        ['AI', 'Test College', 'MD', 'Open', '200'],
    ])
    df = read_file(io.BytesIO(data), 'round2.csv', 2)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df['_round'].iloc[0] == 2

def test_unsupported_format_raises():
    with pytest.raises(ValueError, match='Unsupported'):
        read_file(io.BytesIO(b'data'), 'file.txt', 1)

def test_empty_rows_returns_empty_dataframe():
    data = make_xlsx_bytes([
        ['Quota', 'Institute Name', 'Course', 'Category', 'AIR'],
    ])
    df = read_file(io.BytesIO(data), 'round1.xlsx', 1)
    assert len(df) == 0

def test_detect_header_row_returns_0_for_normal_file():
    import pandas as pd
    data = make_xlsx_bytes([
        ['Quota', 'Institute Name', 'Course', 'Category', 'AIR'],
        ['AI', 'Test College', 'MD', 'Open', '100'],
    ])
    xf = pd.ExcelFile(io.BytesIO(data))
    assert _detect_header_row(xf, xf.sheet_names[0]) == 0

def test_detect_header_row_returns_1_for_title_row_file():
    import pandas as pd
    data = make_xlsx_bytes([
        ['NEET PG 2025 ALL INDIA 1ST ROUND CUT OFF LIST', None, None, None, None],
        ['Quota', 'Institute Name', 'Course', 'Category', 'AIR'],
        ['AI', 'Test College', 'MD', 'Open', '100'],
    ])
    xf = pd.ExcelFile(io.BytesIO(data))
    assert _detect_header_row(xf, xf.sheet_names[0]) == 1

def test_read_xlsx_with_title_row_reads_correct_headers():
    data = make_xlsx_bytes([
        ['NEET PG 2025 ALL INDIA CUT OFF LIST', None, None, None, None],
        ['Quota', 'Institute Name', 'Course', 'Category', 'AIR'],
        ['AI', 'Test College', 'MD', 'Open', '100'],
    ])
    df = read_file(io.BytesIO(data), 'round1.xlsx', 1)
    assert 'Quota' in df.columns
    assert len(df) == 1
