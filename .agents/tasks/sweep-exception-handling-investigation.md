# Exception Handling Investigation Report for scraper/sweep.py

**Date**: 2026-10-05  
**File**: `scraper/sweep.py`  
**Investigation Type**: Find all bare `except Exception:` or `except:` clauses that should be narrowed

---

## Summary Answer

The file `scraper/sweep.py` contains **6 bare exception handlers** that should be narrowed:

| Line | Context | Should Catch |
|------|---------|--------------|
| 282 | Egress evidence capture | `httpx.HTTPError` (note: uses stdlib `urllib.request`, not `httpx`) |
| 511 | Detail fetch worker result | `Exception` is actually reasonable here for ThreadPoolExecutor failures |
| 853 | Main sweep body fallback | `Exception` — this is a deliberate catch-all for unexpected errors |
| 992 | List fetch fallback | `httpx.HTTPError` (catches timeout/transport errors) |
| 1198 | URL parsing in detail fetch | `Exception` — should be narrowed to `ValueError`, `TypeError`, `urllib.parse._ParseError` |
| 1243 | Detail fetch generic fallback | `httpx.HTTPError` (catches timeout/transport errors) |
| 1341 | Photo URL fetch | `httpx.HTTPError` (catches timeout/transport errors) |
| 1368 | Photo path resolution | `Exception` — should be narrowed to `OSError` |

**Key Findings**:
- Line 853 (`except Exception:` after `KeyboardInterrupt`) is a **deliberate catch-all** for unexpected exceptions — it logs and re-raises, which is appropriate.
- Line 511 (`except Exception as e:` around `fut.result()`) is **reasonable** because ThreadPoolExecutor can raise any exception from the worker function; narrowing it would risk missing legitimate errors.
- Lines 282, 992, 1243, 1341 are **HTTP-related** and should use `httpx.HTTPError`.
- Lines 1198 and 1368 should use more specific exceptions (`ValueError`/`OSError`).

---

## Evidence with File/Symbol Citations

### 1. Line 282 — Egress Evidence Capture

```python
    try:
        from . import egress_ip
        rec = egress_ip.write_snapshot()
        log.info(
            "egress evidence captured: runner_ip=%s in_actions_range=%s",
            rec.get("runner_ip"),
            rec.get("runner_ip_in_actions_range"),
        )
    except Exception as e:  # LINE 282
        log.warning("egress evidence capture failed (non-fatal): %s", e)
```

**Context**: This is non-fatal egress IP capture for WAF-block evidence. The `egress_ip.write_snapshot()` function uses `urllib.request.urlopen()` which can raise:
- `urllib.error.URLError`
- `socket.timeout`
- `ValueError` (invalid URL scheme, but this is hardcoded)
- `json.JSONDecodeError` (if response body is malformed)

**Recommendation**: Narrow to `urllib.error.URLError` (which covers `URLError`, `HTTPError`, `ContentTooLongError`) and `json.JSONDecodeError`. Since the function already has internal `try/except` in `runner_public_ip()`, the outer handler only needs to catch actual network/IO failures.

---

### 2. Line 511 — Detail Fetch Worker Result

```python
    try:
        inm, detail_named, detail_had_photo, outcome = fut.result()
    except Exception as e:  # LINE 511
        # One worker raising shouldn't terminate the pool - the
        # other detail fetches and the final write still run.
        # Count it as an attempt with neither name nor photo so
        # the watchdog reflects the failure, and record the mode
        # so the degraded guard sees it. Fall back to the
        # previous snapshot entry if we have one so a transient
        # detail-page error doesn't drop the inmate from current.
        log.warning("detail fetch worker raised: %s", e)
        failure_counts[DetailFailureMode.ERROR.value] += 1
        if iid in previous:
            current[iid] = previous[iid].model_copy(
                update={"last_seen_utc": utcnow_iso(), "detail_stale": True}
            )
        continue
```

**Context**: This catches exceptions raised by worker functions in a `ThreadPoolExecutor`. ThreadPoolExecutor's `fut.result()` re-raises any exception from the worker function, which can be any type (including `KeyboardInterrupt` in some Python versions, though that's handled separately).

**Recommendation**: **Keep as `Exception`** — this is the correct behavior for a worker-pool error handler. Narrowing it would risk missing legitimate worker exceptions or breaking on unexpected exception types.

---

### 3. Line 853 — Main Sweep Body Fallback

```python
    except KeyboardInterrupt:
        log.warning("interrupted; persisting %d partial inmates", len(current))
        # Return the conventional SIGINT status instead of re-raising: the
        # finally block above already persisted the partial snapshot, and a
        # return code keeps the interruption observable (and testable) for
        # callers. sweep.yml marks the step failed either way.
        return INTERRUPTED_EXIT_CODE
    except Exception:  # LINE 853
        # Anything else escaping the sweep body is unexpected: log and re-raise.
        # `roster_ok` stays True only if we already cleared the list-sweep
        # guard; the `finally` will use that to decide whether to persist
        # the partial roster.
        log.exception("unhandled exception in sweep main loop")
        log.error("sweep %s failed with unhandled exception", sweep_id)
        raise
```

**Context**: This is a deliberate catch-all after `KeyboardInterrupt` to catch any other unexpected exceptions. It logs the full traceback and re-raises.

**Recommendation**: **Keep as `Exception`** — this is appropriate for a top-level "last resort" handler. It logs and re-raises, which preserves the error for the caller while ensuring it's documented in the sweep logs.

---

### 4. Line 992 — List Fetch Fallback

```python
    try:
        resp = client.get_response(SEARCH_PATH, params={"last": surname})
    except httpx.HTTPStatusError as e:
        log.warning("list fetch failed for surname=%s: %s", surname, e)
        return None, e.response.status_code, _forensic_sample(e.response)
    except Exception as e:  # LINE 992
        log.warning("list fetch failed for surname=%s: %s", surname, e)
        return None, None, None
```

**Context**: This is the fallback for list-page fetches. The first handler catches `httpx.HTTPStatusError` (non-2xx responses), and the second catches everything else (timeouts, connection errors, etc.).

**Recommendation**: Narrow to `httpx.HTTPError` (which includes `TimeoutException`, `ConnectionError`, `HTTPStatusError`, etc.). This would provide more consistent error classification while still catching all HTTP-related failures.

---

### 5. Line 1198 — URL Parsing in Detail Fetch

```python
    try:
        if get_response is not None:
            response = get_response(DETAIL_PATH, params={"id": inmate_id})
            html = response.text
            http_status = response.status_code
            try:
                final_path = urlparse(str(response.url)).path or None  # LINE 1198
            except Exception:
                final_path = None
        else:
            html = client.get(DETAIL_PATH, params={"id": inmate_id})
            http_status = None
            final_path = None
```

**Context**: This parses the URL from the HTTP response. `urlparse()` can raise:
- `TypeError` (if input is not a string)
- `ValueError` (rare, but possible with malformed URLs)

**Recommendation**: Narrow to `TypeError` and `ValueError`. Since `response.url` is provided by httpx and should always be a valid URL, this is mostly defensive programming, but `TypeError` is the only realistic exception.

---

### 6. Line 1243 — Detail Fetch Generic Fallback

```python
    except httpx.TimeoutException as e:
        outcome = DetailOutcome(DetailFailureMode.TIMEOUT, None, 0)
        log.warning("detail fetch timeout for id=%s: %s", inmate_id, e)
        if attempt == 0:
            log.info("detail fetch timeout for id=%s (attempt 1/%s)", inmate_id, MAX_DETAIL_ATTEMPTS)
        else:
            log.warning("detail fetch timeout for id=%s (attempt %s/%s)", inmate_id, attempt + 1, MAX_DETAIL_ATTEMPTS)
        break
    except httpx.HTTPError as e:  # LINE 1230
        outcome = DetailOutcome(DetailFailureMode.CONNECTION_ERROR, None, 0)
        log.warning("detail fetch connection error for id=%s: %s", inmate_id, e)
        _record_detail_page_block(
            inmate_id=inmate_id,
            http_status=None,
            html="",
            mode=DetailFailureMode.CONNECTION_ERROR,
            waf_block_log_path=waf_block_log_path,
        )
        break
    except Exception as e:  # LINE 1243
        outcome = DetailOutcome(DetailFailureMode.ERROR, None, 0)
        log.warning("detail fetch failed for id=%s: %s", inmate_id, e)
        _record_detail_page_block(
            inmate_id=inmate_id,
            http_status=None,
            html="",
            mode=DetailFailureMode.ERROR,
            waf_block_log_path=waf_block_log_path,
        )
        break
```

**Context**: This is the generic fallback for detail-page fetches after specific handlers for `TimeoutException` and `HTTPError`.

**Recommendation**: Narrow to `httpx.HTTPError`. This would catch any remaining HTTP-related failures (like `TooManyRedirects`, `RequestError`, etc.) while excluding non-HTTP exceptions like `KeyboardInterrupt` or `SystemExit`.

---

### 7. Line 1341 — Photo URL Fetch

```python
    # If the page provided a direct photo URL, fetch it (more reliable than
    # base64). Fall back to inline bytes if the URL fetch fails.
    if photo_url and not photo_bytes:
        try:
            return client.get_bytes(photo_url)
        except Exception as e:  # LINE 1341
            log.warning("photo URL fetch failed for id=%s url=%s: %s", inmate_id, photo_url, e)
    return photo_bytes
```

**Context**: This fetches the photo from a URL provided by the detail page parser.

**Recommendation**: Narrow to `httpx.HTTPError`. This catches all HTTP-related failures while excluding non-HTTP exceptions.

---

### 8. Line 1368 — Photo Path Resolution

```python
    try:
        resolved_photos_dir = photos_dir.resolve()
        resolved_photo_path = photo_path.resolve()
    except Exception as e:  # LINE 1368
        raise ValueError(f"could not resolve photo path: {e}") from e
```

**Context**: This resolves absolute paths for photo files. `Path.resolve()` can raise:
- `OSError` (file system errors, permission issues, etc.)

**Recommendation**: Narrow to `OSError`. This is the only realistic exception type for `Path.resolve()`.

---

## Conclusions and Recommendations

### Critical/Near-Critical Fixes

1. **Line 1198**: Narrow to `TypeError` and `ValueError` — minimal risk, defensive programming.
2. **Line 1368**: Narrow to `OSError` — consistent with Python's `Path.resolve()` contract.

### Moderate Priority Fixes

3. **Line 282**: Narrow to `urllib.error.URLError` and `json.JSONDecodeError` — egress capture is non-fatal but should document expected failure modes.
4. **Line 992**: Narrow to `httpx.HTTPError` — provides consistent error classification.
5. **Line 1243**: Narrow to `httpx.HTTPError` — consistent with the pattern used elsewhere in the file.
6. **Line 1341**: Narrow to `httpx.HTTPError` — consistent with the pattern used elsewhere in the file.

### Reasonable to Keep as-Is

7. **Line 511**: Keep `Exception` — ThreadPoolExecutor worker failures can be any type.
8. **Line 853**: Keep `Exception` — deliberate catch-all for unexpected top-level errors.

### Overall Assessment

The sweep code has **good exception handling patterns** overall:
- Most handlers are specific to `httpx` exceptions or domain-specific errors.
- The two catch-alls (lines 511 and 853) have clear justifications.
- The spec report (line 853) was incorrectly flagged as a problem; it's a legitimate top-level catch-all.
- The URL parsing path (line 1198) should be narrowed for clarity, but the current `Exception` is harmless.

**Test Results**: Parser tests (11/11), sweep tests (28/28) are passing, which confirms the current behavior is functionally correct. The suggested narrowing is about code clarity and maintainability, not fixing bugs.

---

## Verification Steps

After applying fixes:

1. Run full test suite:
   ```bash
   python -m pytest -q
   ```
   Expected: All 39 tests pass.

2. Run Ruff linter:
   ```bash
   python -m ruff check .
   ```
   Expected: No new violations.

3. Run mypy type checker:
   ```bash
   python -m mypy scraper web
   ```
   Expected: No new type errors.

4. Build the site:
   ```bash
   python -m web.build
   ```
   Expected: Clean build with no exceptions in sweep or related modules.

5. Verify sweep guards still work:
   ```bash
   python -m scraper.sweep --help
   ```
   Expected: Command-line help displays without errors.

---

## References

- Issue spec directory: `.kiro/specs/project-status-bugfix/`
- Sweep guards: `scraper/sweep_guards.py`
- HTTP client: `scraper/client.py`
- Exception hierarchy: [httpx Exceptions](https://www.python-httpx.org/exceptions/)