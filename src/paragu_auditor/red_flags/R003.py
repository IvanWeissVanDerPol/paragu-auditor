"""Red flag R003 — Short submission period.

Cardinal reference:
  https://cardinal.readthedocs.io/en/latest/cli/indicators/R/003.html

Methodology:
  For each contracting process, the submission period is calculated as:
    tenderPeriod.endDate - tenderPeriod.startDate (in whole days)
  A process is flagged if the period is shorter than the threshold (default 15 days).

  A corrupt buyer can give the pre-determined bidder an unfair advantage by
  privately informing the pre-determined bidder of the opportunity in advance,
  and by giving other bidders less time to prepare competitive bids.

Paraguay-specific:
  Paraguay's Ley 2051/2003 (De Contrataciones Públicas) sets minimum
  publication periods:
  - LPN: 20 days
  - LPI: 30 days
  - LR: 10 days
  - CM: 3 days
  - AM/AD: N/A (direct)

  We use Cardinal's default of 15 days but allow override.
"""
from __future__ import annotations

from typing import Optional

from .R018 import FlagResult


DEFAULT_THRESHOLD_DAYS = 15


def calculate_submission_period_days(release) -> Optional[int]:
    """Calculate the submission period in whole days.

    Returns None if dates are missing or invalid.
    """
    if not release.tender:
        return None
    start = release.tender.tender_period_start
    end = release.tender.tender_period_end

    if not start or not end:
        return None
    try:
        delta = end - start
        return delta.days
    except (TypeError, ValueError):
        return None


def flag_short_submission_period(
    release,
    threshold_days: int = DEFAULT_THRESHOLD_DAYS,
    competitive_methods: set[str] | None = None,
) -> FlagResult:
    """Flag a contracting process if its submission period is shorter than threshold.

    Args:
        release: A CompiledRelease.
        threshold_days: Minimum allowed days. Default 15 (Cardinal default).
                        Paraguay-specific values: LPN=20, LPI=30, LR=10, CM=3.
        competitive_methods: Set of OCDS methods to consider. If None, all methods
                             that have dates are checked (Cardinal default).

    Returns:
        FlagResult with value=1.0 if period < threshold, value=0.0 otherwise.
        FlagResult with skipped=True if data is insufficient.
    """
    if competitive_methods is None:
        competitive_methods = None  # All methods with data

    # Skip if no tender
    if not release.tender:
        return FlagResult(
            ocid=release.ocid,
            flag_id="R003",
            value=0.0,
            skipped=True,
            skip_reason="no_tender_data",
        )

    # Skip if method filter excludes this one
    method = release.tender.procurement_method
    if competitive_methods is not None and method not in competitive_methods:
        return FlagResult(
            ocid=release.ocid,
            flag_id="R003",
            value=0.0,
            skipped=True,
            skip_reason=f"method_excluded:{method}",
        )

    # Calculate the period
    period_days = calculate_submission_period_days(release)

    # Skip if no dates
    if period_days is None:
        return FlagResult(
            ocid=release.ocid,
            flag_id="R003",
            value=0.0,
            skipped=True,
            skip_reason="no_dates",
        )

    # The actual flag
    if period_days < threshold_days:
        return FlagResult(
            ocid=release.ocid,
            flag_id="R003",
            value=1.0,
            evidence={
                "period_days": period_days,
                "threshold_days": threshold_days,
                "period_start": release.tender.tender_period_start.isoformat(),
                "period_end": release.tender.tender_period_end.isoformat(),
                "procurement_method": method,
            },
        )

    return FlagResult(
        ocid=release.ocid,
        flag_id="R003",
        value=0.0,
        evidence={
            "period_days": period_days,
            "threshold_days": threshold_days,
        },
    )
