"""Best-effort Datadog log emitter for sweep telemetry.

No-op when DD_API_KEY is unset. Never raises to callers.
"""

from __future__ import annotations

import logging
import os
import socket
from datetime import datetime, timezone
from typing import Any

import httpx

log = logging.getLogger(__name__)


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _base_tags() -> list[str]:
    tags: list[str] = []
    env = os.getenv("DD_ENV", "").strip()
    if env:
        tags.append(f"env:{env}")
    run_id = os.getenv("WORKFLOW_RUN_ID", "").strip()
    if run_id:
        tags.append(f"workflow_run_id:{run_id}")
    sha = os.getenv("COMMIT_SHA", "").strip()
    if sha:
        tags.append(f"commit_sha:{sha}")
    return tags


def emit(
    event: str,
    *,
    message: str,
    level: str = "info",
    attrs: dict[str, Any] | None = None,
    timeout_s: float = 5.0,
) -> bool:
    """Send one JSON log event to Datadog Logs v2 intake.

    Returns True on attempted success, False when disabled or on any send error.
    """
    api_key = os.getenv("DD_API_KEY", "").strip()
    if not api_key:
        return False

    dd_site = os.getenv("DD_SITE", "datadoghq.com").strip() or "datadoghq.com"
    url = f"https://http-intake.logs.{dd_site}/api/v2/logs"

    payload: dict[str, Any] = {
        "timestamp": _now_utc(),
        "status": level,
        "message": message,
        "event": event,
        "service": os.getenv("DD_SERVICE", "jcstream"),
        "ddsource": os.getenv("DD_SOURCE", "jcstream"),
        "hostname": socket.gethostname(),
        "ddtags": ",".join(_base_tags() + [f"event:{event}"]),
    }
    if attrs:
        payload.update(attrs)

    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": api_key,
    }
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=timeout_s)
        resp.raise_for_status()
        return True
    except Exception as e:
        log.warning("Datadog transport send failed for event=%s (%s)", event, e)
        return False
