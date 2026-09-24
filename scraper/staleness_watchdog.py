"""Out-of-band staleness watchdog: runs both alarms outside ``sweep.yml``.

Invoked by ``.github/workflows/staleness-watchdog.yml`` on its own schedule, so
a stalled sweep cron can no longer silence the alarms that are supposed to
report it. Two checks, both read-only against the repo:

1. **Roster freeze / sweep stall** -- ``scraper.freeze_alert.alert``. It measures
   wall-clock age of the committed ``data/current.json``, so it fires the same
   way whether the sweep is running-but-WAF-blocked or not running at all. Only
   the issue tier runs here; the sub-6h ``::warning`` tier stays in the sweep,
   because its throttle state is a runner-local file that would not persist
   between watchdog runs and would annotate every cycle.
2. **Stuck Pages deploy** -- ``scraper.deploy_alert.alert``, which compares the
   live ``/data/current.json`` with the committed one.

Each check is isolated: an exception in one is logged and never prevents the
other, and the watchdog always exits 0 (alerting must not create red CI noise
of its own; the alarms surface via ``::error`` annotations and issues).
"""

from __future__ import annotations

import logging
import os

from . import deploy_alert, freeze_alert
from .sweep import CURRENT_PATH, _prev_generated_utc
from .sweep_guards import roster_stale_hours

log = logging.getLogger("jcstream.sweep")


def run(local_generated: str | None, site_url: str) -> dict[str, str]:
    """Run both checks and return ``{"freeze": action, "deploy": action}``."""
    results: dict[str, str] = {}
    try:
        results["freeze"] = freeze_alert.alert(roster_stale_hours(local_generated))
    except Exception as e:  # noqa: BLE001 - one alarm must never block the other
        log.warning("watchdog: freeze check raised %s: %s", type(e).__name__, e)
        results["freeze"] = "error"
    try:
        live_generated = deploy_alert._fetch_live_generated(site_url)
        results["deploy"] = deploy_alert.alert(local_generated, live_generated)
    except Exception as e:  # noqa: BLE001
        log.warning("watchdog: deploy check raised %s: %s", type(e).__name__, e)
        results["deploy"] = "error"
    log.info("watchdog results: %s", results)
    return results


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    site_url = os.environ.get("JCSTREAM_SITE_URL", deploy_alert.DEFAULT_SITE_URL)
    run(_prev_generated_utc(CURRENT_PATH), site_url)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
