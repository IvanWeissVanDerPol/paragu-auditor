"""Cardinal-style OCID fixtures for R003 (short submission period)."""
from __future__ import annotations

from datetime import date

from paragu_auditor.data.schemas import (
    CompiledRelease,
    Money,
    Tender,
)


def make_short_open_tender() -> CompiledRelease:
    """Open tender with 7-day submission period (below default 15)."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T001",
        tender=Tender(
            id="T001",
            ocid="ocds-03ad3f-T001",
            title="Short tender",
            procurement_method="open",
            tender_period_start=date(2024, 1, 1),
            tender_period_end=date(2024, 1, 8),  # 7 days
        ),
    )


def make_just_below_threshold() -> CompiledRelease:
    """Open tender with 14-day period (1 day below default 15)."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T002",
        tender=Tender(
            id="T002",
            ocid="ocds-03ad3f-T002",
            procurement_method="open",
            tender_period_start=date(2024, 1, 1),
            tender_period_end=date(2024, 1, 15),  # 14 days
        ),
    )


def make_exactly_at_threshold() -> CompiledRelease:
    """Open tender with exactly 15-day period (NOT below threshold)."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T003",
        tender=Tender(
            id="T003",
            ocid="ocds-03ad3f-T003",
            procurement_method="open",
            tender_period_start=date(2024, 1, 1),
            tender_period_end=date(2024, 1, 16),  # 15 days
        ),
    )


def make_above_threshold() -> CompiledRelease:
    """Open tender with 30-day period (above default 15)."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T004",
        tender=Tender(
            id="T004",
            ocid="ocds-03ad3f-T004",
            procurement_method="open",
            tender_period_start=date(2024, 1, 1),
            tender_period_end=date(2024, 1, 31),  # 30 days
        ),
    )


def make_no_dates() -> CompiledRelease:
    """Tender with no submission period dates → SKIPPED."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T005",
        tender=Tender(
            id="T005",
            ocid="ocds-03ad3f-T005",
            procurement_method="open",
            tender_period_start=None,
            tender_period_end=None,
        ),
    )


def make_short_lpi_with_high_threshold() -> CompiledRelease:
    """LPI (international) with 25-day period. Default 15d says OK.
    But Paraguay LPI minimum is 30d → with Paraguay override threshold, FLAGGED."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T006",
        tender=Tender(
            id="T006",
            ocid="ocds-03ad3f-T006",
            procurement_method="open",  # Will be flagged as LPI via Paraguay method_details
            tender_period_start=date(2024, 1, 1),
            tender_period_end=date(2024, 1, 26),  # 25 days
        ),
    )


def make_short_direct_tender() -> CompiledRelease:
    """A direct (non-competitive) tender with a short period → NOT FLAGGED (skipped).
    Direct tenders are exempt from submission period rules."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T007",
        tender=Tender(
            id="T007",
            ocid="ocds-03ad3f-T007",
            procurement_method="direct",
            tender_period_start=date(2024, 1, 1),
            tender_period_end=date(2024, 1, 3),  # 2 days
        ),
    )


def make_short_limited_tender() -> CompiledRelease:
    """A limited (Compras Menores) tender with a short period → FLAGGED
    (limited tenders should still have a minimum period per Paraguay law)."""
    return CompiledRelease(
        ocid="ocds-03ad3f-T008",
        tender=Tender(
            id="T008",
            ocid="ocds-03ad3f-T008",
            procurement_method="limited",
            tender_period_start=date(2024, 1, 1),
            tender_period_end=date(2024, 1, 2),  # 1 day
        ),
    )


# Cardinal reference example (parity test)
def make_cardinal_reference_fixture() -> CompiledRelease:
    """Cardinal R003 reference: National Rail Service publishes 5-day tender."""
    return CompiledRelease(
        ocid="ocds-03ad3f-RAIL-001",
        tender=Tender(
            id="RAIL-001",
            ocid="ocds-03ad3f-RAIL-001",
            title="National Rail Service tender",
            procurement_method="open",
            tender_period_start=date(2024, 3, 15),
            tender_period_end=date(2024, 3, 20),  # 5 days
        ),
    )
