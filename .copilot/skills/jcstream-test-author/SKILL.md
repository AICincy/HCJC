# JCStream Test Author
---
name: jcstream-test-author
description: "Test authoring skill for JCStream"
applyTo:
	- "tests/**"
	- "conftest.py"
---

Purpose
- Write and maintain unit tests and fixtures for the JCStream codebase.

Use when
- "pytest", "test", "fixture", "add coverage", "failing test" appears in the prompt.

What this skill does
- Add focused tests, fixtures, and CI-friendly assertions. Prefer small, isolated tests.
- Document changes to test fixtures and mocks.

Checks
- Run `python -m pytest -q` before committing; fix test failures introduced by changes.
- Prefer `monkeypatch` over networked mocks; do not add heavy external deps.

Files to inspect
- `tests/`, `tests/fixtures/`, `conftest.py`.

Triggers
- "add a test", "fix the failing test", "write fixture".
