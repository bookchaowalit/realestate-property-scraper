"""SPEC-001 AC-06: the exports are checked against the property.v1 contract, offline.

The contract lives in the private architecture-docs repository
(``systems/architecture/scraping-contracts/property.v1.yaml``), which CI cannot read,
so the fields are copied here (2026-10-22, status ``draft``,
``collection_approval: pending_operator_approval``). Update them from that file in the
same commit as the code.

The exports do **not** conform yet: the contract requires ``source_channel``,
``source_platform``, ``contact_public`` and ``lead_review_status``, which no writer
emits. That gap is pinned in ``KNOWN_MISSING_REQUIRED`` so it cannot grow silently and
so closing it shows up here; it is a finding for the owner, not something this test
hides.
"""

import csv

import scrape_property_listings as source
from property.ddproperty_scraper import FIELDNAMES as DDPROPERTY_FIELDS
from property.ddproperty_scraper import DDPropertyScraper

CONTRACT_RECORD_FIELDS = {
    "scraped_at",
    "captured_at",
    "title",
    "type",
    "listing_type",
    "url",
    "price_raw",
    "price",
    "bedrooms",
    "bathrooms",
    "area_sqm",
    "location",
    "description",
    "source_channel",
    "source_platform",
    "contact_name",
    "contact_role",
    "co_agent_status",
    "contact_phone",
    "contact_email",
    "contact_line",
    "contact_source_url",
    "contact_evidence",
    "contact_confidence",
    "contact_public",
    "lead_review_status",
    "review_decision",
    "reviewed_at",
    "reviewer_id",
    "outreach_status",
    "retention_until",
    "terms_basis_ref",
}
CONTRACT_REQUIRED = {
    "scraped_at",
    "title",
    "url",
    "source_channel",
    "source_platform",
    "contact_public",
    "lead_review_status",
}
KNOWN_MISSING_REQUIRED = {
    "source_channel",
    "source_platform",
    "contact_public",
    "lead_review_status",
}
CONTACT_FIELDS = {f for f in CONTRACT_RECORD_FIELDS if f.startswith("contact_")}

LISTING = {
    "title": "Condo near BTS Ari",
    "type": "condo_sale_bkk",
    "url": "https://www.ddproperty.com/en/property/condo-ari-1",
    "price_raw": "฿3,500,000",
    "price": 3_500_000.0,
}


def _header(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return csv.DictReader(handle).fieldnames


def test_listing_snapshot_uses_only_contract_field_names(tmp_path):
    source.save_listings([LISTING], tmp_path)
    header = set(_header(tmp_path / "property_listings.csv"))

    assert header <= CONTRACT_RECORD_FIELDS, header - CONTRACT_RECORD_FIELDS
    assert CONTRACT_REQUIRED - header == KNOWN_MISSING_REQUIRED
    # No contact data is collected while PDPA purpose/retention are pending.
    assert not header & CONTACT_FIELDS


def test_ddproperty_snapshot_uses_only_contract_field_names(tmp_path):
    scraper = DDPropertyScraper(output_dir=tmp_path)
    path = scraper._write_snapshot([dict(LISTING)], "2026-10-22T00:00:00+00:00")
    header = set(_header(path))

    assert set(DDPROPERTY_FIELDS) == header
    assert header <= CONTRACT_RECORD_FIELDS, header - CONTRACT_RECORD_FIELDS
    assert CONTRACT_REQUIRED - header == KNOWN_MISSING_REQUIRED
    assert not header & CONTACT_FIELDS


def test_written_rows_carry_title_url_and_timestamp(tmp_path):
    source.save_listings([LISTING], tmp_path)
    with (tmp_path / "property_listings.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert rows and all(
        row["title"] and row["url"] and row["scraped_at"] for row in rows
    )
