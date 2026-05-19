# Audit — `simplify` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: Low
- **Recommendation**: Keep but rarely use

## What it does
Reviews recently-changed code for reuse, quality, and efficiency, then applies fixes for the issues it finds.

## Fit for JCStream
JCStream's hot files are densely commented with intent: `web/build.py` explains why CSS is hashed by content (not data timestamp), why both CFS feeds are merged and deduped, and why `base_url` and `site_url` are distinct; `scraper/sweep.py` annotates the 22-minute wall-clock cap, the bootstrap-vs-corrupt distinction, and the `roster_ok` flag's role in suppressing synthetic "released" events. The code is small (~3k LOC), hand-tuned, and the owner's CLAUDE.md explicitly warns against re-litigating settled decisions — so most "simplifications" a generic skill would propose are already considered and rejected.

## Realistic triggers in this project
- "clean this up" / "tidy this function" — rare; owner usually asks for specific edits.
- "is this code OK?" — possible on a fresh helper just added to `web/build.py`.
- "review my last commit" — overlaps with the built-in `/review` skill, which is the better route.
- "any dead code here?" — plausible after a feature removal.

## Risk
High churn risk: it could collapse the deliberate dedup loop in `build.py`, inline the `_sweep_looks_healthy` back-compat alias, or strip "redundant" comments that are actually load-bearing operational notes.

## Recommendation rationale
Keep enabled because it's a personal/harness skill and disabling isn't really on the table — but it's a poor fit for this repo. The codebase rewards reading comments, not refactoring; the project-specific specialists (`jcstream-build-helper-author`, `jcstream-scraper-author`) already cover quality concerns with domain context `simplify` lacks. Reach for `/review` instead when the owner asks for a code check.
