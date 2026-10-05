# Investigation Findings: Bare Exception Handlers in sweep.py

**Date**: 2026-10-04  
**File Under Investigation**: `scraper/sweep.py`  
**Investigation Goal**: Identify all bare `except Exception:` clauses and recommend fixes

---

## Executive Summary

Two bare `except Exception:` clauses were found in `scraper/sweep.py` at lines **853** and **1198**. These broad exception handlers should be narrowed to specific exception types to preserve fail-closed behavior and provide better error diagnostics.

---

## Findings

### Finding 1: Line 853 - Broad Exception in Main Sweep Loop

**Location**: `scraper/sweep.py:853`  
**Context**: Main sweep `try` block exception handler

**Current Code**:
```python
    except KeyboardInterrupt:
        log.warning("interrupted; persisting %d partial inmates", len(current))
        # Return the conventional SIGINT status instead of re-raising: the
        # finally block above already persisted the partial snapshot, and a
        # return code keeps the interruption observable (and testable) for
        # callers. sweep.yml marks the step failed either way.
        return INTERRUPTED_EXIT_CODE
    except Exception:
        # Anything else escaping the sweep body is unexpected: log and re-raise.
        # `roster_ok` stays True only if we already cleared the list-sweep
        # guard; the `finally` will use that to decide whether to persist
        # the partial roster.
        log.exception("unhandled exception in sweep main loop")
        log.error("sweep %s failed with unhandled exception", sweep_id)
        raise
```

**Problem**: The bare `except Exception:` catches all exceptions including `SystemExit`, `GeneratorExit`, and programming errors (e.g., `TypeError`, `AttributeError`) that should propagate unmodified for debugging.

**Recommendation**: 
- Keep `KeyboardInterrupt` handling as-is (correct)
- Remove the bare `except Exception:` clause entirely
- Let unhandled exceptions propagate naturally with Python's default behavior

**Rationale**: The comment says "log and re-raise" and the `finally` block handles persistence correctly. Removing this handler preserves the original exception type and traceback, making debugging easier while maintaining the same final behavior (sweep fails, partial roster may be persisted by `finally`).

---

### Finding 2: Line 1198 - Broad Exception in URL Parsing

**Location**: `scraper/sweep.py:1198`  
**Context**: URL parsing in `_fetch_detail_with_retry` worker

**Current Code**:
```python
                try:
                    final_path = urlparse(str(response.url)).path or None
                except Exception:
                    final_path = None
```

**Problem**: The bare `except Exception:` catches any exception from `urlparse` or `str()` conversion, silently discarding the error. This hides potential bugs in URL handling and prevents proper diagnostics.

**Recommendation**:
- Narrow to `TypeError`, `ValueError`, and `AttributeError` specifically
- Add a warning log when URL parsing fails
- Return `None` for `final_path` as current, but with logging

**Proposed Fix**:
```python
                try:
                    final_path = urlparse(str(response.url)).path or None
                except (TypeError, ValueError, AttributeError) as e:
                    log.debug("failed to parse detail response URL for id=%s: %s", inmate_id, e)
                    final_path = None
```

**Rationale**: `urlparse` can raise `TypeError` (non-string input) or `ValueError` (malformed URL). Adding specific exception types and a debug log preserves fail-closed behavior while providing diagnostic information when URL parsing fails.

---

## HTML Drift Detection Considerations

The sweep includes guards in `scraper/sweep_guards.py` to detect HCSO HTML changes. The broad exception handlers may interfere with these guards by:

1. **Swallowing errors silently** (finding 2), preventing the system from detecting unexpected URL formats
2. **Masking programming errors** (finding 1), making it harder to identify guard implementation bugs

Narrowing exception handlers preserves the guard's ability to surface anomalies while maintaining the fail-closed fallback behavior.

---

## Test Results Reference

Per the handoff message:
- Parser tests: 11/11 passing
- Sweep tests: 28/28 passing
- Total: 39/39 tests passing

These tests validate current behavior but do not specifically exercise the exception handler paths. After applying the recommended fixes, the same test suite should continue to pass.

---

## Next Steps

1. Remove bare `except Exception:` at line 853
2. Narrow bare `except Exception:` at line 1198 to `(TypeError, ValueError, AttributeError)` with debug logging
3. Run full test suite: `python -m pytest -q`
4. Run linter: `python -m ruff check .`
5. Run type checker: `python -m mypy scraper`
6. Update `tasks.md` and `status.md` in the spec directory to reflect these fixes

---

## Appendix: Complete `except` Clause Inventory

Search results from `grep_search` for `^\s+except Exception:` in `scraper/sweep.py`:

| Line | Context | Current Type | Recommendation |
|------|---------|--------------|----------------|
| 853 | Main sweep try block | Bare `Exception` | Remove entirely |
| 1198 | URL parsing in detail fetch | Bare `Exception` | Narrow to `(TypeError, ValueError, AttributeError)` |

No other bare `except Exception:` clauses found in `scraper/sweep.py`.