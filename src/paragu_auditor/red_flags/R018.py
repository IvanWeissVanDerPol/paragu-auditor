"""Red flag R018 — Single bid received.

Cardinal reference:
  https://cardinal.readthedocs.io/en/latest/cli/indicators/R/018.html

Methodology:
  A contracting process is flagged if the number of tenderers is 1 and the
  procurement method is competitive (open or selective).

  In a competitive procedure, a lack of competition might correspond to a
  suppression of competition and can represent the ideal outcome for a
  corrupt buyer and pre-determined bidder.

Paraguay-specific:
  Paraguay DNCP uses "CO" / "LPN" / "LPI" / "CD" → maps to "open"
  and "LR" / "SO" → maps to "selective"
  These are the only methods that get flagged.
  "AD" (Adjudicación Directa) and "EX" (Excepción) → maps to "direct", NOT flagged.
  "CM" / "CDU" → maps to "limited", NOT flagged (already limited competition).

Output:
  Returns FlagResult with value 1.0 if flagged, 0.0 otherwise.
  Skipped (returns None) if not enough data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class FlagResult:
    """The result of a red flag evaluation."""
    ocid: str
    flag_id: str
    value: float
    evidence: dict = None
    skipped: bool = False
    skip_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "ocid": self.ocid,
            "flag_id": self.flag_id,
            "value": self.value,
            "evidence": self.evidence or {},
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
        }


# Default configuration per Cardinal reference
DEFAULT_COMPETITIVE_METHODS: set[str] = {"open", "selective"}


def flag_single_bid(
    release,
    competitive_methods: set[str] | None = None,
) -> FlagResult:
    """Flag a contracting process if it has only 1 valid bid AND a competitive method.

    Args:
        release: A CompiledRelease (OCDS) object.
        competitive_methods: Set of OCDS procurement methods considered competitive.
                            Defaults to {"open", "selective"}.

    Returns:
        FlagResult with value=1.0 if flagged, value=0.0 if not flagged.
        FlagResult with skipped=True if data is insufficient.
    """
    if competitive_methods is None:
        competitive_methods = DEFAULT_COMPETITIVE_METHODS

    # Skip if no tender (shouldn't happen but defensive)
    if not release.tender:
        return FlagResult(
            ocid=release.ocid,
            flag_id="R018",
            value=0.0,
            skipped=True,
            skip_reason="no_tender_data",
        )

    # Skip if procurement method is unknown or non-competitive
    method = release.tender.procurement_method
    if method not in competitive_methods:
        return FlagResult(
            ocid=release.ocid,
            flag_id="R018",
            value=0.0,
            skipped=True,
            skip_reason=f"non_competitive_method:{method}",
        )

    # Count valid bids
    valid_bids = [b for b in release.tender.bids if b.status == "valid"]

    n_valid = len(valid_bids)
    n_total = len(release.tender.bids)

    # Skip if no bids at all (different anomaly)
    if n_valid == 0:
        return FlagResult(
            ocid=release.ocid,
            flag_id="R018",
            value=0.0,
            skipped=True,
            skip_reason="no_bids",
        )

    # The actual flag
    if n_valid == 1:
        return FlagResult(
            ocid=release.ocid,
            flag_id="R018",
            value=1.0,
            evidence={
                "n_valid_bids": n_valid,
                "n_total_bids": n_total,
                "procurement_method": method,
                "winner_name": release.tender.bids[0].bidder_name,
                "winner_id": release.tender.bids[0].bidder_id,
            },
        )

    return FlagResult(
        ocid=release.ocid,
        flag_id="R018",
        value=0.0,
        evidence={
            "n_valid_bids": n_valid,
            "n_total_bids": n_total,
            "procurement_method": method,
        },
    )
