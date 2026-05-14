import re
import pandas as pd

# All Indian states and UTs, lowercase — used to validate extracted state candidates.
_INDIAN_STATES = {
    'andhra pradesh', 'arunachal pradesh', 'assam', 'bihar', 'chhattisgarh',
    'goa', 'gujarat', 'haryana', 'himachal pradesh', 'jharkhand', 'karnataka',
    'kerala', 'madhya pradesh', 'maharashtra', 'manipur', 'meghalaya', 'mizoram',
    'nagaland', 'odisha', 'punjab', 'rajasthan', 'sikkim', 'tamil nadu',
    'telangana', 'tripura', 'uttar pradesh', 'uttarakhand', 'west bengal',
    'delhi', 'jammu and kashmir', 'ladakh', 'chandigarh', 'puducherry',
    'andaman and nicobar islands', 'dadra and nagar haveli and daman and diu',
    'lakshadweep',
}

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


def _is_state(candidate: str) -> bool:
    return candidate.strip().lower() in _INDIAN_STATES


def _strip_pin(text: str) -> str:
    """Remove a trailing PIN (with optional separator) from a string."""
    return re.sub(r'[\s\-–]+\d{6}\b.*', '', text).strip()


def extract_state(college_name) -> str:
    if not isinstance(college_name, str):
        return 'Unknown'
    parts = [p.strip() for p in college_name.split(',')]

    for i, part in enumerate(parts):
        # Case 1: standalone 6-digit PIN — state is the part before it.
        if re.fullmatch(r'\d{6}', part):
            if i > 0:
                candidate = parts[i - 1].strip()
                return _strip_pin(candidate).title()
            return 'Unknown'

        # Case 2: PIN fused into a part (e.g. "Assam 782462", "Delhi-110010").
        if re.search(r'\b\d{6}\b', part):
            # 2a: state is in the next part (e.g. "Guntur-522002, Andhra Pradesh").
            if i + 1 < len(parts):
                nxt = parts[i + 1].strip()
                if _is_state(nxt):
                    return nxt.title()
            # 2b: state is the prefix before the PIN in the same part
            #     (e.g. "Assam 782462" → "Assam").
            prefix = _strip_pin(part)
            if prefix and _is_state(prefix):
                return prefix.title()

    # No PIN found anywhere — scan parts from the end and return the first
    # recognised state name, skipping address fragments and long strings.
    for part in reversed(parts[1:]):
        candidate = part.strip()
        if _is_state(candidate):
            return candidate.title()

    return 'Unknown'


def expand_abbreviations(name) -> str:
    if not isinstance(name, str):
        return ''
    words = re.split(r'[\s,.\-]+', name.lower())
    return ' '.join(ABBREVIATIONS.get(w, w) for w in words if w)
