#!/usr/bin/env python3
"""Deploy the anon-changelog enrichment fix, repair what is repairable, verify.

Run from the repository root::

    python deploy_fix.py --plan     # measure + decide, change nothing
    python deploy_fix.py            # measure, repair, commit, verify
    python deploy_fix.py --help

Exit codes
    0  success (repair applied and verified, or nothing left to do)
    1  halted before any change was made (precondition failed)
    2  verification failed; changes rolled back

WHAT THIS ACTUALLY DOES, AND WHAT IT CANNOT DO
----------------------------------------------
``_save_changelog_and_anon`` used to build the anon-feed enrichment from the
*current* roster alone, looking up *raw* ORC codes. Two consequences:

  * a ``released`` event is about someone no longer on the roster, so released
    rows were always written with ``tier=None``;
  * booking rows carry subsection codes (``2925.11A``) while
    ``data/orc_offenses.json`` is keyed by base section (``2925.11``), so the
    lookup missed 42% of the roster.

Measured against the live data on 2026-09-24 (1,312 null rows total):

    in retention window, PII intact     1,889 rows   (974 null)
      ├─ inmate still on roster           539 null   → 503 repairable
      └─ inmate gone (350 released)       435 null   → NOT repairable
    already expired, PII stripped       6,028 rows   (338 null) → NOT repairable

So the honest ceiling is ~503 of 974 in-window nulls (≈52%), not the ">90%"
an earlier draft of this runbook claimed. The 435 + 338 rows have no surviving
source for their charges:

  * ``data/anon_changelog.json`` rows past ``ANON_EXPIRY_DAYS`` have had
    ``inmate_number`` stripped, so they cannot be joined to anything;
  * ``data/changelog.json`` keeps ``inmate_number`` but the ``ChangeEvent``
    model carries no charges -- only event/inmate_number/name/timestamp/note;
  * this repository has a single squashed commit, so there is no historical
    roster revision to mine. ``git log --follow -p data/anon_changelog.json``
    *does* contain 1,889 ``inmate_number`` hits, but every one is from the
    current working state, not a prior revision. Probing git history for
    recovery material therefore produces a false positive here.

Gate 1 below probes the real sources instead and reports the split it finds.

The repair only ever fills ``tier``/``category`` on rows that are *already*
inside the retention window and *already* carry PII. It never re-identifies an
expired row, never adds a row, never removes one. V2 asserts exactly that.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
ANON_PATH = REPO_ROOT / "data" / "anon_changelog.json"
CURRENT_PATH = REPO_ROOT / "data" / "current.json"
OFFENSES_PATH = REPO_ROOT / "data" / "orc_offenses.json"
CHANGELOG_PATH = REPO_ROOT / "data" / "changelog.json"

DEPLOY_LOG = REPO_ROOT / ".deployment.log"
INCIDENT_FILE = REPO_ROOT / ".incident_summary.json"

# Files this script is allowed to commit. Anything else in the diff is a bug.
# The runbook set is included so the artifacts travel with the fix they
# document; deploy_fix.py stages exactly these paths and V5 asserts the
# resulting commit contains nothing outside the set.
FIX_TARGETS = (
    "scraper/sweep.py",
    "tests/test_sweep.py",
    "data/anon_changelog.json",
    # Ignores this script's own run artifacts (.deployment.log is already
    # covered by *.log; .incident_summary.json is not).
    ".gitignore",
)
RUNBOOK_FILES = (
    "deploy_fix.py",
    "README_DEPLOY.md",
    "DEPLOYMENT_FLOW.md",
    "DEPLOYMENT_SPEC.md",
    "DEPLOYMENT_OVERVIEW.md",
)
EXPECTED_COMMIT_FILES = set(FIX_TARGETS) | set(RUNBOOK_FILES)

# Untracked/modified paths that are expected to be dirty and are not a reason
# to halt. ``*.log`` and ``.venv/`` are already gitignored; these are the
# ones that are not.
KNOWN_ARTIFACTS = {
    ".deployment.log",
    ".incident_summary.json",
    ".mcp.json",
    "deploy_fix.py",
    "README_DEPLOY.md",
    "DEPLOYMENT_FLOW.md",
    "DEPLOYMENT_SPEC.md",
    "DEPLOYMENT_OVERVIEW.md",
}

ANON_EXPIRY_DAYS = 7  # mirrors scraper.store.ANON_EXPIRY_DAYS

EXIT_OK = 0
EXIT_HALT = 1
EXIT_FAILED = 2


# --------------------------------------------------------------------------- #
# audit log
# --------------------------------------------------------------------------- #


class AuditLog:
    """Append-only JSON event log, flushed after every event.

    Written as a JSON array so ``jq '.[]'`` works on it mid-run. Each event
    carries a UTC timestamp and a ``type`` of decision | action | verification
    | outcome. Flush-per-event means a crash still leaves a usable trail.
    """

    def __init__(self, path: Path, enabled: bool = True) -> None:
        self.path = path
        self.enabled = enabled
        self.events: list[dict[str, Any]] = []

    def _emit(self, event: dict[str, Any]) -> None:
        event = {"timestamp": _now_iso(), **event}
        self.events.append(event)
        if not self.enabled:
            return
        try:
            _atomic_write_text(self.path, json.dumps(self.events, indent=2) + "\n")
        except OSError as e:  # never let logging kill a deployment
            print(f"  ! could not write {self.path.name}: {e}", file=sys.stderr)

    def decision(self, gate: str, choice: str, reason: str, **extra: Any) -> None:
        self._emit({"type": "decision", "gate": gate, "choice": choice, "reason": reason, **extra})

    def action(self, stage: str, status: str, **extra: Any) -> None:
        self._emit({"type": "action", "stage": stage, "status": status, **extra})

    def verification(self, check: str, passed: bool, detail: str, **extra: Any) -> None:
        self._emit({"type": "verification", "check": check, "passed": passed, "detail": detail, **extra})

    def outcome(self, status: str, exit_code: int, **extra: Any) -> None:
        self._emit({"type": "outcome", "status": status, "exit_code": exit_code, **extra})


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write_text(path: Path, content: str) -> None:
    """Same tmp-file + os.replace contract as scraper.store._atomic_write_text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# environment
# --------------------------------------------------------------------------- #


def find_python() -> str:
    """A Python interpreter that can actually import pytest.

    pytest is a ``[project.optional-dependencies] dev`` extra, so it is absent
    from a plain runtime install. An earlier draft of this runbook assumed
    ``python -m pytest`` always works; on a fresh checkout it fails with
    "No module named pytest", which -- under auto-rollback -- would have
    reverted a correct fix. Probe candidates instead of assuming.
    """
    candidates = [
        os.environ.get("JCSTREAM_PYTEST_PYTHON", ""),
        str(REPO_ROOT / ".venv" / "bin" / "python"),
        str(REPO_ROOT / ".venv" / "Scripts" / "python.exe"),
        sys.executable,
        "python3",
        "python",
    ]
    for cand in candidates:
        if not cand:
            continue
        exe = cand if os.path.isabs(cand) else shutil.which(cand)
        if not exe or not Path(exe).exists():
            continue
        try:
            probe = subprocess.run(
                [exe, "-c", "import pytest, sys; sys.stdout.write(pytest.__version__)"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0:
            return exe
    return ""


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=check,
    )


# --------------------------------------------------------------------------- #
# measurement
# --------------------------------------------------------------------------- #


def classify_row(
    row: Any,
    by_number: dict[str, Any],
    offenses: dict[str, Any],
    normalize_code: Any,
    degree_order: tuple[str, ...],
    cutoff: str,
) -> tuple[str, dict[str, Any] | None]:
    """Classify one anon-feed row and, when repairable, return its new tags.

    ``measure_damage`` and ``repair_anon_changelog`` both route through this so
    the reported ceiling and the applied repair cannot drift apart. Two
    predicates that look equivalent but are not will disagree on real data --
    an earlier split here miscounted by 12 rows because some rows carry an
    ``inmate_number`` but no ``timestamp_utc``, so they are neither inside the
    retention window (no timestamp to test) nor fully anonymized (PII still
    present). Those land in ``pii_without_timestamp`` and are reported, never
    silently dropped or written to.

    Returns ``(bucket, tags)`` where bucket is one of:
      tagged                    already has a tier; nothing to do
      repairable                in window, on roster, resolves to real tags
      unresolvable_off_roster   in window, but inmate gone or charge unknown
      expired_null              anonymized (date-only) and null; permanent
      pii_without_timestamp     anomalous: PII present, no timestamp to test
      other                     not a dict, or neither null nor recognizable
    """
    if not isinstance(row, dict):
        return "other", None
    ts = str(row.get("timestamp_utc") or "")
    number = str(row.get("inmate_number") or "")
    is_null = not row.get("tier") or not row.get("category")

    if not is_null:
        return "tagged", None
    if not number:
        # PII already stripped: nothing to join against, permanently null.
        return "expired_null", None
    if not ts:
        return "pii_without_timestamp", None
    if ts < cutoff:
        # Crossed the expiry boundary; treat as anonymized and leave it alone.
        return "expired_null", None

    inmate = by_number.get(number)
    if not isinstance(inmate, dict):
        return "unresolvable_off_roster", None
    charges = inmate.get("charges") or []
    first = charges[0] if charges and isinstance(charges[0], dict) else {}
    code = str(first.get("orc_code") or "").strip()
    entry = offenses.get(normalize_code(code)) if code else None
    if not isinstance(entry, dict):
        return "unresolvable_off_roster", None
    degree = entry.get("degree")
    tier = degree if degree in degree_order else None
    category = entry.get("title") or None
    if not tier and not category:
        return "unresolvable_off_roster", None
    return "repairable", {"tier": tier, "category": category}


def _repair_context() -> tuple[dict[str, Any], dict[str, Any], Any, tuple[str, ...]]:
    """Load the roster + offense table and the normalization helper once."""
    snapshot = _load_json(CURRENT_PATH)
    roster = snapshot.get("inmates") if isinstance(snapshot, dict) else None
    by_number = {
        str(m.get("inmate_number")): m for m in (roster or []) if isinstance(m, dict)
    }
    offenses_raw = _load_json(OFFENSES_PATH)
    table = offenses_raw.get("offenses") if isinstance(offenses_raw, dict) else None
    offenses = table if isinstance(table, dict) else {}

    sys.path.insert(0, str(REPO_ROOT))
    from scraper.orc import DEGREE_ORDER, normalize_code

    return by_number, offenses, normalize_code, DEGREE_ORDER


@dataclass
class Damage:
    """What is null in the anon feed, and how much of it can still be saved."""

    total_rows: int = 0
    null_rows: int = 0
    in_window: int = 0
    in_window_null: int = 0
    expired_null: int = 0
    repairable: int = 0
    unrepairable_offroster: int = 0
    released_null: int = 0
    pii_without_timestamp: int = 0
    roster_size: int = 0
    raw_code_hit_rate: float = 0.0
    normalized_code_hit_rate: float = 0.0
    codes_differing: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def repair_fraction(self) -> float:
        return (self.repairable / self.in_window_null) if self.in_window_null else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "null_rows": self.null_rows,
            "in_window_rows": self.in_window,
            "in_window_null": self.in_window_null,
            "expired_null_permanent": self.expired_null,
            "repairable_now": self.repairable,
            "unrepairable_off_roster": self.unrepairable_offroster,
            "pii_without_timestamp": self.pii_without_timestamp,
            "released_null_rows": self.released_null,
            "roster_size": self.roster_size,
            "max_recovery_fraction_of_in_window_nulls": round(self.repair_fraction, 4),
            "raw_code_lookup_hit_rate": round(self.raw_code_hit_rate, 4),
            "normalized_code_lookup_hit_rate": round(self.normalized_code_hit_rate, 4),
            "codes_needing_normalization": self.codes_differing,
            "notes": self.notes,
        }


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None


def _cutoff(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return (now - timedelta(days=ANON_EXPIRY_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")


def measure_damage() -> Damage:
    """Probe the real sources: the anon feed, the live roster, the offense table.

    Deliberately does not consult git history. See the module docstring for
    why a git-history probe is a false positive on this repository.
    """
    d = Damage()
    anon = _load_json(ANON_PATH)
    if not isinstance(anon, list):
        d.notes.append(f"{ANON_PATH.name} missing or unreadable; nothing to measure")
        return d

    try:
        by_number, offenses, normalize_code, degree_order = _repair_context()
    except ImportError:
        d.notes.append("could not import scraper.orc; measurement needs the repo importable")
        return d
    d.roster_size = len(by_number)

    # Fault 2 magnitude, measured on the live roster's primary charge.
    hits_raw = hits_norm = differing = total_codes = 0
    for m in by_number.values():
        charges = m.get("charges") or []
        first = charges[0] if charges and isinstance(charges[0], dict) else {}
        code = str(first.get("orc_code") or "").strip()
        if not code:
            continue
        total_codes += 1
        if code in offenses:
            hits_raw += 1
        norm = normalize_code(code)
        if norm and norm in offenses:
            hits_norm += 1
        if norm != code:
            differing += 1
    if total_codes:
        d.raw_code_hit_rate = hits_raw / total_codes
        d.normalized_code_hit_rate = hits_norm / total_codes
        d.codes_differing = differing

    cutoff = _cutoff()
    for row in anon:
        if not isinstance(row, dict):
            continue
        d.total_rows += 1
        if not row.get("tier") or not row.get("category"):
            d.null_rows += 1
        if row.get("timestamp_utc"):
            d.in_window += 1

        bucket, _tags = classify_row(
            row, by_number, offenses, normalize_code, degree_order, cutoff
        )
        if bucket == "repairable":
            d.repairable += 1
            d.in_window_null += 1
            if row.get("event") == "released":
                d.released_null += 1
        elif bucket == "unresolvable_off_roster":
            d.unrepairable_offroster += 1
            d.in_window_null += 1
            if row.get("event") == "released":
                d.released_null += 1
        elif bucket == "expired_null":
            d.expired_null += 1
        elif bucket == "pii_without_timestamp":
            d.pii_without_timestamp += 1

    if d.pii_without_timestamp:
        d.notes.append(
            f"{d.pii_without_timestamp} rows carry inmate_number but no timestamp_utc: "
            "not inside the retention window (no timestamp to test) and not fully "
            "anonymized (PII present). Left untouched by the repair and counted "
            "separately so the ceiling is not overstated."
        )
    return d


# --------------------------------------------------------------------------- #
# gates
# --------------------------------------------------------------------------- #


def gate_1_recovery_decision(d: Damage) -> tuple[str, str]:
    """Decide between repairing and accepting the loss.

    Returns ``(choice, reason)`` where choice is ``repair`` or
    ``accept_losses``. The decision is driven by whether a source for the
    missing charges survives -- the live roster -- not by git history.
    """
    if d.total_rows == 0:
        return "accept_losses", "anon changelog is empty or unreadable; nothing to repair"
    if d.in_window_null == 0:
        return "accept_losses", "no null rows inside the retention window; nothing left to repair"
    if d.repairable == 0:
        return (
            "accept_losses",
            f"all {d.in_window_null} in-window nulls belong to inmates no longer on the "
            "roster and no historical roster survives; the charges are unrecoverable",
        )
    return (
        "repair",
        f"{d.repairable} of {d.in_window_null} in-window null rows are resolvable from the "
        f"live roster ({d.repair_fraction:.0%} ceiling); "
        f"{d.unrepairable_offroster} in-window + {d.expired_null} expired rows are not",
    )


def gate_2_worktree(log: AuditLog) -> tuple[bool, list[str]]:
    """Refuse to run against a tree with unrelated pending changes.

    Auto-rollback uses ``git reset --hard``, which destroys uncommitted work.
    That is only safe if this gate has confirmed there is none. Files this
    script owns (its own docs, logs, and the fix targets) are expected and
    excluded; ``.mcp.json`` is excluded for compatibility with the original
    runbook, though it does not exist in this repository and is not
    gitignored -- excluding it is harmless rather than load-bearing.
    """
    tracked_modified = _git("diff", "--name-only").stdout.split()
    staged = _git("diff", "--cached", "--name-only").stdout.split()
    untracked = _git(
        "ls-files", "--others", "--exclude-standard"
    ).stdout.split()

    offenders = sorted(
        {p for p in (*tracked_modified, *staged, *untracked) if p not in KNOWN_ARTIFACTS}
        - set(EXPECTED_COMMIT_FILES)
    )
    if offenders:
        log.action("gate_2_worktree", "fail", offenders=offenders)
        return False, offenders
    log.action(
        "gate_2_worktree",
        "ok",
        tracked_modified=tracked_modified,
        staged=staged,
        untracked_excluded=sorted(set(untracked) & KNOWN_ARTIFACTS),
    )
    return True, []


# --------------------------------------------------------------------------- #
# repair
# --------------------------------------------------------------------------- #


def backup(path: Path) -> Path | None:
    """Copy a data file to a temp location outside the repo, for rollback."""
    if not path.exists():
        return None
    fd, tmp = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".bak")
    os.close(fd)
    shutil.copy2(path, tmp)
    return Path(tmp)


def repair_anon_changelog(log: AuditLog, dry: bool = False) -> dict[str, Any]:
    """Fill tier/category on in-window rows whose inmate is still on the roster.

    Deliberately narrow. It touches only rows that (a) still carry
    ``timestamp_utc``, i.e. are inside the retention window, and (b) still
    carry an ``inmate_number``, i.e. already hold PII by design. Expired rows
    are skipped unconditionally so the repair can never re-identify anyone.

    Idempotent: a second run finds no nulls left to fill and reports
    ``repaired: 0``.
    """
    anon = _load_json(ANON_PATH)
    if not isinstance(anon, list):
        return {"error": f"{ANON_PATH.name} missing or unreadable; refusing to write"}

    by_number, offenses, normalize_code, degree_order = _repair_context()

    before_nulls = sum(1 for r in anon if isinstance(r, dict) and not r.get("tier"))
    before_rows = len(anon)
    before_pii = sum(1 for r in anon if isinstance(r, dict) and r.get("inmate_number"))

    repaired = 0
    skipped_expired = 0
    skipped_anomalous = 0
    unresolvable = 0
    # Rows holding PII with no timestamp to test retention against. Counted
    # before the write so V2 can assert the repair leaves the population alone.
    before_anomalous = sum(
        1
        for r in anon
        if isinstance(r, dict) and not r.get("timestamp_utc") and r.get("inmate_number")
    )
    cutoff = _cutoff()
    for row in anon:
        bucket, tags = classify_row(
            row, by_number, offenses, normalize_code, degree_order, cutoff
        )
        if bucket == "repairable" and tags:
            if not dry:
                row["tier"] = tags["tier"]
                row["category"] = tags["category"]
            repaired += 1
        elif bucket == "unresolvable_off_roster":
            unresolvable += 1
        elif bucket == "expired_null":
            skipped_expired += 1
        elif bucket == "pii_without_timestamp":
            # Never written to: without a timestamp we cannot prove the row is
            # still inside the retention window, so filling it could extend PII
            # retention. Reported instead.
            skipped_anomalous += 1

    result = {
        "repaired": repaired,
        "before_rows": before_rows,
        "before_nulls": before_nulls,
        "before_pii_rows": before_pii,
        "skipped_expired_or_anonymized": skipped_expired,
        "skipped_pii_without_timestamp": skipped_anomalous,
        "before_anomalous_rows": before_anomalous,
        "unresolvable_in_window": unresolvable,
        "dry_run": dry,
    }

    if dry:
        # Nothing is written, so the "after" figures equal the "before" ones.
        # Populate them anyway: V1/V2 read these keys on both paths, and an
        # accept_losses run still has to prove the file was left untouched.
        result["after_rows"] = before_rows
        result["after_nulls"] = before_nulls
        result["after_pii_rows"] = before_pii
        result["after_anomalous_rows"] = before_anomalous
        log.action("repair_anon_changelog", "planned", **result)
        return result

    _atomic_write_text(ANON_PATH, json.dumps(anon, indent=2))

    after = _load_json(ANON_PATH) or []
    result["after_rows"] = len(after)
    result["after_nulls"] = sum(1 for r in after if isinstance(r, dict) and not r.get("tier"))
    result["after_pii_rows"] = sum(1 for r in after if isinstance(r, dict) and r.get("inmate_number"))
    result["after_anomalous_rows"] = sum(
        1
        for r in after
        if isinstance(r, dict) and not r.get("timestamp_utc") and r.get("inmate_number")
    )
    log.action("repair_anon_changelog", "ok", **result)
    return result


def write_incident_summary(d: Damage, repair: dict[str, Any], head: str) -> None:
    """Record the permanent portion of the damage for downstream consumers."""
    permanent = d.unrepairable_offroster + d.expired_null
    summary = {
        "date": _now_iso(),
        "bug_id": "tier_category_null_corruption",
        "root_causes": [
            "enrichment built from the current roster only; released inmates are never on it",
            "raw ORC subsection codes looked up against a base-section-keyed offense table",
        ],
        "fix_commit": head,
        "damage": d.as_dict(),
        "recovery": {
            "attempted": d.repairable > 0,
            "rows_repaired": repair.get("repaired", 0),
            "rows_permanently_lost": permanent,
            "recovery_ceiling_fraction": round(d.repair_fraction, 4),
            "why_not_more": (
                "expired rows have inmate_number stripped and cannot be joined; "
                "in-window rows for released inmates have no surviving charge source; "
                "changelog.json keeps inmate_number but ChangeEvent carries no charges; "
                "the repository has one squashed commit, so no historical roster exists"
            ),
        },
        "next_steps": [
            "notify data consumers that tier/category is null on the rows above",
            "confirm the first post-deploy live sweep tags released events",
            "do not re-run the repair expecting further recovery; it is at its ceiling",
        ],
    }
    _atomic_write_text(INCIDENT_FILE, json.dumps(summary, indent=2) + "\n")


# --------------------------------------------------------------------------- #
# verification
# --------------------------------------------------------------------------- #


def v1_null_audit(d: Damage, repair: dict[str, Any], log: AuditLog) -> bool:
    """Null count must have fallen by exactly the number of rows repaired."""
    after = _load_json(ANON_PATH)
    if not isinstance(after, list):
        log.verification("v1_null_audit", False, "anon changelog unreadable after repair")
        return False
    nulls_now = sum(1 for r in after if isinstance(r, dict) and not r.get("tier"))
    expected = repair["before_nulls"] - repair["repaired"]
    passed = nulls_now == expected
    log.verification(
        "v1_null_audit",
        passed,
        f"nulls {repair['before_nulls']} -> {nulls_now} (expected {expected}); "
        f"{repair['repaired']} repaired, {d.unrepairable_offroster} in-window and "
        f"{d.expired_null} expired rows remain null permanently",
        before=repair["before_nulls"],
        after=nulls_now,
        expected=expected,
        repaired=repair["repaired"],
        permanently_null=nulls_now,
    )
    return passed


def v2_privacy_invariant(repair: dict[str, Any], log: AuditLog) -> bool:
    """The repair must not change the file's shape or its PII surface.

    An earlier draft made V2 a "sweep dry-run showing no new nulls". That
    check was vacuous twice over: ``_save_changelog_and_anon`` is guarded by
    ``if not dry_run and roster_ok``, so a dry run cannot write nulls at all;
    and it needs a live HCSO roster, which is unavailable offline. This
    replaces it with something that actually constrains the repair.
    """
    after = _load_json(ANON_PATH)
    if not isinstance(after, list):
        log.verification("v2_privacy_invariant", False, "anon changelog unreadable after repair")
        return False

    after_anomalous = sum(
        1
        for row in after
        if isinstance(row, dict) and not row.get("timestamp_utc") and row.get("inmate_number")
    )

    checks = {
        "row_count_unchanged": len(after) == repair["before_rows"],
        "pii_row_count_unchanged": repair.get("after_pii_rows") == repair["before_pii_rows"],
        "no_new_pii_rows": (repair.get("after_pii_rows") or 0) <= repair["before_pii_rows"],
        # Rows carrying inmate_number with no timestamp_utc predate this fix
        # (there are 12 in the live file). The invariant is that the repair
        # leaves that population alone in both directions: it must not
        # re-identify an anonymized row, nor strip or add PII anywhere.
        "anomalous_population_unchanged": after_anomalous
        == repair.get("before_anomalous_rows", after_anomalous),
    }

    passed = all(checks.values())
    log.verification(
        "v2_privacy_invariant",
        passed,
        "row count and PII surface unchanged; no anonymized row re-identified"
        if passed
        else f"invariant violated: {checks}",
        after_anomalous_rows=after_anomalous,
        **checks,
    )
    return passed


def v3_regression_tests(py: str, log: AuditLog) -> bool:
    """Run the enrichment regression tests offline, with a real interpreter."""
    if not py:
        log.verification(
            "v3_regression_tests",
            False,
            "no interpreter with pytest found. pytest is a dev extra: run "
            "`python -m venv .venv && .venv/bin/pip install -r requirements.txt`, "
            "or point JCSTREAM_PYTEST_PYTHON at one",
        )
        return False
    cmd = [
        py,
        "-m",
        "pytest",
        "-q",
        "-k",
        "anon_enrichment or released_inmate_row",
        "tests/test_sweep.py",
    ]
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as e:
        log.verification("v3_regression_tests", False, f"could not run pytest: {e}", cmd=cmd)
        return False
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-1:] or [""]
    passed = proc.returncode == 0
    log.verification(
        "v3_regression_tests",
        passed,
        tail[0].strip(),
        cmd=" ".join(cmd),
        returncode=proc.returncode,
    )
    return passed


def v4_full_suite(py: str, log: AuditLog) -> bool:
    """The whole suite must stay green: the fix touches a shared code path."""
    if not py:
        log.verification("v4_full_suite", False, "skipped: no interpreter with pytest")
        return False
    try:
        proc = subprocess.run(
            [py, "-m", "pytest", "-q"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=1800,
        )
    except (OSError, subprocess.SubprocessError) as e:
        log.verification("v4_full_suite", False, f"could not run pytest: {e}")
        return False
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-1:] or [""]
    passed = proc.returncode == 0
    log.verification("v4_full_suite", passed, tail[0].strip(), returncode=proc.returncode)
    return passed


def v5_commit_contents(log: AuditLog, before_head: str) -> bool:
    """The commit must contain exactly the intended files and nothing else."""
    files = _git("diff", "--name-only", before_head, "HEAD").stdout.split()
    unexpected = sorted(set(files) - EXPECTED_COMMIT_FILES)
    passed = bool(files) and not unexpected
    log.verification(
        "v5_commit_contents",
        passed,
        f"committed {files}" if passed else f"unexpected files in commit: {unexpected or '(none)'}",
        files=files,
        unexpected=unexpected,
    )
    return passed


# --------------------------------------------------------------------------- #
# rollback
# --------------------------------------------------------------------------- #


def rollback(log: AuditLog, before_head: str, data_backup: Path | None, allow: bool) -> None:
    if not allow:
        log.action("rollback", "skipped", reason="--no-rollback given; changes left in place")
        print("\n  rollback disabled by --no-rollback; inspect and clean up manually")
        return
    try:
        if data_backup and data_backup.exists():
            shutil.copy2(data_backup, ANON_PATH)
            log.action("rollback_restore_data", "ok", file=ANON_PATH.name)
        head_now = _git("rev-parse", "HEAD").stdout.strip()
        if head_now != before_head:
            # Safe because gate 2 proved there was no uncommitted work to lose.
            _git("reset", "--hard", before_head)
            log.action("rollback_reset", "ok", to=before_head, from_=head_now)
        print(f"  rolled back to {before_head[:12]}")
    except (subprocess.CalledProcessError, OSError) as e:
        log.action("rollback", "failed", error=str(e))
        print(f"  ! ROLLBACK FAILED: {e}\n    restore manually from {data_backup}", file=sys.stderr)


# --------------------------------------------------------------------------- #
# orchestration
# --------------------------------------------------------------------------- #


def commit_fix(log: AuditLog, message: str) -> str:
    """Stage exactly the fix targets plus the runbook set, then commit.

    Paths are staged explicitly rather than with ``git add -A`` so an
    unexpected artifact can never ride along; V5 re-checks the resulting diff.
    A path with no changes stages as a no-op, so a re-run after a successful
    deployment finds nothing staged and returns HEAD without creating an empty
    commit -- that is what makes the script idempotent.
    """
    for path in (*FIX_TARGETS, *RUNBOOK_FILES):
        _git("add", "--", path, check=False)
    staged = _git("diff", "--cached", "--name-only").stdout.split()
    if not staged:
        log.action("commit", "skipped", reason="nothing staged; fix already committed")
        return _git("rev-parse", "HEAD").stdout.strip()
    unexpected = sorted(set(staged) - EXPECTED_COMMIT_FILES)
    if unexpected:
        # Unstage rather than commit something we did not intend to ship.
        for path in unexpected:
            _git("restore", "--staged", "--", path, check=False)
        log.action("commit", "refused", unexpected_staged=unexpected)
        raise RuntimeError(f"refusing to commit unexpected paths: {unexpected}")
    _git("commit", "-m", message)
    head = _git("rev-parse", "HEAD").stdout.strip()
    log.action("commit", "ok", commit_sha=head, files=staged)
    return head


COMMIT_MESSAGE = """Fix anon-feed enrichment: tag released inmates, normalize ORC codes

_save_changelog_and_anon built its tier/category enrichment from the current
roster alone, looking up raw ORC codes. Two independent faults, one symptom:
null aggregate signal on the public long-term feed.

1. Released inmates were never tagged. A `released` event is by definition
   about someone no longer on the roster, so iterating `current` guaranteed a
   miss. On live data every one of the 970 released rows was null and not one
   tagged row was a release. The enrichment now merges `previous` and
   `current`, with `current` winning as the fresher record.

2. Subsection codes never matched. Booking rows carry codes like 2925.11A and
   2903.02A1; data/orc_offenses.json is keyed by base section. The raw lookup
   resolved 58.0% of the roster against 98.8% for normalize_code, which every
   other consumer of that table already uses. 487 of 1,160 primary codes
   needed normalizing.

Also: a missing degree is now None rather than orc's "?" placeholder, so
downstream aggregates don't count a sentinel as a severity bucket, and a
malformed offenses file degrades to empty tags instead of raising inside the
sweep's finally block.

Logic extracted to _anon_enrichment(previous, current, offenses_path) so it is
testable in isolation. Six regression tests added; all six fail against the
prior implementation and pass against this one.

Repairable rows in data/anon_changelog.json were backfilled in the same
commit: 503 of 974 in-window nulls (52%). The remaining 435 in-window nulls
belong to inmates already off the roster and the 338 expired nulls have had
inmate_number stripped, so neither can be joined to a charge source; both are
recorded in the incident summary rather than silently dropped. The backfill
only fills tier/category on rows already inside the retention window and
already carrying PII -- no expired row was re-identified and the row count is
unchanged.

Also adds the deployment runbook (deploy_fix.py and the four DEPLOYMENT/README
documents) so the measurement, the recovery ceiling, and the reasoning behind
the gates are reproducible rather than tribal knowledge.
"""


def run(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Deploy and verify the anon-changelog enrichment fix.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="exit codes: 0 success, 1 halted before any change, 2 verification failed (rolled back)",
    )
    ap.add_argument("--plan", action="store_true", help="measure and decide; change nothing")
    ap.add_argument("--no-commit", action="store_true", help="repair data but do not commit")
    ap.add_argument("--no-rollback", action="store_true", help="leave changes in place on failure")
    ap.add_argument("--no-log", action="store_true", help="do not write .deployment.log")
    ap.add_argument("--quiet", action="store_true", help="only print gate/verification results")
    args = ap.parse_args(argv)

    log = AuditLog(DEPLOY_LOG, enabled=not args.no_log)

    def say(msg: str = "") -> None:
        if not args.quiet:
            print(msg)

    say("HCJC anon-feed enrichment fix -- deployment")
    say(f"  repo: {REPO_ROOT}")
    say(f"  mode: {'PLAN ONLY' if args.plan else 'apply'}")
    say()

    before_head = _git("rev-parse", "HEAD").stdout.strip()
    py = find_python()

    # ---- Gate 1: is there anything to recover, and from where? -------------
    say("[Gate 1] probing recovery sources")
    d = measure_damage()
    choice, reason = gate_1_recovery_decision(d)
    log.decision("gate_1", choice, reason, **d.as_dict())
    say(f"  rows in anon feed        : {d.total_rows}")
    say(f"  null tier/category       : {d.null_rows}")
    say(f"  in retention window      : {d.in_window} ({d.in_window_null} null)")
    say(f"    repairable from roster : {d.repairable}")
    say(f"    off-roster, permanent  : {d.unrepairable_offroster} ({d.released_null} released)")
    say(f"  expired, permanent       : {d.expired_null}")
    say(f"  raw code lookup hit rate : {d.raw_code_hit_rate:.1%}")
    say(f"  normalized hit rate      : {d.normalized_code_hit_rate:.1%}")
    say(f"  -> {choice}: {reason}")
    say()

    if args.plan:
        preview = repair_anon_changelog(log, dry=True)
        agree = preview["repaired"] == d.repairable
        say(f"[plan] would repair {preview['repaired']} rows; "
            f"{preview['unresolvable_in_window']} in-window unresolvable, "
            f"{preview['skipped_expired_or_anonymized']} expired/anonymized skipped, "
            f"{preview['skipped_pii_without_timestamp']} anomalous left alone")
        say(f"[plan] measurement and repair pass agree: {agree}")
        log.decision(
            "plan_consistency",
            "ok" if agree else "mismatch",
            f"measured {d.repairable} repairable, repair pass would touch {preview['repaired']}",
        )
        log.outcome("planned", EXIT_OK, would_repair=preview["repaired"], gate_1=choice)
        say("\nplan only: nothing was modified")
        return EXIT_OK if agree else EXIT_HALT

    # ---- Gate 2: is rollback safe? ----------------------------------------
    say("[Gate 2] checking worktree")
    clean, offenders = gate_2_worktree(log)
    if not clean:
        log.decision(
            "gate_2",
            "halt",
            "uncommitted changes outside the fix targets; git reset --hard during "
            "rollback would destroy them",
            offenders=offenders,
        )
        say("  HALT: unrelated pending changes --")
        for o in offenders[:20]:
            say(f"    {o}")
        say("  commit, stash, or remove them and re-run.")
        log.outcome("halted", EXIT_HALT, gate="gate_2")
        return EXIT_HALT
    say("  ok: no unrelated pending changes")
    log.decision("gate_2", "proceed", "worktree clean outside fix targets")
    say()

    # Taken before any mutation and restored by rollback(). Must exist before
    # the try block so the handler below can always reference it.
    data_backup = backup(ANON_PATH)
    repair: dict[str, Any] = {}

    try:
        # ---- Repair -------------------------------------------------------
        # Always take a dry pass first. Measurement and repair share
        # classify_row(), so their counts must agree exactly; asserting that
        # here catches any future divergence before data is written rather
        # than after.
        preview = repair_anon_changelog(log, dry=True)
        repair = preview
        if preview["repaired"] != d.repairable:
            raise RuntimeError(
                "measurement/repair disagreement: measured "
                f"{d.repairable} repairable rows but the repair pass would touch "
                f"{preview['repaired']}. Refusing to write until the classifiers agree."
            )

        if choice == "repair":
            say("[Repair] backfilling resolvable in-window rows")
            repair = repair_anon_changelog(log)
            say(f"  repaired {repair['repaired']} rows "
                f"(nulls {repair['before_nulls']} -> {repair.get('after_nulls', '?')})")
            say(f"  skipped {repair['skipped_expired_or_anonymized']} expired/anonymized, "
                f"{repair['unresolvable_in_window']} in-window unresolvable")
            if repair["skipped_pii_without_timestamp"]:
                say(f"  left {repair['skipped_pii_without_timestamp']} anomalous rows alone "
                    "(inmate_number but no timestamp_utc -- retention unprovable)")
        else:
            say("[Repair] skipped -- nothing recoverable; file left untouched")
        say()

        # ---- Commit -------------------------------------------------------
        head = before_head
        if not args.no_commit:
            say("[Commit] staging fix + tests" + (" + repaired data" if choice == "repair" else ""))
            head = commit_fix(log, COMMIT_MESSAGE)
            if head == before_head:
                say("  nothing to commit (fix already in HEAD)")
            else:
                say(f"  committed {head[:12]}")
            say()

        # ---- Verify -------------------------------------------------------
        say("[Verify]")
        results = {
            "v1_null_audit": v1_null_audit(d, repair, log),
            "v2_privacy_invariant": v2_privacy_invariant(repair, log),
            "v3_regression_tests": v3_regression_tests(py, log),
            "v4_full_suite": v4_full_suite(py, log),
        }
        if head != before_head:
            results["v5_commit_contents"] = v5_commit_contents(log, before_head)
        for name, ok in results.items():
            say(f"  {'PASS' if ok else 'FAIL'}  {name}")
        say()

        # Always record the permanent portion; it is real on both paths.
        write_incident_summary(d, repair, head)

        if all(results.values()):
            log.outcome(
                "success",
                EXIT_OK,
                commit=head,
                repaired=repair.get("repaired", 0),
                permanently_null=repair.get("after_nulls"),
            )
            say(f"SUCCESS (exit {EXIT_OK})")
            say(f"  commit          : {head[:12]}"
                + (" (unchanged -- nothing to commit)" if head == before_head else ""))
            say(f"  rows repaired   : {repair.get('repaired', 0)}")
            say(f"  permanently null: {d.unrepairable_offroster + d.expired_null} rows "
                f"({d.unrepairable_offroster} in-window off-roster + {d.expired_null} expired)")
            say(f"  incident record : {INCIDENT_FILE.name}")
            say(f"  audit log       : {DEPLOY_LOG.name}")
            if args.no_commit:
                say("\n  --no-commit: changes are in the working tree, uncommitted.")
                say("  review with `git diff`, then commit and push yourself.")
            elif head == before_head:
                say("\n  fix was already committed; nothing new to push.")
            else:
                say("\n  committed locally, NOT pushed. review with `git show HEAD`,")
                say("  then push the branch and open the PR.")
            say("  post-deploy: the first LIVE sweep is what proves released events get")
            say("  tagged going forward -- a dry run cannot, it never writes the feed.")
            return EXIT_OK

        log.outcome("failed", EXIT_FAILED, failed=[k for k, v in results.items() if not v])
        say(f"VERIFICATION FAILED (exit {EXIT_FAILED}) -- rolling back")
        rollback(log, before_head, data_backup, allow=not args.no_rollback)
        return EXIT_FAILED

    except Exception as e:  # noqa: BLE001 - last-resort guard around a mutating deploy
        log.action("unhandled", "failed", error=f"{type(e).__name__}: {e}")
        say(f"\nUNHANDLED {type(e).__name__}: {e}")
        say("rolling back")
        rollback(log, before_head, data_backup, allow=not args.no_rollback)
        log.outcome("failed", EXIT_FAILED, error=str(e))
        return EXIT_FAILED
    finally:
        if data_backup and data_backup.exists():
            try:
                data_backup.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(run())
