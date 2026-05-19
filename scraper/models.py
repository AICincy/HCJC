"""Pydantic data models for JCStream records."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Permitted shape for generated_utc on a populated snapshot. Empty is allowed
# at bootstrap time (web/build.py constructs an empty Snapshot when no data
# file exists yet); a real, written snapshot must use utcnow_iso().
_GENERATED_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class Charge(BaseModel):
    common_pleas_case: str = ""
    municipal_case: str = ""
    other_case: str = ""
    court_date: str = ""
    orc_code: str = ""
    description: str = ""
    bond_type: str = ""
    bond_amount: str = ""
    disposition: str = ""
    comments: str = ""


class Inmate(BaseModel):
    """A single currently-in-custody person, as published by HCSO."""

    inmate_number: str
    booking_number: str = ""

    @field_validator("inmate_number")
    @classmethod
    def _inmate_number_shape(cls, v: str) -> str:
        # HCSO inmate numbers are 7-8 digits; both list-side regex (\d+) and
        # the live data agree. Enforce digits-only at the model layer so a
        # parser-drift edge case (e.g. bio table override at parsers.py:77)
        # cannot leak `..` or `/` into photo_filename and template URLs.
        stripped = (v or "").strip()
        if not stripped:
            raise ValueError("inmate_number must be non-empty")
        if not stripped.isdigit():
            raise ValueError(
                f"inmate_number must be digits, got {stripped!r}"
            )
        return stripped
    last_name: str = ""
    first_name: str = ""
    middle_name: str = ""
    date_of_birth: str = ""
    sex: str = ""
    race: str = ""
    booking_date: str = ""
    projected_release_date: str = ""
    holder_status: str = ""
    charges: list[Charge] = Field(default_factory=list)
    photo_filename: Optional[str] = None
    first_seen_utc: str = ""
    last_seen_utc: str = ""

    @property
    def full_name(self) -> str:
        # Per-part cap defends against a parser-drift edge case where an entire
        # detail page bleeds into the heading; downstream renderers and OG
        # tags shouldn't have to think about pathological strings.
        parts = [p[:80] for p in (self.last_name, self.first_name, self.middle_name) if p]
        return " ".join(parts).strip()[:256]


class ListRow(BaseModel):
    """A single row returned by the surname search list page."""

    inmate_number: str
    last_name: str
    first_name: str
    admit_date: str


class ChangeEvent(BaseModel):
    """A change event written to the changelog."""

    event: str  # "booked" | "released" | "updated"
    inmate_number: str
    name: str
    timestamp_utc: str
    note: str = ""


class Snapshot(BaseModel):
    """Top-level container committed to data/current.json."""

    # Bumped only when current.json adds required fields or otherwise becomes
    # incompatible with an older reader. Existing files without this key load
    # as version 1 (Pydantic supplies the default), so adding it is a no-op
    # data migration. Sweep refuses to bootstrap from a file whose
    # schema_version is greater than the reader knows.
    schema_version: int = 1
    generated_utc: str
    inmate_count: int
    inmates: list[Inmate]

    @field_validator("generated_utc")
    @classmethod
    def _generated_utc_shape(cls, v: str) -> str:
        # Empty string is intentional at bootstrap (web/build.py builds an
        # empty Snapshot when no data file exists yet). For populated
        # snapshots, accept only the strict utcnow_iso() shape so a
        # hand-edited or NTP-skewed file is caught on load instead of
        # breaking downstream sort and compare logic.
        if v == "":
            return v
        if not _GENERATED_UTC_RE.match(v):
            raise ValueError(
                f"generated_utc must be empty or YYYY-MM-DDTHH:MM:SSZ, got {v!r}"
            )
        return v

    @model_validator(mode="after")
    def _check_snapshot_invariants(self) -> "Snapshot":
        # Enforce the count/list invariant on both write and read. This costs
        # nothing on healthy files and catches a hand-edited or merged file
        # before web/build.py renders incorrect totals.
        if self.inmate_count != len(self.inmates):
            raise ValueError(
                f"inmate_count={self.inmate_count} != len(inmates)={len(self.inmates)}"
            )
        ids = [i.inmate_number for i in self.inmates]
        if len(set(ids)) != len(ids):
            # Find the duplicate(s) for a useful error message.
            seen: set[str] = set()
            dupes: set[str] = set()
            for iid in ids:
                if iid in seen:
                    dupes.add(iid)
                seen.add(iid)
            raise ValueError(
                f"duplicate inmate_number in snapshot: {sorted(dupes)}"
            )
        return self


# Maximum schema_version this build knows how to read. Bump in lockstep with
# any schema_version increment on Snapshot. A file at a higher version makes
# sweep refuse the cycle (keeps last-good intact).
SNAPSHOT_SCHEMA_VERSION = 1


class HistoryRecord(BaseModel):
    """One daily record in ``data/history.json``.

    Counts only - no individuals are archived. Written by web/build.py once
    per build day (the latest record for `date` is replaced in place).
    """

    date: str       # YYYY-MM-DD, UTC
    count: int      # roster size at write time
    booked_24h: int = 0
    released_24h: int = 0

    @field_validator("date")
    @classmethod
    def _date_shape(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v or ""):
            raise ValueError(f"date must be YYYY-MM-DD, got {v!r}")
        return v


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
