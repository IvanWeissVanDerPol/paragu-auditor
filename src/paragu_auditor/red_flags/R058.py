"""Red flag R058 — Heavily discounted bid.

Cardinal reference:
  https://cardinal.readthedocs.io/en/latest/cli/indicators/R/058.html

Methodology:
  For each contracting process, compute:
    difference = (second_lowest_valid_bid - winning_bid) / winning_bid
  Flag if difference >= upper_fence = Q3 + 1.5 * IQR of all differences.

  Unlike R024 (close price), this uses dataset-wide percentiles.
  A heavily discounted bid can mean the winner cut corners on quality.
"""
from __future__ import annotations

from typing import Optional

from .R018 import FlagResult


def compute_differences_across_dataset(releases: list) -> list[float]:
    """Compute the bid difference for each release in a dataset.

    difference = (second_lowest_bid - winning_bid) / winning_bid
    Only includes releases with at least 2 valid bids.
    """
    diffs = []
    for r in releases:
        if not r.tender:
            continue
        valid_bids = sorted(
            [b for b in r.tender.bids if b.status == "valid" and b.amount],
            key=lambda b: b.amount.amount,
        )
        if len(valid_bids) < 2:
            continue
        winning = valid_bids[0].amount.amount
        second = valid_bids[1].amount.amount
        if winning <= 0:
            continue
        diff = (second - winning) / winning
        diffs.append(diff)
    return diffs


def compute_upper_fence(values: list[float], multiplier: float = 1.5) -> Optional[float]:
    """Compute Q3 + multiplier * IQR for a list of values.

    Returns None if not enough values to compute IQR.
    """
    if len(values) < 5:
        return None
    sorted_v = sorted(values)
    n = len(sorted_v)
    q1 = sorted_v[n // 4]
    q3 = sorted_v[3 * n // 4]
    iqr = q3 - q1
    if iqr == 0:
        return None
    return q3 + multiplier * iqr


def flag_heavily_discounted_bid(
    release,
    dataset_differences: Optional[list[float]] = None,
    upper_fence: Optional[float] = None,
    multiplier: float = 1.5,
) -> FlagResult:
    """Flag if the bid difference exceeds the upper fence of the dataset.

    Provide either dataset_differences (pre-computed from the dataset)
    or upper_fence (pre-calculated). At least one required.
    """
    if not release.tender:
        return FlagResult(ocid=release.ocid, flag_id="R058", value=0.0, skipped=True, skip_reason="no_tender")

    valid_bids = sorted(
        [b for b in release.tender.bids if b.status == "valid" and b.amount],
        key=lambda b: b.amount.amount,
    )
    if len(valid_bids) < 2:
        return FlagResult(ocid=release.ocid, flag_id="R058", value=0.0, skipped=True, skip_reason="not_enough_bids")

    # Exclude multiple active awards (per Cardinal)
    if len(release.awards) > 1:
        return FlagResult(ocid=release.ocid, flag_id="R058", value=0.0, skipped=True, skip_reason="multiple_awards")

    winning = valid_bids[0].amount.amount
    second = valid_bids[1].amount.amount
    if winning <= 0:
        return FlagResult(ocid=release.ocid, flag_id="R058", value=0.0, skipped=True, skip_reason="zero_winning_bid")

    diff = (second - winning) / winning

    # Compute fence if not provided
    if upper_fence is None and dataset_differences is not None:
        upper_fence = compute_upper_fence(dataset_differences, multiplier)

    if upper_fence is None:
        return FlagResult(ocid=release.ocid, flag_id="R058", value=0.0, skipped=True, skip_reason="no_reference_baseline")

    if diff >= upper_fence:
        return FlagResult(
            ocid=release.ocid,
            flag_id="R058",
            value=diff,  # Cardinal uses the diff value itself
            evidence={
                "difference_pct": diff * 100,
                "upper_fence_pct": upper_fence * 100,
                "winning_bid": winning,
                "second_lowest_bid": second,
            },
        )

    return FlagResult(
        ocid=release.ocid,
        flag_id="R058",
        value=0.0,
        evidence={"difference_pct": diff * 100, "upper_fence_pct": upper_fence * 100},
    )
