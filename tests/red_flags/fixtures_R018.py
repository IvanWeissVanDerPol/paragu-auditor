"""Cardinal-style OCID fixtures for R018 (single bid) tests.

Each fixture is a single CompiledRelease that exercises a specific case
of the R018 algorithm. The structure mirrors what Cardinal expects.
"""
from __future__ import annotations

from datetime import date

from paragu_auditor.data.schemas import (
    Award,
    Bid,
    CompiledRelease,
    Contract,
    Money,
    Tender,
)


def make_open_tender_one_valid_bid() -> CompiledRelease:
    """A competitive (open) tender with exactly 1 valid bid → FLAGGED."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T001",
        tender=Tender(
            id="T001",
            ocid="ocds-03ad3f-T001",
            title="Adquisición de equipos",
            procurement_method="open",
            procurement_method_details="CO",
            procuring_entity_name="Ministerio de Salud",
            tender_period_start=date(2024, 1, 1),
            tender_period_end=date(2024, 2, 1),
            value=Money(amount=1000000.0),
            bids=[
                Bid(
                    id="b1",
                    bidder_id="v1",
                    bidder_name="Vendor A",
                    amount=Money(amount=1000000.0),
                    status="valid",
                ),
            ],
            n_bids=1,
            n_valid_bids=1,
        ),
        awards=[
            Award(
                id="a1",
                ocid="ocds-03ad3f-T001",
                status="active",
                value=Money(amount=1000000.0),
                supplier_ids=["v1"],
                supplier_names=["Vendor A"],
            )
        ],
    )


def make_open_tender_two_valid_bids() -> CompiledRelease:
    """A competitive (open) tender with 2 valid bids → NOT FLAGGED."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T002",
        tender=Tender(
            id="T002",
            ocid="ocds-03ad3f-T002",
            title="Adquisición de equipos",
            procurement_method="open",
            procurement_method_details="LPN",
            bids=[
                Bid(id="b1", bidder_id="v1", bidder_name="Vendor A", amount=Money(amount=1000.0), status="valid"),
                Bid(id="b2", bidder_id="v2", bidder_name="Vendor B", amount=Money(amount=1100.0), status="valid"),
            ],
            n_bids=2,
            n_valid_bids=2,
        ),
    )


def make_open_tender_one_valid_one_disqualified() -> CompiledRelease:
    """Open tender, 1 valid + 1 disqualified → FLAGGED (count valid only)."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T003",
        tender=Tender(
            id="T003",
            ocid="ocds-03ad3f-T003",
            procurement_method="open",
            bids=[
                Bid(id="b1", bidder_id="v1", bidder_name="Vendor A", amount=Money(amount=1000.0), status="valid"),
                Bid(id="b2", bidder_id="v2", bidder_name="Vendor B", amount=Money(amount=1100.0), status="disqualified"),
            ],
            n_bids=2,
            n_valid_bids=1,
        ),
    )


def make_open_tender_zero_bids() -> CompiledRelease:
    """Open tender with no bids → SKIPPED (different anomaly)."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T004",
        tender=Tender(
            id="T004",
            ocid="ocds-03ad3f-T004",
            procurement_method="open",
            bids=[],
            n_bids=0,
            n_valid_bids=0,
        ),
    )


def make_selective_tender_one_bid() -> CompiledRelease:
    """A selective tender with 1 bid → FLAGGED."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T005",
        tender=Tender(
            id="T005",
            ocid="ocds-03ad3f-T005",
            procurement_method="selective",
            bids=[
                Bid(id="b1", bidder_id="v1", bidder_name="Vendor A", amount=Money(amount=500.0), status="valid"),
            ],
            n_bids=1,
            n_valid_bids=1,
        ),
    )


def make_direct_tender_one_bid() -> CompiledRelease:
    """A direct (non-competitive) tender with 1 bid → SKIPPED (not competitive)."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T006",
        tender=Tender(
            id="T006",
            ocid="ocds-03ad3f-T006",
            procurement_method="direct",
            bids=[
                Bid(id="b1", bidder_id="v1", bidder_name="Vendor A", amount=Money(amount=500.0), status="valid"),
            ],
            n_bids=1,
            n_valid_bids=1,
        ),
    )


def make_limited_tender_one_bid() -> CompiledRelease:
    """A limited (Compras Menores) tender with 1 bid → SKIPPED (already limited)."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T007",
        tender=Tender(
            id="T007",
            ocid="ocds-03ad3f-T007",
            procurement_method="limited",
            bids=[
                Bid(id="b1", bidder_id="v1", bidder_name="Vendor A", amount=Money(amount=500.0), status="valid"),
            ],
            n_bids=1,
            n_valid_bids=1,
        ),
    )


def make_limited_tender_excluded() -> CompiledRelease:
    """A limited tender should be excluded by default (not competitive)."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T008",
        tender=Tender(
            id="T008",
            ocid="ocds-03ad3f-T008",
            procurement_method="limited",
            bids=[
                Bid(id="b1", bidder_id="v1", bidder_name="Vendor A", amount=Money(amount=500.0), status="valid"),
            ],
            n_bids=1,
            n_valid_bids=1,
        ),
    )


def make_open_tender_one_bid_null_amount() -> CompiledRelease:
    """An open tender with 1 valid bid that has no amount → still FLAGGED."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T009",
        tender=Tender(
            id="T009",
            ocid="ocds-03ad3f-T009",
            procurement_method="open",
            bids=[
                Bid(id="b1", bidder_id="v1", bidder_name="Vendor A", amount=None, status="valid"),
            ],
            n_bids=1,
            n_valid_bids=1,
        ),
    )


# Cardinal reference example (parity test)
def make_cardinal_reference_fixture() -> CompiledRelease:
    """The exact Cardinal R018 example (paraguay-context-adjusted).

    Cardinal's example: an Education Ministry open tender with 1 bid.
    Output: {"OCID":{"F":{"R018":1.0}}}
    """
    return CompiledRelease(
        ocid="ocds-03ad3f-EDU-001",
        tender=Tender(
            id="EDU-001",
            ocid="ocds-03ad3f-EDU-001",
            title="School supplies tender",
            procurement_method="open",
            bids=[
                Bid(id="b1", bidder_id="edu-vendor", bidder_name="EduVendor Co", amount=Money(amount=5000000.0), status="valid"),
            ],
            n_bids=1,
            n_valid_bids=1,
        ),
    )
