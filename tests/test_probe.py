import importlib.util
import pytest

spec = importlib.util.spec_from_file_location("lab_probe", "lab/probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_allowlist_and_connection_time_validation(monkeypatch):
    with pytest.raises(ValueError, match="allowlisted"):
        probe.probe("example.com", 443)
    monkeypatch.setattr(
        probe.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("169.254.169.254", 8080))],
    )
    with pytest.raises(ValueError, match="private lab"):
        probe.probe("api", 8080)
    assert not probe.allowed("127.0.0.1")
    assert not probe.allowed("8.8.8.8")
    assert probe.allowed("172.20.1.5")
