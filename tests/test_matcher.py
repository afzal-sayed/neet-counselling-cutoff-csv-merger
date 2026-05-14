import pandas as pd
from services.matcher import build_fuzzy_mapping, apply_mapping

def make_round_df(rows, round_num):
    df = pd.DataFrame(rows, columns=[
        'Allotted Quota', 'Allotted Institute', 'Alloted Course',
        'Alloted Category', 'rank', '_round', 'State'
    ])
    df['_round'] = round_num
    return df

def test_exact_match_not_remapped():
    r1 = make_round_df([['AI', 'Government Medical College Bhopal', 'MD', 'Open', '100', 1, 'Madhya Pradesh']], 1)
    r2 = make_round_df([['AI', 'Government Medical College Bhopal', 'MD', 'Open', '120', 2, 'Madhya Pradesh']], 2)
    mapping, log = build_fuzzy_mapping([r1, r2])
    assert 'Government Medical College Bhopal' not in mapping

def test_fuzzy_match_found():
    r1 = make_round_df([['AI', 'Government Medical College Bhopal', 'MD', 'Open', '100', 1, 'Madhya Pradesh']], 1)
    r2 = make_round_df([['AI', 'Govt. Medical College Bhopal', 'MD', 'Open', '120', 2, 'Madhya Pradesh']], 2)
    mapping, log = build_fuzzy_mapping([r1, r2])
    assert len(mapping) == 1
    assert len(log) == 1
    assert log[0]['score'] >= 90

def test_cross_state_not_matched():
    r1 = make_round_df([['AI', 'Government Medical College', 'MD', 'Open', '100', 1, 'Kerala']], 1)
    r2 = make_round_df([['AI', 'Government Medical College', 'MD', 'Open', '120', 2, 'Karnataka']], 2)
    mapping, log = build_fuzzy_mapping([r1, r2])
    assert len(mapping) == 0

def test_apply_mapping_replaces_names():
    r1 = make_round_df([['AI', 'Govt. Medical College Bhopal', 'MD', 'Open', '120', 1, 'Madhya Pradesh']], 1)
    mapping = {'Govt. Medical College Bhopal': 'Government Medical College Bhopal'}
    result = apply_mapping(r1, mapping)
    assert result['Allotted Institute'].iloc[0] == 'Government Medical College Bhopal'

def test_apply_mapping_leaves_unmapped_unchanged():
    r1 = make_round_df([['AI', 'AIIMS Delhi', 'MD', 'Open', '1', 1, 'Delhi']], 1)
    result = apply_mapping(r1, {})
    assert result['Allotted Institute'].iloc[0] == 'AIIMS Delhi'
