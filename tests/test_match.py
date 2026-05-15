from scraper.match import candidates_for
from scraper.models import Inmate


def _cfs(create_time: str, disposition: str = "ARR: ARREST", agency: str = "CPD") -> dict:
    return {
        "create_time_incident": create_time,
        "disposition_text": disposition,
        "agency": agency,
        "address_x": "1 MAIN ST",
        "cpd_neighborhood": "DOWNTOWN",
    }


def _inmate(booking_date: str) -> Inmate:
    return Inmate(inmate_number="100", booking_date=booking_date)


def test_candidates_within_window_are_returned():
    inm = _inmate("5/10/26")
    rows = [
        _cfs("2026-05-09T22:00:00"),  # 2h before midnight booking — within window
        _cfs("2026-05-10T05:00:00"),  # 5h after midnight — within window
        _cfs("2026-05-11T15:00:00"),  # +39h — outside 12h window
        _cfs("2026-05-08T00:00:00"),  # -48h — outside
    ]
    cands = candidates_for(inm, rows)
    assert len(cands) == 2


def test_non_cpd_agency_excluded():
    inm = _inmate("5/10/26")
    rows = [_cfs("2026-05-10T01:00:00", agency="CFD")]
    assert candidates_for(inm, rows) == []


def test_unparseable_booking_date_returns_empty():
    inm = _inmate("garbage")
    assert candidates_for(inm, [_cfs("2026-05-10T01:00:00")]) == []


def test_candidates_sorted_by_proximity():
    inm = _inmate("5/10/26")
    far = _cfs("2026-05-10T11:00:00")
    near = _cfs("2026-05-10T01:00:00")
    cands = candidates_for(inm, [far, near])
    assert cands[0]["create_time_incident"] == near["create_time_incident"]
