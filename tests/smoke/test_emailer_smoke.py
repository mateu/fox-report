import smtplib
from types import SimpleNamespace

from fox_report.emailer import send


class DummySSL:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return SimpleNamespace(login=lambda u, p: None, send_message=lambda m: None)

    def __exit__(self, exc_type, exc, tb):
        return False


def test_send_uses_smtp_ssl(monkeypatch):
    calls = []

    def fake_ssl(host):
        calls.append(host)
        return DummySSL()

    # Patch SMTP_SSL and config settings
    monkeypatch.setattr(smtplib, "SMTP_SSL", fake_ssl)

    # Minimal message object
    class Msg:
        pass

    # Patch settings import inside module by simulating attribute
    import fox_report.config as cfg

    original_host = getattr(cfg.settings, "smtp_host", None)
    try:
        cfg.settings.smtp_host = "smtp.test.local"
        send(Msg())
    finally:
        if original_host is not None:
            cfg.settings.smtp_host = original_host

    assert calls == ["smtp.test.local"]
