# AreTheyInJail v2 — locked visual system

## Direction

A modern public index: newspaper-like scanning, retail-search clarity, and human pacing without government ornament or SaaS-dashboard components.

The public-facing identity is **Are They In Jail?**. `JCStream` remains a quiet data/source attribution, not the dominant masthead brand.

## Hard exclusions

- No pill navigation, capsule tags, badge soup, or rounded filter bars.
- No seals in the primary masthead.
- No centered civic crest composition.
- No monospace display logo.
- No Public Sans, IBM Plex, Inter, Roboto, Arial, DM Sans, or system UI as the chosen design voice.
- No beige coffee-shop civic palette.
- No red-as-punishment visual system.
- No dashboard cards for every metric or action.
- No novelty display fonts, loud gradients, or playful illustrations.
- No batch of superficial variants. One system, implemented deeply.

## Typography

### Primary family

Use **Instrument Sans** throughout the public interface, self-hosted in regular, medium, semibold, and bold weights.

Why:
- contemporary and calm;
- friendly without becoming quirky;
- strong at both large search-led headings and dense roster metadata;
- avoids the institutional character of Public Sans and the technical tone of IBM Plex Mono.

### Numeric/data treatment

Use the same family with tabular numerals. Do not introduce a monospace face for booking numbers, ORC codes, timestamps, or counts unless a later usability test proves it necessary.

### Scale

- Brand: 28–34px, 700, tight tracking.
- Hero question: clamp(42px, 7vw, 84px), 650–700, compact line-height.
- Roster name: 19–24px, 650.
- Section/month heading: 24–34px, 650.
- Body: 16px, 400, 1.55 line-height.
- Metadata: 13–14px, 500.
- Legal/supporting copy: 13–14px, 400, 1.5 line-height.

## Color

Use a cool, quiet base with one confident accent.

```css
:root {
  --paper: #F4F6F7;
  --surface: #FFFFFF;
  --ink: #151719;
  --ink-soft: #41464B;
  --ink-muted: #6F777E;
  --line: #D8DDE1;
  --line-strong: #AEB6BC;
  --accent: #F05A3C;
  --accent-dark: #C83F27;
  --accent-wash: #FFF0EC;
  --positive: #2F7A56;
  --focus: #2457D6;
}
```

Rules:
- Accent appears on the search action, active text, focus moments, and sparse category rules.
- Do not fill large page areas with the accent.
- Charge categories may use muted secondary hues, but labels remain text-first and are never rendered as pills.
- Legal/disclaimer content uses neutral ink and separators, not warning red.

## Shape language

- Default radius: 0–4px.
- Search input may use 6px maximum.
- Buttons are rectangular, not capsules.
- Use horizontal rules, vertical rules, underlines, and edge alignment as the primary grouping devices.
- Use shadows only for transient layers such as search suggestions or lightboxes.
- Roster entries are separated by rules and spacing, not floating cards.

## Masthead

Desktop structure:

1. Left: `Are They In Jail?`
2. Center/right: plain-text navigation with no subtitles under every item.
3. Far right: live custody count as a sentence, not a badge.

Secondary line:

`Hamilton County, Ohio · current public custody roster · data by JCStream`

Government and social seals move out of the masthead. They may appear in a source/about area if retained.

## Homepage composition

### 1. Search stage

The first screen is dominated by one question and one search field.

Headline:

> Are they in jail?

Supporting line:

> Search the current Hamilton County custody roster by name, booking number, charge, or Ohio code.

Search field:
- full-width rectangular field;
- large type;
- visible keyboard focus;
- inline clear action;
- search suggestions shown in a restrained white layer;
- no search button if Enter and live results are sufficient; otherwise use one rectangular accent button.

### 2. Live snapshot

Render as an inline editorial sentence, not four cards:

> 1,273 people listed now · 34 booked in the last 24 hours · 28 released · checked 6 minutes ago

The timestamp must communicate freshness in human language first, with the exact UTC value available secondarily.

### 3. Legal framing

Use one quiet line immediately below the snapshot:

> Arrest is not conviction. Charges are accusations. This is an independent public-record mirror.

`Read the full notice` expands the complete legal text. The full notice must remain available and accessible, but should not visually dominate the entry experience.

### 4. Roster workspace

Desktop uses an asymmetric two-column layout:

- Left rail, 240–280px: filters, sort, quick links, and roster context.
- Main column: dense roster index grouped by month/date.

The left rail is not a dashboard panel. It is a plain column separated by a vertical rule.

Filter controls:
- labels above rectangular selects/inputs;
- no enclosing rounded bar;
- active filters listed as removable text rows with an `×`, not chips;
- reset is a text action.

### 5. Roster entries

Each row contains:

- optional booking photo thumbnail;
- person name;
- booking number and booked date;
- time in custody;
- leading charge/category as text;
- degree aligned at the far edge;
- a thin category-colored rule or small square marker, never a pill.

Rows should feel like a public index or classified listing, not profile cards.

Desktop row rhythm:
- 20–28px vertical padding;
- 1px separator;
- name and metadata left-aligned;
- details reveal through row expansion or detail-page navigation.

Mobile:
- one-column stacked rows;
- filter drawer uses a square-edged sheet;
- search remains sticky after the first scroll threshold;
- no sideways table dependence.

## Navigation

Primary:
- Roster
- Court dates
- Bond
- Visit
- Help

Secondary links such as statistics, statutes, access, data, RSS, and GitHub move into a compact `More` area or footer index. The initial header should not present eleven equally weighted destinations.

## Quick actions

Quick actions appear as underlined text links in a two-column list with short descriptions, not six bordered buttons.

Example:

- **Find a court date** — Check upcoming Hamilton County appearances.
- **Understand bond** — Read the bond and release guide.
- **Visit or contact someone** — Hours, phone, mail, and location.
- **Get free help** — Legal aid and community resources.

## Motion

One orchestrated page-load sequence only:

1. masthead enters;
2. headline and search rise into place;
3. snapshot/legal line appears;
4. first roster rows reveal.

Duration should stay under 450ms and respect `prefers-reduced-motion`.

Hover behavior is limited to:
- underline movement;
- row background wash;
- image scale of 1.01–1.02 maximum;
- accent shift on active links.

## Accessibility

- Preserve existing semantic labels, live result status, and reduced-motion behavior.
- Keep minimum 44px touch targets where controls require tapping.
- Focus ring uses `--focus`, not the accent.
- Do not rely on category color alone; category and degree remain explicit text.
- Legal and source information remains reachable without JavaScript.
- Search and filters must work with keyboard-only navigation.

## First implementation slice

Only the homepage shell and roster browsing experience are redesigned in the first pass:

1. `web/templates/base.html`
2. `web/templates/index.html`
3. a new v2 stylesheet layer or replacement sections in `web/static/style.css`
4. only the JavaScript changes required by the revised filter/search markup

Do not restyle every secondary page before the homepage direction is validated.

## Acceptance test

The first viewport must answer these questions immediately:

1. What is this site for?
2. Where do I search?
3. How fresh is the data?
4. Is an arrest the same as a conviction?
5. What can I do next if I find the person?

The design fails if it resembles a government portal, admin dashboard, component-library demo, courthouse website, or playful social app.