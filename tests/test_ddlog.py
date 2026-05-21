import httpx

from scraper import ddlog


def test_emit_returns_false_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("DD_API_KEY", raising=False)
    assert ddlog.emit("x", message="msg") is False


def test_emit_posts_expected_payload(monkeypatch):
    monkeypatch.setenv("DD_API_KEY", "k")
    monkeypatch.setenv("DD_SITE", "us5.datadoghq.com")
    monkeypatch.setenv("DD_ENV", "prod")
    monkeypatch.setenv("DD_SERVICE", "jcstream")
    monkeypatch.setenv("DD_SOURCE", "jcstream")
    monkeypatch.setenv("WORKFLOW_RUN_ID", "123")
    monkeypatch.setenv("COMMIT_SHA", "abc")

    sent: dict = {}

    def _fake_post(url, json=None, headers=None, timeout=None):
        sent["url"] = url
        sent["json"] = json
        sent["headers"] = headers
        sent["timeout"] = timeout
        return httpx.Response(202, request=httpx.Request("POST", url))

    monkeypatch.setattr(ddlog.httpx, "post", _fake_post)

    ok = ddlog.emit("sweep.degraded.list", message="degraded", level="error", attrs={"seen_count": 0})

    assert ok is True
    assert sent["url"] == "https://http-intake.logs.us5.datadoghq.com/api/v2/logs"
    assert sent["headers"]["DD-API-KEY"] == "k"
    assert sent["json"]["event"] == "sweep.degraded.list"
    assert sent["json"]["status"] == "error"
    assert sent["json"]["seen_count"] == 0
    assert "env:prod" in sent["json"]["ddtags"]
    assert "workflow_run_id:123" in sent["json"]["ddtags"]
    assert "commit_sha:abc" in sent["json"]["ddtags"]
    assert "event:sweep.degraded.list" in sent["json"]["ddtags"]


def test_emit_swallows_send_errors(monkeypatch):
    monkeypatch.setenv("DD_API_KEY", "k")

    def _boom(*args, **kwargs):
        raise RuntimeError("nope")

    monkeypatch.setattr(ddlog.httpx, "post", _boom)
    assert ddlog.emit("x", message="msg") is False
