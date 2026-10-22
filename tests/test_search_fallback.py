"""Offline tests for the search-fallback and page-to-markdown helpers.

Every HTTP call is replaced by a fake response built from hand-written HTML, so no
request leaves the process (the conftest guard would fail it anyway). These pin how
search result pages are parsed, which garbage URLs are dropped, and that failures
degrade to an empty result instead of raising.
"""

import base64
from unittest.mock import patch

import httpx

import scrape_property_listings as source

DDP = "https://www.ddproperty.com/en/property/condo-ari-1"


def _resp(status, text="", url="https://example.invalid/", json=None):
    request = httpx.Request("GET", url)
    if json is not None:
        return httpx.Response(status, json=json, request=request)
    return httpx.Response(status, text=text, request=request)


BRAVE_HTML = f"""
<div data-pos="1"><a class="result-header" href="{DDP}">Condo Ari ฿3,500,000</a>
  <p class="snippet-description">2 beds near BTS</p></div>
<div data-pos="2"><a class="result-header" href="https://www.youtube.com/watch?v=1">Video</a></div>
<div data-pos="3"><a class="result-header" href="/relative">Relative</a></div>
"""

BING_TARGET = "https://www.ddproperty.com/en/property/condo-ekkamai-2"
BING_ENCODED = "a1" + base64.b64encode(BING_TARGET.encode()).decode().rstrip("=")
BING_HTML = f"""
<ol>
<li class="b_algo"><h2><a href="https://www.bing.com/ck/a?u={BING_ENCODED}&ntb=1">Condo Ekkamai</a></h2>
  <p>฿22,000/month</p></li>
<li class="b_algo"><h2>No link</h2></li>
<li class="b_algo"><h2><a href="https://accounts.google.com/x">Login</a></h2></li>
</ol>
"""


def test_decode_bing_redirect_handles_base64_plain_and_other_urls():
    assert (
        source._decode_bing_redirect(f"https://www.bing.com/ck/a?u={BING_ENCODED}")
        == BING_TARGET
    )
    assert (
        source._decode_bing_redirect(
            "https://www.bing.com/ck/a?u=https%3A%2F%2Fx.test%2Fa"
        )
        == "https://x.test/a"
    )
    assert source._decode_bing_redirect(DDP) == DDP


def test_brave_search_keeps_valid_absolute_results():
    with patch.object(source.httpx, "get", return_value=_resp(200, BRAVE_HTML)):
        results = source._brave_search("ddproperty condo", limit=5)

    assert results == [
        {"title": "Condo Ari ฿3,500,000", "url": DDP, "description": "2 beds near BTS"}
    ]


def test_brave_rate_limit_falls_back_to_bing():
    responses = [_resp(429), _resp(200, BING_HTML)]
    with patch.object(source.httpx, "get", side_effect=responses):
        results = source._brave_search("ddproperty condo", limit=5)

    assert [item["url"] for item in results] == [BING_TARGET]
    assert results[0]["description"] == "฿22,000/month"


def test_search_failures_degrade_to_empty_results(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    with patch.object(source.httpx, "get", side_effect=httpx.ConnectError("offline")):
        assert source._bing_search("q") == []
        assert source._brave_search("q") == []
        assert source.google_search("q") == []
    assert source._firecrawl_search("q") == []


def test_firecrawl_search_maps_results_when_a_key_is_set(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    payload = {
        "data": [
            {"title": "Condo Ari", "url": DDP, "description": "฿3.5 ล้าน"},
            {"title": ""},
        ]
    }
    with patch.object(
        source.httpx, "post", return_value=_resp(200, json=payload)
    ) as post:
        results = source._firecrawl_search("q", limit=5)

    assert results == [{"title": "Condo Ari", "url": DDP, "description": "฿3.5 ล้าน"}]
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_free_scrape_url_turns_main_content_into_markdown():
    html = """<html><body><nav>menu</nav><main>
      <h2>Condo Ari</h2><p><b>฿3,500,000</b></p><a href="/p/1">details</a>
      <script>secret()</script></main></body></html>"""
    with patch.object(source.httpx, "get", return_value=_resp(200, html)):
        text = source.free_scrape_url("https://www.ddproperty.com/x")

    assert "## Condo Ari" in text
    assert "**฿3,500,000**" in text
    assert "[details](/p/1)" in text
    assert "menu" not in text and "secret" not in text


def test_free_scrape_url_returns_empty_on_http_error():
    with patch.object(source.httpx, "get", return_value=_resp(403, "blocked")):
        assert source.free_scrape_url("https://www.ddproperty.com/x") == ""


def test_search_fallback_keeps_portal_hosts_and_price_hints():
    results = [
        {
            "title": "DDProperty › Condo for Sale › Ari Residence",
            "url": DDP,
            "description": "฿3,500,000",
        },
        {
            "title": "Lookalike",
            "url": "https://ddproperty.com.evil.test/x",
            "description": "",
        },
    ]
    with patch.object(source, "google_search", return_value=results):
        listings = source._search_fallback_listings("condo_sale_bkk")

    assert [(item["title"], item["price"]) for item in listings] == [
        ("Ari Residence", 3_500_000.0)
    ]
    assert listings[0]["location"] == "Bkk"
