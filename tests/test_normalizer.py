import pandas as pd
import pytest
from services.normalizer import normalize_columns, extract_state, expand_abbreviations

def make_df(cols, rows=None, round_num=1):
    rows = rows or [['x'] * len(cols)]
    df = pd.DataFrame(rows, columns=cols)
    df['_round'] = round_num
    return df

def test_normalize_round1_columns():
    df = make_df(['Quota', 'Institute Name', 'Course', 'Category', 'AIR'])
    result = normalize_columns(df)
    assert 'Allotted Quota' in result.columns
    assert 'Allotted Institute' in result.columns
    assert 'Alloted Course' in result.columns
    assert 'Alloted Category' in result.columns
    assert 'rank' in result.columns

def test_normalize_round2_columns():
    df = make_df(['QUOTA', 'COLLEGE', 'COURSE', 'CATEGORY', 'AIR'])
    result = normalize_columns(df)
    assert 'Allotted Institute' in result.columns

def test_normalize_round3_columns():
    df = make_df(['Allotted Quota', 'Allotted Institute', 'Course', 'Alloted Category', 'Rank'])
    result = normalize_columns(df)
    assert 'rank' in result.columns

def test_normalize_round4_columns():
    df = make_df(['Allotted Quota', 'Allotted Institute', 'Alloted Course', 'Alloted Category', 'Rank'])
    result = normalize_columns(df)
    assert 'Alloted Course' in result.columns

def test_normalize_raises_on_unknown_columns():
    df = make_df(['ColA', 'ColB', 'ColC', 'ColD', 'ColE'])
    with pytest.raises(ValueError, match='Could not map'):
        normalize_columns(df)

def test_normalize_keeps_round_column():
    df = make_df(['Quota', 'Institute Name', 'Course', 'Category', 'AIR'])
    result = normalize_columns(df)
    assert '_round' in result.columns

def test_extract_state_with_pin():
    name = "Andhra Medical College,Andhra Medical College, Andhra Pradesh, 530002"
    assert extract_state(name) == "Andhra Pradesh"

def test_extract_state_without_pin_uses_last_part():
    # Format without PIN: "Name, City, State" — state is the last comma-separated part.
    name = "Some College, Some City, Tamil Nadu"
    assert extract_state(name) == "Tamil Nadu"

def test_extract_state_comma_in_college_name():
    name = "College of Medicine, Technology,Some City, Rajasthan, 302001"
    assert extract_state(name) == "Rajasthan"

def test_extract_state_pin_fused_with_space():
    # "Assam 782462" — PIN glued to state name with a space
    name = "Diphu Medical College & Hospital,Thana Road, Diphu, Assam 782462"
    assert extract_state(name) == "Assam"

def test_extract_state_pin_fused_with_hyphen():
    # "Delhi-110010" — PIN glued to state/UT name with a hyphen
    name = "Some Hospital, Karol Bagh, Delhi-110010"
    assert extract_state(name) == "Delhi"

def test_extract_state_pin_fused_state_before_city():
    # "Guntur-522002, Andhra Pradesh" — PIN in city part, state is the next part
    name = "BMR Hospitals, 6/2, Arundelpet, Guntur-522002, Andhra Pradesh"
    assert extract_state(name) == "Andhra Pradesh"

def test_extract_state_duplicate_address_trailing():
    # Duplicate free-text address appended after the structured address;
    # fallback must not pick the address blob as the state
    name = "Govt Medical College, Ramagundam, Telangana, Malkapur Village Ramagundam Mandal Pedapalli"
    assert extract_state(name) == "Telangana"

def test_extract_state_non_string_returns_unknown():
    assert extract_state(None) == "Unknown"

def test_extract_state_single_part_returns_unknown():
    assert extract_state("NoCommaHere") == "Unknown"

def test_expand_govt():
    assert 'government' in expand_abbreviations('Govt Medical College')

def test_expand_gmc():
    assert 'government medical college' in expand_abbreviations('GMC Bhopal')

def test_expand_aiims():
    assert 'all india institute of medical sciences' in expand_abbreviations('AIIMS Delhi')

def test_expand_preserves_unknown_words():
    result = expand_abbreviations('Unique Hospital Name')
    assert 'hospital' in result
    assert 'unique' in result

def test_expand_non_string_returns_empty():
    assert expand_abbreviations(None) == ''
