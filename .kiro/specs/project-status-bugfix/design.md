# Project Status Bugfix Design

## Overview

This document outlines the architectural approach for fixing 15 known bugs across the JCStream project. The bugs span four categories: parser robustness (bugs 1.1-1.6), sweep reliability (bugs 1.7-1.8), accessibility (bugs 1.9-1.12), and networking (bugs 1.13-1.15).

The approach uses the bug condition methodology:
- **C(X)**: identifies buggy inputs/conditions
- **P(result)**: expected correct behavior for buggy inputs
- **¬C(X)**: non-buggy inputs that must be preserved

The design documents current status with fixes annotated, provides technical solutions for each bug category, and outlines a comprehensive testing strategy for validation.

## Glossary

- **Bug_Condition (C)**: The condition that triggers a bug - a specific input or state that causes incorrect behavior
- **Property (P)**: The desired behavior when bug condition holds - correct system response
- **Preservation**: Existing behavior that must remain unchanged for non-buggy inputs
- **Parser**: Code responsible for extracting structured data from HCSO detail pages
- **Sweep**: The periodic process of fetching current inmate roster and comparing against previous state
- **Inmate Record**: Structured data extracted from detail pages containing bio, name, and charges
- **Changelog**: Time-series log of inmate status changes (booked, released, etc.)
- **Accessibility (a11y)**: Techniques to ensure screen reader compatibility and keyboard navigation

## Bug Details

### Bug Conditions

The 15 bugs can be categorized into four groups based on their root cause patterns:

**Parser Robustness Bugs (1.1-1.6)**
```
FUNCTION isParserBug(input)
  INPUT: input of type PageInfo (HTML content, page URL, element selectors)
  OUTPUT: boolean
  
  RETURN (input.name_format == "title-case" AND heading selector fails)
         OR (input.label_name != expected AND no fallback present)
         OR (input.photo_width != 274px AND no byte-marker fallback)
         OR (input.id_format == "path-form" AND query-string regex doesn't match)
         OR (input.label_pattern != r"^[A-Za-z]" AND label dropped silently)
         OR (input.structured_fields == 0 AND no per-record breadcrumb)
END FUNCTION
```

**Sweep Reliability Bugs (1.7-1.8)**
```
FUNCTION isSweepBug(input)
  INPUT: input of type SweepContext (snapshot state, interrupt status, file integrity)
  OUTPUT: boolean
  
  RETURN (input.interrupted AND changelog incomplete)
         OR (input.snapshot_corrupted AND error swallowed)
END FUNCTION
```

**Accessibility Bugs (1.9-1.12)**
```
FUNCTION isAccessibilityBug(input)
  INPUT: input of type AccessibilityTest (focus state, keyboard event, ARIA attributes)
  OUTPUT: boolean
  
  RETURN (input.dialog_open AND input.key == "Tab" AND focus_escapes_dialog)
         OR (input.combo_expanded AND input.key IN ["ArrowUp", "ArrowDown"] AND no activeDescendant)
         OR (input.tier_focused AND input.hover AND AT_ignores_card_tip)
         OR (input.filter_empty AND input.role != "status")
END FUNCTION
```

**Networking Bugs (1.13-1.15)**
```
FUNCTION isNetworkingBug(input)
  INPUT: input of type NetworkRequest (status_code, headers, docstring)
  OUTPUT: boolean
  
  RETURN (input.status_code == 429 AND no_retry_after_honor)
         OR (input.schema_changed AND broad_exception_catch)
         OR (input.docstring != observed_behavior)
END FUNCTION
```

### Examples

**Parser Bug Example (1.1)**
- Expected: Name extracted from `<meta og:title>` fallback, then `<title>`, then log debug breadcrumb
- Actual: `last_name` and `first_name` are empty with no warning

**Parser Bug Example (1.3)**
- Expected: Photo bytes extracted using JPEG-SOI byte-marker fallback, INFO logged when fallback fires
- Actual: Zero photos displayed site-wide when width changes from 274px to 280px

**Accessibility Bug Example (1.9)**
- Expected: Focus cycles within dialog (close button ↔ backdrop) or dialog has `inert`
- Actual: Focus moves to underlying page elements when user presses Tab

**Sweep Bug Example (1.7)**
- Expected: `_clean_finish` flag set only after full changelog append
- Actual: Synthetic `released` events synthesized from partial current vs full previous diff

**Networking Bug Example (1.13)**
- Expected: 429 added to retry branch with capped `Retry-After` honor (max 30 seconds)
- Actual: 429 treated as hard failure with no retry

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

1. **Parser Preservation:**
   - All-caps names with comma (e.g., "DOE, JOHN") continue to extract from heading tier
   - Standard charge labels (Description, ORC Code) continue to parse with same behavior
   - 274px photo width with valid base64 continues to use preferred selector

2. **Sweep Preservation:**
   - Healthy sweeps (≥50% roster fraction, ≥70% names found) continue to write current.json
   - List-row name fallback continues to work when detail fetch fails
   - Normal sweep completion (diff, changelog, photo pruning) continues unchanged

3. **Accessibility Preservation:**
   - Name, charge, ID chip, and filter count continue to be announced with aria-live
   - Search autocomplete from `search.json` continues to display results
   - Lazy-loaded Leaflet map and shooting/CFS lists continue to render below map
   - Noindex meta tags continue to be respected by crawlers

4. **Networking Preservation:**
   - 5xx status codes continue to retry once at 0.5s, then 1s with exponential backoff
   - Valid `data/current.json` files continue to validate against Pydantic model
   - PRA dry-run mode continues to log `to`, `subject`, message body without secrets

**Scope:**
All inputs that do NOT involve the specific bug conditions above should be completely unaffected by the fixes.

## Hypothesized Root Cause

Based on the bug descriptions, the most likely issues are:

1. **Parser Robustness - Incomplete Fallback Chains:**
   - Name extraction uses only heading tier, no meta/title fallback
   - Label matching is exact string match, no regex or fuzzy fallback
   - Photo extraction relies on fixed 274px width, no byte-marker fallback

2. **Parser Robustness - Missing Validation Breadcrumbs:**
   - Zero structured fields doesn't emit warning log with inmate_number context
   - No telemetry on label coverage percentages

3. **Sweep Reliability - Incomplete Interrupt Handling:**
   - `KeyboardInterrupt` cleanup doesn't wait for changelog append
   - Corrupt snapshot error swallowed instead of propagating sentinel

4. **Accessibility - ARIA Pattern Gaps:**
   - Dialog lacks `inert` or focus cycling implementation
   - Search combobox missing `aria-activedescendant` for arrow-key navigation
   - Tier tooltip missing `aria-describedby` association
   - Empty filter state missing `role="status"` announcement

5. **Networking - Incomplete Retry Logic:**
   - 429 rate limit not in retry branch, no `Retry-After` header honor
   - Exception handling too broad (catches all `Exception` instead of specific HTTP errors)
   - Documentation contradicts observed behavior (docstring vs `DEFAULT_CRAWL_DELAY = 0.0`)

## Correctness Properties

Property 1: Parser Robustness - Fallback Chains

_For any_ detail page with non-standard formatting (title-case names, renamed labels, photo width changes, path-form IDs, or digit-containing labels), the fixed parser SHALL extract the required data using fallback mechanisms and emit appropriate debug telemetry.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

Property 2: Sweep Reliability - Clean Shutdown

_For any_ sweep context where `KeyboardInterrupt` occurs or snapshot file is corrupted, the fixed sweep system SHALL either (a) complete changelog append before setting `_clean_finish` flag, or (b) return a sentinel and refuse degraded bootstrap.

**Validates: Requirements 2.7, 2.8**

Property 3: Accessibility - Keyboard and Screen Reader Compatibility

_For any_ user interaction involving keyboard navigation or screen reader announcements, the fixed UI SHALL implement proper ARIA patterns: focus trapping in dialogs, `aria-activedescendant` for combobox navigation, `aria-describedby` for tooltip associations, and `role="status"` for empty state announcements.

**Validates: Requirements 2.9, 2.10, 2.11, 2.12**

Property 4: Networking - Robust Error Handling

_For any_ network response or schema change scenario, the fixed client SHALL: (a) honor 429 `Retry-After` headers with capped retry delay, (b) narrow exception handling to specific HTTP errors, and (c) reconcile documentation with observed behavior.

**Validates: Requirements 2.13, 2.14, 2.15**

Property 5: Preservation - No Regression in Existing Functionality

_For any_ input where the bug conditions do NOT hold, the fixed code SHALL produce exactly the same behavior as the original code for all preserved scenarios including standard name formats, label matching, healthy sweeps, accessibility features, and networking retry logic.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `scraper/parser.py`

**Function**: `extract_inmate_data(html, inmate_number)`

**Specific Changes**:

1. **Name Extraction Enhancement**: Add fallback chain for name extraction
   - First, try original heading tier extraction (preserve backward compatibility)
   - Second, try `<meta property="og:title">` content
   - Third, try `<title>` content
   - Log debug breadcrumb when fallback is used

2. **Label Matching Enhancement**: Add regex pattern for label parsing
   - Accept labels matching `r"^\s*([A-Za-z][A-Za-z0-9 #/_-]*?)\s*:\s*(.*?)\s*$"`
   - This allows punctuation, digits, and various label formats

3. **Photo Extraction Enhancement**: Add JPEG-SOI byte-marker fallback`n   - Try preferred 274px width selector first`n   - If no match, search for JPEG-SOI byte markers (0xFFD8)`n   - Log INFO when fallback fires`n`n4. **Zero Fields Breadcrumb**: Emit warning log for empty structured fields`n   - When parser produces zero structured fields, emit log.info("detail page produced no structured fields for id=%s", inmate_number)

**File**: `scraper/sweep.py`

**Function**: `_fetch_one`, `cleanup_on_interrupt`, `load_current_snapshot`

**Specific Changes**:

1. **Interrupt Handling**: Set `_clean_finish` flag only after full changelog append
   - Move `_clean_finish = True` to after changelog append operation
   - Ensure changelog is written even during KeyboardInterrupt

2. **Corrupt Snapshot Handling**: Return sentinel instead of `{}` for corrupt files
   - Validate `schema_version` on load
   - Raise specific exception for corrupt/invalid files
   - Refuse to bootstrap from degraded sweep

**File**: `src/components/Accessibility.tsx` (or equivalent file)

**Function**: Dialog focus management, combobox arrow-key handling, tier badge tooltip

**Specific Changes**:

1. **Dialog Focus Management**: Add `inert` attribute or focus cycling
   - Set `inert` on all body children except dialog when dialog is open
   - OR cycle focus between close button and backdrop on Tab key

2. **Combobox Arrow-Key Navigation**: Implement `aria-activedescendant`
   - Track active option index for ArrowUp/ArrowDown key handling
   - Update `aria-activedescendant` attribute on combobox
   - Scroll option into view when navigated

3. **Tier Badge Tooltip**: Add `aria-describedby` association
   - Add unique ID to tooltip element
   - Set `aria-describedby="tier-tip-id"` on tier badge
   - Ensure tooltip is in AT tree when visible

4. **Filter Empty State**: Add `role="status"`
   - Set `role="status"` on `#filter-empty` element
   - Ensure screen readers announce "No one in custody matches that filter"

**File**: `scraper/client.py`

**Function**: `fetch_with_retry`, `get_inmate_details`

**Specific Changes**:

1. **429 Retry Handling**: Add 429 to retry branch with capped `Retry-After`
   - Parse `Retry-After` header value
   - Cap at maximum 30 seconds to prevent excessive delays
   - Include 429 in retry status codes

2. **Exception Handling**: Narrow exception scope
   - Catch `httpx.HTTPStatusError` for 429/5xx handling
   - Let `httpx.RequestError` propagate for network issues
   - Cap fallback limit to prevent excessive data fetching

3. **Documentation Reconciliation**: Update docstring or behavior
   - Either update docstring to match `DEFAULT_CRAWL_DELAY = 0.0`
   - OR implement crawl delay based on `Crawl-delay` from robots.txt
   - Ensure UA string reflects actual behavior

**File**: `.kiro/specs/project-status-bugfix/status.md`

**Specific Changes**:

1. **Status Report Format**: Create structured status report
   - Document which bugs are fixed vs remaining
   - Include fix version number
   - Link to specific test cases validating each fix

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that simulate problematic inputs and assert correct behavior. Run these tests on the UNFIXED code to observe failures and understand the root cause.

**Test Cases**:

**Parser Robustness Tests** (will fail on unfixed code):
1. **Title-case Name Test**: Parse detail page with "John Doe" name format (will fail on unfixed code)
2. **Renamed Label Test**: Parse detail page with "Charge Description" instead of "Description" (will fail on unfixed code)
3. **Photo Width Change Test**: Parse detail page with 280px photo width (will fail on unfixed code)
4. **Path-form ID Test**: Parse detail page with `/inmate-detail/123/` URL format (will fail on unfixed code)
5. **Punctuation Label Test**: Parse detail page with "Class #" label (will fail on unfixed code)
6. **Zero Fields Test**: Parse detail page with no structured fields (will fail on unfixed code)

**Sweep Reliability Tests** (will fail on unfixed code):
1. **Interrupt Test**: Trigger KeyboardInterrupt during sweep and verify no synthetic released events (will fail on unfixed code)
2. **Corrupt Snapshot Test**: Load corrupt `data/current.json` and verify sentinel returned (will fail on unfixed code)

**Accessibility Tests** (will fail on unfixed code):
1. **Dialog Tab Test**: Open dialog and press Tab, verify focus stays within dialog (will fail on unfixed code)
2. **Combobox Arrow Test**: Expand combobox and press ArrowDown, verify option selection (will fail on unfixed code)
3. **Tier Badge AT Test**: Focus tier badge and verify screen reader hears `card_tip` content (will fail on unfixed code)
4. **Filter Empty AT Test**: Search with zero results and verify screen reader announces empty state (will fail on unfixed code)

**Networking Tests** (will fail on unfixed code):
1. **429 Retry Test**: Simulate 429 response with Retry-After header (will fail on unfixed code)
2. **Schema Change Test**: Simulate Socrata schema change with where clause errors (will fail on unfixed code)

**Expected Counterexamples**:
- Parser uses only heading tier for names, no meta/title fallback
- Parser requires exact label match, no regex pattern
- Parser relies on fixed 274px width, no byte-marker fallback
- Sweep changelog incomplete during KeyboardInterrupt
- Snapshot error swallowed for corrupt files
- Dialog focus escapes to underlying elements on Tab
- Combobox arrow keys don't navigate options
- Screen reader misses tier tooltip content
- Screen reader misses empty filter announcement
- 429 not in retry branch, no Retry-After honor
- Broad exception catch swallows schema changes
- Docstring contradicts observed behavior

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isParserBug(input) DO
  result := extract_inmate_data_fixed(input.html, input.inmate_number)
  ASSERT result.name IS NOT EMPTY
  ASSERT result.labels ARE PARSED CORRECTLY
  ASSERT result.photos ARE EXTRACTED
  ASSERT result.inmate_number IS PARSED
END FOR

FOR ALL input WHERE isSweepBug(input) DO
  result := sweep_fixed(input.snapshot_path)
  ASSERT _clean_finish SET AFTER CHANGELOG
  ASSERT sentinel RETURNED FOR CORRUPT FILE
END FOR

FOR ALL input WHERE isAccessibilityBug(input) DO
  result := accessibility_test_fixed(input.focus_state, input.keyboard_event)
  ASSERT focus TRAPPED IN DIALOG
  ASSERT aria-activedescendant UPDATED
  ASSERT AT HEARS card_tip CONTENT
  ASSERT AT HEARS EMPTY STATE
END FOR

FOR ALL input WHERE isNetworkingBug(input) DO
  result := client_fixed.fetch_with_retry(input.url, input.headers)
  ASSERT retry WITH 429 AND Retry-After
  ASSERT narrow EXCEPTION CATCHING
  ASSERT docstring MATCHES BEHAVIOR
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isParserBug(input) DO
  result_original := extract_inmate_data_original(input.html, input.inmate_number)
  result_fixed := extract_inmate_data_fixed(input.html, input.inmate_number)
  ASSERT result_original == result_fixed
END FOR

FOR ALL input WHERE NOT isSweepBug(input) DO
  result_original := sweep_original(input.snapshot_path)
  result_fixed := sweep_fixed(input.snapshot_path)
  ASSERT result_original == result_fixed
END FOR

FOR ALL input WHERE NOT isAccessibilityBug(input) DO
  result_original := accessibility_original(input.user_action)
  result_fixed := accessibility_fixed(input.user_action)
  ASSERT result_original == result_fixed
END FOR

FOR ALL input WHERE NOT isNetworkingBug(input) DO
  result_original := client_original.fetch_with_retry(input.url)
  result_fixed := client_fixed.fetch_with_retry(input.url)
  ASSERT result_original == result_fixed
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for standard inputs, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Name Format Preservation**: Observe that all-caps comma format works on unfixed code, write test to verify this continues after fix
2. **Label Matching Preservation**: Observe that standard labels parse correctly on unfixed code, write test to verify this continues after fix
3. **Photo Extraction Preservation**: Observe that 274px width with valid base64 works on unfixed code, write test to verify this continues after fix
4. **Sweep Flow Preservation**: Observe that healthy sweeps write current.json on unfixed code, write test to verify this continues after fix
5. **Accessibility Features Preservation**: Observe that screen reader announcements work on unfixed code, write test to verify this continues after fix
6. **Network Retry Preservation**: Observe that 5xx retries work on unfixed code, write test to verify this continues after fix

### Unit Tests

**Parser Robustness Unit Tests:**
- Parse detail page with title-case name (should extract from fallback)
- Parse detail page with renamed labels (should parse with regex)
- Parse detail page with photo width change (should use byte-marker fallback)
- Parse detail page with path-form ID (should match regex pattern)
- Parse detail page with punctuation in label (should accept regex)
- Parse detail page with zero structured fields (should log breadcrumb)

**Sweep Reliability Unit Tests:**
- Trigger KeyboardInterrupt during sweep (should complete changelog)
- Load corrupt snapshot file (should return sentinel)
- Load valid snapshot file (should validate schema and return Inmate list)

**Accessibility Unit Tests:**
- Dialog with Tab key (should trap focus or use inert)
- Combobox with ArrowDown key (should update aria-activedescendant)
- Tier badge with focus (should have aria-describedby)
- Filter empty with search (should have role="status")

**Networking Unit Tests:**
- 429 response with Retry-After (should retry with capped delay)
- Schema change with where clause errors (should narrow exception)
- 5xx response (should retry with exponential backoff)

### Property-Based Tests

**Parser Property-Based Tests:**
- Generate random name formats (title-case, all-caps, mixed case) and verify extraction
- Generate random label variations and verify parsing with regex
- Generate random photo width values and verify fallback mechanism
- Generate random URL ID formats and verify extraction

**Accessibility Property-Based Tests:**
- Generate random focus sequences and verify focus trapping
- Generate random keyboard events and verify ARIA updates
- Generate random screen reader configurations and verify announcements

**Networking Property-Based Tests:**
- Generate random Retry-After values and verify capping at 30 seconds
- Generate random status codes and verify appropriate retry behavior
- Generate random schema changes and verify proper exception handling

### Integration Tests

**Parser Integration Tests:**
- Full detail page parsing with non-standard formatting
- Multiple pages with varying formats in single sweep
- Verify telemetry emitted for fallback usage

**Sweep Integration Tests:**
- Full sweep workflow with keyboard interrupt
- Bootstrap from corrupt snapshot
- Verify changelog consistency

**Accessibility Integration Tests:**
- Full keyboard navigation flow through roster
- Screen reader test with NVDA/JAWS
- Verify focus management across all interactive elements

**Networking Integration Tests:**
- Full sweep with rate limiting
- Socrata schema change scenario
- Verify documentation matches observed behavior


## Status Tracking

### Current Status

| Bug ID | Category | Status | Fix Applied | Tests Added |
|--------|----------|--------|-------------|-------------|
| 1.1 | Parser | Not Started | Name fallback chain (meta → title → breadcrumb) | ❌ |
| 1.2 | Parser | Not Started | Label regex pattern | ❌ |
| 1.3 | Parser | Not Started | JPEG-SOI fallback | ❌ |
| 1.4 | Parser | Not Started | Path-form ID regex | ❌ |
| 1.5 | Parser | Not Started | Punctuation label regex | ❌ |
| 1.6 | Parser | Not Started | Zero fields breadcrumb | ❌ |
| 1.7 | Sweep | Not Started | Clean interrupt handling | ❌ |
| 1.8 | Sweep | Not Started | Sentinel for corrupt snapshot | ❌ |
| 1.9 | Accessibility | Not Started | Dialog focus management | ❌ |
| 1.10 | Accessibility | Not Started | Combobox aria-activedescendant | ❌ |
| 1.11 | Accessibility | Not Started | Tier badge aria-describedby | ❌ |
| 1.12 | Accessibility | Not Started | Filter empty role="status" | ❌ |
| 1.13 | Networking | Not Started | 429 retry with Retry-After | ❌ |
| 1.14 | Networking | Not Started | Narrow exception handling | ❌ |
| 1.15 | Networking | Not Started | Docstring reconciliation | ❌ |

### Release Notes

**Version 2.0.0 - Project Status Bugfix (In Progress)**

**Status**: In Progress - Implementation not yet started

**Components to Fix**:
- `scraper/parser.py` - Parser robustness improvements (6 bugs)
- `scraper/sweep.py` - Sweep reliability improvements (2 bugs)
- `src/components/Accessibility.tsx` - Accessibility pattern fixes (4 bugs)
- `scraper/client.py` - Networking robustness improvements (3 bugs)

**Testing Strategy**:
- Property-based exploration tests for all 15 bugs
- Preservation property tests for regression prevention
- Full integration test suite before release

**Known Issues**: None - all 15 bugs documented for fix in this release

**Migration Notes**:
- No breaking changes introduced
- All existing tests continue to pass
- New telemetry added for parser fallback debugging

### Next Steps

1. Implement fixes according to specification
2. Run exploratory tests on unfixed code to confirm bug conditions
3. Apply fixes and run fix checking tests
4. Run preservation checking tests to ensure no regression
5. Complete integration tests for full workflow validation
6. Update documentation to reflect fixes
7. Deploy to staging for user acceptance testing

