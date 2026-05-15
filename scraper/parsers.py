"""HTML parsers for the HCSO inmate-search list page and inmate-detail page."""

from __future__ import annotations

import base64
import logging
import re
from typing import Iterable

from selectolax.parser import HTMLParser, Node

from .models import Charge, Inmate, ListRow

log = logging.getLogger(__name__)

# Regex to pull "id=NNNNNNNN" out of an inmate-detail link. Accepts both the
# current query-string form (?id=N) and a hypothetical path-permalink form
# (/inmate-detail/N) so a WordPress permalink shift doesn't zero the roster.
_DETAIL_ID = re.compile(r"(?:[?&]id=|/inmate-detail/)(\d+)")

# Regex to split a "<Label> : <Value>" line from the biography <li> blocks.
# Accepts digits, #, /, _, and - in label names so a HCSO addition like
# "Class #" or "Cell-Block" is captured rather than silently dropped.
_BIO_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 #/_-]*?)\s*:\s*(.*?)\s*$")

# JPEG start-of-image marker. HCSO declares image/png but serves JPEG bytes;
# the photo extractor uses this as a fallback when the 274px style hook drifts.
_JPEG_SOI = b"\xff\xd8\xff"

# High-value charge labels: if any of these is absent from every charge row in
# a single detail page, the parser warns once per process (label-drift signal).
_HIGH_VALUE_CHARGE_LABELS = ("Description", "ORC Code", "Bond Amount", "Court Date")
_WARNED_MISSING_LABELS: set[str] = set()


def parse_list_page(html: str) -> list[ListRow]:
    """Parse the surname-search result table.

    Returns one ``ListRow`` per inmate currently in custody whose surname matched.
    """
    tree = HTMLParser(html)
    rows: list[ListRow] = []
    for tr in tree.css("tr"):
        cells = {c.attributes.get("label", ""): _text(c) for c in tr.css("td[label]")}
        last = cells.get("Last Name", "").strip()
        first = cells.get("First Name", "").strip()
        admit = cells.get("Admit Date", "").strip()
        if not (last or first):
            continue
        inmate_number = _extract_inmate_id_from_row(tr)
        if not inmate_number:
            log.debug("row has names but no inmate id; skipping (last=%s first=%s)", last, first)
            continue
        rows.append(
            ListRow(
                inmate_number=inmate_number,
                last_name=last,
                first_name=first,
                admit_date=admit,
            )
        )
    return rows


def _extract_inmate_id_from_row(tr: Node) -> str:
    for a in tr.css("a"):
        href = a.attributes.get("href", "")
        m = _DETAIL_ID.search(href)
        if m:
            return m.group(1)
    return ""


def parse_detail_page(html: str, inmate_number: str) -> tuple[Inmate, bytes | None]:
    """Parse an inmate-detail page.

    Returns the structured ``Inmate`` plus the raw booking-photo JPEG bytes
    (or ``None`` if the page lacks a non-empty inline image).
    """
    tree = HTMLParser(html)
    bio = _parse_bio(tree)
    name = _parse_name(tree)
    charges = _parse_charges(tree)
    photo_bytes = _extract_inline_photo(tree)

    last, first, middle = _split_name(name)

    # parser-F8: per-id breadcrumb when a detail page passes raise_for_status
    # but yields zero structured fields (HCSO error / interstitial page that
    # still returned 200). The list-row fallback hides this in normal sweeps;
    # this log gives the operator a discoverable signal per affected id.
    if not bio and not name and not charges:
        log.info("detail page produced no structured fields for id=%s", inmate_number)

    return (
        Inmate(
            inmate_number=bio.get("Inmate Number") or inmate_number,
            booking_number=bio.get("Booking Number", ""),
            last_name=last,
            first_name=first,
            middle_name=middle,
            date_of_birth=bio.get("Date of Birth", ""),
            sex=bio.get("Sex", ""),
            race=bio.get("Race", ""),
            booking_date=bio.get("Booking Date", ""),
            projected_release_date=bio.get("Projected Release Date", ""),
            holder_status=bio.get("Holder", "") or bio.get("Holder Status", ""),
            charges=charges,
        ),
        photo_bytes,
    )


def _parse_bio(tree: HTMLParser) -> dict[str, str]:
    out: dict[str, str] = {}
    for li in tree.css("li"):
        text = _text(li)
        m = _BIO_LINE.match(text)
        if not m:
            continue
        label, value = m.group(1).strip(), m.group(2).strip()
        if label and value:
            out[label] = value
    return out


def _parse_name(tree: HTMLParser) -> str:
    """The detail page shows the inmate's name in a prominent heading,
    formatted ``LAST, FIRST [MIDDLE]``.

    Tiered fallback so a single drift in heading markup, casing, or location
    doesn't zero every detail-page name:
      1. h1/h2/h3 with comma + all-caps + at least one letter (current shape).
      2. meta[property="og:title"] with the same shape.
      3. document <title> with at least a comma.
    Each non-tier-1 success logs a debug breadcrumb so the operator can see
    which tier saved the cycle.
    """
    for tag in ("h1", "h2", "h3"):
        for node in tree.css(tag):
            text = _text(node)
            if "," in text and text.upper() == text and any(c.isalpha() for c in text):
                return text.strip()
    for meta in tree.css('meta[property="og:title"]'):
        content = (meta.attributes.get("content") or "").strip()
        if "," in content and content.upper() == content and any(c.isalpha() for c in content):
            log.debug("name extracted from og:title fallback")
            return content
    title = tree.css_first("title")
    if title is not None:
        text = _text(title)
        if "," in text:
            log.debug("name extracted from <title> fallback")
            return text.strip()
    # All tiers missed. Sweep's list-row fallback will still produce a
    # usable record for new bookings; --refresh-known has no fallback.
    log.warning("inmate-detail name heading (LAST, FIRST all-caps) not found")
    return ""


def _split_name(formal: str) -> tuple[str, str, str]:
    """Split ``LAST, FIRST [MIDDLE]`` into the three parts."""
    if "," not in formal:
        return (formal.strip(), "", "")
    last, _, rest = formal.partition(",")
    parts = rest.strip().split()
    first = parts[0] if parts else ""
    middle = " ".join(parts[1:]) if len(parts) > 1 else ""
    return (last.strip(), first, middle)


def _find_charges_table(tree: HTMLParser):
    """Return the <table> whose <thead> declares both Description and ORC Code,
    or None to fall back to a global ``tr`` scan.

    parser-F6: a future labeled-but-unrelated table (e.g. holds/warrants) on
    the detail page would otherwise leak spurious rows into the charge list.
    Scoping to the table whose thead matches both anchor labels prevents that
    without changing behavior on today's HCSO HTML.
    """
    for table in tree.css("table"):
        thead_labels = {_text(th) for th in table.css("thead th")}
        if "Description" in thead_labels and "ORC Code" in thead_labels:
            return table
    return None


def _parse_charges(tree: HTMLParser) -> list[Charge]:
    """Extract rows from the charges table.

    The table cells carry ``label="..."`` attributes (the same responsive-table
    pattern the list page uses). We collect cells by label per row.
    """
    charges: list[Charge] = []
    skipped_with_cells = 0
    seen_charge_labels: set[str] = set()
    # Prefer the table whose thead names Description + ORC Code; fall back to
    # the global tr scan if no such table is found (preserves current behavior).
    charges_table = _find_charges_table(tree)
    row_source = charges_table if charges_table is not None else tree
    for tr in row_source.css("tr"):
        cells = {c.attributes.get("label", ""): _text(c) for c in tr.css("td[label]")}
        if not cells:
            continue
        if {"Last Name", "First Name", "Admit Date"}.issubset(cells.keys()):
            continue  # list-page row pattern, not a charge
        description = cells.get("Description", "").strip()
        orc = cells.get("ORC Code", "").strip()
        if not description and not orc:
            # A row carried labeled cells but neither Description nor ORC Code
            # - if HCSO renames either label we'd drop every charge silently.
            skipped_with_cells += 1
            continue
        seen_charge_labels.update(k for k, v in cells.items() if v and v.strip())
        charges.append(
            Charge(
                common_pleas_case=cells.get("Common Pleas Case #", "").strip(),
                municipal_case=cells.get("Municipal Case #", "").strip(),
                other_case=cells.get("Other Case #", "").strip(),
                court_date=cells.get("Court Date", "").strip(),
                orc_code=orc,
                description=description,
                bond_type=cells.get("Bond Type", "").strip(),
                bond_amount=cells.get("Bond Amount", "").strip(),
                disposition=cells.get("Disposition", "").strip(),
                comments=cells.get("Comments", "").strip(),
            )
        )
    if skipped_with_cells and not charges:
        log.warning(
            "charge table parser found %d labeled rows but extracted 0 charges "
            "(Description/ORC Code labels may have drifted)",
            skipped_with_cells,
        )
    # Per-process drift signal: when a detail page yielded charges but a
    # high-value column was absent from every row, warn once. Catches the
    # case where one column rename (e.g. "Bond Amount" to "Bond ($)") would
    # otherwise silently empty that field with no aggregate watchdog hit.
    if charges:
        for label in _HIGH_VALUE_CHARGE_LABELS:
            if label in seen_charge_labels or label in _WARNED_MISSING_LABELS:
                continue
            _WARNED_MISSING_LABELS.add(label)
            log.warning(
                "charge label %r absent from every row on a detail page; "
                "HCSO may have renamed the column",
                label,
            )
    return charges


def _extract_inline_photo(tree: HTMLParser) -> bytes | None:
    """Return raw image bytes from the inline base64 placeholder, if present.

    HCSO embeds the booking photo as a data URI on the inmate-detail page,
    declared as ``image/png`` but actually JPEG bytes (SOI marker ``\\xff\\xd8``).
    The placeholder is the only ``<img>`` whose inline style sets ``width:274px``.

    Falls back to any data-URI ``<img>`` whose decoded bytes start with the
    JPEG SOI marker, so a HCSO width tweak (e.g. 274px to 280px) no longer
    loses photos site-wide. The 274px hit still wins when present.
    """
    soi_candidate: bytes | None = None
    for img in tree.css("img"):
        src = img.attributes.get("src", "")
        if not src.startswith("data:"):
            continue
        header, _, payload = src.partition(",")
        if "base64" not in header or not payload:
            continue
        try:
            data = base64.b64decode(payload, validate=False)
        except (ValueError, base64.binascii.Error):
            log.warning("failed to base64-decode inline photo candidate")
            continue
        style = img.attributes.get("style", "")
        if "274px" in style:
            return data
        if soi_candidate is None and data[:3] == _JPEG_SOI:
            soi_candidate = data
    if soi_candidate is not None:
        log.info("inline photo matched JPEG-SOI fallback, not the 274px hook")
        return soi_candidate
    return None


def _text(node: Node) -> str:
    return (node.text(deep=True, separator=" ", strip=True) or "").strip()


def iter_inmate_ids(rows: Iterable[ListRow]) -> set[str]:
    return {r.inmate_number for r in rows if r.inmate_number}
