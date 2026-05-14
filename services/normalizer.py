import re
import pandas as pd

_COLUMN_MAP = {
    'quota':               'Allotted Quota',
    'allotted quota':      'Allotted Quota',
    'institute name':      'Allotted Institute',
    'college':             'Allotted Institute',
    'allotted institute':  'Allotted Institute',
    'course':              'Alloted Course',
    'alloted course':      'Alloted Course',
    'category':            'Alloted Category',
    'alloted category':    'Alloted Category',
    'air':                 'rank',
    'rank':                'rank',
}

ABBREVIATIONS = {
    'gmc':   'government medical college',
    'govt':  'government',
    'gov':   'government',
    'med':   'medical',
    'clg':   'college',
    'inst':  'institute',
    'hosp':  'hospital',
    'aiims': 'all india institute of medical sciences',
    'kgmc':  'king george medical college',
    'rims':  'regional institute of medical sciences',
}

_REQUIRED = ['Allotted Quota', 'Allotted Institute', 'Alloted Course', 'Alloted Category', 'rank']


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {col: _COLUMN_MAP[col.strip().lower()]
              for col in df.columns if col.strip().lower() in _COLUMN_MAP}
    df = df.rename(columns=rename)
    missing = [c for c in _REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(
            f"Could not map columns: {missing}. Detected: {list(df.columns)}"
        )
    return df[_REQUIRED + ['_round']].copy()


def extract_state(college_name) -> str:
    if not isinstance(college_name, str):
        return 'Unknown'
    parts = [p.strip() for p in college_name.split(',')]
    for i, part in enumerate(parts):
        if re.fullmatch(r'\d{6}', part):
            return parts[i - 1].strip().title() if i > 0 else 'Unknown'
    # No PIN found. Real format is "Name, City, State" — state is the last part.
    if len(parts) >= 2:
        return parts[-1].strip().title()
    return 'Unknown'


def expand_abbreviations(name) -> str:
    if not isinstance(name, str):
        return ''
    words = re.split(r'[\s,.\-]+', name.lower())
    return ' '.join(ABBREVIATIONS.get(w, w) for w in words if w)
