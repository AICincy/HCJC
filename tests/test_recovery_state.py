"""Guards for the Phase 4 recovery state file and its human-facing dashboard.

Phase 4 Section 5 of the architecture carries a reconciliation rule: if
``recovery-state.json`` and the Markdown dashboard disagree, processing stops.
Nothing enforced that mechanically. This test does, covering six properties:
schema validity, status vocabulary, append-only event monotonicity, C4
eligibility consistency, state-machine transition direction, and dashboard
agreement with a git-based synchrony warning.

Design notes that differ from the Phase 5 brief, each for a concrete reason:

* Transitions are keyed by state machine (``d1_gate``) rather than by bare
  status, because ``STALLED`` and ``PENDING`` appear in more than one machine
  with different legal successors.
* The synchrony check compares last-commit timestamps, not file mtimes. mtimes
  are assigned at checkout and are identical for every tracked file, so an
  mtime rule can never fire in CI and fires arbitrarily in a working tree.
* The vocabulary and transition maps are cross-checked against the lines this
  file parses out of ``state-schema.md``, so prose and enforcement cannot drift
  apart unnoticed.
* Property 6 warns instead of failing, and no property touches the network.

Run: ``python -m pytest tests/test_recovery_state.py -q``
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import warnings
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "audit-output" / "phase-4-release-recovery-2026-09-23"
STATE_FILE = STATE_DIR / "recovery-state.json"
SCHEMA_DOC = STATE_DIR / "state-schema.md"
DASHBOARD = STATE_DIR / "cross-agent-state-table.md"

SYNCY_WARN_MINUTES = 30.0

REQUIRED_TOP_LEVEL = {
    "schema_version",
    "as_of_date_utc",
    "state_authority",
    "candidate",
    "phase_3_snapshot",
    "recovery_items",
    "c4_activation",
    "events",
}
REQUIRED_ITEM_FIELDS = {"agent", "status", "feeds_back_to"}
REQUIRED_EVENT_FIELDS = {
    "event_id",
    "utc_timestamp",
    "item",
    "from_status",
    "to_status",
    "actor",
    "evidence",
    "feeds_back_to",
}

GATE_STATUSES = {
    "CLOSED",
    "FAILED",
    "NOT-RUN",
    "OPEN",
    "BLOCKED",
    "LOCAL-PASS",
    "PASSED",
    "RISK-ACCEPTED",
    "SUPERSEDED-PARTIAL",
}
D0_STATUSES = {"NOT-RUN", "RECONCILE-FIRST", "DELTAS-EMITTED", "CURRENT"}
D1_GATE_STATUSES = {"NOT-ACTIVATED", "IN-PROGRESS", "STALLED", "READY-FOR-C1-REINGESTION"}
DEFECT_STATUSES = {
    "OPEN",
    "IN-FIX",
    "RETEST-READY",
    "RETEST-COMPLETE",
    "RESOLVED",
    "WONT-FIX",
    "STALLED",
    "ESCALATED",
}
D2_OPTION_STATUSES = {
    "NOT-ACTIVATED",
    "PENDING",
    "PENDING-BLOCKED",
    "INCOMPLETE",
    "PASS",
    "FAIL",
    "STALLED",
    "READY-FOR-C2-REINGESTION",
}
D3_STATUSES = {"NOT-ACTIVATED", "PENDING-NEXT-SWEEP", "SWEEP-VERIFIED", "SWEEP-FAILED"}
D4_STATUSES = {"NOT-AGED", "VALID-NO-ACTION", "RENEWAL-REQUIRED", "RENEWED"}
D5_STATUSES = {
    "NOT-ACTIVATED",
    "INCONCLUSIVE-EVIDENCE",
    "SITE-EVIDENCE",
    "PATH-EVIDENCE",
    "STALLED",
}

VOCABULARIES = {
    "gate_status": GATE_STATUSES,
    "d0": D0_STATUSES,
    "d1_gate": D1_GATE_STATUSES,
    "d1_defect": DEFECT_STATUSES,
    "d2_option": D2_OPTION_STATUSES,
    "d3": D3_STATUSES,
    "d4": D4_STATUSES,
    "d5": D5_STATUSES,
}

ITEM_MACHINE = {
    "d0_snapshot": "d0",
    "d1_gate_a": "d1_gate",
    "d1_gate_b": "d1_gate",
    "d2_option_2": "d2_option",
    "d2_option_3": "d2_option",
    "d3_sweep": "d3",
    "d4_freshness": "d4",
    "d5_live_probe": "d5",
}

INITIAL_STATUS = {
    "d0": "NOT-RUN",
    "d1_gate": "NOT-ACTIVATED",
    "d2_option": "NOT-ACTIVATED",
    "d3": "NOT-ACTIVATED",
    "d4": "NOT-AGED",
    "d5": "NOT-ACTIVATED",
}

# Legal successors per state machine. Terminal states map to an empty set.
VALID_TRANSITIONS: dict[str, dict[str, set[str]]] = {
    "d0": {
        "NOT-RUN": {"RECONCILE-FIRST", "DELTAS-EMITTED", "CURRENT"},
        "RECONCILE-FIRST": {"DELTAS-EMITTED", "CURRENT"},
        "DELTAS-EMITTED": {"CURRENT"},
        "CURRENT": {"RECONCILE-FIRST"},
    },
    "d1_gate": {
        "NOT-ACTIVATED": {"IN-PROGRESS", "STALLED"},
        "IN-PROGRESS": {"READY-FOR-C1-REINGESTION", "STALLED"},
        "STALLED": {"IN-PROGRESS"},
        "READY-FOR-C1-REINGESTION": {"IN-PROGRESS"},
    },
    "d1_defect": {
        "OPEN": {"IN-FIX", "STALLED", "ESCALATED"},
        "IN-FIX": {"RETEST-READY", "OPEN"},
        "RETEST-READY": {"RETEST-COMPLETE", "OPEN"},
        "RETEST-COMPLETE": {"RESOLVED", "OPEN", "ESCALATED"},
        "ESCALATED": {"WONT-FIX", "IN-FIX"},
        "STALLED": {"OPEN"},
        "RESOLVED": set(),
        "WONT-FIX": set(),
    },
    "d2_option": {
        "NOT-ACTIVATED": {"PENDING", "PENDING-BLOCKED"},
        "PENDING-BLOCKED": {"PENDING"},
        "PENDING": {"INCOMPLETE", "PASS", "FAIL", "STALLED"},
        "INCOMPLETE": {"PENDING"},
        "FAIL": {"PENDING"},
        "PASS": {"READY-FOR-C2-REINGESTION"},
        "STALLED": {"PENDING"},
        "READY-FOR-C2-REINGESTION": {"PENDING"},
    },
    "d3": {
        "NOT-ACTIVATED": {"PENDING-NEXT-SWEEP"},
        "PENDING-NEXT-SWEEP": {"SWEEP-VERIFIED", "SWEEP-FAILED"},
        "SWEEP-FAILED": {"PENDING-NEXT-SWEEP"},
        "SWEEP-VERIFIED": set(),
    },
    "d4": {
        "NOT-AGED": {"VALID-NO-ACTION", "RENEWAL-REQUIRED"},
        "VALID-NO-ACTION": {"RENEWAL-REQUIRED", "VALID-NO-ACTION"},
        "RENEWAL-REQUIRED": {"RENEWED"},
        "RENEWED": {"VALID-NO-ACTION"},
    },
    "d5": {
        "NOT-ACTIVATED": {"INCONCLUSIVE-EVIDENCE", "SITE-EVIDENCE", "PATH-EVIDENCE", "STALLED"},
        "INCONCLUSIVE-EVIDENCE": {"SITE-EVIDENCE", "PATH-EVIDENCE", "STALLED"},
        "PATH-EVIDENCE": {"INCONCLUSIVE-EVIDENCE", "SITE-EVIDENCE"},
        "SITE-EVIDENCE": set(),
        "STALLED": {"INCONCLUSIVE-EVIDENCE"},
    },
}

D1_BLOCKING = {"IN-PROGRESS", "STALLED", "READY-FOR-C1-REINGESTION"}
D2_BLOCKING = {"PENDING", "PENDING-BLOCKED", "INCOMPLETE", "STALLED"}
OPEN_DEFECT_STATUSES = {"OPEN", "IN-FIX", "RETEST-READY", "RETEST-COMPLETE", "ESCALATED"}

# Clause names the schema document must list, so prose and code agree.
C4_CLAUSE_NAMES = (
    'phase_3_snapshot.gate_a == "CLOSED"',
    'phase_3_snapshot.gate_b == "CLOSED"',
    'phase_3_snapshot.gate_c == "CLOSED"',
    'phase_3_snapshot.isolation_merge == "CLOSED"',
    "d1_gate_a.status not blocking",
    "d1_gate_b.status not blocking",
    "d2_option_2.status not blocking",
    "d2_option_3.status not blocking",
    "d4 has no RENEWAL-REQUIRED item",
)


def load_state(path: Path = STATE_FILE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compute_c4_eligibility(state: dict[str, Any]) -> bool:
    """Phase 4 Section 5 blocking calculation, reproduced from the schema doc.

    D3 status is deliberately absent: the sweep verification is a post-LIVE-D
    closure event, and holding C4 for it would reintroduce the blocking
    behaviour D3 was written to avoid.
    """
    snap = state.get("phase_3_snapshot", {})
    items = state.get("recovery_items", {})

    def blocked_d1(key: str) -> bool:
        item = items.get(key, {})
        if item.get("status") in D1_BLOCKING:
            return True
        return any(d.get("status") in OPEN_DEFECT_STATUSES for d in item.get("defects", []))

    def blocked_d2(key: str) -> bool:
        return items.get(key, {}).get("status") in D2_BLOCKING

    d4_renewal = any(
        i.get("outcome") == "RENEWAL-REQUIRED" for i in items.get("d4_freshness", {}).get("aged_items", [])
    )

    return (
        snap.get("gate_a") == "CLOSED"
        and snap.get("gate_b") == "CLOSED"
        and snap.get("gate_c") == "CLOSED"
        and snap.get("isolation_merge") == "CLOSED"
        and not blocked_d1("d1_gate_a")
        and not blocked_d1("d1_gate_b")
        and not blocked_d2("d2_option_2")
        and not blocked_d2("d2_option_3")
        and not d4_renewal
    )


def validate_schema(state: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    missing = REQUIRED_TOP_LEVEL - set(state)
    if missing:
        problems.append(f"missing top-level keys: {sorted(missing)}")
    if state.get("schema_version") != 1:
        problems.append(f"unsupported schema_version: {state.get('schema_version')!r}")
    items = state.get("recovery_items", {})
    if not isinstance(items, dict):
        return problems + ["recovery_items must be an object"]
    unknown = set(items) - set(ITEM_MACHINE)
    if unknown:
        problems.append(f"recovery_items has unmanaged keys: {sorted(unknown)}")
    for key, item in items.items():
        if not isinstance(item, dict):
            problems.append(f"{key}: item must be an object")
            continue
        gaps = REQUIRED_ITEM_FIELDS - set(item)
        if gaps:
            problems.append(f"{key}: missing {sorted(gaps)}")
        if (
            key in ITEM_MACHINE
            and item.get("agent")
            and not item["agent"].upper().startswith(key.split("_")[0].upper())
        ):
            problems.append(f"{key}: agent {item['agent']!r} does not match the item's owning agent")
        if not isinstance(item.get("feeds_back_to"), list) or not item.get("feeds_back_to"):
            problems.append(f"{key}: feeds_back_to must be a non-empty list")
    for key, required in (
        ("d1_gate_a", "defects"),
        ("d1_gate_b", "defects"),
        ("d2_option_2", "attempts"),
        ("d2_option_3", "attempts"),
        ("d3_sweep", "verification_runs"),
        ("d4_freshness", "aged_items"),
        ("d5_live_probe", "observations"),
    ):
        if key in items and required not in items[key]:
            problems.append(f"{key}: missing type-specific array {required!r}")
    return problems


def validate_statuses(state: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    snap = state.get("phase_3_snapshot", {})
    for gate in ("gate_a", "gate_b", "gate_c", "gate_d", "gate_e", "isolation_merge", "ci_01", "release_01"):
        if gate in snap and snap[gate] not in GATE_STATUSES:
            problems.append(f"phase_3_snapshot.{gate}: {snap[gate]!r} not in the gate vocabulary")
    for key, item in state.get("recovery_items", {}).items():
        machine = ITEM_MACHINE.get(key)
        if machine is None or not isinstance(item, dict):
            continue
        status = item.get("status")
        allowed = VOCABULARIES[machine]
        if status not in allowed:
            problems.append(f"{key}: status {status!r} not in {machine} vocabulary {sorted(allowed)}")
        for defect in item.get("defects", []):
            ds = defect.get("status", "<missing>")
            if ds not in DEFECT_STATUSES:
                did = defect.get("id", "?")
                problems.append(f"{key} defect {did}: status {ds!r} not in {sorted(DEFECT_STATUSES)}")
    return problems


def parse_utc(ts: Any) -> dt.datetime | None:
    if not isinstance(ts, str) or not ts.endswith("Z"):
        return None
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_events(state: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    events = state.get("events", [])
    if not isinstance(events, list):
        return ["events must be an array"]
    seen: set[str] = set()
    last_per_item: dict[str, str] = {}
    prev_ts: dt.datetime | None = None
    for index, ev in enumerate(events):
        if not isinstance(ev, dict):
            problems.append(f"event {index}: must be an object")
            continue
        gaps = REQUIRED_EVENT_FIELDS - set(ev)
        if gaps:
            problems.append(f"event {index}: missing {sorted(gaps)}")
            continue
        eid = ev["event_id"]
        if eid in seen:
            problems.append(f"duplicate event_id: {eid}")
        seen.add(eid)
        if not str(ev.get("actor", "")).strip():
            problems.append(f"event {eid}: actor must be non-empty")
        if not isinstance(ev.get("evidence"), list):
            problems.append(f"event {eid}: evidence must be a list")
        stamp = parse_utc(ev["utc_timestamp"])
        if stamp is None:
            problems.append(f"event {eid}: utc_timestamp must be ISO-8601 ending in Z, got {ev['utc_timestamp']!r}")
        elif prev_ts is not None and stamp < prev_ts:
            problems.append(
                f"event {eid}: timestamp {ev['utc_timestamp']} precedes the previous event; the log is append-only"
            )
        if prev_ts is not None and stamp is not None:
            prev_ts = max(prev_ts, stamp)
        elif stamp is not None:
            prev_ts = stamp
        item = ev["item"]
        if item not in state.get("recovery_items", {}):
            problems.append(f"event {eid}: item {item!r} is not a managed recovery item")
        if item in last_per_item:
            if last_per_item[item] != ev["from_status"]:
                problems.append(
                    f"event {eid}: from_status {ev['from_status']!r} does not continue "
                    f"{item} at {last_per_item[item]!r}"
                )
        else:
            machine = ITEM_MACHINE.get(item)
            initial = INITIAL_STATUS.get(machine or "", ev["from_status"])
            if ev["from_status"] != initial:
                problems.append(f"event {eid}: {item} must open at {initial!r}, not {ev['from_status']!r}")
        last_per_item[item] = ev["to_status"]
    for key, item in state.get("recovery_items", {}).items():
        if not isinstance(item, dict):
            continue
        if key in last_per_item and last_per_item[key] != item.get("status"):
            problems.append(
                f"{key}: status {item.get('status')!r} does not match the event log head {last_per_item[key]!r}"
            )
    return problems


def validate_transitions(state: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for ev in state.get("events", []):
        if not isinstance(ev, dict):
            continue
        machine = ITEM_MACHINE.get(ev.get("item", ""))
        if machine is None:
            continue
        table = VALID_TRANSITIONS[machine]
        frm, to = ev.get("from_status"), ev.get("to_status")
        if frm not in table:
            problems.append(f"event {ev.get('event_id')}: {machine} has no state {frm!r}")
        elif to not in table[frm]:
            problems.append(
                f"event {ev.get('event_id')}: {frm} -> {to} is not a valid {machine} transition; "
                f"allowed: {sorted(table[frm]) or 'none, the state is terminal'}"
            )
    return problems


def validate_c4(state: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    activation = state.get("c4_activation", {})
    if "eligible" not in activation:
        return ["c4_activation.eligible is missing"]
    expected = compute_c4_eligibility(state)
    actual = activation["eligible"]
    if actual is not expected:
        problems.append(
            f"c4_activation.eligible={actual!r} but the calculation gives {expected!r}. "
            "Either the flag was hand-edited or an item moved without re-deriving eligibility."
        )
    if not str(activation.get("rationale", "")).strip():
        problems.append("c4_activation.rationale must be non-empty")
    listed = set(activation.get("blocking_items", [])) | set(activation.get("non_blocking_items", []))
    managed = set(state.get("recovery_items", {}))
    if listed and listed != managed:
        problems.append(
            f"c4_activation item lists must cover every recovery item; missing {sorted(managed - listed)}, "
            f"unknown {sorted(listed - managed)}"
        )
    return problems


def validate_dashboard(state: dict[str, Any], dashboard_text: str) -> list[str]:
    problems: list[str] = []
    for key in state.get("recovery_items", {}):
        if key not in dashboard_text:
            problems.append(f"{key}: absent from {DASHBOARD.name}; the human dashboard must carry every JSON item")
    for key, item in state.get("recovery_items", {}).items():
        note = item.get("sync_note") if isinstance(item, dict) else None
        if not note:
            problems.append(f"{key}: sync_note is required so a reader can find its dashboard row")
    return problems


def parse_schema_doc(text: str) -> tuple[dict[str, set[str]], dict[str, dict[str, set[str]]]]:
    vocabs: dict[str, set[str]] = {}
    transitions: dict[str, dict[str, set[str]]] = {}
    for line in text.splitlines():
        vocab = re.match(r"^VOCAB\s+(\w+):\s*(.+)$", line.strip())
        if vocab:
            vocabs[vocab.group(1)] = {v.strip() for v in vocab.group(2).split(",") if v.strip()}
            continue
        trans = re.match(r"^TRANS\s+(\w+):\s*([\w-]+)\s*->\s*(.+)$", line.strip())
        if trans:
            machine, frm, targets = trans.group(1), trans.group(2), trans.group(3)
            parsed = {t.strip() for t in targets.split("|") if t.strip()}
            transitions.setdefault(machine, {})[frm] = set() if parsed == {"NONE"} else parsed
    return vocabs, transitions


def _git_mtime(path: Path) -> float | None:
    """Last commit timestamp touching a path, or None when git cannot answer."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(path.relative_to(REPO_ROOT))],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    raw = out.stdout.strip()
    return float(raw) if out.returncode == 0 and raw.isdigit() else None


# --- checks against the real state file ------------------------------------


def test_schema_validity() -> None:
    assert STATE_FILE.is_file(), f"{STATE_FILE.relative_to(REPO_ROOT)} must exist and be committed"
    problems = validate_schema(load_state())
    assert not problems, "recovery-state.json schema invalid: " + "; ".join(problems)


def test_status_vocabulary() -> None:
    problems = validate_statuses(load_state())
    assert not problems, "status vocabulary violated: " + "; ".join(problems)


def test_event_log_monotonicity() -> None:
    problems = validate_events(load_state())
    assert not problems, "event log invalid: " + "; ".join(problems)


def test_c4_eligibility_consistency() -> None:
    problems = validate_c4(load_state())
    assert not problems, "C4 eligibility disagrees with the calculation: " + "; ".join(problems)


def test_transition_direction() -> None:
    problems = validate_transitions(load_state())
    assert not problems, "illegal state transition: " + "; ".join(problems)


def test_dashboard_agreement() -> None:
    assert DASHBOARD.is_file(), f"{DASHBOARD.relative_to(REPO_ROOT)} must exist"
    problems = validate_dashboard(load_state(), DASHBOARD.read_text(encoding="utf-8"))
    assert not problems, "dashboard and state file diverge: " + "; ".join(problems)


def test_dashboard_synchrony_warning(recwarn: Any) -> None:
    """Warn, never fail, when the dashboard moved long after the state file.

    Uses commit times rather than mtimes; see the module docstring.
    """
    state_mtime = _git_mtime(STATE_FILE)
    dash_mtime = _git_mtime(DASHBOARD)
    if state_mtime is None or dash_mtime is None:
        return  # no git history available (e.g. archive export); not a failure
    delta_minutes = (dash_mtime - state_mtime) / 60
    if abs(delta_minutes) > SYNCY_WARN_MINUTES:
        recwarn.clear()
        warnings.warn(
            f"{DASHBOARD.name} was committed {delta_minutes:+.1f} minutes relative to "
            f"recovery-state.json. Phase 4 reconciliation rule: if the dashboard and the "
            "state file disagree, stop processing. Verify the dashboard reflects the "
            "current JSON before any D-agent transition.",
            stacklevel=1,
        )


# --- the guard must catch the drift it exists to catch ---------------------


def _findings(state: dict[str, Any]) -> list[str]:
    """Every finding the validators produce for a candidate state."""
    problems: list[str] = []
    problems += validate_schema(state)
    problems += validate_statuses(state)
    problems += validate_events(state)
    problems += validate_transitions(state)
    problems += validate_c4(state)
    return problems


def _mutate(mutator: Any) -> list[str]:
    """Apply a mutation to a copy of the real state and collect every finding."""
    state = load_state()
    mutator(state)
    return _findings(state)


def _walk(state: dict[str, Any], item: str, *to_statuses: str) -> None:
    """Move an item along a legal path, appending events and syncing its status.

    The guard's own tests use this, so a legal sequence must stay legal. If the
    helper raises, the transition table contradicts the schema document.
    """
    machine = ITEM_MACHINE[item]
    table = VALID_TRANSITIONS[machine]
    entry = state["recovery_items"][item]
    current = entry["status"]
    offset = len(state["events"])
    for i, to in enumerate(to_statuses):
        if to not in table.get(current, set()):
            raise AssertionError(f"test setup: {current} -> {to} is not legal for {machine}")
        state["events"].append(
            {
                "event_id": f"RS-T{offset + i + 1:03d}",
                "utc_timestamp": f"2026-09-23T04:{offset + i:02d}:00Z",
                "item": item,
                "from_status": current,
                "to_status": to,
                "actor": "test fixture",
                "evidence": ["tests/test_recovery_state.py"],
                "feeds_back_to": entry["feeds_back_to"],
            }
        )
        current = to
    entry["status"] = current


def test_guard_rejects_invented_status() -> None:
    def mutate(state: dict[str, Any]) -> None:
        state["recovery_items"]["d3_sweep"]["status"] = "SWEEP-PROBABLY-FINE"

    problems = _mutate(mutate)
    assert any("vocabulary" in p for p in problems), problems


def test_guard_rejects_illegal_transition() -> None:
    # A legal move must leave no finding, or the table is stricter than the state machine.
    state = load_state()
    _walk(state, "d3_sweep", "SWEEP-VERIFIED")
    assert _findings(state) == [], "a legitimate transition must pass the guard"

    # Departing a terminal state is not legal.
    state["events"].append(
        {
            "event_id": "RS-T900",
            "utc_timestamp": "2026-09-23T05:00:00Z",
            "item": "d3_sweep",
            "from_status": "SWEEP-VERIFIED",
            "to_status": "SWEEP-FAILED",
            "actor": "test fixture",
            "evidence": [],
            "feeds_back_to": ["standing note in BUILD-E"],
        }
    )
    problems = _findings(state)
    assert any("not a valid" in p for p in problems), problems


def test_guard_rejects_terminal_state_departure() -> None:
    def mutate(state: dict[str, Any]) -> None:
        state["events"] = [e for e in state["events"] if e["item"] != "d3_sweep"]
        state["events"].append(
            {
                "event_id": "RS-998",
                "utc_timestamp": "2026-09-23T04:10:00Z",
                "item": "d4_freshness",
                "from_status": "VALID-NO-ACTION",
                "to_status": "NOT-AGED",
                "actor": "test",
                "evidence": [],
                "feeds_back_to": ["C1"],
            }
        )
        state["recovery_items"]["d4_freshness"]["status"] = "NOT-AGED"

    problems = _mutate(mutate)
    assert any("not a valid" in p or "does not continue" in p for p in problems), problems


def test_guard_rejects_eligibility_hand_edit() -> None:
    def mutate(state: dict[str, Any]) -> None:
        state["c4_activation"]["eligible"] = True

    problems = _mutate(mutate)
    assert any("c4_activation.eligible" in p for p in problems), problems


def test_guard_rejects_closed_snapshot_without_evidence() -> None:
    """Hand-marking the snapshot CLOSED is not enough; the D items must be clear too."""

    def close_everything(state: dict[str, Any]) -> None:
        for gate in ("gate_a", "gate_b", "gate_c", "isolation_merge"):
            state["phase_3_snapshot"][gate] = "CLOSED"
        _walk(state, "d2_option_3", "PENDING", "PASS", "READY-FOR-C2-REINGESTION")
        state["c4_activation"]["eligible"] = True

    assert _mutate(close_everything) == [], "a fully closed and cleared state should be eligible"

    def reopen(state: dict[str, Any]) -> None:
        close_everything(state)
        state["recovery_items"]["d1_gate_a"]["defects"].append({"id": "A-1", "status": "IN-FIX"})

    problems = _mutate(reopen)
    assert any("c4_activation.eligible" in p for p in problems), problems


def test_guard_rejects_backdated_or_duplicate_events() -> None:
    def mutate(state: dict[str, Any]) -> None:
        state["events"][-1]["event_id"] = state["events"][-2]["event_id"]

    assert any("Duplicate" in p or "duplicate" in p for p in _mutate(mutate))

    def backdate(state: dict[str, Any]) -> None:
        state["events"][-1]["utc_timestamp"] = "2026-01-01T00:00:00Z"
        state["recovery_items"]["d2_option_3"]["status"] = "PENDING-BLOCKED"

    problems = _mutate(backdate)
    assert any("precedes the previous event" in p for p in problems), problems


def test_guard_requires_named_actor() -> None:
    def mutate(state: dict[str, Any]) -> None:
        state["events"][-1]["actor"] = ""

    assert any("actor" in p for p in _mutate(mutate))


def test_dashboard_agreement_guard_catches_missing_row() -> None:
    problems = validate_dashboard(load_state(), "no rows here at all")
    assert len(problems) == len(load_state()["recovery_items"]), problems


# --- prose and enforcement must agree ---------------------------------------


def test_schema_document_vocabularies_match_constants() -> None:
    vocabs, _ = parse_schema_doc(SCHEMA_DOC.read_text(encoding="utf-8"))
    assert set(vocabs) == set(VOCABULARIES), (
        f"state-schema.md declares {sorted(vocabs)}, the test enforces {sorted(VOCABULARIES)}"
    )
    for name, allowed in VOCABULARIES.items():
        assert vocabs[name] == allowed, (
            f"vocabulary drift in {name}: doc has {sorted(vocabs[name])}, test has {sorted(allowed)}"
        )


def test_schema_document_transitions_match_constants() -> None:
    _, doc_transitions = parse_schema_doc(SCHEMA_DOC.read_text(encoding="utf-8"))
    assert set(doc_transitions) == set(VALID_TRANSITIONS), (
        f"documented machines {sorted(doc_transitions)} != enforced {sorted(VALID_TRANSITIONS)}"
    )
    for machine, table in VALID_TRANSITIONS.items():
        doc_table = doc_transitions[machine]
        assert set(doc_table) == set(table), (
            f"{machine}: documented sources {sorted(doc_table)} != enforced {sorted(table)}"
        )
        for frm, targets in table.items():
            assert doc_table[frm] == targets, (
                f"{machine}: {frm} -> documented {sorted(doc_table[frm])} != enforced {sorted(targets)}"
            )


def test_schema_document_states_the_c4_clauses_and_d3_exclusion() -> None:
    text = SCHEMA_DOC.read_text(encoding="utf-8")
    for clause in C4_CLAUSE_NAMES:
        assert clause in text, f"state-schema.md must document the C4 clause: {clause}"
    assert "D3 status is excluded from the C4 eligibility calculation" in text, (
        "the document must state that D3 is excluded, or a reader will assume it blocks C4"
    )
