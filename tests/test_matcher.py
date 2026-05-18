import pandas as pd
from services.matcher import build_fuzzy_mapping, build_course_context, apply_mapping

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

def test_build_course_context_basic():
    r1 = make_round_df([
        ['AI', 'Govt. Medical College Bhopal', 'MD Medicine', 'Open', '100', 1, 'Madhya Pradesh'],
        ['AI', 'Govt. Medical College Bhopal', 'MS Surgery', 'Open', '200', 1, 'Madhya Pradesh'],
    ], 1)
    r2 = make_round_df([
        ['AI', 'Government Medical College Bhopal', 'MD Medicine', 'Open', '110', 2, 'Madhya Pradesh'],
    ], 2)
    review_log = [{'original': 'Govt. Medical College Bhopal',
                   'matched': 'Government Medical College Bhopal',
                   'score': 88.5, 'state': 'Madhya Pradesh'}]
    groups = build_course_context([r1, r2], review_log)
    assert len(groups) == 1
    group = groups[0]
    assert group['original'] == 'Govt. Medical College Bhopal'
    assert group['matched'] == 'Government Medical College Bhopal'
    course_names = {c['name'] for c in group['courses']}
    assert 'MD Medicine' in course_names
    assert 'MS Surgery' in course_names

def test_build_course_context_conflict_detection():
    # Both variants appear in Round 1 with the same course → conflict
    r1 = make_round_df([
        ['AI', 'Govt. Med Clg Bhopal', 'MD Medicine', 'Open', '100', 1, 'Madhya Pradesh'],
        ['AI', 'Government Medical College Bhopal', 'MD Medicine', 'Open', '101', 1, 'Madhya Pradesh'],
    ], 1)
    review_log = [{'original': 'Govt. Med Clg Bhopal',
                   'matched': 'Government Medical College Bhopal',
                   'score': 88.0, 'state': 'Madhya Pradesh'}]
    full_log = review_log  # only one variant in borderline, but conflict check uses full_log
    groups = build_course_context([r1], review_log, full_log)
    md_course = next(c for c in groups[0]['courses'] if c['name'] == 'MD Medicine')
    assert md_course['conflict'] is True

def test_apply_mapping_exclude_pairs():
    r1 = make_round_df([
        ['AI', 'Govt. Med Clg', 'MD Medicine', 'Open', '100', 1, 'Kerala'],
        ['AI', 'Govt. Med Clg', 'MS Surgery', 'Open', '200', 1, 'Kerala'],
    ], 1)
    mapping = {'Govt. Med Clg': 'Government Medical College'}
    # Exclude the MD Medicine course from renaming
    exclude = {('Govt. Med Clg', 'MD Medicine')}
    result = apply_mapping(r1, mapping, exclude_pairs=exclude)
    assert result.iloc[0]['Allotted Institute'] == 'Govt. Med Clg'   # excluded
    assert result.iloc[1]['Allotted Institute'] == 'Government Medical College'  # renamed
