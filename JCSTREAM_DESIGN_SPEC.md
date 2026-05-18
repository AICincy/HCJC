# JCStream Design Specification

## For: Claude Opus Implementation
## Source: Hamilton County Justice Center Mirror (jcstream.com)

---

## 1. AESTHETIC DIRECTION

**Style:** Brutalist editorial, institutional transparency, typewriter/legal document hybrid.

This is not a consumer product. It is a civic data mirror that presents jail roster records as public documents. The aesthetic communicates: raw authority, no spin, document-grade seriousness. Think newspaper of record crossed with a court filing.

**Core principles:**
- Monospace typography everywhere. No sans-serif body text. No decorative fonts.
- Three-color palette: black, white, red. Nothing else.
- Dense information layout. No decorative whitespace.
- Every element earns its pixels through function.
- The site should feel like a legal exhibit, not an app.

---

## 2. COLOR PALETTE

| Token             | Value       | Usage                                                |
|--------------------|-------------|------------------------------------------------------|
| `--bg-page`        | `#ffffff`   | Main content background                              |
| `--bg-header`      | `#1a1a1a`  | Site header bar                                      |
| `--bg-disclaimer`  | `#fdf5e6`  | Legal disclaimer box background (old lace/cream)     |
| `--bg-badge-hover` | `#f5f5f5`  | Table row hover, subtle alternation                  |
| `--text-primary`   | `#1a1a1a`  | Body text, headings, labels                          |
| `--text-secondary` | `#666666`  | Metadata, captions, secondary info                   |
| `--text-header`    | `#ffffff`  | Header bar text                                      |
| `--text-muted`     | `#999999`  | Timestamps, "38 days ago" style annotations          |
| `--accent-red`     | `#b33a3a`  | Links, accent badges, horizontal rules, alert text   |
| `--border-light`   | `#e0e0e0`  | Table row borders, card outlines                     |
| `--border-red`     | `#b33a3a`  | Disclaimer dashed border, double-rule separator      |

No gradients. No shadows. No opacity layers. Flat, high-contrast, print-ready.

---

## 3. TYPOGRAPHY

**Single font family across the entire site:** A monospace typeface.

The original site uses a system monospace stack. For implementation, use:

```css
font-family: 'JetBrains Mono', 'IBM Plex Mono', 'Courier Prime', 'Courier New', monospace;
```

Import from Google Fonts: `JetBrains Mono` (weights 400, 500, 700) or `IBM Plex Mono` (same weights).

**All text is uppercase where noted.** The site uses `text-transform: uppercase` and `letter-spacing` aggressively. Do not fake this with all-caps strings in markup; use CSS transforms so the HTML remains semantic.

| Element                     | Size    | Weight | Transform   | Letter-spacing | Notes                                  |
|-----------------------------|---------|--------|-------------|----------------|----------------------------------------|
| Site name "JCSTREAM"        | 24px    | 700    | uppercase   | 0.05em         | Header bar, left-aligned               |
| Header subtitle             | 11px    | 400    | uppercase   | 0.15em         | Below site name, same line or stacked  |
| Header nav links            | 13px    | 500    | uppercase   | 0.1em          | Horizontal, right-aligned              |
| Population counter          | 14px    | 700    | none        | 0              | Number bold, "IN CUSTODY" in 400       |
| Breadcrumb                  | 13px    | 400    | uppercase   | 0.05em         | "← ALL INMATES / NAME"                |
| Page title                  | 28px    | 700    | uppercase   | 0.12em         | "INMATE RECORD", centered              |
| Page subtitle               | 12px    | 400    | uppercase   | 0.15em         | "HAMILTON COUNTY JUSTICE CENTER..."     |
| Source attribution           | 11px    | 400    | uppercase   | 0.1em          | "JCSTREAM/HCSO · INMATE-ROSTER..."     |
| Inmate name                 | 36px    | 700    | uppercase   | 0.08em         | Largest text on page                   |
| Section heading (h2)        | 20px    | 700    | uppercase   | 0.1em          | "FILES", "DATA & METHODOLOGY"          |
| Table header cells          | 12px    | 700    | uppercase   | 0.12em         | Column headers                         |
| Table label cells           | 13px    | 500    | uppercase   | 0.08em         | Left column (INMATE #, BOOKED, etc.)   |
| Table value cells           | 14px    | 400    | none        | 0              | Right column, mixed case               |
| Body paragraph              | 14px    | 400    | none        | 0.01em         | Data methodology page prose            |
| Legal disclaimer text       | 13px    | 400    | none        | 0              | Inside dashed border box               |
| Legal disclaimer emphasis   | 13px    | 700    | uppercase   | 0.05em         | "ARREST IS NOT CONVICTION."            |
| Caption text                | 11px    | 400    | uppercase   | 0.1em          | Photo caption, footer notes            |

---

## 4. LAYOUT STRUCTURE

### 4.1 Global Header

Full-width dark bar (`--bg-header`). Fixed or static (original is static).

```
[JCSTREAM                          ] [1,226 IN CUSTODY] [STATS COURT STATUTES VISIT HELP DATA RSS GITHUB]
[HAMILTON COUNTY · JUSTICE CENTER MIRROR]
```

- Left: Site name + subtitle stacked.
- Center-left: Population count with vertical pipe separator. The number is bold; "IN CUSTODY" is regular weight.
- Right: Navigation links, horizontal, evenly spaced. No underlines. Hover: underline or color shift to `--accent-red`.
- Padding: `12px 24px` approximate.
- Max-width: none (full bleed header).

### 4.2 Content Container

White card on a very light warm gray body (`#f7f6f3` or `#fafaf8`). The card has:
- `max-width: 1200px`
- `margin: 0 auto`
- Slight border or 1px `--border-light` outline. No shadow.
- Internal padding: `32px 40px`

### 4.3 Breadcrumb Row

Top of content card. Left-aligned.
- Format: `← ALL INMATES / CURRENT PAGE NAME`
- The "←" is a literal left arrow character, not an icon.
- Separated from content below by a dashed horizontal rule (`border-bottom: 1px dashed --border-light`).

### 4.4 Public Record Stamp (Inmate Page)

Top-right corner of the content card, positioned absolute or float-right.
- Red border box, slightly rotated (~2deg clockwise).
- Text: "PUBLIC RECORD · ORC § 149.43"
- Font: 12px, uppercase, bold, `--accent-red` color.
- Border: 2px solid `--accent-red`.
- Padding: `6px 12px`.
- The rotation gives it a "rubber stamp" feel.

---

## 5. PAGE: INMATE RECORD

This is the primary data page. Two-column layout below the name.

### 5.1 Title Block (Centered)

```
JCSTREAM/HCSO · INMATE-ROSTER-MIRROR · ORC § 149.43    [source attribution, 11px]
                    INMATE RECORD                        [page title, 28px bold]
       HAMILTON COUNTY JUSTICE CENTER · CINCINNATI, OHIO [subtitle, 12px]
═══════════════════════════════════════════════════════  [double red rule]
```

The double horizontal rule is 3px total: two 1px red lines separated by 2px gap. Use a border technique or two `<hr>` elements. Color: `--accent-red`.

### 5.2 Charge Tags + Inmate Number Row

Horizontal row below the double rule.

**Tags (left-aligned):**
- "FELONY x6" - Filled red background (`--accent-red`), white text, rounded pill (`border-radius: 4px`, `padding: 4px 12px`).
- "MISDEMEANOR" - Outlined style: `border: 1px solid --text-primary`, no fill, dark text.
- "BREAKING AND ENTERING" - Same outlined style.
- Tags have 8px horizontal gap.

**Inmate number (right-aligned):**
- "#1006094" in `--text-secondary`, 14px.

### 5.3 Name

Full-width. `MCANALLY BRADEN` in the largest type on the page (36px, 700 weight, uppercase).
Below the name: a single 1px red horizontal rule.

### 5.4 Legal Disclaimer Box

Immediately below the name rule.
- Border: `3px dashed --border-red`.
- Background: `--bg-disclaimer` (cream/old lace).
- Padding: `20px 24px`.
- Content:
  - Line 1: **"ARREST IS NOT CONVICTION."** (red, bold, uppercase)
  - Line 2: "This individual is" (regular)
  - Line 3: **"LEGALLY PRESUMED INNOCENT"** (red, bold, uppercase)
  - Lines 4-5: "unless and until proven guilty in a court of law. The charges below are accusations only and are not evidence of guilt." (regular)

### 5.5 Two-Column Detail Area

**Left column (~280px fixed):**
- Booking photo in a gray-bordered box.
  - The photo is grayscale.
  - Below the photo: label "EXHIBIT A - BOOKING" (uppercase, bold, 12px) above the image.
  - Below the image: caption "BOOKING PHOTO · ORC § 149.43" (11px, muted).

**Right column (remaining width):**
- Key-value data table. See Section 5.6.

### 5.6 Data Table

Two-column table. No outer border. Rows separated by `1px solid --border-light`.

| Left column (label)    | Right column (value)                                |
|------------------------|-----------------------------------------------------|
| INMATE #               | `1006094` (in a subtle inline code box)             |
| BOOKING #              | `26001499` (inline code box) + "booking #1,499 of 2026" |
| BOOKED                 | `4/8/26` bold + "38 days ago" muted                 |
| PROJECTED RELEASE      | `NA`                                                |
| NEXT COURT DATE        | `6/11/26`                                           |
| CHARGES                | `7` bold + "1 pending · 6 disposed" regular         |
| TOTAL BOND             | `$55,000`                                           |
| CASE #S                | Comma-separated links (red, underlined on hover)    |
| DATE OF BIRTH          | `9/18/63` + "age ~62" muted                         |
| SEX · RACE             | `Male · Black`                                      |
| HOLDER / DETAINER      | `Yes`                                               |

**Inline code boxes:** Certain values (inmate #, booking #) appear inside a small bordered box: `border: 1px solid --border-light`, `padding: 2px 6px`, `background: #f9f9f9`.

**Label column:** ~200px width, `--text-primary`, uppercase, 500 weight.
**Value column:** remaining width, 400 weight, mixed formatting as noted.

### 5.7 Charges by Category Row

Below the data table. Horizontal layout:
- Label: "CHARGES BY CATEGORY:" (uppercase, 12px, muted)
- Followed by outlined pill badges:
  - "BREAKING AND ENTERING 6"
  - "DRUG PARAPHERNALIA 1"
- Badge style: `border: 1px solid --text-primary`, `padding: 4px 10px`, uppercase, 12px.

### 5.8 Footer Note

Small text at the very bottom:
- "This is a public record under ORC § 149.43 and is removed automatically when the Hamilton County Sheriff's Office..."
- 11px, muted color, with "ORC § 149.43" as a red link.

### 5.9 Scroll-to-Top Button

Fixed position, bottom-right corner.
- Dark circle (`--bg-header`), white up-arrow icon.
- Size: ~40px diameter.
- Appears on scroll.

---

## 6. PAGE: DATA & METHODOLOGY

### 6.1 Title Block

Same pattern as inmate page:
```
DATA & METHODOLOGY                [page heading, 20px bold uppercase]
OPEN DATA FEEDS, LICENSING, AND LEGAL NOTICES   [subtitle, 12px uppercase]
═══════════════════════════════════════════════  [double red rule]
```

### 6.2 Main Heading

Below the double rule:
- "DATA, METHODOLOGY & LEGAL NOTICES" in large serif-weight monospace, ~28px, bold.
- Single red rule below.

### 6.3 Body Text

Monospace paragraph text, 14px, line-height 1.7. The text describes the data source methodology.
- Links within prose are `--accent-red` with underline on hover.
- Italics used for emphasis (e.g., "*current*").

### 6.4 Section Heading

"FILES" - 18px, bold, uppercase, `letter-spacing: 0.1em`.
Preceded by a thin horizontal rule and followed by a double red rule.

### 6.5 Files Table

Two-column table:

| Column   | Width  | Style                                              |
|----------|--------|----------------------------------------------------|
| FILE     | ~250px | Red link text, monospace. `--accent-red`.          |
| CONTENTS | rest   | Regular monospace body text, 13px, wrapping.       |

- Header row: uppercase, bold, 12px, `letter-spacing: 0.12em`. Light gray background (`#f5f5f5`).
- Row borders: `1px solid --border-light`.
- Cell padding: `12px 16px`.
- Code-like values within descriptions (field names, JSON keys) appear in a slightly different weight or inline code style.

---

## 7. INTERACTIVE ELEMENTS

### 7.1 Links

- Color: `--accent-red` (#b33a3a).
- Default: no underline.
- Hover: underline.
- Visited: slightly darker red or same (no purple).

### 7.2 Header Navigation

- White text on dark background.
- Hover: underline or slight opacity change.
- No active/current indicator beyond context.

### 7.3 Tags/Badges

Two variants:
1. **Filled (alert):** Red background, white text, 4px border-radius. Used for felony count.
2. **Outlined (neutral):** 1px dark border, no fill, dark text. Used for charge categories.

### 7.4 Hover States

- Table rows: subtle background shift to `#fafafa`.
- Links: underline appears.
- No transforms, no scale, no shadows.

---

## 8. RESPONSIVE BEHAVIOR

### Desktop (>1024px)
- Two-column layout on inmate page (photo left, data right).
- Full header with all nav items visible.

### Tablet (768-1024px)
- Content padding reduces.
- Photo column may shrink.

### Mobile (<768px)
- Single column. Photo above data table.
- Header nav collapses to hamburger or stacks.
- Tags wrap to multiple rows.
- Table becomes full-width, label column narrows.

---

## 9. COMPONENT INVENTORY

These are the reusable components needed:

1. **SiteHeader** - Dark bar with logo, population counter, nav links.
2. **Breadcrumb** - "← PARENT / CURRENT" with dashed separator below.
3. **PublicRecordStamp** - Rotated red-border badge, top-right.
4. **PageTitleBlock** - Source attribution + title + subtitle + double red rule.
5. **ChargeBadge** - Two variants: filled (red) and outlined.
6. **LegalDisclaimer** - Dashed red border box with cream background.
7. **BookingPhoto** - Grayscale image with exhibit label and caption.
8. **DataTable** - Key-value table with typed value formatting.
9. **InlineCodeBox** - Small bordered box for numeric IDs.
10. **CategoryRow** - "CHARGES BY CATEGORY:" + badge list.
11. **SectionDivider** - Double red horizontal rule.
12. **ThinDivider** - Single 1px light rule.
13. **DashedDivider** - Dashed light rule (breadcrumb separator).
14. **FilesTable** - Two-column table for data feeds.
15. **ScrollToTop** - Fixed dark circle button, bottom-right.
16. **FooterNote** - Small muted text with statutory citation.

---

## 10. CRITICAL IMPLEMENTATION NOTES

1. **No shadows anywhere.** The entire site is flat.
2. **No border-radius on cards or containers.** Only on pill badges (4px).
3. **No icons.** The only graphical elements are the booking photo and the scroll-to-top arrow (plain text arrow or minimal SVG).
4. **Middot (·) as a separator.** Used extensively: "HAMILTON COUNTY · JUSTICE CENTER MIRROR", "Male · Black", "BOOKING PHOTO · ORC § 149.43". Use the literal `·` character, not a bullet or period.
5. **Letter-spacing is load-bearing.** The entire aesthetic depends on generous letter-spacing in uppercase text. Without it, the site looks like a broken terminal instead of an editorial document.
6. **Line-height in body text: 1.7.** Monospace needs extra vertical breathing room.
7. **The double red rule is a signature element.** It appears below every page title. Get this right: two thin red lines with a 2-3px gap between them.
8. **Print-friendly.** The original site is designed to print cleanly. Avoid anything that breaks in `@media print`.

---

## 11. SAMPLE CSS VARIABLES BLOCK

```css
:root {
  --font-mono: 'JetBrains Mono', 'IBM Plex Mono', 'Courier Prime', 'Courier New', monospace;
  --bg-page: #ffffff;
  --bg-body: #f7f6f3;
  --bg-header: #1a1a1a;
  --bg-disclaimer: #fdf5e6;
  --text-primary: #1a1a1a;
  --text-secondary: #666666;
  --text-muted: #999999;
  --text-header: #ffffff;
  --accent-red: #b33a3a;
  --border-light: #e0e0e0;
  --border-red: #b33a3a;
  --radius-badge: 4px;
  --spacing-page: 32px 40px;
  --max-width: 1200px;
  --line-height-body: 1.7;
  --line-height-dense: 1.4;
}
```

---

## 12. WHAT THIS IS NOT

- Not a dashboard. No charts, no sparklines, no widgets.
- Not a SaaS product. No call-to-action buttons, no onboarding, no modals.
- Not a portfolio site. No hero images, no parallax, no testimonials.
- Not an app. No hamburger menus on desktop, no bottom nav, no floating action buttons.

It is a **public records mirror** that presents jail booking data with the same formality a court clerk would use. Every design decision should answer: "Would this look appropriate stamped as Exhibit A in a court filing?"
