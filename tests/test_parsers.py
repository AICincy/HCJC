from pathlib import Path

import pytest

from scraper.parsers import parse_detail_page, parse_list_page

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_list_page_skips_rows_without_detail_link():
    rows = parse_list_page(_load("list_smith.html"))
    inmate_numbers = [r.inmate_number for r in rows]
    assert inmate_numbers == ["14502205", "14600001", "14700099"]
    assert all(r.last_name == "DOE" for r in rows)
    assert rows[0].first_name == "JOHN"
    assert rows[0].admit_date == "7/4/24"


def test_detail_page_extracts_bio_charges_and_inline_photo():
    inm, photo = parse_detail_page(_load("detail_inmate.html"), "14502205")
    assert inm.inmate_number == "14502205"
    assert inm.booking_number == "26003334"
    assert inm.last_name == "ROE"
    assert inm.first_name == "RICHARD"
    assert inm.middle_name == "ALEXANDER"
    assert inm.full_name == "ROE RICHARD ALEXANDER"
    assert inm.date_of_birth == "12/27/01"
    assert inm.sex == "M"
    assert inm.race == "U"
    assert inm.booking_date == "5/10/26"
    assert inm.projected_release_date == "NA"
    assert inm.holder_status == "No"
    assert len(inm.charges) == 2
    assert inm.charges[0].orc_code == "2903.02"
    assert inm.charges[0].description == "MURDER"
    assert inm.charges[0].bond_amount == "$2,000,000.00"
    assert inm.charges[1].municipal_case == "25CRA12345"
    assert inm.charges[1].comments == "co-defendant"
    assert photo == b"PLACEHOLDER"  # base64 "UExBQ0VIT0xERVI=" decodes to PLACEHOLDER


def test_detail_page_handles_empty_base64_photo():
    inm, photo = parse_detail_page(_load("detail_no_photo.html"), "14600000")
    assert inm.inmate_number == "14600000"
    assert inm.last_name == "DOE"
    assert inm.first_name == "JANE"
    assert photo is None


def test_list_page_accepts_path_form_detail_id():
    # parser-F4: a permalink shift from ?id= to /inmate-detail/N/ must not
    # zero the roster. _DETAIL_ID accepts both forms.
    html = """
    <table>
      <tr>
        <td label="Last Name">DOE</td>
        <td label="First Name">JOHN</td>
        <td label="Admit Date">5/10/26</td>
        <td><a href="/inmate-detail/9999999/">view</a></td>
      </tr>
    </table>
    """
    rows = parse_list_page(html)
    assert len(rows) == 1
    assert rows[0].inmate_number == "9999999"


def test_parse_name_falls_back_to_og_title(caplog):
    # parser-F1: if the LAST,FIRST heading drifts, og:title rescues the name.
    html = """
    <html>
      <head><meta property="og:title" content="ROE, RICHARD"></head>
      <body><h1>Some other heading</h1></body>
    </html>
    """
    import logging
    caplog.set_level(logging.DEBUG, logger="scraper.parsers")
    inm, _ = parse_detail_page(html, "1234567")
    assert inm.last_name == "ROE"
    assert inm.first_name == "RICHARD"
    assert any("og:title fallback" in rec.message for rec in caplog.records)


def test_parse_name_handles_inmate_label_prefix():
    # parser-F1 follow-up: HCSO added an "Inmate:" prefix to the name heading
    # on 2026-05-18. The all-uppercase check used to reject the mixed-case
    # prefix and zero out every name in the cycle. Pin both shapes here so a
    # regression to the bare-name format or to the label-prefixed format both
    # stay green.
    html_prefixed = """
    <html><body>
      <h2>Inmate: ACOSTA, ANDREW</h2>
      <ul>
        <li>Inmate Number : 14544515</li>
        <li>Booking Number : 26002866</li>
      </ul>
    </body></html>
    """
    inm, _ = parse_detail_page(html_prefixed, "14544515")
    assert inm.last_name == "ACOSTA"
    assert inm.first_name == "ANDREW"

    html_bare = """
    <html><body>
      <h2>ACOSTA, ANDREW</h2>
    </body></html>
    """
    inm, _ = parse_detail_page(html_bare, "14544515")
    assert inm.last_name == "ACOSTA"
    assert inm.first_name == "ANDREW"


def test_extract_inline_photo_jpeg_soi_fallback():
    # parser-F3: when the 274px hook drifts (e.g. 280px), JPEG SOI bytes
    # are accepted as a fallback so photos don't disappear site-wide.
    import base64
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIFsynthetic"
    encoded = base64.b64encode(jpeg_bytes).decode("ascii")
    html = f"""
    <html><body>
      <img src="data:image/png;base64,{encoded}" style="width:280px;" alt="">
    </body></html>
    """
    inm, photo = parse_detail_page(html, "5555555")
    assert photo == jpeg_bytes


def test_parse_charges_ignores_spurious_table_without_description_columns():
    # parser-F6: if HCSO adds an unrelated labeled table on the detail page
    # (e.g. a holds/warrants table), rows from that table must not leak into
    # the charges list. The scoped scan picks the table whose thead names
    # both Description and ORC Code.
    html = """
    <html><body>
      <h1>DOE, JANE</h1>
      <table>
        <thead><tr><th>Hold #</th><th>Agency</th></tr></thead>
        <tbody>
          <tr>
            <td label="Hold #">H-001</td>
            <td label="Agency">SHERIFF</td>
          </tr>
        </tbody>
      </table>
      <table>
        <thead>
          <tr>
            <th>Common Pleas Case #</th><th>ORC Code</th><th>Description</th>
            <th>Bond Type</th><th>Bond Amount</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td label="Common Pleas Case #">B2400123</td>
            <td label="ORC Code">2903.13</td>
            <td label="Description">ASSAULT</td>
            <td label="Bond Type">CASH</td>
            <td label="Bond Amount">$5,000.00</td>
          </tr>
        </tbody>
      </table>
    </body></html>
    """
    inm, _ = parse_detail_page(html, "7777777")
    # Exactly one charge - the spurious holds row contributed nothing.
    assert len(inm.charges) == 1
    assert inm.charges[0].orc_code == "2903.13"
    assert inm.charges[0].description == "ASSAULT"


def test_parse_detail_page_logs_when_no_structured_fields_found(caplog):
    # parser-F8: a detail page that returns 200 but yields zero structured
    # fields (HCSO error / interstitial page) must produce a discoverable
    # per-id INFO log so the operator can find the affected ids.
    import logging
    caplog.set_level(logging.INFO, logger="scraper.parsers")
    inm, photo = parse_detail_page(
        "<html><body><p>Service unavailable</p></body></html>",
        "8888888",
    )
    assert inm.last_name == ""
    assert inm.first_name == ""
    assert inm.charges == []
    assert photo is None
    assert any(
        "no structured fields" in r.message and "8888888" in r.message
        for r in caplog.records
    )
