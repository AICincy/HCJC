# JCStream Remediations: Execution Task for Claude Opus

> **Role:** Senior Python engineer working in Claude Code on the `AICincy/HCJC` repository.
> **Mode:** Direct file edits. No clarifying questions. Implement everything below, run tests, commit.
> **Engine target:** Claude Opus 4 (or higher) with extended thinking enabled.

---

## Mission

Apply 6 audit remediations to the JCStream scraper. Each fix has a numbered specification with the exact file, the problem statement, and the required change. After all edits, run the test suite and produce a single commit.

**Do not** open clarifying dialogues. **Do not** ask which fix to start with. **Do not** propose alternatives mid-execution. If a spec is ambiguous, choose the option that most closely matches the existing codebase style (defensive engineering, atomic writes, thread-safe primitives, narrow docstrings on every helper).

---

## Repository preconditions

| Item | Value |
|---|---|
| Repo | `github.com/AICincy/HCJC` |
| Branch | Create `remediations/audit-2026-05-21` from default `HEAD` |
| Python | 3.12 |
| Test runner | `python -m pytest tests/ -q` |
| Style | f-strings, full type hints, narrow docstrings, atomic writes via `os.replace` |

Before editing: run `python -m pytest tests/ -q` once on the clean checkout to establish a baseline. Record the pass count in your commit message.

---

## Fix index

| # | File | Concern | LOC delta (approx) |
|---|---|---|---|
| 1 | `scraper/client.py` | Crawl-delay race window | +5 / -4 |
| 2 | `scraper/client.py` | Retry off-by-one vs docstring | +5 / -5 |
| 3 | `scraper/sweep.py` + `tests/test_sweep.py` | Module-global WAF streak | +60 / -40 |
| 4 | `scraper/parsers.py` | Container name fallback too permissive | +28 / -1 |
| 5 | `scraper/client.py` | Missing pool keepalive expiry | +2 / -1 |
| 6 | `scraper/store.py` | `anon_changelog` grows unbounded | +63 / -0 |

---

## Fix 1: Move crawl-delay sleep inside the lock

**File:** `scraper/client.py`
**Method:** `HcsoClient._sleep_for_crawl_delay`

### Problem
`time.sleep(wait)` runs outside the lock. With 16 concurrent workers, every thread can read the same `_last_request_at`, compute the same `wait`, release the lock, and burst-sleep in parallel. The WAF then sees 16 simultaneous requests instead of one-every-0.5s.

### Required change
Move `time.sleep(wait)` inside the `with self._lock:` block. Set `_last_request_at` only after the sleep completes, using `time.monotonic()` (not the precomputed deadline).

### Final shape

```python
def _sleep_for_crawl_delay(self) -> None:
    if self.crawl_delay <= 0:
        return
    with self._lock:  # serialize gating AND sleep so concurrent workers
        # cannot all read the same elapsed and burst simultaneously.
        elapsed = time.monotonic() - self._last_request_at
        wait = self.crawl_delay - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()
```

---

## Fix 2: Align retry loop with documented behavior

**File:** `scraper/client.py`
**Method:** `HcsoClient.get_response`

### Problem
The initial response is fetched at line 126. The loop `for attempt in range(2):` can issue 2 more requests. Total: up to 3 requests. The docstring says "Retries once on transient 5xx" so either the loop or the doc is wrong.

### Required change
Change `range(2)` to `range(1)`. Update the docstring on `get()` to say "after one retry on transient 5xx and 429" and "Uses a 0.5s backoff on 5xx" (single backoff, not exponential).

### Final docstring (on `get`)

```
Thread-safe. Raises httpx.HTTPStatusError on non-2xx after one retry on
transient 5xx and 429. Uses a 0.5s backoff on 5xx so a degraded HCSO
front-end isn't hammered immediately. On 429, the Retry-After header
is honored (parsed in seconds or HTTP-date form), capped at
RETRY_AFTER_CAP_S.
```

---

## Fix 3: Replace global WAF streak with `WafBackoffTracker` dataclass

**Files:** `scraper/sweep.py`, `tests/test_sweep.py`

### Problem
`_waf_block_streak`, `_waf_block_lock`, `_on_waf_block_observed`, `_on_waf_block_cleared`, `_waf_backoff_seconds` are module-level globals. The pattern `streak = _on_waf_block_observed()` then `backoff = _waf_backoff_seconds(streak)` reads the streak outside the lock, so a second thread can mutate it in between. Each `run()` also inherits stale state from the previous invocation in tests.

### Required change

#### 3a. Add `WafBackoffTracker` to `scraper/sweep.py`

Place after `MIN_SWEEP_INTERVAL_S` declaration. Remove the 4 module-level globals and the 3 helper functions they back. Also remove `_reset_waf_block_streak_for_tests`.

```python
@dataclass
class WafBackoffTracker:
    """Thread-safe WAF-block backoff tracker, instantiated once per sweep run.

    Replaces the prior module-level globals (_waf_block_streak, _waf_block_lock)
    so each run() gets a clean instance and there is no stale-streak window:
    observe() atomically increments the streak AND computes the backoff inside
    the lock, returning the backoff seconds directly.
    """

    _BASE_S: float = 2.0
    _CAP_S: float = 30.0
    _streak: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def observe(self) -> tuple[int, float]:
        """Record a WAF-block-shaped response (thread-safe).

        Returns ``(streak, backoff_seconds)`` computed atomically so the
        caller never acts on a stale streak value.
        """
        with self._lock:
            self._streak += 1
            streak = self._streak
            backoff = min(self._BASE_S * (2 ** (streak - 1)), self._CAP_S)
        return streak, backoff

    def clear(self) -> None:
        """Reset the streak after a successful parse."""
        with self._lock:
            self._streak = 0

    @property
    def streak(self) -> int:
        with self._lock:
            return self._streak
```

Update the import: `from dataclasses import dataclass, field`.

#### 3b. Thread the tracker through the call chain

| Function | Change |
|---|---|
| `_fetch_detail_with_retry` | Add `waf_tracker: WafBackoffTracker` parameter. Replace `_on_waf_block_cleared()` with `waf_tracker.clear()`. Replace `streak = _on_waf_block_observed(); backoff = _waf_backoff_seconds(streak)` with `streak, backoff = waf_tracker.observe()`. |
| `_fetch_one` | Add `waf_tracker: WafBackoffTracker \| None = None` parameter. Pass `waf_tracker or WafBackoffTracker()` down to `_fetch_detail_with_retry`. |
| `_fetch_details` | Add `waf_tracker: WafBackoffTracker` parameter. Pass it as the last positional arg in `pool.submit(_fetch_one, client, iid, previous, row_by_id.get(iid), waf_tracker)`. |
| `run()` | Instantiate `waf_tracker = WafBackoffTracker()` before the `_fetch_details(...)` call and pass it as `waf_tracker=waf_tracker`. |

#### 3c. Update `tests/test_sweep.py`

Two tests reference `sweep._reset_waf_block_streak_for_tests()`:

- `test_fetch_one_returns_none_on_waf_blocked_response_for_known_inmate`
- `test_fetch_one_retries_within_same_cycle_and_recovers_on_second_attempt`

Replace each call with a fresh `tracker = WafBackoffTracker()` and pass `waf_tracker=tracker` into every `_fetch_one(...)` call in those tests. Update the import:

```python
from scraper.sweep import WafBackoffTracker, _fetch_one
```

---

## Fix 4: Tighten the container-text name fallback

**File:** `scraper/parsers.py`
**Function:** `_name_from_container_text`

### Problem
The fallback matches any `<div>`, `<span>`, or `<p>` containing an all-caps comma-bearing string under 200 chars. Boilerplate like `"HAMILTON COUNTY, OHIO"` in a footer satisfies the predicate.

### Required change
Add a `_BOILERPLATE_KEYWORDS` frozenset and a `_looks_like_person_name` predicate that combines the existing shape check with two extra guards:

1. Reject if the candidate contains any boilerplate keyword as a whitespace-delimited token.
2. Require at least one alphabetic character after the comma.

```python
_BOILERPLATE_KEYWORDS = frozenset({
    "COUNTY", "STATE", "OFFICE", "DEPARTMENT", "SHERIFF",
    "COURT", "OHIO", "JUSTICE", "CENTER", "SERVICES",
    "GOVERNMENT", "DISTRICT", "MUNICIPAL", "COMMON PLEAS",
})


def _looks_like_person_name(text: str) -> bool:
    """Stricter check than _looks_like_formal_name for the container fallback.

    Requires LAST, FIRST shape (second part has at least one letter after the
    comma) and rejects strings containing known boilerplate keywords."""
    if not _looks_like_formal_name(text):
        return False
    words = set(text.split())
    if words & _BOILERPLATE_KEYWORDS:
        return False
    _, _, after_comma = text.partition(",")
    if not after_comma.strip() or not any(c.isalpha() for c in after_comma):
        return False
    return True
```

In `_name_from_container_text`, replace `_looks_like_formal_name(text)` with `_looks_like_person_name(text)`. Keep the 200-char length cap and the debug log.

---

## Fix 5: Add `keepalive_expiry` to httpx pool limits

**File:** `scraper/client.py`
**Location:** `HcsoClient.__enter__`, inside `httpx.Client(...)` construction.

### Problem
`httpx.Limits` has no `keepalive_expiry` set. Stale keep-alive connections accumulate. When HCSO silently drops one, the next worker that reuses it gets a timeout.

### Required change
Add `keepalive_expiry=30` to the existing `httpx.Limits(...)` call. Match the existing per-request timeout. No comment needed; the value is self-documenting alongside `max_keepalive_connections`.

```python
limits=httpx.Limits(max_connections=self.concurrency * 2,
                    max_keepalive_connections=self.concurrency,
                    keepalive_expiry=30),
```

---

## Fix 6: Compact anon_changelog after 365 days

**File:** `scraper/store.py`

### Problem
`save_anon_changelog` writes `out` directly to disk with no growth limit. At a 30-min cron cadence, the file gains ~17k rows per year and grows without bound.

### Required change

#### 6a. Add module-level constant near `ANON_EXPIRY_DAYS`

```python
# Compaction horizon: anonymized records older than this are collapsed into
# monthly summary counts (one row per month+event+tier+category). Preserves
# aggregate signal for long-term institutional trend analysis while bounding
# file growth. At ~30-min cron cadence, 365 days ≈ 17k raw anon rows before
# compaction; afterwards each month compresses to a handful of summary rows.
ANON_COMPACTION_MAX_DAYS = 365
```

#### 6b. Add `_compact_anon_entries` helper before `save_anon_changelog`

```python
def _compact_anon_entries(entries: list[dict]) -> list[dict]:
    """Compact old anonymized records into monthly summary counts.

    Records newer than ``ANON_COMPACTION_MAX_DAYS`` pass through unchanged.
    Older records are grouped by (year-month, event type, tier, category) and
    replaced with a single summary dict per group carrying a ``count``.
    Already-compacted summary rows (``event_summary: True``) are merged into
    the same grouping so re-runs are idempotent.
    """
    from datetime import datetime, timedelta, timezone
    from collections import Counter

    compact_cutoff = (
        datetime.now(timezone.utc) - timedelta(days=ANON_COMPACTION_MAX_DAYS)
    ).strftime("%Y-%m-%d")

    recent: list[dict] = []
    old_groups: Counter = Counter()

    for row in entries:
        ts = row.get("timestamp_utc") or row.get("date") or ""
        date_str = ts[:10] if ts else ""

        if not date_str or date_str >= compact_cutoff:
            recent.append(row)
            continue

        month = date_str[:7]
        event = row.get("event")
        tier = row.get("tier")
        category = row.get("category")
        count = row.get("count", 1) if row.get("event_summary") else 1
        old_groups[(month, event, tier, category)] += count

    summaries: list[dict] = []
    for (month, event, tier, category), count in sorted(old_groups.items()):
        summaries.append({
            "event_summary": True,
            "month": month,
            "event": event,
            "tier": tier,
            "category": category,
            "count": count,
        })

    return summaries + recent
```

#### 6c. Invoke compaction in `save_anon_changelog`

After the existing `out.sort(...)` line and before `_atomic_write_text(...)`:

```python
    out = _compact_anon_entries(out)
```

Idempotency requirement: `_compact_anon_entries` must accept its own previous output. A summary row carries `event_summary: True` and a `count` field; merging summaries adds counts together.

---

## Acceptance criteria

Every item must hold before commit. Verify in order.

| Check | Command / Action | Pass condition |
|---|---|---|
| Syntax | `python -m py_compile scraper/client.py scraper/parsers.py scraper/store.py scraper/sweep.py tests/test_sweep.py` | exit 0, no output |
| Imports | `python -c "from scraper import sweep, client, parsers, store"` | exit 0 |
| Lint (if configured) | `python -m flake8 scraper/ tests/` | no new violations vs baseline |
| Test suite | `python -m pytest tests/ -q` | all tests pass; the two updated sweep tests still cover both WAF paths |
| Module surface | `grep -E "_waf_block_streak\|_on_waf_block_observed\|_on_waf_block_cleared\|_waf_backoff_seconds\|_reset_waf_block_streak_for_tests" scraper/sweep.py` | no matches |
| Compaction idempotent | Add a unit test in `tests/test_store.py` that calls `_compact_anon_entries` twice on the same input and asserts equal output |
| Parser tightening | Add a unit test in `tests/test_parsers.py` that confirms `_looks_like_person_name("HAMILTON COUNTY, OHIO")` returns `False` and `_looks_like_person_name("DOE, JOHN MICHAEL")` returns `True` |

---

## New tests to add

### `tests/test_store.py` (append)

```python
def test_compact_anon_entries_is_idempotent():
    from datetime import datetime, timedelta, timezone

    from scraper.store import _compact_anon_entries

    old_day = (
        datetime.now(timezone.utc) - timedelta(days=400)
    ).strftime("%Y-%m-%d")
    recent_day = (
        datetime.now(timezone.utc) - timedelta(days=10)
    ).strftime("%Y-%m-%d")

    entries = [
        {"event": "booked", "date": old_day, "tier": "F5", "category": "theft"},
        {"event": "booked", "date": old_day, "tier": "F5", "category": "theft"},
        {"event": "released", "date": recent_day, "tier": "M1", "category": "traffic"},
    ]

    first = _compact_anon_entries(entries)
    second = _compact_anon_entries(first)

    assert first == second, "compaction must be idempotent"
    assert any(r.get("event_summary") and r.get("count") == 2 for r in first)
    assert any(r.get("event") == "released" and not r.get("event_summary") for r in first)
```

### `tests/test_parsers.py` (append)

```python
def test_looks_like_person_name_rejects_boilerplate():
    from scraper.parsers import _looks_like_person_name

    assert _looks_like_person_name("DOE, JOHN MICHAEL") is True
    assert _looks_like_person_name("HAMILTON COUNTY, OHIO") is False
    assert _looks_like_person_name("SHERIFF, OFFICE") is False
    assert _looks_like_person_name("DOE,") is False  # no letters after comma
```

---

## Commit and PR

After all acceptance checks pass:

1. Stage exactly these files: `scraper/client.py`, `scraper/parsers.py`, `scraper/store.py`, `scraper/sweep.py`, `tests/test_sweep.py`, `tests/test_store.py`, `tests/test_parsers.py`.
2. Commit with this message verbatim:

```
fix(scraper): apply 6 audit remediations from 2026-05-21 review

1. client: serialize crawl-delay sleep inside the lock (was racing on
   _last_request_at, allowing 16 workers to burst past WAF tripwires).
2. client: align retry loop with docstring (range(2) -> range(1)); now
   issues at most one retry on 5xx/429 as documented.
3. sweep: replace module-global _waf_block_streak with a per-run
   WafBackoffTracker dataclass; observe() atomically returns
   (streak, backoff) so the value never goes stale under concurrency.
4. parsers: tighten _name_from_container_text with a boilerplate
   keyword denylist and a letters-after-comma requirement, so footer
   strings like "HAMILTON COUNTY, OHIO" no longer match.
5. client: add keepalive_expiry=30 to httpx.Limits so stale keep-alive
   connections cannot accumulate and time out on reuse.
6. store: compact anon_changelog records older than
   ANON_COMPACTION_MAX_DAYS (365) into monthly summary counts, bounding
   file growth while preserving aggregate signal. Compaction is
   idempotent.

Tests:
- baseline pass count (pre-change): <N>
- post-change pass count: <N>+2 (two new tests for compaction +
  boilerplate rejection)
```

3. Open a PR against the default branch titled:
   `Audit remediations 2026-05-21: thread safety, retry semantics, anon log compaction`

PR body should reference each fix number and link to the line ranges in the original review. Do not squash; the single commit above is the intended history.

---

## Do-not-do list

1. Do not rename existing public functions (`_fetch_one`, `_fetch_details`, `_fetch_detail_with_retry`).
2. Do not change the `Snapshot` schema or bump `SNAPSHOT_SCHEMA_VERSION`.
3. Do not touch `data/*.json` files. Compaction runs at write time, not as a migration.
4. Do not introduce new runtime dependencies. Everything required is already in `requirements.txt` (`httpx`, `pydantic`, `selectolax`, stdlib).
5. Do not delete the back-compat aliases at the bottom of `scraper/sweep.py` (`_sweep_looks_healthy`, `_prune_photos`); other modules may import them.
6. Do not change crawl-delay timing constants (`DEFAULT_CRAWL_DELAY`, `DEFAULT_CONCURRENCY`).
7. Do not edit `.github/workflows/*` files.

---

## Rollback

If post-commit verification fails or production behavior regresses, recover using one of the paths below.

### Before pushing

```bash
git reset --hard HEAD~1
```

### After pushing, before merge

```bash
git revert <commit-sha>
git push
```

### After merge to default branch

Open a revert PR from the GitHub UI on the merge commit. The revert keeps the audit findings traceable in history while restoring prior behavior. Do not force-push to the default branch.

### Partial rollback

Each fix lives in a distinct hunk. To keep some fixes and drop others, restore individual files from the pre-change tree:

```bash
git checkout HEAD~1 -- scraper/<file>
```

This restores one file to its prior state without touching the others. The corresponding new test in `tests/` may then fail. Remove that test in the same partial-rollback commit.

### Rollback decision table

| Symptom after deploy | Most likely culprit | Recommended action |
|---|---|---|
| Sweep wall-clock 2x slower | Fix 1 over-serializing requests | Partial rollback of `scraper/client.py` `_sleep_for_crawl_delay` only |
| Tests pass locally, CI fails on `test_sweep.py` | Fix 3 tracker plumbing missed a caller | Re-check `_fetch_one` callers in `tests/test_sweep.py`; do not roll back |
| `anon_changelog.json` shrinks unexpectedly on first run | Fix 6 compacting historical rows that crossed the 365-day cutoff | Expected behavior; verify monthly summary rows are present before rolling back |
| WAF blocks spike immediately | Fix 5 keepalive_expiry too aggressive | Lower to `keepalive_expiry=10` rather than removing the parameter |
| Detail-page name parse rate drops | Fix 4 boilerplate list too broad | Trim the keyword set; keep the predicate |

---

## Self-check before reporting completion

Answer each question to yourself. If any answer is "no" or "unsure," fix it before claiming done.

1. Did `python -m pytest tests/ -q` pass on the modified tree?
2. Are there exactly 0 remaining references to `_waf_block_streak`, `_on_waf_block_observed`, `_on_waf_block_cleared`, `_waf_backoff_seconds`, `_reset_waf_block_streak_for_tests` across the repo?
3. Does `_compact_anon_entries(_compact_anon_entries(x)) == _compact_anon_entries(x)` hold for the test inputs?
4. Does the patched `_sleep_for_crawl_delay` perform its `time.sleep` inside the `with self._lock:` block?
5. Does `get_response` issue at most 2 total HTTP requests (1 original + 1 retry)?
6. Does the new `_looks_like_person_name` predicate accept `"DOE, JOHN MICHAEL"` and reject `"HAMILTON COUNTY, OHIO"`?

When all six answers are "yes," the task is complete.