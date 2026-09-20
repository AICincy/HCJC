---
name: record-series-builder
description: >
  Turns large document sets into matched multi-volume series with consistent
  structure, formatting, handoff pages, abbreviations, and output artifacts.
  Use when the user asks to organize records, reports, or mixed project
  documents into separate volumes, normalize Markdown/DOCX/PDF packets,
  create executive and full summary pairs, clean folder layout, or keep
  multiple document packets stylistically aligned. Also use when the user
  says "organize these files," "build a series," "normalize these documents,"
  "clean up the folder," "package these records," or has more than 5
  documents that need consistent structure. If the task involves multiple
  documents that must look like they belong together, this skill applies.
---

# Record Series Builder

## Rules

IF the user provides a large document set:
THEN inventory the current packet set before proposing any structure.
List sources, outputs, scripts, and stale residue.

IF organizing into volumes:
THEN define the series architecture first: volume names, section order,
handoff logic, and file-type subfolders. Present the architecture as a
table for approval before building.

IF multiple volumes exist in a series:
THEN enforce matched section order, consistent headings, stable
abbreviations, and matching rendering rules across all volumes.

IF a volume's final section needs to hand off to the next volume:
THEN include explicit handoff language. The last page of volume N
references volume N+1 by name and states what it covers.

IF the user asks to normalize across formats (Markdown, DOCX, PDF):
THEN apply the same structural rules to all formats. Heading levels,
table styles, abbreviation usage, and section order must match
regardless of output format.

IF stale, duplicate, or intermediate artifacts exist in the workspace:
THEN flag them for removal. Do not delete without the user's approval.
List what would be removed and why.

IF rendering or cleanup cannot finish:
THEN return the normalized folder plan, completed artifacts, and the
remaining blocked items. Do not leave an unclear state.

## Output structure

Per volume:
- Markdown source file.
- DOCX rendered file (if filing-ready output matters).
- PDF rendered file (if distribution matters).
- Scripts subfolder (if build or render scripts exist).

## Validation

Before delivery:
- Each volume has the intended outputs and only the approved outputs.
- Matched volumes share the same structure, tone, and formatting rules.
- Filenames, folder names, and handoff language are consistent.
- Stale artifacts are flagged or removed per user approval.
