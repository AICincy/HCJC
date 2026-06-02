"""HTML parsers for the HCSO inmate-search list page and inmate-detail page."""

from __future__ import annotations

import base64
import logging
import re
import threading as _threading
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
# Module-level set of labels already warned about. Under CPython 3.12 + the
# GIL + ThreadPoolExecutor the bare `set.add` is benign: the worst observable
# consequence is a few redundant warning emissions across workers, not a
# data race. The lock below is forward-looking defense in advance of any
# free-threaded Python (PEP 703) or async-worker refactor, where the bare
# mutation would no longer be serialized by the GIL. Lock scope is
# intentionally narrow (read + possible add); the log.warning call runs
# outside the critical section so a slow logger never serializes workers.
# Module-level dedup set: suppresses repeated warnings for the same missing
# label within a single process lifetime. In the cron-per-process model this
# is fine; a long-running daemon would need per-run scoping or TTL eviction.
_WARNED_MISSING_LABELS: set[str] = set()
_WARNED_MISSING_LABELS_LOCK = _threading.Lock()


def parse_list_page(html: str) -> list[ListRow]:
    """Parse the surname-search result table.

    Returns one ``ListRow`` per inmate currently in custody whose surname matched.
    """
    tree = HTMLParser(html)
    rows: list[ListRow] = []
    for tr in tree.css("tr"):
        cells = {_attr(c, "label"): _text(c) for c in tr.css("td[label]")}
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
        href = _attr(a, "href")
        m = _DETAIL_ID.search(href)
        if m:
            return m.group(1)
    return ""


def parse_detail_page(html: str, inmate_number: str) -> tuple[Inmate, bytes | None, str | None]:
    """Parse an inmate-detail page.

    Returns ``(Inmate, photo_bytes, photo_url)``. ``photo_url`` is a direct
    URL to the booking photo when the page provides one (preferred over base64).
    ``photo_bytes`` is the base64-decoded fallback. Either or both can be None.
    """
    tree = HTMLParser(html)
    bio = _parse_bio(tree)
    name = _parse_name(tree)
    charges = _parse_charges(tree)
    photo_url, photo_bytes, img_stats = _extract_photo(tree)

    last, first, middle = _split_name(name)

    if not bio and not name and not charges:
        log.info("detail page produced no structured fields for id=%s", inmate_number)
    elif photo_url is None and photo_bytes is None:
        img_count, nondata_count, data_count = img_stats
        log.info(
            "detail page id=%s parsed (bio=%d name=%s charges=%d) but no photo extracted "
            "(imgs=%d non-data=%d data=%d). If HCSO has a photo here, the alt/class/274px "
            "hooks and the size+extension fallback all missed it - investigate HTML drift.",
            inmate_number, len(bio), bool(name), len(charges), img_count, nondata_count, data_count,
        )

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
        photo_url,
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
    """The detail page shows the inmate's name in a prominent heading.

    Expected format: ``LAST, FIRST [MIDDLE]`` in all-caps.

    Tiered fallback strategy to handle HCSO page structure changes:
      1. h1/h2/h3 with comma + all-caps + at least one letter (current shape).
         A leading "Inmate:" (or similar single-label-with-colon prefix that
         HCSO added 2026-05-18) is stripped before the all-caps check, so the
         parser tolerates both "VOE, ANDREW" and "Inmate: VOE, ANDREW".
      2. meta[property="og:title"] with the same shape.
      3. Any text node with comma + all-caps (e.g., in container divs).
      4. Bio table extraction: look for cells labeled "Name", "Full Name", 
         "Inmate", or similar.
      5. document <title> with at least a comma.
    
    Each non-tier-1 success logs a debug breadcrumb so the operator can see
    which tier saved the cycle.
    """
    heading_name = _name_from_heading_tags(tree)
    if heading_name:
        return heading_name
    og_title_name = _name_from_og_title(tree)
    if og_title_name:
        return og_title_name
    container_name = _name_from_container_text(tree)
    if container_name:
        return container_name
    labeled_cell_name = _name_from_labeled_cell(tree)
    if labeled_cell_name:
        return labeled_cell_name
    title_name = _name_from_title(tree)
    if title_name:
        return title_name

    # All tiers missed. Sweep's list-row fallback will still produce a
    # usable record for new bookings; --refresh-known has no fallback.
    log.warning("inmate-detail name heading (LAST, FIRST all-caps) not found")
    return ""


def _looks_like_formal_name(text: str) -> bool:
    return "," in text and text.upper() == text and any(c.isalpha() for c in text)


def _strip_name_label_prefix(text: str) -> str:
    return text.split(":", 1)[1].strip() if ":" in text else text.strip()


def _name_from_heading_tags(tree: HTMLParser) -> str:
    for tag in ("h1", "h2", "h3"):
        for node in tree.css(tag):
            text = _text(node)
            if "," not in text:
                continue
            candidate = _strip_name_label_prefix(text)
            if _looks_like_formal_name(candidate):
                return candidate
    return ""


def _name_from_og_title(tree: HTMLParser) -> str:
    for meta in tree.css('meta[property="og:title"]'):
        content = _attr(meta, "content").strip()
        if _looks_like_formal_name(content):
            log.debug("name extracted from og:title fallback")
            return content
    return ""


_BOILERPLATE_KEYWORDS = frozenset({
    "COUNTY", "STATE", "OFFICE", "DEPARTMENT", "SHERIFF",
    "COURT", "OHIO", "JUSTICE", "CENTER", "SERVICES",
    "GOVERNMENT", "DISTRICT", "MUNICIPAL", "COMMON PLEAS",
})
# Single word-boundary alternation, longest-first so "COMMON PLEAS" wins over
# a bare token match. Compiled once instead of per-call per-keyword.
_BOILERPLATE_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in sorted(_BOILERPLATE_KEYWORDS, key=len, reverse=True)) + r")\b"
)


def _looks_like_person_name(text: str) -> bool:
    """Stricter check than _looks_like_formal_name for the container fallback.

    Requires LAST, FIRST shape (second part has at least one letter after the
    comma) and rejects strings containing known boilerplate keywords."""
    if not _looks_like_formal_name(text):
        return False
    if _BOILERPLATE_RE.search(text):
        return False
    _, _, after_comma = text.partition(",")
    if not after_comma.strip() or not any(c.isalpha() for c in after_comma):
        return False
    return True


def _name_from_container_text(tree: HTMLParser) -> str:
    for div in tree.css("div, span, p"):
        text = _text(div)
        if not text:
            continue
        if _looks_like_person_name(text) and len(text) < 200:
            log.debug("name extracted from container text fallback (tag=%s)", div.tag)
            return text.strip()
    return ""


def _name_from_labeled_cell(tree: HTMLParser) -> str:
    for td in tree.css("td[label], th"):
        label = _attr(td, "label").strip()
        if label.lower() in ("name", "full name", "inmate", "inmate name"):
            text = _text(td)
            if text:
                log.debug("name extracted from labeled cell (label=%s)", label)
                return text.strip()
    return ""


def _name_from_title(tree: HTMLParser) -> str:
    title = tree.css_first("title")
    if title is not None:
        text = _text(title)
        if "," in text:
            log.debug("name extracted from <title> fallback")
            return text.strip()
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


def _log_skipped_charge_rows(skipped: int, n_charges: int) -> None:
    """Report charge rows that carried labeled cells but neither Description
    nor ORC Code. A total drop (skipped rows, zero charges) is a label-drift
    warning; a partial skip alongside real charges is usually benign
    (non-charge labeled rows), so it logs at debug for label-drift diagnosis."""
    if not skipped:
        return
    if not n_charges:
        log.warning(
            "charge table parser found %d labeled rows but extracted 0 charges "
            "(Description/ORC Code labels may have drifted)",
            skipped,
        )
    else:
        log.debug(
            "charge table parser skipped %d labeled rows that lacked both "
            "Description and ORC Code (extracted %d charges)",
            skipped, n_charges,
        )


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
        cells = {_attr(c, "label"): _text(c) for c in tr.css("td[label]")}
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
    _log_skipped_charge_rows(skipped_with_cells, len(charges))
    # Per-process drift signal: when a detail page yielded charges but a
    # high-value column was absent from every row, warn once. Catches the
    # case where one column rename (e.g. "Bond Amount" to "Bond ($)") would
    # otherwise silently empty that field with no aggregate watchdog hit.
    if charges:
        for label in _HIGH_VALUE_CHARGE_LABELS:
            if label in seen_charge_labels:
                continue
            with _WARNED_MISSING_LABELS_LOCK:
                if label in _WARNED_MISSING_LABELS:
                    continue
                _WARNED_MISSING_LABELS.add(label)
            log.warning(
                "charge label %r absent from every row on a detail page; "
                "HCSO may have renamed the column",
                label,
            )
    return charges


_UI_ICON_HINTS = (
    "logo", "icon", "menu", "header", "footer", "spinner", "loader",
    "alert", "warn", "search", "social", "share", "facebook", "twitter",
    "instagram", "youtube", "linkedin", "/uploads/", "/themes/",
    "/plugins/", "/wp-content/", "/wp-includes/",
)


def _looks_like_ui_chrome(img) -> bool:
    """True if an <img> looks like UI chrome (a logo, icon, alert glyph, etc.)
    rather than a booking photo. Used by the size-fallback path in
    _extract_photo so a permissive match doesn't latch onto a 51x51 alert
    icon when HCSO drops the 274px style hook.
    """
    src = _attr(img, "src").lower()
    alt = _attr(img, "alt").lower()
    if any(h in src for h in _UI_ICON_HINTS):
        return True
    if any(h in alt for h in ("logo", "icon", "menu", "alert", "warn")):
        return True
    try:
        w = int(img.attributes.get("width") or "0")
        h = int(img.attributes.get("height") or "0")
    except (TypeError, ValueError):
        w = h = 0
    # Booking mug shots are ~200-300 px wide. UI chrome is usually <80 px.
    return 0 < w < 80 or 0 < h < 80


def _extract_photo(tree: HTMLParser) -> tuple[str | None, bytes | None, tuple[int, int, int]]:
    """Single-pass photo extraction and image inventory.

    Walks ``tree.css("img")`` once, combining the URL-extraction tiers,
    inline-base64 decoding, and image counting that previously required up
    to five separate traversals.

    Returns ``(photo_url, photo_bytes, (img_count, nondata_count, data_count))``.
    ``photo_url`` is preferred over ``photo_bytes``; when a URL is found,
    inline base64 decoding is skipped for remaining images.

    URL tiers (first match wins):
      1. alt / class / style hooks ("photo", "mug", "inmate", "booking",
         "274px"). Historical HCSO pattern.
      2. Size-and-extension fallback: non-data ``<img>`` ending in a common
         image extension that does not look like UI chrome.

    Inline tiers (only when no URL found):
      1. ``274px`` in the ``style`` attribute.
      2. JPEG start-of-image marker in decoded bytes.
    """
    photo_url: str | None = None
    url_fallback: str | None = None
    inline_274px: bytes | None = None
    soi_candidate: bytes | None = None
    img_count = 0
    nondata_count = 0
    data_count = 0

    for img in tree.css("img"):
        img_count += 1
        src = _attr(img, "src")
        
        # Fallback to lazy-loaded source if src is absent or a tiny/SVG placeholder
        if not src or "placeholder" in src.lower() or src.startswith("data:image/svg") or src.startswith("data:image/gif"):
            for attr in ("data-src", "data-lazy-src", "data-original"):
                val = _attr(img, attr)
                if val:
                    src = val
                    break

        if not src:
            continue

        if src.startswith("data:"):
            # Skip SVG base64 strings as they are vector silhouettes, not real photo bytes
            if "image/svg" in src or "xml" in src:
                continue
            data_count += 1
            if photo_url is not None or url_fallback is not None:
                continue
            header, _, payload = src.partition(",")
            if "base64" not in header or not payload:
                continue
            try:
                raw = base64.b64decode(payload, validate=False)
            except ValueError:  # binascii.Error subclasses ValueError
                log.warning("failed to base64-decode inline photo candidate")
                continue
            style = _attr(img, "style")
            if "274px" in style:
                inline_274px = raw
            elif soi_candidate is None and raw[:3] == _JPEG_SOI:
                soi_candidate = raw
        else:
            nondata_count += 1
            if photo_url is not None:
                continue
            alt = _attr(img, "alt").lower()
            style = _attr(img, "style")
            cls = _attr(img, "class")
            if any(k in alt for k in ("photo", "mug", "inmate", "booking")):
                photo_url = src
            elif any(k in cls for k in ("photo", "mug", "inmate")):
                photo_url = src
            elif "274px" in style:
                photo_url = src
            elif url_fallback is None and src.lower().rsplit("?", 1)[0].endswith(
                (".jpg", ".jpeg", ".png", ".webp")
            ) and not _looks_like_ui_chrome(img):
                url_fallback = src

    if photo_url is None and url_fallback is not None:
        log.info("photo url matched size+extension fallback (no alt/class/274px hook): %s", url_fallback)
        photo_url = url_fallback

    photo_bytes: bytes | None = None
    if photo_url is None:
        if inline_274px is not None:
            photo_bytes = inline_274px
        elif soi_candidate is not None:
            log.info("inline photo matched JPEG-SOI fallback, not the 274px hook")
            photo_bytes = soi_candidate

    return photo_url, photo_bytes, (img_count, nondata_count, data_count)


def _text(node: Node) -> str:
    return (node.text(deep=True, separator=" ", strip=True) or "").strip()


def _attr(node: Node, key: str) -> str:
    """A node attribute as a non-None str. selectolax returns ``str | None``
    (a present-but-valueless attribute like ``disabled`` yields None); this
    normalizes to ``""`` so callers can string-handle without guarding."""
    return node.attributes.get(key) or ""


def iter_inmate_ids(rows: Iterable[ListRow]) -> set[str]:
    return {r.inmate_number for r in rows if r.inmate_number}
