"""Detail fetching and photo attachment helpers."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ..client import DEFAULT_CONCURRENCY, HcsoClient
from ..models import Inmate, ListRow, utcnow_iso
from ..parsers import parse_detail_page
from ..photos import downscale_and_save
from ..store import save_current
from ..sweep_guards import (
    SWEEP_BOOTSTRAP_FLOOR,
    SWEEP_MIN_ROSTER_FRACTION,
    looks_like_waf_block,
)
from .evidence import WafBackoffTracker

log = logging.getLogger("jcstream.sweep")

DETAIL_PATH = "/justice-center-services/inmate-search/inmate-detail/"
PHOTOS_DIR = Path("data/photos")
SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60


def _plan_detail_fetch(seen_ids: set[str], previous: dict[str, Inmate], refresh_known: bool) -> list[str]:
    """Return the sorted inmate ids whose detail pages should be fetched."""
    to_fetch: list[str] = []
    for inmate_id in sorted(seen_ids):
        if inmate_id not in previous:
            to_fetch.append(inmate_id)
        elif refresh_known:
            to_fetch.append(inmate_id)
        elif not previous[inmate_id].photo_filename:
            to_fetch.append(inmate_id)
    return to_fetch


def _carry_forward_known(
    current: dict[str, Inmate],
    seen_ids: set[str],
    previous: dict[str, Inmate],
    to_fetch: list[str],
) -> None:
    """Copy unchanged known inmates into ``current`` with refreshed last_seen."""
    to_fetch_set = set(to_fetch)
    for inmate_id in seen_ids:
        if inmate_id in previous and inmate_id not in to_fetch_set:
            current[inmate_id] = previous[inmate_id].model_copy(update={"last_seen_utc": utcnow_iso()})


def _maybe_checkpoint_partial(
    previous: dict[str, Inmate],
    current: dict[str, Inmate],
    done: int,
    total: int,
    current_path: Path,
) -> None:
    """Persist an in-progress roster checkpoint when it clears safety guards."""
    if len(previous) < SWEEP_BOOTSTRAP_FLOOR or len(current) >= SWEEP_MIN_ROSTER_FRACTION * len(previous):
        save_current(current_path, current.values())
        log.info("checkpoint: %d/%d details fetched, %d inmates", done, total, len(current))
    else:
        log.info(
            "checkpoint skipped at %d/%d details: in-memory roster %d below %.0f%% of previous %d",
            done,
            total,
            len(current),
            100 * SWEEP_MIN_ROSTER_FRACTION,
            len(previous),
        )


def _fetch_details(
    *,
    client: HcsoClient,
    to_fetch: list[str],
    previous: dict[str, Inmate],
    current: dict[str, Inmate],
    row_by_id: dict[str, ListRow],
    dry_run: bool,
    waf_tracker: WafBackoffTracker,
    current_path: Path,
    photos_dir: Path,
) -> tuple[int, int, int]:
    """Run the detail-page worker pool and merge successful or fallback rows."""
    done = 0
    n_detail_attempts = 0
    n_detail_named = 0
    n_detail_with_photo = 0
    t0 = time.monotonic()
    sweep_started = time.monotonic()
    with ThreadPoolExecutor(max_workers=DEFAULT_CONCURRENCY) as pool:
        futures = {
            pool.submit(
                _fetch_one,
                client,
                iid,
                previous,
                row_by_id.get(iid),
                waf_tracker=waf_tracker,
                photos_dir=photos_dir,
            ): iid
            for iid in to_fetch
        }
        for fut in as_completed(futures):
            if time.monotonic() - sweep_started > SWEEP_WALLCLOCK_HARD_CAP_S:
                log.warning(
                    "sweep wall-clock cap reached at %d/%d details; finalizing",
                    done,
                    len(to_fetch),
                )
                break
            done += 1
            n_detail_attempts += 1
            iid = futures[fut]
            try:
                inm, detail_named, detail_had_photo = fut.result()
            except Exception as e:
                log.warning("detail fetch worker raised: %s", e)
                if iid in previous:
                    current[iid] = previous[iid].model_copy(update={"last_seen_utc": utcnow_iso()})
                continue
            if inm is not None:
                current[inm.inmate_number] = inm
            elif iid in previous:
                current[iid] = previous[iid].model_copy(update={"last_seen_utc": utcnow_iso()})
            if detail_named:
                n_detail_named += 1
            if detail_had_photo:
                n_detail_with_photo += 1
            if not dry_run and done % 50 == 0:
                _maybe_checkpoint_partial(previous, current, done, len(to_fetch), current_path)
    elapsed_s = round(time.monotonic() - t0, 2)
    log.info(
        "detail phase: %d attempts, %d named, %d with photo in %.1fs",
        n_detail_attempts,
        n_detail_named,
        n_detail_with_photo,
        elapsed_s,
    )
    return n_detail_attempts, n_detail_named, n_detail_with_photo


def _fetch_one(
    client: HcsoClient,
    inmate_id: str,
    previous: dict[str, Inmate],
    list_row: ListRow | None = None,
    *,
    waf_tracker: WafBackoffTracker,
    photos_dir: Path | None = None,
) -> tuple[Inmate | None, bool, bool]:
    """Fetch and parse one detail page."""
    if photos_dir is None:
        from ..sweep import PHOTOS_DIR
        photos_dir = PHOTOS_DIR
    inm, photo_bytes, photo_url = _fetch_detail_with_retry(client, inmate_id, previous, waf_tracker)
    if inm is None:
        return None, False, False
    detail_named = bool(inm.last_name or inm.first_name)
    detail_had_photo = bool(photo_bytes or photo_url)

    photo_bytes = _fetch_photo_bytes_from_url(client, inmate_id, photo_url, photo_bytes)
    _apply_list_row_fallback(inm, list_row)
    _attach_photo_filename(inm, photo_bytes, photos_dir)
    _set_seen_timestamps(inm, inmate_id, previous)
    return inm, detail_named, detail_had_photo


def _fetch_detail_with_retry(
    client: HcsoClient,
    inmate_id: str,
    previous: dict[str, Inmate],
    waf_tracker: WafBackoffTracker,
) -> tuple[Inmate | None, bytes | None, str | None]:
    inm = None
    photo_bytes = None
    photo_url = None
    html = ""
    for attempt in range(2):
        try:
            html = client.get(DETAIL_PATH, params={"id": inmate_id})
        except Exception as e:
            log.warning("detail fetch failed for id=%s: %s", inmate_id, e)
            return None, None, None
        inm, photo_bytes, photo_url = parse_detail_page(html, inmate_id)
        if not looks_like_waf_block(html, inm, photo_bytes, photo_url):
            waf_tracker.clear()
            break
        streak, backoff = waf_tracker.observe()
        if attempt == 0:
            log.warning(
                "WAF-block-shaped response for id=%s (%d bytes, streak=%d); sleeping %.1fs and retrying once",
                inmate_id,
                len(html),
                streak,
                backoff,
            )
            from ..import sweep
            sweep.time.sleep(backoff)
            continue
        log.warning(
            "WAF-block-shaped response for id=%s (%d bytes, streak=%d); "
            "retry also blocked, returning without overwriting",
            inmate_id,
            len(html),
            streak,
        )
        from ..import sweep
        sweep.time.sleep(backoff)
        if inmate_id in previous:
            return None, None, None
        break
    assert inm is not None
    return inm, photo_bytes, photo_url


def _fetch_photo_bytes_from_url(
    client: HcsoClient,
    inmate_id: str,
    photo_url: str | None,
    photo_bytes: bytes | None,
) -> bytes | None:
    if photo_url and not photo_bytes:
        try:
            return client.get_bytes(photo_url)
        except Exception as e:
            log.warning("photo URL fetch failed for id=%s url=%s: %s", inmate_id, photo_url, e)
    return photo_bytes


def _apply_list_row_fallback(inm: Inmate, list_row: ListRow | None) -> None:
    if list_row is None:
        return
    if not inm.last_name and list_row.last_name:
        inm.last_name = list_row.last_name
    if not inm.first_name and list_row.first_name:
        inm.first_name = list_row.first_name
    if not inm.booking_date and list_row.admit_date:
        inm.booking_date = list_row.admit_date


def _attach_photo_filename(inm: Inmate, photo_bytes: bytes | None, photos_dir: Path) -> None:
    photo_path = photos_dir / f"{inm.inmate_number}.jpg"
    if ".." in photo_path.name or "/" in photo_path.name or "\\" in photo_path.name:
        raise ValueError(f"unsafe photo filename: {photo_path.name!r}")

    try:
        resolved_photos_dir = photos_dir.resolve()
        resolved_photo_path = photo_path.resolve()
    except Exception as e:
        raise ValueError(f"could not resolve photo path: {e}") from e

    try:
        resolved_photo_path.relative_to(resolved_photos_dir)
    except ValueError as e:
        raise ValueError(
            f"unsafe photo path traversal: {photo_path} (resolved: {resolved_photo_path}) "
            f"is outside PHOTOS_DIR ({resolved_photos_dir})"
        ) from e

    if photo_bytes and downscale_and_save(photo_bytes, photo_path):
        inm.photo_filename = photo_path.name
    elif photo_path.exists():
        inm.photo_filename = photo_path.name


def _set_seen_timestamps(inm: Inmate, inmate_id: str, previous: dict[str, Inmate]) -> None:
    inm.first_seen_utc = (
        previous[inmate_id].first_seen_utc
        if inmate_id in previous and previous[inmate_id].first_seen_utc
        else utcnow_iso()
    )
    inm.last_seen_utc = utcnow_iso()
