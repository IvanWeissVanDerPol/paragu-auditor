"""Tests for red flag R003 — short submission period.

Cardinal reference:
  https://cardinal.readthedocs.io/en/latest/cli/indicators/R/003.html

Algorithm:
  Flag if (tenderPeriod.endDate - tenderPeriod.startDate) < threshold.
  Default threshold: 15 days.
  Default config: applied to all procurement methods with dates.
"""
import pytest

from paragu_auditor.red_flags.R003 import (
    DEFAULT_THRESHOLD_DAYS,
    calculate_submission_period_days,
    flag_short_submission_period,
)
from paragu_auditor.red_flags.R018 import FlagResult
from tests.red_flags.fixtures_R003 import (
    make_short_open_tender,
    make_just_below_threshold,
    make_exactly_at_threshold,
    make_above_threshold,
    make_no_dates,
    make_short_lpi_with_high_threshold,
    make_short_direct_tender,
    make_short_limited_tender,
    make_cardinal_reference_fixture,
)


class TestFlagShortSubmissionPeriod:
    def test_7_days_flagged(self):
        """7-day period < 15-day threshold → FLAGGED (1.0)."""
        release = make_short_open_tender()
        result = flag_short_submission_period(release)

        assert result.value == 1.0
        assert result.evidence["period_days"] == 7
        assert result.evidence["threshold_days"] == 15

    def test_14_days_flagged(self):
        """14-day period < 15-day threshold → FLAGGED."""
        release = make_just_below_threshold()
        result = flag_short_submission_period(release)

        assert result.value == 1.0
        assert result.evidence["period_days"] == 14

    def test_15_days_not_flagged(self):
        """Exactly 15-day period is NOT below 15-day threshold."""
        release = make_exactly_at_threshold()
        result = flag_short_submission_period(release)

        assert result.value == 0.0
        assert result.evidence["period_days"] == 15

    def test_30_days_not_flagged(self):
        """30-day period > threshold → NOT FLAGGED."""
        release = make_above_threshold()
        result = flag_short_submission_period(release)

        assert result.value == 0.0
        assert result.evidence["period_days"] == 30

    def test_no_dates_skipped(self):
        """Missing dates → SKIPPED (not enough data)."""
        release = make_no_dates()
        result = flag_short_submission_period(release)

        assert result.value == 0.0
        assert result.skipped is True
        assert result.skip_reason == "no_dates"

    def test_threshold_override(self):
        """A 12-day period is below 15d default. With override of 10d → NOT FLAGGED."""
        release = make_just_below_threshold()  # 14 days
        result = flag_short_submission_period(release, threshold_days=10)

        # 14 < 10 is False
        assert result.value == 0.0

    def test_threshold_override_higher(self):
        """A 25-day period is OK by default. With override of 30d → FLAGGED."""
        release = make_short_lpi_with_high_threshold()  # 25 days
        result = flag_short_submission_period(release, threshold_days=30)

        assert result.value == 1.0


class TestProcurementMethodFilter:
    def test_method_filter_excludes_direct(self):
        """With method filter = {open, selective}, direct tenders are skipped."""
        release = make_short_direct_tender()
        result = flag_short_submission_period(
            release,
            competitive_methods={"open", "selective"},
        )

        assert result.value == 0.0
        assert result.skipped is True
        assert "direct" in result.skip_reason

    def test_method_filter_includes_limited(self):
        """Limited tenders are also checked if included in the filter."""
        release = make_short_limited_tender()
        result = flag_short_submission_period(
            release,
            competitive_methods={"open", "selective", "limited"},
        )

        assert result.value == 1.0


class TestSubmissionPeriodCalculation:
    def test_simple_calculation(self):
        from paragu_auditor.data.schemas import CompiledRelease, Tender
        release = CompiledRelease(
            ocid="ocds-03ad3f-X",
            tender=Tender(
                id="X",
                ocid="ocds-03ad3f-X",
                procurement_method="open",
                tender_period_start=__import__("datetime").date(2024, 1, 1),
                tender_period_end=__import__("datetime").date(2024, 1, 11),  # 10 days
            ),
        )
        assert calculate_submission_period_days(release) == 10

    def test_returns_none_for_missing_start(self):
        from paragu_auditor.data.schemas import CompiledRelease, Tender
        release = CompiledRelease(
            ocid="ocds-03ad3f-X",
            tender=Tender(
                id="X",
                ocid="ocds-03ad3f-X",
                procurement_method="open",
                tender_period_start=None,
                tender_period_end=__import__("datetime").date(2024, 1, 11),
            ),
        )
        assert calculate_submission_period_days(release) is None


class TestDefaults:
    def test_default_threshold(self):
        assert DEFAULT_THRESHOLD_DAYS == 15


class TestCardinalParity:
    def test_cardinal_reference_example_flagged(self):
        """The Cardinal R003 reference example (5-day National Rail tender)
        must produce value=1.0.
        """
        release = make_cardinal_reference_fixture()
        result = flag_short_submission_period(release)

        assert result.value == 1.0
        assert result.evidence["period_days"] == 5
