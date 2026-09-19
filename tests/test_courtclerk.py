from scraper.courtclerk import case_summary_url, name_search_url


def test_name_search_includes_dob_when_provided():
    # Synthetic fixture identity (not a real person).
    url = name_search_url("Test", "Person", "01/01/70")
    assert url.startswith("https://www.courtclerk.org/data/crim_name_results.php?")
    assert "lname=TEST" in url
    assert "fname=PERSON" in url
    assert "dob=01%2F01%2F70" in url  # slash url-encoded


def test_name_search_omits_dob_when_blank():
    url = name_search_url("Smith", "John")
    assert "dob=" not in url


def test_case_summary_url_encodes_slashes():
    url = case_summary_url("00/CRA/19659")
    assert url == "https://www.courtclerk.org/data/case_summary.php?casenumber=00%2FCRA%2F19659"


def test_case_summary_empty_returns_empty():
    assert case_summary_url("") == ""
    assert case_summary_url("   ") == ""


def test_case_summary_with_spaces_in_case_number():
    # Some Hamilton County case numbers have spaces (e.g. "B 24 1234").
    url = case_summary_url("B 24 1234")
    assert "B%2024%201234" in url
