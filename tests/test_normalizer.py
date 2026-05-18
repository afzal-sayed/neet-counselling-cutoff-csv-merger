import pandas as pd
import pytest
from services.normalizer import normalize_columns, extract_state, expand_abbreviations, normalize_category, normalize_course

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

# ── State alias / variant normalisation ───────────────────────────────────

def test_alias_up_abbreviation():
    assert extract_state("Some Hospital, Lucknow, UP") == "Uttar Pradesh"

def test_alias_u_dot_p():
    assert extract_state("Some Hospital, Pratapgarh U.P") == "Uttar Pradesh"

def test_alias_westbengal_fused():
    assert extract_state("Some Hospital, Kolkata, Westbengal") == "West Bengal"

def test_alias_tamilnadu_fused():
    assert extract_state("Some Hospital, Chennai, Tamilnadu") == "Tamil Nadu"

def test_alias_tami_l_nadu_ocr():
    assert extract_state("Some Hospital, Coimbatore, Tami L Nadu") == "Tamil Nadu"

def test_alias_chennai_maps_to_tamilnadu():
    # "Chennai" appears as a state value in NEET data; it is in Tamil Nadu.
    assert extract_state("Some Hospital, Chennai") == "Tamil Nadu"

def test_alias_jk_abbreviation():
    assert extract_state("Some Hospital, Srinagar, J&K") == "Jammu And Kashmir"

def test_alias_delhi_nct():
    assert extract_state("Some Hospital, Delhi (Nct)") == "Delhi"

def test_alias_new_delhi():
    assert extract_state("Some Hospital, New Delhi") == "Delhi"

def test_alias_uttarajgand_typo():
    assert extract_state("Some Hospital, Dehradun, Uttarajgand") == "Uttarakhand"

def test_alias_telangana_state():
    assert extract_state("Some Hospital, Hyderabad, Telangana State") == "Telangana"

def test_alias_orissa_old_name():
    assert extract_state("Some Hospital, Bhubaneswar, Orissa") == "Odisha"

def test_alias_hp_abbreviation():
    assert extract_state("Some Hospital, Shimla, Hp") == "Himachal Pradesh"

# ── State embedded in free-form text ──────────────────────────────────────

def test_state_embedded_at_end_of_part():
    # "Hubballi Karnataka" — city + state fused, state at end
    name = "KLE Hospital, Hubballi Karnataka"
    assert extract_state(name) == "Karnataka"

def test_state_embedded_with_pin_and_text():
    # "Bagalkot – 587103 Karnataka" — PIN then state in same part
    name = "Some Hospital, Bagalkot – 587103 Karnataka"
    assert extract_state(name) == "Karnataka"

def test_state_embedded_in_long_address():
    # State appears at end of long free-text last part
    name = "District Hospital Campus, Jail Road Ratlam Madhya Pradesh"
    assert extract_state(name) == "Madhya Pradesh"

def test_state_embedded_jk_in_text():
    # J&K appears inside a longer descriptive string
    name = "J&K- Main Campus Dialgam, Anantnag"
    assert extract_state(name) == "Jammu And Kashmir"

def test_state_concatenated_suffix():
    # "malappuramkerala" — state name glued onto city name with no space
    name = "Hospital, Malappuramkerala"
    assert extract_state(name) == "Kerala"

def test_state_concatenated_chennai_suffix():
    # "vadapalanichennai" — city+city concatenated, Chennai → Tamil Nadu
    name = "Hospital, Vadapalanichennai"
    assert extract_state(name) == "Tamil Nadu"

def test_state_in_duplicate_trailing_blob():
    # Real pattern: structured address + duplicate free-text blob
    name = ("Accord Superspeciality Hospital, Sector 86, "
            "Village Tehsil-District Faridabad Haryana – 121002,"
            "Accord Superspeciality Hospital Khasra No.22 Sector 86")
    assert extract_state(name) == "Haryana"

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

# ── Category normalization ─────────────────────────────────────────

def test_category_obcpwd_fused():
    assert normalize_category('OBCPwD') == 'OBC PwD'

def test_category_ewspwd_fused():
    assert normalize_category('EWSPwD') == 'EWS PwD'

def test_category_scpwd_fused():
    assert normalize_category('SCPwD') == 'SC PwD'

def test_category_stpwd_fused():
    assert normalize_category('STPwD') == 'ST PwD'

def test_category_open_unchanged():
    assert normalize_category('Open') == 'Open'

def test_category_scpwd_with_space_unchanged():
    assert normalize_category('SC PwD') == 'SC PwD'

def test_category_non_string_passthrough():
    assert normalize_category(None) is None

# ── Course normalization ───────────────────────────────────────────

def test_course_anaesthesiology_ocr():
    assert normalize_course('ANAESTHESIOLOG Y') == 'ANAESTHESIOLOGY'

def test_course_venereology_split():
    assert normalize_course('VENEREOLOG Y') == 'VENEREOLOGY'

def test_course_vener_eology_split():
    assert normalize_course('VENER EOLOGY') == 'VENEREOLOGY'

def test_course_dermatology_split():
    assert normalize_course('DERMATOLOG Y') == 'DERMATOLOGY'

def test_course_radio_diagnosis_space():
    assert normalize_course('RADIO- DIAGNOSIS') == 'RADIO-DIAGNOSIS'

def test_course_oto_rhino_laryngology():
    assert normalize_course('OTO- RHINO-LARYNGOLOGY') == 'OTO-RHINO-LARYNGOLOGY'

def test_course_nbems_prefix_space():
    assert normalize_course('(NBEMS)Otorhinolaryngology') == '(NBEMS) Otorhinolaryngology'

def test_course_nbems_diploma_prefix_space():
    assert normalize_course('(NBEMS-DIPLOMA)Obstetrics') == '(NBEMS-DIPLOMA) Obstetrics'

def test_course_md_paren_space():
    assert normalize_course('M.D.(Emergency Medicine)') == 'M.D. (Emergency Medicine)'

def test_course_transfusion_medicine_fused():
    assert normalize_course('TRANSFUSIONMEDICINE') == 'TRANSFUSION MEDICINE'

def test_course_double_space_collapsed():
    assert normalize_course('COMMUNITY HEALTH  and ADMN.') == 'COMMUNITY HEALTH and ADMN.'

def test_course_leprosy_split():
    assert normalize_course('LEPROS Y') == 'LEPROSY'

def test_course_non_string_passthrough():
    assert normalize_course(None) is None

def test_course_slash_space_normalization():
    assert normalize_course('DERMATOLOGY /VENEREOLOGY') == 'DERMATOLOGY/VENEREOLOGY'
    assert normalize_course('LEPROSY/ VENEREAL DISEASE') == 'LEPROSY/VENEREAL DISEASE'
    assert normalize_course('A / B / C') == 'A/B/C'

def test_course_hyphen_space_normalization():
    assert normalize_course('OTO-RHINO- LARYNGOLOGY') == 'OTO-RHINO-LARYNGOLOGY'
    assert normalize_course('RADIO- THERAPY') == 'RADIO-THERAPY'
    assert normalize_course('IMMUNO- HAEMATOLOGY') == 'IMMUNO-HAEMATOLOGY'
