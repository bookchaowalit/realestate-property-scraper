# book-property-scraping — Product brief

**Slug:** `bookchaowalit/realestate-property-scraper`  
**Tier:** B (catalog label) · target Big Loop L3  
**Status (2026-10-22):** DDproperty listing parsers and a runner with offline tests. Live
DDproperty collection is **not approved** (owner decision 2026-10-15, BOO-129; direct
access is also Cloudflare-challenged). Nothing from this repository runs on a schedule.

## Purpose

Property domain producer and target owner of `property.v1`: capture property listings
(type, price, rooms, area, location, URL) into CSVs for research and price-drop tracking.
Until a source is approved, the repo is kept as tested code and fixtures only.

## What exists

- `scrape_property_listings.py`: runner for 12 DDproperty listing types (one page each,
  2 s between types). It turns the page into markdown and extracts cards; when the page is
  empty it falls back to search-result pages (Brave → Bing → Firecrawl with
  `FIRECRAWL_API_KEY` → Google), which is degraded, prototype-only evidence. Writes
  `data/exported/property_listings.csv` and appends `property_history.csv`; reports price
  drops (default ≥ 10%) against history. `--dry-run` prints the plan without network,
  writes or reading `.env`. A failed type or a run with no listings exits 1.
- `property/ddproperty_scraper.py`: Bangkok condo-rent adapter for the Thai `/เช่าคอนโด`
  page (`__NEXT_DATA__` cards, then markdown, then search fallback); writes
  `ddproperty_condos.csv`. It has no command-line entry point of its own.
- `property/observability.py`: opt-in Sentry (see below).

Requests use a browser-like User-Agent and have no retry/backoff or robots.txt check
(see README and `docs/UPGRADE-PLAN.md`).

## Runtime status (verified 2026-10-22)

| What | Status |
|---|---|
| Entry point | `python scrape_property_listings.py [--type TYPE] [--alert-drop-pct N] [--output-dir DIR] [--dry-run]` |
| Who schedules it | Nobody from this repo: there is no cron or task script here, and this WSL host's crontab has no scraper entries on 2026-10-22. book-job-scraping's `config/jobs.yaml` still has `property_listings` enabled (daily 09:00), but it runs that repo's own copy, not this code; whether that scheduler runs on any host is not verified [ต้องยืนยัน] |
| Hosted deployment | None. No API, no port, no cloud job (scheduler host is owner decision D6) |
| Error reporting | Sentry, opt-in: with `SENTRY_DSN` set, each failed listing type (or an empty run) sends one `error` event (type + exception class; no page content, no PII; locals, request bodies, exception messages and breadcrumbs are stripped from any event, including uncaught crashes). No DSN is configured for this product yet [ต้องยืนยัน] |
| Contract | `property.v1` (architecture-docs `systems/architecture/scraping-contracts/`): status `draft`, `collection_approval: pending_operator_approval`. The exports use only contract field names but **miss four required fields** (`source_channel`, `source_platform`, `contact_public`, `lead_review_status`); `tests/test_contract.py` pins that gap |
| Lake landing | Not wired: no Bronze `property_listings` manifest is produced |
| Quality gates in CI | ruff, ruff format, mypy (gradual), offline pytest with coverage ≥ 87%, dry-run smoke, on Python 3.10 and 3.13; shared security scan (platform-ci-workflows v1.1.1) |

## Limits

- Not production: no approved source, no schedule, no lake landing, contract not met.
- The DDproperty decision is a policy; the code does not refuse a live run by itself.
- No contact or lead data is collected (PDPA purpose and retention pending).

## Docs

- `specs/001-l2-baseline/spec.md`: current spec (acceptance, red/green log, contract
  findings, planned schedule).
- `docs/measurement/KPI-PLAN.md`: data-product KPIs (freshness, rows, fallback share, contract).
- `docs/UPGRADE-PLAN.md`: earlier upgrade notes.
