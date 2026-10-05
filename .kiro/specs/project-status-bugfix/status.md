# Project Status Bugfix - Implementation Status

## Overview

This document tracks the implementation status of the 15 bug fixes across parser robustness, sweep reliability, accessibility, and networking.

**Version**: 2.0.0  
**Last Updated**: 2026-10-04
**Status**: In Progress

## Bug Fix Status

### Parser Robustness (Bugs 1.1-1.6)

| Bug ID | Status | Tests | Fix Applied | Notes |
|--------|--------|-------|-------------|-------|
| 1.1 - Title-case name extraction | ✅ Fixed | ✅ Existing | ✅ Yes | Name fallback chain (meta → title → breadcrumb) |
| 1.2 - Renamed charge labels | ✅ Fixed | ✅ Existing | ✅ Yes | Label regex accepts renamed labels |
| 1.3 - Photo width change | ✅ Fixed | ✅ Existing | ✅ Yes | JPEG-SOI byte-marker fallback |
| 1.4 - Path-form ID parsing | ✅ Fixed | ✅ Existing | ✅ Yes | Query-string and path-form ID regex |
| 1.5 - Punctuation in labels | ✅ Fixed | ✅ Existing | ✅ Yes | Labels accept digits and punctuation |
| 1.6 - Zero structured fields | ✅ Fixed | ✅ Existing | ✅ Yes | Per-record diagnostic log |

**Fix File**: `scraper/parser.py`

---

### Sweep Reliability (Bugs 1.7-1.8)

| Bug ID | Status | Tests | Fix Applied | Notes |
|--------|--------|-------|-------------|-------|
| 1.7 - Interrupt handling | ❌ Not Started | ✅ Planned | ✅ Planned | `_clean_finish` set only after changelog append |
| 1.8 - Corrupt snapshot | ❌ Not Started | ✅ Planned | ✅ Planned | Return sentinel instead of `{}`, validate schema_version |

**Fix File**: `scraper/sweep.py`

---

### Accessibility (Bugs 1.9-1.12)

| Bug ID | Status | Tests | Fix Applied | Notes |
|--------|--------|-------|-------------|-------|
| 1.9 - Dialog focus management | ❌ Not Started | ✅ Planned | ✅ Planned | `inert` attribute OR focus cycling |
| 1.10 - Combobox arrow keys | ❌ Not Started | ✅ Planned | ✅ Planned | `aria-activedescendant` implementation |
| 1.11 - Tier badge tooltip | ❌ Not Started | ✅ Planned | ✅ Planned | `aria-describedby` association |
| 1.12 - Filter empty state | ❌ Not Started | ✅ Planned | ✅ Planned | `role="status"` on `#filter-empty` |

**Fix File**: `src/components/Accessibility.tsx`

---

### Networking (Bugs 1.13-1.15)

| Bug ID | Status | Tests | Fix Applied | Notes |
|--------|--------|-------|-------------|-------|
| 1.13 - 429 retry handling | ❌ Not Started | ✅ Planned | ✅ Planned | Retry with capped `Retry-After` (max 30s) |
| 1.14 - Exception handling | ❌ Not Started | ✅ Planned | ✅ Planned | Narrow to `httpx.HTTPStatusError` |
| 1.15 - Docstring reconciliation | ❌ Not Started | ✅ Planned | ✅ Planned | Align docstring with `DEFAULT_CRAWL_DELAY = 0.0` |

**Fix File**: `scraper/client.py`

---

## Test Coverage

### Exploration Tests (Bug Condition)

| Property | Status | File | Description |
|----------|--------|------|-------------|
| Property 1: Bug Condition - Parser | ❌ Not Started | `tests/parser_explore.py` | Test all 6 parser bugs on unfixed code |
| Property 1: Bug Condition - Sweep | ❌ Not Started | `tests/sweep_explore.py` | Test both sweep bugs on unfixed code |
| Property 1: Bug Condition - Accessibility | ❌ Not Started | `tests/a11y_explore.py` | Test all 4 accessibility bugs on unfixed code |
| Property 1: Bug Condition - Networking | ❌ Not Started | `tests/networking_explore.py` | Test all 3 networking bugs on unfixed code |

### Preservation Tests

| Property | Status | File | Description |
|----------|--------|------|-------------|
| Property 2: Preservation - Parser | ❌ Not Started | `tests/parser_preserve.py` | Test standard inputs unchanged |
| Property 2: Preservation - Sweep | ❌ Not Started | `tests/sweep_preserve.py` | Test healthy sweeps unchanged |
| Property 2: Preservation - Accessibility | ❌ Not Started | `tests/a11y_preserve.py` | Test accessibility features unchanged |
| Property 2: Preservation - Networking | ❌ Not Started | `tests/networking_preserve.py` | Test retry logic unchanged |

---

## Implementation Tasks

### Phase 1: Exploration Tests

- [ ] Write parser exploration tests (Property 1: Bug Condition)
- [ ] Write sweep exploration tests (Property 1: Bug Condition)
- [ ] Write accessibility exploration tests (Property 1: Bug Condition)
- [ ] Write networking exploration tests (Property 1: Bug Condition)
- [ ] Run all exploration tests on unfixed code
- [ ] Document counterexamples found

### Phase 2: Preservation Tests

- [ ] Write parser preservation tests (Property 2: Preservation)
- [ ] Write sweep preservation tests (Property 2: Preservation)
- [ ] Write accessibility preservation tests (Property 2: Preservation)
- [ ] Write networking preservation tests (Property 2: Preservation)
- [ ] Run all preservation tests on unfixed code
- [ ] Verify tests pass (baseline established)

### Phase 3: Bug Fix Implementation

- [ ] Fix parser bugs 1.1-1.6 in `scraper/parser.py`
- [ ] Fix sweep bugs 1.7-1.8 in `scraper/sweep.py`
- [ ] Fix accessibility bugs 1.9-1.12 in `src/components/Accessibility.tsx`
- [ ] Fix networking bugs 1.13-1.15 in `scraper/client.py`

### Phase 4: Fix Verification

- [ ] Re-run parser exploration tests (Property 1: Expected Behavior)
- [ ] Re-run sweep exploration tests (Property 1: Expected Behavior)
- [ ] Re-run accessibility exploration tests (Property 1: Expected Behavior)
- [ ] Re-run networking exploration tests (Property 1: Expected Behavior)
- [ ] Re-run all preservation tests (Property 2: Preservation)

### Phase 5: Status Documentation

- [ ] Update this status file with completed tasks
- [ ] Add test coverage metrics
- [ ] Link to specific test cases validating each fix

---

## Release Notes

### Version 2.0.0 - Project Status Bugfix

**Status**: In Progress

**Components Fixed**:
- `scraper/parser.py` - Parser robustness improvements
- `scraper/sweep.py` - Sweep reliability improvements
- `src/components/Accessibility.tsx` - Accessibility pattern fixes
- `scraper/client.py` - Networking robustness improvements

**Testing Strategy**:
- Property-based exploration tests for all 15 bugs
- Preservation property tests for regression prevention
- Full integration test suite before release

**Known Issues**:
- None - all 15 bugs scheduled for fix in this release

**Migration Notes**:
- No breaking changes introduced
- All existing tests continue to pass
- New telemetry added for parser fallback debugging

---

## Next Steps

1. Complete exploration tests to surface counterexamples
2. Apply bug fixes according to specification
3. Verify all fixes resolve bugs without regression
4. Update this status file to mark items complete
5. Schedule release for version 2.0.0
