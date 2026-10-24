---
id: SPEC-001
title: L2/L3 baseline for realestate-property-scraper
status: approved
created: 2026-10-22
owner: bookchaowalit
---

# SPEC-001: L2/L3 baseline

## Document control

| Field | Value |
|---|---|
| Main-only | yes (ADR-0004 v1.1: red run is local, red and green commits pushed together) |
| Maker | Claude session b-data (2026-10-22) |
| Checker / approver | independent Claude reviewer / AI approval 2026-10-24 (see Approval) |

## Problem

The Big Loop scorecard (2026-10-22) had this repo at L0: no lockfile, no type check, no
error reporting, no KPI plan and no spec. Two real bugs were found while adding tests:

- `scrape_property_listings.main()` returned 0 even when every listing type raised or
  nothing was parsed: `collect()` prints the error and moves on, so a broken run looked
  like a success to any scheduler.
- `DDPropertyScraper` gave every card without its own URL the search page URL, so all
  URL-less cards shared one dedupe key (and one `property.v1` identity) and all but the
  first were silently dropped.

## Behaviour

1. Dependencies resolve from the committed `uv.lock`; CI installs with
   `uv sync --frozen --all-extras`. `requirements.txt` stays (README install path) and is
   kept in sync with `pyproject.toml` by hand.
2. `mypy` runs in CI over `property/`, `scrape_property_listings.py` and `tests/`
   (gradual; strict on `property/observability.py`).
3. `collect(..., failures=[...])` records each failed listing type as
   `{"job": <type>, "error": <ExceptionClass>}`. A non-dry `main()` exits 1 when any type
   failed or no listing was parsed (`{"job": "property_listings", "error":
   "NoListingsParsed"}`), as the sibling runners do; the other types are still written.
4. When `SENTRY_DSN` is set and `sentry-sdk` is installed, each such failure sends one
   Sentry `error` event with the type name and exception class only. Init sets
   `send_default_pii=False`, `include_local_variables=False`,
   `max_request_body_size="never"`, tracing off, and `before_send=scrub_event`, which drops
   frame variables and source context, exception messages, request data, breadcrumbs,
   extras, user and contexts (this also covers uncaught crashes reported by the SDK
   excepthook). Without a DSN, or with `--dry-run`, Sentry is never initialised and
   `.env` is not read.
5. A DDproperty card without a URL keeps an empty `url` and is deduped by title.
6. CI fails when total coverage drops below 87%.

## Acceptance

| AC | Given / When / Then | Test |
|---|---|---|
| AC-01 | Given `SENTRY_DSN` is set, when one listing type raises and the others succeed, then the run exits 1, writes the other types, and sends one `error` event naming the type and `RuntimeError` with no page text | `tests/test_observability.py::test_failed_type_reaches_sentry_and_exits_1` |
| AC-02 | Given `SENTRY_DSN` is set, when no listing is parsed, then the run exits 1, writes nothing and sends one event | `test_run_with_no_listings_exits_1_and_is_reported` |
| AC-03 | Given a run with listings and no failure, then it exits 0 and sends nothing; without a DSN or with `--dry-run`, Sentry is not initialised | `test_successful_run_sends_nothing`, `test_without_dsn_sentry_stays_off`, `test_dry_run_never_initialises_sentry` |
| AC-04 | Given `SENTRY_DSN` is set, when Sentry is initialised, then locals and request bodies are off and `before_send` strips page text, tokens and request data while keeping the exception type | `test_init_never_sends_locals_bodies_or_messages` |
| AC-05 | Given two DDproperty markdown cards without URLs, when parsed, then both are kept with an empty `url` | `tests/test_ddproperty_scraper.py::test_listings_without_urls_are_not_collapsed_into_one` |
| AC-06 | The snapshot headers use only `property.v1` field names, carry no contact fields, and miss exactly the known required fields (see Contract findings) | `tests/test_contract.py` |
| AC-07 | CI on `main` is green on Python 3.10 and 3.13 with ruff, ruff format, mypy and the 87% coverage gate | CI run below |

## Red/green log

| AC | Red (sha · command · failure) | Green |
|---|---|---|
| AC-05 | `3092096` · `python -m pytest -q tests/test_ddproperty_scraper.py` · `AssertionError: Lists differ: ['Condo for rent near BTS Ari'] != ['Condo for rent near BTS Ari', 'Condo for rent near BTS Ekkamai']` | [CI 39755698429](https://github.com/bookchaowalit/realestate-property-scraper/actions/runs/39755698429) (success, 3.10 + 3.13, coverage gate 87) |
| AC-01..AC-04 | `bfd6224` · `python -m pytest -q tests/test_observability.py` · `assert 0 == 1` (exit code 0 for a failed / empty run) and `ModuleNotFoundError: No module named 'property.observability'` | [CI 39755698429](https://github.com/bookchaowalit/realestate-property-scraper/actions/runs/39755698429) (success, 3.10 + 3.13, coverage gate 87) |
| AC-06 | none: written green as a guard that pins the known contract gap | [CI 39755698429](https://github.com/bookchaowalit/realestate-property-scraper/actions/runs/39755698429) (success, 3.10 + 3.13, coverage gate 87) |

## Contract findings (property.v1, not fixed here)

- Required `source_channel`, `source_platform`, `contact_public` and `lead_review_status`
  are written by neither `property_listings.csv` nor `ddproperty_condos.csv`, so every row
  would be quarantined; identity `<source_platform>|<url>` cannot be formed.
- `scraped_at` is local naive time (`%Y-%m-%d %H:%M:%S`) in `property_listings.csv`, but
  UTC ISO-8601 in `ddproperty_condos.csv`; no `captured_at` is written.
- Rows from the markdown parser or the search fallback can have an empty `url` (required).
- The DDproperty source itself is `not_approved_unlicensed_automation` (BOO-129).

## Schedule (planned replacement, D6)

No scheduler was changed (owner decision D6 on the schedule host is open).

- Today: this repository has no scheduler script. On 2026-10-22 this WSL host's crontab
  has no scraper entries. book-job-scraping (`career-job-scraper`) `config/jobs.yaml` still
  has `property_listings` **enabled** (daily 09:00) but it runs that repo's own copy
  (`scripts.scrape_property_listings`), not this code; its `ddproperty_condos` job is
  disabled. Whether that scheduler runs on any host is not verified [ต้องยืนยัน].
- Planned replacement once D6 is decided **and** a property source is approved under
  property.v1: one hosted daily job (36-hour freshness SLO in the roadmap) that runs
  `python scrape_property_listings.py --type <approved type>` from this repository with
  `SENTRY_DSN` set, so a failed type or empty run is a Sentry event and a non-zero exit, and
  hands the capture to the parent replay into Bronze `property_listings`. The
  book-job-scraping job is disabled at the same time (roadmap prp-g2). Until then there is
  nothing to schedule.

## Out of scope

Live captures (DDproperty not approved), lake writes to R2, migrating the property lanes
from book-job-scraping, contact/lead fields (PDPA pending), and the contract gaps above.

## Approval (2026-10-24)

| Field | Value |
|---|---|
| Checker | independent Claude reviewer subagent (`solo:solo-reviewer`, Sonnet, read-only, no maker context) |
| Approver | AI approval under the owner's process (approvals by the owner or AI with evidence; maker and checker are different agents). Recorded by Claude session oa-remainder on the owner's instruction "ทำที่เหลือให้หน่อย" (2026-10-24) |
| Verdict | **approved** |
| Tests run by the checker | uv run --frozen --offline pytest -q --cov: 63 passed, coverage 88% (gate 87) |
| Evidence | tests/test_observability.py (AC-01..04), test_ddproperty_scraper.py, test_contract.py; collect(failures=), exit 1, ci.yml gate 87. AC-07 CI run not re-verified. |
