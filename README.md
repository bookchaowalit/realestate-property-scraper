# book-property-scraping

**Tier:** B (catalog label; Big Loop target L3)  
**Owner path:** `bookchaowalit/book-apps/tools/book-property-scraping`

> **Source terms (2026-10-15):** unlicensed DDproperty automation is not approved; live runs below are not approved. See [Source terms decision](#source-terms-decision-2026-10-15).

## Purpose

Property listing scrape prototypes (e.g. DDProperty-style modules).

## Entry points

- `scrape_property_listings.py` (runner; exits 1 when a listing type fails or nothing is parsed)
- `property/ddproperty_scraper.py` (Bangkok condo-rent adapter, no CLI of its own)

## Stack

Python

## How to run (local)

```bash
# From this repository root
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 scrape_property_listings.py --dry-run              # plan only, no network or writes
# Live DDproperty runs are NOT approved (owner decision 2026-10-15):
# python3 scrape_property_listings.py --type condo_sale_bkk
```

Output goes to this repository's git-ignored `data/exported/`
(`property_listings.csv`, `property_history.csv`; the DDproperty adapter writes
`ddproperty_condos.csv`). The generic runner fetches one page per listing
type; `--max-pages` / `max_pages` are still accepted for scheduler
compatibility but ignored. Price drops are detected against the previous
history (before the current run is appended) and keyed by listing URL, falling
back to the title for rows written before `property_history.csv` had a `url`
column. URLs are canonicalised for that key (lower-case host, no fragment,
trailing slash or `utm_*`/`fbclid`/`gclid`-style tracking parameters), so the
same listing reached via different links keeps one history. All CSVs are
written atomically (`property/atomic_io.py`: temp file + fsync +
`os.replace`); `--alert-drop-pct` must be in (0, 100].

## Crawling behaviour (honest)

- Every request has a timeout (15-30 s); the generic runner waits 2 s between
  listing types.
- There is no retry/backoff or robots.txt check yet, and requests still send a
  browser-like `User-Agent`; see `docs/UPGRADE-PLAN.md`.
- When the direct page is empty, the runner falls back to scraping Brave/Bing
  (and Google) result pages, or Firecrawl when `FIRECRAWL_API_KEY` is set in
  the environment. Search-engine HTML scraping is against those engines' terms;
  treat it as prototype-only.

## Checks (offline)

```bash
uv sync --frozen --all-extras          # runtime deps + dev extra (pytest, ruff, mypy) from uv.lock
uv run ruff check . && uv run ruff format --check .
uv run mypy                            # scope and strictness: [tool.mypy] in pyproject.toml
uv run python -m pytest -q --cov       # CI gate: total coverage >= 87%
uv run python scrape_property_listings.py --dry-run   # plan only, no network
```

Tests replay `tests/fixtures/` and mock the HTTP layer (search pages included); a
conftest guard fails any real socket connection. CI (`.github/workflows/ci.yml`, shared
platform-ci-workflows v1.1.1) runs the same checks on Python 3.10 and 3.13.
`requirements.txt` is kept for the pip install path above; keep it in sync with
`pyproject.toml`.

## Error reporting (opt-in)

With `SENTRY_DSN` set (optionally `SENTRY_ENVIRONMENT`), a non-dry run sends one Sentry
`error` event per failed listing type, or one when nothing was parsed, carrying the type
and exception class only (`property/observability.py`). Init sets
`send_default_pii=False`, `include_local_variables=False`,
`max_request_body_size="never"`, tracing off, and `before_send=scrub_event`, which drops
locals, exception text, request data and breadcrumbs from every event, including
uncaught crashes. Without a DSN nothing is initialised; `--dry-run` never initialises it.

## Boundaries

- Target producer for `property.v1` (draft, pending); it does **not** land data in the lake, and its exports miss four required contract fields (see `specs/001-l2-baseline/spec.md`).
- **Not** coupled to Solo Empire monorepo runtime. Nested Git repo; commit only inside this tree.
- Never commit `.env`, cookies, session dumps, or scraped PII dumps to Git.

## Source terms decision (2026-10-15)

**property.v1 stays draft/pending (owner decision 2026-10-15, BOO-129).** Terms
are reviewed source by source:

- **DDproperty:** unlicensed automated collection is not approved. Its
  advertising rules prohibit unauthorised bots, crawling and data mining. The
  search-HTML fallback and "metadata is accessible" are **not** an exception for
  DDproperty.
- **Brave Search API:** no plan/order granting durable storage rights is
  evidenced, so no new persistent result payload. Such an order would not cover
  destination pages or contact data.
- **ENNXO, PropertyHub, LivingInsider, Zmyhome, TG Condo:** each still needs its
  own terms review; none is cleared.
- **PDPA:** contact purpose, legal basis, retention and deletion still need an
  operator/controller decision. No phone/email/LINE/individual contact use is
  approved.
- **Not yet enforced:** the parent scheduler's `property_listings` DDproperty
  job is still enabled at the time of this note; disabling it is a separate
  runtime follow-up.

This is an owner decision based on the published terms, not legal advice. Record: architecture-docs `systems/ai-data/source-terms-decisions-2026-10-15.md` (private repository).
Sources: [DDproperty advertising rules](https://www.ddproperty.com/en/advertising-rules),
[Brave Search API terms](https://api-dashboard.search.brave.com/documentation/resources/terms-of-service),
[Brave API storage FAQ](https://brave.com/search/api/).

## Limitations (honest)

Listing sites often ban scraping. Research/prototype only. No claim of live MLS integration.

## Related

- Active collection product: `book-job-scraping` (Tier A tool)
- Lake products: `book-crypto-data`, `book-fx-data`, `book-stock-data`, …
- Solo Empire catalog: `repository-catalog/BOOK-DEV-BACKLOG-BD.md` (BD-012)
