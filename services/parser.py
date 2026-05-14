import pandas as pd
from io import BytesIO


def read_file(file_bytes: BytesIO, filename: str, round_num: int) -> pd.DataFrame:
    name = filename.lower()
    if name.endswith('.xlsx') or name.endswith('.xls'):
        xf = pd.ExcelFile(file_bytes)
        df = pd.read_excel(xf, sheet_name=xf.sheet_names[0], header=0, dtype=str)
    elif name.endswith('.csv'):
        df = pd.read_csv(file_bytes, dtype=str, encoding='utf-8-sig', on_bad_lines='skip')
    else:
        raise ValueError(f"Unsupported file format: {filename}. Use .xlsx or .csv")

    df.columns = df.columns.str.strip()
    df = df.dropna(how='all')
    df['_round'] = round_num
    return df.reset_index(drop=True)
