# Implementation Plan

## Bug Condition Exploration Tests

- [ ] **Property 1: Bug Condition** - Parser Robustness Exploration Test
  - **IMPORTANT**: Write this property-based test BEFORE implementing the fix
  - **GOAL**: Surface counterexamples that demonstrate the parser bugs exist
  - Test all 6 parser bugs:
    - Test 1.1: title-case name format ("John Doe") - should extract from meta/title fallback, NOT return empty
    - Test 1.2: renamed charge labels ("Charge Description") - should parse with regex, NOT silently empty
    - Test 1.3: photo width change (280px) - should use JPEG-SOI byte-marker fallback, NOT display zero photos
    - Test 1.4: path-form ID (`/inmate-detail/123/`) - should match regex, NOT skip record
    - Test 1.5: punctuation label ("Class #") - should accept regex pattern, NOT silently drop
    - Test 1.6: zero structured fields - should emit breadcrumb log, NOT produce empty record
  - Run test on CURRENT code - expect PASS (this confirms regression coverage for existing parser behavior)
  - Document counterexamples found to understand root cause
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [ ] **Property 2: Preservation** - Parser Preservation Test
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for standard inputs (all-caps names, standard labels, 274px photos, query-string IDs)
  - Write property-based tests capturing observed behavior patterns
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code - expect PASS (this confirms baseline behavior to preserve)
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] **Property 1: Bug Condition** - Sweep Reliability Exploration Test
  - **IMPORTANT**: Write this property-based test BEFORE implementing the fix
  - **GOAL**: Surface counterexamples that demonstrate the sweep bugs exist
  - Test both sweep bugs:
    - Test 1.7: KeyboardInterrupt during sweep - should complete changelog append, NOT synthesize released events
    - Test 1.8: corrupt snapshot file - should return sentinel, NOT return empty dict
  - Run test on UNFIXED code - expect FAILURE (this confirms the bugs exist)
  - Document counterexamples found to understand root cause
  - _Requirements: 1.7, 1.8_

- [ ] **Property 2: Preservation** - Sweep Preservation Test
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for healthy sweeps (≥50% roster, ≥70% names found)
  - Write property-based tests capturing observed behavior patterns
  - Run tests on UNFIXED code - expect PASS (this confirms baseline behavior to preserve)
  - _Requirements: 3.4, 3.5, 3.6, 3.7, 3.8_

- [ ] **Property 1: Bug Condition** - Accessibility Exploration Test
  - **IMPORTANT**: Write this property-based test BEFORE implementing the fix
  - **GOAL**: Surface counterexamples that demonstrate the accessibility bugs exist
  - Test all 4 accessibility bugs:
    - Test 1.9: dialog open + Tab key - focus should stay within dialog, NOT escape to underlying elements
    - Test 1.10: combobox expanded + ArrowDown - should navigate options with aria-activedescendant
    - Test 1.11: tier badge focused + hover - screen reader should hear card_tip content
    - Test 1.12: filter empty - screen reader should announce empty state with role="status"
  - Run test on UNFIXED code - expect FAILURE (this confirms the bugs exist)
  - Document counterexamples found to understand root cause
  - _Requirements: 1.9, 1.10, 1.11, 1.12_

- [ ] **Property 2: Preservation** - Accessibility Preservation Test
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for standard accessibility patterns
  - Write property-based tests capturing observed behavior patterns
  - Run tests on UNFIXED code - expect PASS (this confirms baseline behavior to preserve)
  - _Requirements: 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15_

- [ ] **Property 1: Bug Condition** - Networking Exploration Test
  - **IMPORTANT**: Write this property-based test BEFORE implementing the fix
  - **GOAL**: Surface counterexamples that demonstrate the networking bugs exist
  - Test both networking bugs:
    - Test 1.13: 429 response with Retry-After - should retry with capped delay, NOT treat as hard failure
    - Test 1.14: schema change with where clause errors - should narrow exception, NOT catch broad Exception
    - Test 1.15: docstring vs behavior mismatch - should reconcile docstring and actual behavior
  - Run test on UNFIXED code - expect FAILURE (this confirms the bugs exist)
  - Document counterexamples found to understand root cause
  - _Requirements: 1.13, 1.14, 1.15_

- [ ] **Property 2: Preservation** - Networking Preservation Test
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for standard networking scenarios (5xx retries, valid current.json)
  - Write property-based tests capturing observed behavior patterns
  - Run tests on UNFIXED code - expect PASS (this confirms baseline behavior to preserve)
  - _Requirements: 3.12, 3.13_

## Bug Fix Implementation

- [ ] **Property 1: Expected Behavior** - Parser Fixes Verification
  - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
  - The test from task 1 encodes the expected behavior
  - When this test passes, it confirms the expected behavior is satisfied
  - Run parser exploration test from step 1
  - **EXPECTED OUTCOME**: Test PASSES (confirms all 6 parser bugs are fixed)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [ ] **Property 2: Preservation** - Parser Preservation Verification
  - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
  - Run parser preservation tests from step 2
  - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] **Property 1: Expected Behavior** - Sweep Fixes Verification
  - **IMPORTANT**: Re-run the SAME test from task 3 - do NOT write a new test
  - Run sweep exploration test from step 3
  - **EXPECTED OUTCOME**: Test PASSES (confirms both sweep bugs are fixed)
  - _Requirements: 2.7, 2.8_

- [ ] **Property 2: Preservation** - Sweep Preservation Verification
  - **IMPORTANT**: Re-run the SAME tests from task 4 - do NOT write new tests
  - Run sweep preservation tests from step 4
  - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
  - _Requirements: 3.4, 3.5, 3.6, 3.7, 3.8_

- [ ] **Property 1: Expected Behavior** - Accessibility Fixes Verification
  - **IMPORTANT**: Re-run the SAME test from task 5 - do NOT write a new test
  - Run accessibility exploration test from step 5
  - **EXPECTED OUTCOME**: Test PASSES (confirms all 4 accessibility bugs are fixed)
  - _Requirements: 2.9, 2.10, 2.11, 2.12_

- [ ] **Property 2: Preservation** - Accessibility Preservation Verification
  - **IMPORTANT**: Re-run the SAME tests from task 6 - do NOT write new tests
  - Run accessibility preservation tests from step 6
  - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
  - _Requirements: 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15_

- [ ] **Property 1: Expected Behavior** - Networking Fixes Verification
  - **IMPORTANT**: Re-run the SAME test from task 7 - do NOT write a new test
  - Run networking exploration test from step 7
  - **EXPECTED OUTCOME**: Test PASSES (confirms all 3 networking bugs are fixed)
  - _Requirements: 2.13, 2.14, 2.15_

- [ ] **Property 2: Preservation** - Networking Preservation Verification
  - **IMPORTANT**: Re-run the SAME tests from task 8 - do NOT write new tests
  - Run networking preservation tests from step 8
  - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
  - _Requirements: 3.12, 3.13_

## Status Documentation

- [ ] Create status documentation file
  - Document which bugs are fixed vs remaining
  - Include fix version number
  - Link to specific test cases validating each fix
  - _Requirements: 2.15, 3.15_

## Checkpoint

- [ ] Ensure all tests pass
  - Verify all bug condition exploration tests now pass (Property 1: Expected Behavior)
  - Verify all preservation tests still pass (Property 2: Preservation)
  - Ensure no regressions introduced
  - Run full test suite to confirm everything works

