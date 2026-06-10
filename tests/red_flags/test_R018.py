"""Tests for red flag R018 — single bid received.

These tests are written first (TDD), then the implementation in
src/paragu_auditor/red_flags/R018.py satisfies them.

The algorithm:
  Flag if the number of valid bids is exactly 1 AND the procurement method
  is in {"open", "selective"} (the competitive methods).
"""
import pytest

from paragu_auditor.red_flags.R018 import (
    DEFAULT_COMPETITIVE_METHODS,
    FlagResult,
    flag_single_bid,
)
from tests.red_flags.fixtures_R018 import (
    make_open_tender_one_valid_bid,
    make_open_tender_two_valid_bids,
    make_open_tender_one_valid_one_disqualified,
    make_open_tender_zero_bids,
    make_selective_tender_one_bid,
    make_direct_tender_one_bid,
    make_limited_tender_one_bid,
    make_limited_tender_excluded,
    make_open_tender_one_bid_null_amount,
    make_cardinal_reference_fixture,
)


class TestFlagSingleBid:
    def test_open_tender_with_one_valid_bid_flagged(self):
        """Open tender, 1 valid bid → FLAGGED (1.0)."""
        release = make_open_tender_one_valid_bid()
        result = flag_single_bid(release)

        assert isinstance(result, FlagResult)
        assert result.ocid == "ocds-03ad3f-T001"
        assert result.flag_id == "R018"
        assert result.value == 1.0
        assert not result.skipped
        assert result.evidence["n_valid_bids"] == 1
        assert result.evidence["n_total_bids"] == 1
        assert result.evidence["procurement_method"] == "open"
        assert result.evidence["winner_id"] == "v1"

    def test_open_tender_with_two_valid_bids_not_flagged(self):
        """Open tender, 2+ valid bids → NOT FLAGGED (0.0)."""
        release = make_open_tender_two_valid_bids()
        result = flag_single_bid(release)

        assert result.value == 0.0
        assert not result.skipped
        assert result.evidence["n_valid_bids"] == 2

    def test_one_valid_one_disqualified_flagged(self):
        """Open tender, 1 valid + 1 disqualified → FLAGGED (count only valid)."""
        release = make_open_tender_one_valid_one_disqualified()
        result = flag_single_bid(release)

        assert result.value == 1.0
        assert result.evidence["n_valid_bids"] == 1
        assert result.evidence["n_total_bids"] == 2  # Raw total also recorded

    def test_zero_bids_skipped(self):
        """Open tender, 0 bids → SKIPPED (different anomaly, not single-bidder)."""
        release = make_open_tender_zero_bids()
        result = flag_single_bid(release)

        assert result.value == 0.0
        assert result.skipped is True
        assert result.skip_reason == "no_bids"

    def test_selective_tender_with_one_bid_flagged(self):
        """Selective tender, 1 valid bid → FLAGGED."""
        release = make_selective_tender_one_bid()
        result = flag_single_bid(release)

        assert result.value == 1.0
        assert result.evidence["procurement_method"] == "selective"

    def test_direct_tender_with_one_bid_skipped(self):
        """Direct (non-competitive) tender, 1 bid → SKIPPED (not a red flag)."""
        release = make_direct_tender_one_bid()
        result = flag_single_bid(release)

        assert result.value == 0.0
        assert result.skipped is True
        assert "non_competitive" in result.skip_reason
        assert "direct" in result.skip_reason

    def test_limited_tender_with_one_bid_skipped(self):
        """Limited (Compras Menores) tender, 1 bid → SKIPPED (already limited)."""
        release = make_limited_tender_one_bid()
        result = flag_single_bid(release)

        assert result.value == 0.0
        assert result.skipped is True
        assert "non_competitive" in result.skip_reason
        assert "limited" in result.skip_reason

    def test_null_amount_bid_still_flagged(self):
        """Bid with null amount shouldn't prevent flagging (count is what matters)."""
        release = make_open_tender_one_bid_null_amount()
        result = flag_single_bid(release)

        assert result.value == 1.0
        assert result.evidence["n_valid_bids"] == 1


class TestConfigOverride:
    def test_config_competitive_methods_override(self):
        """We can configure which methods count as 'competitive'."""
        release = make_limited_tender_excluded()
        result = flag_single_bid(release, competitive_methods={"limited", "open"})

        # Now "limited" IS competitive, so 1 bid → flagged
        assert result.value == 1.0

    def test_default_competitive_methods(self):
        """Default methods are open + selective (per Cardinal)."""
        assert "open" in DEFAULT_COMPETITIVE_METHODS
        assert "selective" in DEFAULT_COMPETITIVE_METHODS
        assert "limited" not in DEFAULT_COMPETITIVE_METHODS
        assert "direct" not in DEFAULT_COMPETITIVE_METHODS


class TestCardinalParity:
    def test_cardinal_reference_example_produces_1_0(self):
        """The Cardinal R018 reference example must produce value=1.0.

        This is the parity test: our Python implementation matches Cardinal's
        reference output for the documented example.
        """
        release = make_cardinal_reference_fixture()
        result = flag_single_bid(release)

        # Cardinal's expected output: {"OCID":{"F":{"R018":1.0}}}
        assert result.value == 1.0
        assert result.ocid == "ocds-03ad3f-EDU-001"
        assert result.flag_id == "R018"


class TestFlagResultSerialization:
    def test_to_dict(self):
        release = make_open_tender_one_valid_bid()
        result = flag_single_bid(release)
        d = result.to_dict()

        assert d["ocid"] == "ocds-03ad3f-T001"
        assert d["flag_id"] == "R018"
        assert d["value"] == 1.0
        assert "evidence" in d
        assert d["evidence"]["n_valid_bids"] == 1
        assert d["skipped"] is False
