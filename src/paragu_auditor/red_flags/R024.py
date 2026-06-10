"""Red flag R024 — Price close to winning bid.

Cardinal reference:
  https://cardinal.readthedocs.io/en/latest/cli/indicators/R/024.html

Methodology:
  For each contracting process, compute:
    difference = (second_lowest_valid_bid - winning_bid) / winning_bid
  Flag if difference <= threshold (default 0.05, i.e., 5%).

  Very close bid prices can indicate bid rigging (the losing bidder
  intentionally priced just above the winner).
"""
from __future__ import annotations

from typing import Optional

from .R018 import FlagResult


DEFAULT_THRESHOLD = 0.05


def flag_price_close_to_winning(
    release,
    threshold: float = DEFAULT_THRESHOLD,
) -> FlagResult:
    """Flag if winning bid is too close to second-lowest bid."""
    if not release.tender:
        return FlagResult(ocid=release.ocid, flag_id="R024", value=0.0, skipped=True, skip_reason="no_tender")

    valid_bids = sorted(
        [b for b in release.tender.bids if b.status == "valid" and b.amount],
        key=lambda b: b.amount.amount,
    )
    if len(valid_bids) < 2:
        return FlagResult(ocid=release.ocid, flag_id="R024", value=0.0, skipped=True, skip_reason="not_enough_bids")

    winning = valid_bids[0].amount.amount
    second = valid_bids[1].amount.amount
    if winning <= 0:
        return FlagResult(ocid=release.ocid, flag_id="R024", value=0.0, skipped=True, skip_reason="zero_winning_bid")

    difference = (second - winning) / winning
    if difference <= threshold:
        return FlagResult(
            ocid=release.ocid,
            flag_id="R024",
            value=1.0,
            evidence={
                "winning_bid": winning,
                "second_lowest_bid": second,
                "difference_pct": difference * 100,
                "threshold_pct": threshold * 100,
            },
        )

    return FlagResult(
        ocid=release.ocid,
        flag_id="R024",
        value=0.0,
        evidence={
            "winning_bid": winning,
            "second_lowest_bid": second,
            "difference_pct": difference * 100,
        },
    )
