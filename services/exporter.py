import pandas as pd
from io import BytesIO

ROUND_LABELS = {
    1: 'Round 1', 2: 'Round 2', 3: 'Round 3',
    4: 'Stray Vacancy', 5: 'Sp.Stray Vacancy',
}
KEY_COLS = ['Allotted Quota', 'Allotted Institute', 'State', 'Alloted Category', 'Alloted Course']
ROUND_COLS = ['Round 1', 'Round 2', 'Round 3', 'Stray Vacancy', 'Sp.Stray Vacancy']
OUTPUT_COLS = KEY_COLS + ROUND_COLS


def merge_rounds(dfs: list) -> pd.DataFrame:
    if not dfs:
        return pd.DataFrame(columns=OUTPUT_COLS)
    merged = None
    for df in sorted(dfs, key=lambda d: int(d['_round'].iloc[0])):
        round_num = int(df['_round'].iloc[0])
        col = ROUND_LABELS[round_num]
        round_df = df[KEY_COLS + ['rank']].copy()
        round_df = round_df.rename(columns={'rank': col})
        round_df = round_df.drop_duplicates(subset=KEY_COLS)
        merged = round_df if merged is None else pd.merge(merged, round_df, on=KEY_COLS, how='outer')

    for col in ROUND_COLS:
        if col not in merged.columns:
            merged[col] = 'N/A'

    merged = merged.fillna('N/A')
    return merged[OUTPUT_COLS].reset_index(drop=True)


def build_xlsx(merged_df: pd.DataFrame, match_log: list) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        merged_df.to_excel(writer, sheet_name='All Rounds', index=False)
        if match_log:
            match_df = pd.DataFrame(match_log).rename(columns={
                'original': 'Original Name', 'matched': 'Matched To',
                'score': 'Similarity Score', 'round': 'Round', 'state': 'State',
            })
            match_df.to_excel(writer, sheet_name='Match Report', index=False)
    return buf.getvalue()


def build_csv(merged_df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    merged_df.to_csv(buf, index=False, encoding='utf-8-sig', quoting=1)  # QUOTE_ALL
    return buf.getvalue()
