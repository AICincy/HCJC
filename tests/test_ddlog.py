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


def test_emit_swallows_send_errors(monkeypatch, caplog):
    monkeypatch.setenv("DD_API_KEY", "k")

    def _boom(*args, **kwargs):
        raise RuntimeError("nope")

    monkeypatch.setattr(ddlog.httpx, "post", _boom)
    with caplog.at_level("WARNING"):
        assert ddlog.emit("x", message="msg") is False
    assert "Datadog transport send failed for event=x" in caplog.text


def test_sweep_id_threaded_into_payload(monkeypatch):
    monkeypatch.setenv("DD_API_KEY", "k")
    sent: dict = {}

    def _fake_post(url, json=None, headers=None, timeout=None):
        sent["json"] = json
        return httpx.Response(202, request=httpx.Request("POST", url))

    monkeypatch.setattr(ddlog.httpx, "post", _fake_post)

    ddlog.set_sweep_id("abc123")
    try:
        ddlog.emit("test_event", message="test")
        assert sent["json"]["sweep_id"] == "abc123"
        assert "sweep_id:abc123" in sent["json"]["ddtags"]
    finally:
        ddlog.set_sweep_id(None)


def test_sweep_id_absent_when_not_set(monkeypatch):
    monkeypatch.setenv("DD_API_KEY", "k")
    sent: dict = {}

    def _fake_post(url, json=None, headers=None, timeout=None):
        sent["json"] = json
        return httpx.Response(202, request=httpx.Request("POST", url))

    monkeypatch.setattr(ddlog.httpx, "post", _fake_post)
    ddlog.set_sweep_id(None)
    ddlog.emit("test_event", message="test")
    assert "sweep_id" not in sent["json"]
    assert "sweep_id:" not in sent["json"]["ddtags"]
