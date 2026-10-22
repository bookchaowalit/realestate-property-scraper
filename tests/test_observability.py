"""SPEC-001 AC-01..AC-04: failed listing types are reported, opt-in Sentry only.

``collect`` catches each listing type's exception, prints it and moves on, and
``main`` returned 0 even when every type failed or nothing was parsed, so a
broken scheduled run looked like a success. These tests pin that a failed type
or an empty run exits 1 and, with ``SENTRY_DSN`` set, becomes a Sentry event
carrying only the type and the exception class (never page content). No
network: ``collect_type`` and ``sentry_sdk`` are fakes, and ``.env`` is never read.
"""

import sys
import types
from unittest import mock

import pytest

import scrape_property_listings as source

SECRET_PAGE_TEXT = "agent phone 081-234-5678"
LISTING = {
    "title": "Condo near BTS Ari",
    "type": "condo_sale_bkk",
    "url": "https://www.ddproperty.com/en/property/condo-ari-1",
    "price_raw": "฿3,500,000",
    "price": 3_500_000.0,
}


class FakeSentry(types.ModuleType):
    def __init__(self):
        super().__init__("sentry_sdk")
        self.init_kwargs = None
        self.messages = []
        self.tags = {}

    def init(self, **kwargs):
        self.init_kwargs = kwargs

    def set_tag(self, key, value):
        self.tags[key] = value

    def capture_message(self, message, level=None):
        self.messages.append((message, level))

    def flush(self, timeout=None):
        return None


@pytest.fixture
def sentry(monkeypatch):
    fake = FakeSentry()
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake)
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.delenv("SENTRY_ENVIRONMENT", raising=False)
    monkeypatch.setattr(source, "_load_runtime_env", lambda: None)
    return fake


def _run(tmp_path, collect_type, *types_):
    argv = ["--output-dir", str(tmp_path)]
    if len(types_) == 1:
        argv += ["--type", types_[0]]
    with (
        mock.patch.object(source, "collect_type", side_effect=collect_type),
        mock.patch.object(source, "TYPE_DELAY_SECONDS", 0),
    ):
        return source.main(argv)


def test_failed_type_reaches_sentry_and_exits_1(sentry, monkeypatch, tmp_path):
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.invalid/1")

    def collect_type(listing_type, _url):
        if listing_type == "land_sale_bkk":
            raise RuntimeError(SECRET_PAGE_TEXT)
        return [dict(LISTING, type=listing_type)]

    code = _run(tmp_path, collect_type)

    assert code == 1
    assert len(sentry.messages) == 1, sentry.messages
    message, level = sentry.messages[0]
    assert level == "error"
    assert "land_sale_bkk" in message and "RuntimeError" in message
    assert SECRET_PAGE_TEXT not in message
    assert sentry.init_kwargs["send_default_pii"] is False
    # The other types were still written.
    assert (tmp_path / "property_listings.csv").exists()


def test_run_with_no_listings_exits_1_and_is_reported(sentry, monkeypatch, tmp_path):
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.invalid/1")

    code = _run(tmp_path, lambda _t, _u: [], "condo_sale_bkk")

    assert code == 1
    assert len(sentry.messages) == 1, sentry.messages
    assert "property_listings" in sentry.messages[0][0]
    assert not (tmp_path / "property_listings.csv").exists()


def test_successful_run_sends_nothing(sentry, monkeypatch, tmp_path):
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.invalid/1")

    code = _run(tmp_path, lambda t, _u: [dict(LISTING, type=t)], "condo_sale_bkk")

    assert code == 0
    assert sentry.messages == []


def test_without_dsn_sentry_stays_off(sentry, tmp_path):
    code = _run(tmp_path, lambda _t, _u: [], "condo_sale_bkk")

    assert code == 1
    assert sentry.init_kwargs is None


def test_dry_run_never_initialises_sentry(sentry, monkeypatch, tmp_path):
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.invalid/1")
    assert source.main(["--dry-run", "--output-dir", str(tmp_path)]) == 0
    assert sentry.init_kwargs is None


def test_init_never_sends_locals_bodies_or_messages(sentry, monkeypatch):
    # AC-04: sentry_sdk.init also installs the excepthook, so an uncaught crash
    # would otherwise carry frame locals and the exception message (page text).
    from property.observability import init_sentry

    monkeypatch.setenv("SENTRY_DSN", "https://public@example.invalid/1")
    assert init_sentry("test") is not None
    kwargs = sentry.init_kwargs
    assert kwargs["include_local_variables"] is False
    assert kwargs["max_request_body_size"] == "never"

    event = {
        "request": {"data": SECRET_PAGE_TEXT},
        "breadcrumbs": {"values": [{"message": SECRET_PAGE_TEXT}]},
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": SECRET_PAGE_TEXT,
                    "stacktrace": {
                        "frames": [{"function": "collect", "vars": {"key": "secret"}}]
                    },
                }
            ]
        },
    }
    scrubbed = kwargs["before_send"](event, {})

    assert SECRET_PAGE_TEXT not in repr(scrubbed)
    assert "secret" not in repr(scrubbed)
    assert scrubbed["exception"]["values"][0]["type"] == "ValueError"
