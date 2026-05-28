"""Tests for Hamilton County case-number classification (web/classify.py) and
the grouped view-model (web/shape.py _cases_grouped)."""
from __future__ import annotations

from typing import cast

import pytest

from scraper.models import Inmate
from web.classify import case_category, case_year
from web.shape import _cases_grouped


@pytest.mark.parametrize("number,category", [
    ("B 2403956", "criminal"),      # common pleas criminal
    ("B2506473", "criminal"),       # no-space common pleas
    ("C/26/CRB/9272/A", "criminal"),  # municipal misdemeanor
    ("25/CRA/12436/B", "criminal"),   # municipal criminal arraignment
    ("/26/TRD/3987", "traffic"),    # traffic
    ("C/25/TRD/29405", "traffic"),
    ("A 2401234", "civil"),         # common pleas civil
    ("C/26/CVG/1234", "civil"),     # municipal civil
    ("24/DR/555", "other"),         # domestic relations -> not mislabeled
    ("", "other"),
    (None, "other"),
])
def test_case_category(number, category):
    assert case_category(number) == category


@pytest.mark.parametrize("number,year", [
    ("B 2403956", 2024),
    ("B2506473", 2025),
    ("C/26/CRB/9272/A", 2026),
    ("25/CRA/12436/B", 2025),
    ("/26/TRD/3987", 2026),
    ("A 2401234", 2024),
    ("", None),
    (None, None),
])
def test_case_year(number, year):
    assert case_year(number) == year


class _Charge:
    def __init__(self, cp="", muni="", other=""):
        self.common_pleas_case = cp
        self.municipal_case = muni
        self.other_case = other


class _Inmate:
    def __init__(self, charges):
        self.charges = charges


def test_cases_grouped_orders_categories_and_years():
    inmate = _Inmate([
        _Charge(cp="B 2403956"),          # criminal 2024
        _Charge(muni="C/26/CRB/9272/A"),  # criminal 2026
        _Charge(muni="C/25/TRD/29405"),   # traffic 2025
        _Charge(cp="A 2601234"),          # civil 2026
    ])
    groups = _cases_grouped(cast(Inmate, inmate))
    # Category order is fixed: criminal, traffic, civil, other (present only).
    assert [g["key"] for g in groups] == ["criminal", "traffic", "civil"]

    criminal = groups[0]
    assert criminal["cases_n"] == 2
    # Years descending: 2026 before 2024.
    assert [row["year"] for row in criminal["years"]] == [2026, 2024]
    assert criminal["years"][0]["cases"] == ["C/26/CRB/9272/A"]


def test_cases_grouped_empty_when_no_cases():
    assert _cases_grouped(cast(Inmate, _Inmate([_Charge()]))) == []
