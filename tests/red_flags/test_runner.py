"""Tests for the FlagRunner orchestrator."""
import pytest

from paragu_auditor.red_flags.runner import (
    RED_FLAG_REGISTRY,
    run_all_flags,
    run_all_flags_on_dataset,
    summarize_flag_results,
)
from paragu_auditor.red_flags.R018 import FlagResult
from tests.data.fixtures.synthetic import make_basic_record
from paragu_auditor.data.jsonld_mapper import jsonld_to_ocds
from tests.red_flags.fixtures_R003 import make_short_open_tender, make_above_threshold
from tests.red_flags.fixtures_R018 import make_open_tender_one_valid_bid


class TestRedFlagRegistry:
    def test_r003_registered(self):
        assert "R003" in RED_FLAG_REGISTRY
        assert RED_FLAG_REGISTRY["R003"]["name"] == "Short submission period"

    def test_r018_registered(self):
        assert "R018" in RED_FLAG_REGISTRY
        assert RED_FLAG_REGISTRY["R018"]["name"] == "Single bid received"

    def test_all_five_flags_registered(self):
        """All 5 flags are registered."""
        for fid in ["R003", "R018", "R024", "R028", "R058"]:
            assert fid in RED_FLAG_REGISTRY, f"{fid} should be registered in MVP"
        assert len(RED_FLAG_REGISTRY) == 5


class TestRunAllFlags:
    def test_runs_all_default_flags(self):
        release = make_open_tender_one_valid_bid()
        results = run_all_flags(release)

        # Should have one result per registered flag
        assert len(results) == len(RED_FLAG_REGISTRY)
        # Both R003 and R018 should be there
        flag_ids = {r.flag_id for r in results}
        assert "R003" in flag_ids
        assert "R018" in flag_ids

    def test_runs_specific_flags(self):
        release = make_open_tender_one_valid_bid()
        results = run_all_flags(release, flag_ids=["R018"])

        assert len(results) == 1
        assert results[0].flag_id == "R018"

    def test_handles_error_gracefully(self):
        """If a flag function raises, the runner should not crash."""
        from paragu_auditor.red_flags import runner

        # Monkey-patch R018 to raise
        original_r018 = runner.RED_FLAG_REGISTRY["R018"]["function"]
        def broken_fn(release):
            raise ValueError("test error")
        runner.RED_FLAG_REGISTRY["R018"]["function"] = broken_fn

        try:
            release = make_open_tender_one_valid_bid()
            results = run_all_flags(release)
            # R003 should still work, R018 should be skipped with error reason
            r018_result = next(r for r in results if r.flag_id == "R018")
            assert r018_result.skipped is True
            assert "error" in r018_result.skip_reason
        finally:
            runner.RED_FLAG_REGISTRY["R018"]["function"] = original_r018


class TestRunAllFlagsOnDataset:
    def test_runs_on_multiple_releases(self):
        releases = [
            make_open_tender_one_valid_bid(),  # R018 flagged
            make_short_open_tender(),          # R003 flagged
            make_above_threshold(),             # R003 not flagged
        ]
        results = run_all_flags_on_dataset(releases)

        # 3 releases × 5 flags = 15 results
        assert len(results) == 15

    def test_on_real_paraguay_synthetic(self):
        """End-to-end: take synthetic DNCP records, map, flag."""
        record = make_basic_record()
        release = jsonld_to_ocds(record)
        results = run_all_flags_on_dataset([release])

        assert len(results) == 5  # 5 flags, 1 release
        # This record has 2 valid bids → R018 NOT flagged
        r018 = next(r for r in results if r.flag_id == "R018")
        assert r018.value == 0.0


class TestSummarizeFlagResults:
    def test_summary_counts(self):
        results = [
            FlagResult(ocid="t1", flag_id="R003", value=1.0),
            FlagResult(ocid="t2", flag_id="R003", value=0.0),
            FlagResult(ocid="t3", flag_id="R003", value=1.0, skipped=True),
            FlagResult(ocid="t1", flag_id="R018", value=0.0),
            FlagResult(ocid="t2", flag_id="R018", value=1.0),
        ]
        summary = summarize_flag_results(results)

        assert summary["R003"]["flagged"] == 1
        assert summary["R003"]["not_flagged"] == 1
        assert summary["R003"]["skipped"] == 1
        assert summary["R003"]["total"] == 3

        assert summary["R018"]["flagged"] == 1
        assert summary["R018"]["not_flagged"] == 1
        assert summary["R018"]["total"] == 2

        assert summary["total_flagged"] == 2
        assert summary["total"] == 5
