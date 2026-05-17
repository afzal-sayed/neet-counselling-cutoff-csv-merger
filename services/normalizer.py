import re
import pandas as pd

# Maps every known variant (lowercase) → canonical Title Case state name.
# Variants include abbreviations, typos, fused spellings, and OCR artefacts
# seen in real NEET PG/UG MCC Excel files.
_STATE_ALIASES: dict[str, str] = {
    # Andhra Pradesh
    'andhra pradesh': 'Andhra Pradesh',
    'andhrapradesh':  'Andhra Pradesh',
    'andhra':         'Andhra Pradesh',
    # Arunachal Pradesh
    'arunachal pradesh': 'Arunachal Pradesh',
    # Assam
    'assam': 'Assam',
    # Bihar
    'bihar': 'Bihar',
    # Chhattisgarh
    'chhattisgarh': 'Chhattisgarh',
    'c.g':          'Chhattisgarh',
    'cg':           'Chhattisgarh',
    # Delhi (NCT)
    'delhi':      'Delhi',
    'delhi (nct)': 'Delhi',
    'delhi(nct)': 'Delhi',
    'new delhi':  'Delhi',
    # Goa
    'goa': 'Goa',
    # Gujarat
    'gujarat': 'Gujarat',
    # Haryana
    'haryana': 'Haryana',
    # Himachal Pradesh
    'himachal pradesh': 'Himachal Pradesh',
    'hp':  'Himachal Pradesh',
    'h.p': 'Himachal Pradesh',
    'h p': 'Himachal Pradesh',
    # Jammu And Kashmir
    'jammu and kashmir':  'Jammu And Kashmir',
    'jammu & kashmir':    'Jammu And Kashmir',
    'jammu andkashmir':   'Jammu And Kashmir',
    'jammu kashmir':      'Jammu And Kashmir',
    'j&k':   'Jammu And Kashmir',
    'j & k': 'Jammu And Kashmir',
    # Jharkhand
    'jharkhand': 'Jharkhand',
    # Karnataka
    'karnataka': 'Karnataka',
    # Kerala
    'kerala': 'Kerala',
    # Ladakh
    'ladakh': 'Ladakh',
    # Lakshadweep
    'lakshadweep': 'Lakshadweep',
    # Madhya Pradesh
    'madhya pradesh': 'Madhya Pradesh',
    'madhyapradesh':  'Madhya Pradesh',
    'm.p':  'Madhya Pradesh',
    'm.p.': 'Madhya Pradesh',
    # Maharashtra
    'maharashtra':   'Maharashtra',
    'maharasht ra':  'Maharashtra',
    # Manipur
    'manipur': 'Manipur',
    # Meghalaya
    'meghalaya': 'Meghalaya',
    # Mizoram
    'mizoram': 'Mizoram',
    # Nagaland
    'nagaland': 'Nagaland',
    # Odisha (also old name Orissa)
    'odisha': 'Odisha',
    'orissa': 'Odisha',
    # Puducherry (also old name Pondicherry)
    'puducherry':  'Puducherry',
    'pondicherry': 'Puducherry',
    # Punjab
    'punjab': 'Punjab',
    # Rajasthan
    'rajasthan': 'Rajasthan',
    # Sikkim
    'sikkim': 'Sikkim',
    # Tamil Nadu  (Chennai is a city in TN; its variants appear as state values in the data)
    'tamil nadu':  'Tamil Nadu',
    'tamilnadu':   'Tamil Nadu',
    'tami l nadu': 'Tamil Nadu',
    'chennai':     'Tamil Nadu',
    'ch ennai':    'Tamil Nadu',
    # Telangana
    'telangana':       'Telangana',
    'telangana state': 'Telangana',
    'telan gana':      'Telangana',
    # Tripura
    'tripura': 'Tripura',
    # Uttar Pradesh
    'uttar pradesh': 'Uttar Pradesh',
    'uttarpradesh':  'Uttar Pradesh',
    'up':   'Uttar Pradesh',
    'u.p':  'Uttar Pradesh',
    'u.p.': 'Uttar Pradesh',
    # Uttarakhand (also old name Uttaranchal)
    'uttarakhand':  'Uttarakhand',
    'uttarajgand':  'Uttarakhand',
    'uttaranchal':  'Uttarakhand',
    # West Bengal
    'west bengal': 'West Bengal',
    'westbengal':  'West Bengal',
    # Union Territories
    'andaman and nicobar islands': 'Andaman And Nicobar Islands',
    'andaman and nicobar':         'Andaman And Nicobar Islands',
    'chandigarh': 'Chandigarh',
    'dadra and nagar haveli and daman and diu': 'Dadra And Nagar Haveli And Daman And Diu',
    'dadra and nagar haveli': 'Dadra And Nagar Haveli And Daman And Diu',
}

_COLUMN_MAP = {
    'quota':               'Allotted Quota',
    'allotted quota':      'Allotted Quota',
    'institute name':      'Allotted Institute',
    'institute':           'Allotted Institute',
    'college':             'Allotted Institute',
    'allotted institute':  'Allotted Institute',
    'course':              'Alloted Course',
    'alloted course':      'Alloted Course',
    'category':            'Alloted Category',
    'alloted category':    'Alloted Category',
    'air':                 'rank',
    'rank':                'rank',
}

_CATEGORY_ALIASES: dict[str, str] = {
    'open':    'Open',
    'obc':     'OBC',
    'sc':      'SC',
    'st':      'ST',
    'ews':     'EWS',
    'openpwd': 'Open PwD',
    'obcpwd':  'OBC PwD',
    'scpwd':   'SC PwD',
    'stpwd':   'ST PwD',
    'ewspwd':  'EWS PwD',
}

_COURSE_OCR_FIXES: list[tuple] = [
    # Stray spaces inside hyphenated compounds
    (r'RADIO-\s+DIAGNOSIS',          'RADIO-DIAGNOSIS'),
    (r'OTO-\s+RHINO-\s*LARYNGOLOGY', 'OTO-RHINO-LARYNGOLOGY'),
    (r'IMMUNO-\s+HAEMATOLOGY',       'IMMUNO-HAEMATOLOGY'),
    # OCR mid-word splits
    (r'ANAESTHESIOLOG\s+Y',  'ANAESTHESIOLOGY'),
    (r'VENEREOLOG\s+Y',      'VENEREOLOGY'),
    (r'VENEREOL\s+OGY',      'VENEREOLOGY'),
    (r'VENER\s+EOLOGY',      'VENEREOLOGY'),
    (r'VENEREOLO\s+GY',      'VENEREOLOGY'),
    (r'DERMATOLOG\s+Y',      'DERMATOLOGY'),
    (r'DERMATOLO\s+GY',      'DERMATOLOGY'),
    (r'DERMAT\s+OLOGY',      'DERMATOLOGY'),
    (r'LEPROS\s+Y',          'LEPROSY'),
    (r'LEPRO\s+SY',          'LEPROSY'),
    (r'LE\s+PROSY',          'LEPROSY'),
    (r'S\s+KIN\b',           'SKIN'),
    # Fused words
    (r'Obstetricsand\b',     'Obstetrics and'),
    (r'PREVENTIVEand\b',     'PREVENTIVE and'),
    (r'DERMATOLOGYand\b',    'DERMATOLOGY and'),
    (r'VENEREOLOGYand\b',    'VENEREOLOGY and'),
    (r'VENE\.and\b',         'VENE. and'),
    (r'TRANSFUSIONMEDICINE', 'TRANSFUSION MEDICINE'),
    (r'PHYSICALMED\.',       'PHYSICAL MED.'),
    (r'COMMUNITYHEALTH',     'COMMUNITY HEALTH'),
    (r'Respiratorydiseases', 'Respiratory diseases'),
    (r'EmergencyMedicine',   'Emergency Medicine'),
    # Missing space after (NBEMS) / (NBEMS-DIPLOMA) prefix
    (r'\(NBEMS\)(?=[A-Za-z])',         '(NBEMS) '),
    (r'\(NBEMS-DIPLOMA\)(?=[A-Za-z])', '(NBEMS-DIPLOMA) '),
    # Missing space before opening paren after M.D. / MS
    (r'M\.D\.\(',  'M.D. ('),
    (r'\bMS\(',    'MS ('),
    # DIP.IN / DIPLOMA variants
    (r'DIP\.IN MEDICAL RADIO-\s*DIAGNOSIS', 'DIP.IN MEDICAL RADIO-DIAGNOSIS'),
    (r'DIPLOMA IN OPHTHALMOLOGY/DOM\s+S',   'DIPLOMA IN OPHTHALMOLOGY/DOMS'),
    (r'DIP\. IN PHY\. MEDICINEand REHAB\.', 'DIP. IN PHY. MEDICINE and REHAB.'),
    # Collapse double spaces (run last)
    (r'  +', ' '),
]

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

# Aliases sorted longest-first so multi-word matches beat single-word ones.
_SORTED_ALIASES = sorted(_STATE_ALIASES.keys(), key=len, reverse=True)


def normalize_category(value) -> str:
    if not isinstance(value, str):
        return value
    key = re.sub(r'\s+', '', value).lower()
    return _CATEGORY_ALIASES.get(key, value)


def normalize_course(value) -> str:
    if not isinstance(value, str):
        return value
    result = value
    for pattern, replacement in _COURSE_OCR_FIXES:
        result = re.sub(pattern, replacement, result)
    return result.strip()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {col: _COLUMN_MAP[col.strip().lower()]
              for col in df.columns if col.strip().lower() in _COLUMN_MAP}
    df = df.rename(columns=rename)
    missing = [c for c in _REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(
            f"Could not map columns: {missing}. Detected: {list(df.columns)}"
        )
    df = df[_REQUIRED + ['_round']].copy()
    df['Alloted Category'] = df['Alloted Category'].map(normalize_category)
    df['Alloted Course']   = df['Alloted Course'].map(normalize_course)
    return df


# ── State extraction helpers ───────────────────────────────────────────────

def _norm(text: str) -> str:
    """Lowercase, strip trailing punctuation, collapse whitespace."""
    return re.sub(r'\s+', ' ', text.lower().strip().rstrip('.,;- '))


def _lookup(candidate: str) -> str | None:
    """Return the canonical state name if candidate matches any known alias."""
    return _STATE_ALIASES.get(_norm(candidate))


def _strip_pin(text: str) -> str:
    """Remove a PIN code (and everything after it) from the end of a string.
    Handles separators: space, hyphen, en-dash (–), em-dash (—).
    """
    return re.sub(r'[\s\-–—]+\d{6}\b.*', '', text).strip()


def _scan_for_state(text: str) -> str | None:
    """Search free-form text for any known state name or alias.

    Strategy:
    1. Word/phrase boundary scan for all aliases (longest first).
    2. Suffix scan on each token for concatenated forms (e.g. "malappuramkerala").
    """
    # Normalise: keep only letters, digits, spaces, & and dots; collapse spaces.
    cleaned = re.sub(r'[^a-zA-Z0-9\s&.]', ' ', text)
    norm = re.sub(r'\s+', ' ', cleaned.lower()).strip()

    for alias in _SORTED_ALIASES:
        escaped = re.escape(alias)
        # Lookahead/behind on alphanumerics so special chars like & work correctly.
        if re.search(r'(?<![a-z0-9])' + escaped + r'(?![a-z0-9])', norm):
            return _STATE_ALIASES[alias]

    # Suffix check: "malappuramkerala" → ends with "kerala"
    for token in norm.split():
        for alias in _SORTED_ALIASES:
            if len(alias) >= 4 and token != alias and token.endswith(alias):
                return _STATE_ALIASES[alias]

    return None


def extract_state(college_name) -> str:
    if not isinstance(college_name, str):
        return 'Unknown'

    parts = [p.strip() for p in college_name.split(',')]

    for i, part in enumerate(parts):
        # Case 1: standalone 6-digit PIN — state is the preceding part.
        if re.fullmatch(r'\d{6}', part):
            if i > 0:
                candidate = _strip_pin(parts[i - 1])
                s = _lookup(candidate) or _scan_for_state(candidate)
                if s:
                    return s
            break

        # Case 2: PIN fused into a part (e.g. "Assam 782462", "Guntur-522002").
        if re.search(r'\b\d{6}\b', part):
            # 2a: state is in the next part (e.g. "Guntur-522002, Andhra Pradesh").
            if i + 1 < len(parts):
                s = _lookup(parts[i + 1]) or _scan_for_state(parts[i + 1])
                if s:
                    return s
            # 2b: state is the prefix before the PIN (e.g. "Assam 782462" → "Assam").
            prefix = _strip_pin(part)
            s = _lookup(prefix) or _scan_for_state(prefix)
            if s:
                return s
            break

    # No PIN found (or PIN-based extraction failed) — scan each part for a state
    # name, starting from the end where the state is most likely to appear.
    for part in reversed(parts[1:]):
        s = _lookup(part) or _scan_for_state(part)
        if s:
            return s

    # Last resort: search the entire string.
    return _scan_for_state(college_name) or 'Unknown'


def expand_abbreviations(name) -> str:
    if not isinstance(name, str):
        return ''
    words = re.split(r'[\s,.\-]+', name.lower())
    return ' '.join(ABBREVIATIONS.get(w, w) for w in words if w)
