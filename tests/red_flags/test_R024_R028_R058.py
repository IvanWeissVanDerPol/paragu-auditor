"""Tests for R024, R028, R058."""
import pytest
from paragu_auditor.red_flags.R024 import flag_price_close_to_winning
from paragu_auditor.red_flags.R028 import flag_identical_bid_prices
from paragu_auditor.red_flags.R058 import (
    flag_heavily_discounted_bid,
    compute_differences_across_dataset,
    compute_upper_fence,
)
from tests.red_flags.fixtures_R024_R028_R058 import (
    make_close_price_open_tender,
    make_normal_price_open_tender,
    make_identical_price_tender,
    make_different_price_tender,
    make_dataset_for_R058,
)


class TestR024:
    def test_close_price_flagged(self):
        result = flag_price_close_to_winning(make_close_price_open_tender())
        assert result.value == 1.0
        assert result.flag_id == "R024"
        assert result.evidence["difference_pct"] <= 5.0

    def test_normal_price_not_flagged(self):
        result = flag_price_close_to_winning(make_normal_price_open_tender())
        assert result.value == 0.0
        assert not result.skipped

    def test_config_override(self):
        """With 2% threshold, 4% diff is NOT flagged."""
        r = make_close_price_open_tender()
        result = flag_price_close_to_winning(r, threshold=0.02)
        assert result.value == 0.0

    def test_only_one_bid_skipped(self):
        from tests.red_flags.fixtures_R003 import make_short_open_tender
        result = flag_price_close_to_winning(make_short_open_tender())
        assert result.skipped is True


class TestR028:
    def test_identical_prices_flagged(self):
        result = flag_identical_bid_prices(make_identical_price_tender())
        assert result.value == 1.0
        assert "duplicate_amounts" in result.evidence

    def test_different_prices_not_flagged(self):
        result = flag_identical_bid_prices(make_different_price_tender())
        assert result.value == 0.0

    def test_only_one_bid_skipped(self):
        from tests.red_flags.fixtures_R018 import make_open_tender_one_valid_bid
        result = flag_identical_bid_prices(make_open_tender_one_valid_bid())
        assert result.skipped is True


class TestR058:
    def test_outlier_flagged(self):
        dataset = make_dataset_for_R058()
        diffs = compute_differences_across_dataset(dataset)
        assert len(diffs) == 5
        # The last tenders diff should be (300-100)/100 = 2.0 (200%)
        assert diffs[-1] == 2.0

        outlier = dataset[-1]  # The one with 200% diff
        result = flag_heavily_discounted_bid(outlier, dataset_differences=diffs)
        assert result.value >= 1.0  # diff > 0, values is the diff

    def test_normal_not_flagged(self):
        dataset = make_dataset_for_R058()
        diffs = compute_differences_across_dataset(dataset)
        normal = dataset[0]  # One of the 10-25% diff tenders
        result = flag_heavily_discounted_bid(normal, dataset_differences=diffs)
        assert result.value == 0.0

    def test_insufficient_data_skipped(self):
        dataset = make_dataset_for_R058()
        diffs = compute_differences_across_dataset(dataset[:2])  # Only 2
        normal = dataset[0]
        result = flag_heavily_discounted_bid(normal, dataset_differences=diffs)
        assert result.skipped
