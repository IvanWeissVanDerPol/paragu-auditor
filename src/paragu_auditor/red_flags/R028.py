"""Red flag R028 — Identical bid prices.

Cardinal reference:
  https://cardinal.readthedocs.io/en/latest/cli/indicators/R/028.html

Methodology:
  Flag if different tenderers submitted bids with the same price.
  Also flag the tenderers who submitted duplicate prices.

  Identical bids from different companies can indicate collusion.
"""
from __future__ import annotations

from collections import Counter

from .R018 import FlagResult


def flag_identical_bid_prices(release) -> FlagResult:
    """Flag if two or more valid bids have the same amount."""
    if not release.tender:
        return FlagResult(ocid=release.ocid, flag_id="R028", value=0.0, skipped=True, skip_reason="no_tender")

    valid_bids = [b for b in release.tender.bids if b.status == "valid" and b.amount]
    if len(valid_bids) < 2:
        return FlagResult(ocid=release.ocid, flag_id="R028", value=0.0, skipped=True, skip_reason="not_enough_bids")

    amounts = [b.amount.amount for b in valid_bids]
    duplicates = {amt for amt, count in Counter(amounts).items() if count > 1}

    if not duplicates:
        return FlagResult(ocid=release.ocid, flag_id="R028", value=0.0, skipped=False)

    flagged_tenderers = []
    for b in valid_bids:
        if b.amount.amount in duplicates:
            flagged_tenderers.append({"bidder_id": b.bidder_id, "bidder_name": b.bidder_name, "amount": b.amount.amount})

    return FlagResult(
        ocid=release.ocid,
        flag_id="R028",
        value=1.0,
        evidence={
            "duplicate_amounts": list(duplicates),
            "flagged_tenderers": flagged_tenderers,
            "n_bids": len(valid_bids),
        },
    )
