from scraper.courtclerk import case_summary_url, name_search_url, normalize_clerk_case_number


def test_name_search_includes_dob_when_provided():
    url = name_search_url("Test", "Person", "01/01/70")
    assert url.startswith("https://www.courtclerk.org/data/crim_name_results.php?")
    assert "lname=TEST" in url
    assert "fname=PERSON" in url
    assert "dob=01%2F01%2F70" in url


def test_name_search_omits_dob_when_blank():
    url = name_search_url("Smith", "John")
    assert "dob=" not in url


def test_normalize_city_municipal_keeps_leading_slash():
    assert normalize_clerk_case_number("/26/CRB/19119") == "/26/CRB/19119"
    assert normalize_clerk_case_number("26/CRA/19118") == "/26/CRA/19118"


def test_normalize_county_municipal_keeps_c_prefix():
    assert normalize_clerk_case_number("C/26/CRA/17570") == "C/26/CRA/17570"
    assert normalize_clerk_case_number("C/26/CRB/17568/A") == "C/26/CRB/17568"


def test_normalize_maps_d_category_to_trd():
    assert normalize_clerk_case_number("C/26/D/16529") == "C/26/TRD/16529"
    assert normalize_clerk_case_number("C/26/D/04398/B") == "C/26/TRD/04398"


def test_normalize_common_pleas_space_after_letter():
    assert normalize_clerk_case_number("B 2504495") == "B 2504495"
    assert normalize_clerk_case_number("B2504495") == "B 2504495"


def test_case_summary_url_uses_clerk_form():
    url = case_summary_url("/26/CRB/19119")
    assert url == "https://www.courtclerk.org/data/case_summary.php?casenumber=%2F26%2FCRB%2F19119"
    url = case_summary_url("C/26/D/16529")
    assert url == "https://www.courtclerk.org/data/case_summary.php?casenumber=C%2F26%2FTRD%2F16529"


def test_case_summary_empty_returns_empty():
    assert case_summary_url("") == ""
    assert case_summary_url("   ") == ""


def test_case_summary_with_spaces_in_case_number():
    url = case_summary_url("B 24 1234")
    assert "B%2024%201234" in url
