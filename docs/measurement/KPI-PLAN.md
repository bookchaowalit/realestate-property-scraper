---
title: KPI and Instrumentation Plan — realestate-property-scraper
created: 2026-10-22
updated: 2026-10-22
status: draft
template: architecture-docs templates/sdlc/kpi-and-instrumentation-plan.md
---

# book-property-scraping — KPI and Instrumentation Plan

This is a data producer, not a user-facing product, so its KPIs are data-product KPIs:
freshness, volume, parse quality and contract conformance. **Live collection is not
approved** (DDproperty automation not approved by the owner on 2026-10-15, BOO-129;
`property.v1` is `draft`, `collection_approval: pending_operator_approval`), so no production baseline can be measured. Every
production figure below is `baseline: not yet measured`, and the targets apply only if a
property source is approved.

## Document control

| Field | Value |
|---|---|
| Project / product ID | book-property-scraping (`bookchaowalit/realestate-property-scraper`) |
| Version | 0.1 |
| Status | draft |
| Metric owner | bookchaowalit (owner) |
| AI maker | Claude session b-data (2026-10-22) |
| AI reviewer | pending [ต้องยืนยัน] |
| Charter objectives | Roadmap `data-scrapers.yaml` prp-g1..prp-g4 (no charter) |
| Analytics / data source of truth | Run output (stdout summary, exit code, `data/exported/*.csv`), Sentry events from `property/observability.py`; Bronze `property_listings` once wired |
| Dashboard | none yet [ต้องยืนยัน] |
| Next review | when property.v1 leaves `draft`/pending, or 2026-12-31 (roadmap horizon) |

## KPI tree

```text
OBJ-01 A contract-valid, fresh property listing feed (only if a source is approved)
  └─ KPI-O-01 Bronze freshness (hours since last successful capture)
       ├─ KPI-L-01 Rows per run
       ├─ KPI-L-02 Search-fallback share (degraded rows from search results)
       ├─ KPI-G-01 Contract violations per run
       ├─ KPI-G-02 Failed runs not reported
       └─ KPI-G-03 Contact data in exports
```

## KPI definitions

| KPI ID | Type | Name | Objective | Formula (numerator / denominator) | Unit | Min volume for a rate | Segment / filter | Data source and event(s) | Baseline (value, period, evidence) | Target (value, by date) | Alert threshold | Cadence | Owner |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KPI-O-01 | outcome | Bronze freshness | OBJ-01 | now − max(`captured_at`) of `property_listings` | hours | N/A | listing types of the approved source | Bronze manifest (not wired) | not yet measured (collection not approved) | ≤ 36 h, from the first approved schedule [ต้องยืนยัน] | > 36 h | per run | owner |
| KPI-L-01 | leading | Rows per run | OBJ-01 | listings written to `property_listings.csv` in one run | rows | N/A | per listing type | `scrape_property_listings.py` stdout (`Extracted N listings`) | not yet measured | ≥ 1 per listing type [ต้องยืนยัน] (0 overall fails the run) | 0 rows (the run already fails then) | per run | owner |
| KPI-L-02 | leading | Search-fallback share | OBJ-01 | rows from the search fallback / all rows | % | ≥ 20 rows | per run | not instrumented (rows do not record whether they came from search) | not yet measured | ≤ 10% [ต้องยืนยัน] | > 50% | per run | owner |
| KPI-G-01 | guardrail | Contract violations | OBJ-01 | rows missing a `property.v1` required field | rows | N/A | snapshot CSVs | `tests/test_contract.py` (offline, pins the known gap) | **every row**: 4 required fields are never written (`source_channel`, `source_platform`, `contact_public`, `lead_review_status`), 2026-10-22 | 0 before any approval [ต้องยืนยัน] | ≥ 1 | every CI run | owner |
| KPI-G-02 | guardrail | Failed runs not reported | OBJ-01 | failed jobs without a Sentry event / failed jobs | % | N/A | runs with `SENTRY_DSN` set | `property/observability.py` → Sentry; `tests/test_observability.py` | 0 in tests; production not measured (no DSN configured) | must stay 0 | ≥ 1 | per run | owner |
| KPI-G-03 | guardrail | Contact data in exports | OBJ-01 | `contact_*` fields present in any export (PDPA purpose/retention pending) | fields | N/A | all exports | `tests/test_contract.py` | 0, 2026-10-22 | must stay 0 until PDPA approval | ≥ 1 | every CI run | owner |

Rules from the template apply: no KPI without a baseline is used to claim a benefit, and
rates below the minimum volume are reported as `not measurable`.

## Event and data specification

| Event / field | Trigger (exact user or system action) | Properties | Personal data (incl. IDs / IP)? | Emitted by | Requirement / story | Status |
|---|---|---|---|---|---|---|
| failure row | a listing type raises, or the run parses nothing | `job` (type or `property_listings`), `error` (exception class) | no | `scrape_property_listings.py` | SPEC-001 | implemented |
| Sentry `error` event | a job fails in a non-dry run with `SENTRY_DSN` set | message `job <type> failed: <ExceptionClass>`, tag `component=scrape_property_listings`; locals, bodies, messages scrubbed, `environment` | no (`send_default_pii=False`) | `property/observability.py` | SPEC-001 AC-01 | implemented, not live (no DSN) |
| `scraped_at` | snapshot write | local naive time in `property_listings.csv`, UTC ISO-8601 in `ddproperty_condos.csv` (inconsistent; contract finding) | no | `scrape_property_listings.py`, `property/ddproperty_scraper.py` | property.v1 | implemented, needs UTC |
| fallback marker per row | a listing type falls back to search | page URL, reason | no | not implemented | KPI-L-02 | planned |

Privacy: no contact or lead fields are written; Sentry events carry no listing data.
PDPA purpose and retention are `pending_operator_legal_approval` in the contract [ต้องยืนยัน].

## Dashboards and alerts

| Dashboard / alert | KPIs shown | Audience | Location | Refresh | Alert channel | Status |
|---|---|---|---|---|---|---|
| Sentry project for this collector | KPI-G-02 | owner | not created [ต้องยืนยัน] | per event | Sentry → owner | planned (owner action) |
| Lake freshness monitor | KPI-O-01, KPI-L-01 | owner | parent `task scraping:coverage` | per run | [ต้องยืนยัน] | planned (needs an approved source and lake landing) |

## Instrumentation verification (before G10)

| # | Check | Evidence | Result |
|---|---|---|---|
| 1 | Events fire once per real action | `tests/test_observability.py` (one event per failed job) | pass (offline) |
| 2 | Counts reconcile with the system of record | needs a live run | not run (collection not approved) |
| 3 | No PII in payloads | `tests/test_contract.py` (no contact fields), `scrub_event` test | pass (offline) |
| 4 | Dashboard renders each KPI | no dashboard | not run |
| 5 | Alerts reach the channel | no Sentry DSN configured | not run |
| 6 | Baselines captured | not yet measured | waived until a source is approved |
| 7 | Consent | not applicable (no end users) | N/A |

## Change history of definitions

| Date | KPI ID | Change | Reason | Baseline restated? | Approved by |
|---|---|---|---|---|---|
| 2026-10-22 | all | First draft | Big Loop L3 baseline | no | pending |

## Quality gate and approval

| Gate | Condition | Decision | Approver | Date | Evidence |
|---|---|---|---|---|---|
| G5 | KPI definitions accepted | pending | owner | — | this file |
| G10 | Instrumentation checks pass | blocked: no approved source, no DSN | owner | — | — |
| G11 | Dashboard live | blocked | owner | — | — |
