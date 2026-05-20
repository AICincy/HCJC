from scraper import egress_ip


def test_ip_in_ranges():
    assert egress_ip.ip_in_ranges("192.30.252.1", ["192.30.252.0/22"]) is True
    assert egress_ip.ip_in_ranges("8.8.8.8", ["192.30.252.0/22"]) is False
    # A malformed IP or CIDR never matches (and never raises).
    assert egress_ip.ip_in_ranges("not-an-ip", ["192.30.252.0/22"]) is False
    assert egress_ip.ip_in_ranges("8.8.8.8", ["garbage"]) is False


def test_snapshot_uses_provided_ip(monkeypatch):
    # Mock the network: a provided runner_ip skips the ipify lookup entirely.
    monkeypatch.setattr(egress_ip, "github_actions_ranges", lambda: ["10.0.0.0/8"])
    rec = egress_ip.snapshot("10.1.2.3")
    assert rec["runner_ip"] == "10.1.2.3"
    assert rec["runner_ip_in_actions_range"] is True
    assert rec["actions_range_count"] == 1
    assert isinstance(rec["captured_utc"], str)


def test_snapshot_ip_outside_range(monkeypatch):
    monkeypatch.setattr(egress_ip, "github_actions_ranges", lambda: ["10.0.0.0/8"])
    rec = egress_ip.snapshot("8.8.8.8")
    assert rec["runner_ip_in_actions_range"] is False


def test_main_writes_out(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(egress_ip, "github_actions_ranges", lambda: ["10.0.0.0/8"])
    out = tmp_path / "egress_evidence.json"
    rc = egress_ip.main(["10.1.2.3", "--out", str(out)])
    assert rc == 0
    assert out.exists()
    assert "10.1.2.3" in capsys.readouterr().out
