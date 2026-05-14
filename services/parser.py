import pandas as pd
from io import BytesIO


def _detect_header_row(xf, sheet_name) -> int:
    """Return 0 if row 0 looks like real headers, else 1 (title row present)."""
    peek = pd.read_excel(xf, sheet_name=sheet_name, header=None, nrows=2, dtype=str)
    if peek.empty:
        return 0
    first_row = peek.iloc[0]
    non_null = first_row.dropna()
    # A title row typically has only one non-null cell (the title string)
    if len(non_null) == 1:
        return 1
    return 0


def read_file(file_bytes: BytesIO, filename: str, round_num: int) -> pd.DataFrame:
    name = filename.lower()
    if name.endswith('.xlsx') or name.endswith('.xls'):
        xf = pd.ExcelFile(file_bytes)
        header_row = _detect_header_row(xf, xf.sheet_names[0])
        df = pd.read_excel(xf, sheet_name=xf.sheet_names[0], header=header_row, dtype=str)
    elif name.endswith('.csv'):
        df = pd.read_csv(file_bytes, dtype=str, encoding='utf-8-sig', on_bad_lines='skip')
    else:
        raise ValueError(f"Unsupported file format: {filename}. Use .xlsx or .csv")

    df.columns = df.columns.str.strip()
    df = df.dropna(how='all')
    df['_round'] = round_num
    return df.reset_index(drop=True)
