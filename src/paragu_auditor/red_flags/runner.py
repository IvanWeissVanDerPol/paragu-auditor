"""FlagRunner — runs all red flags on a list of CompiledReleases.

Aggregates results into a single list of FlagResult objects.
Useful for batch processing and dashboard display.
"""
from __future__ import annotations

from typing import Optional

from .R003 import flag_short_submission_period
from .R018 import flag_single_bid
from .R018 import FlagResult


from .R024 import flag_price_close_to_winning
from .R028 import flag_identical_bid_prices
from .R058 import flag_heavily_discounted_bid, compute_differences_across_dataset, compute_upper_fence

# Registry of available red flags
RED_FLAG_REGISTRY = {
    "R003": {
        "name": "Short submission period",
        "function": flag_short_submission_period,
        "description": "Tender submission period is shorter than threshold (default 15 days).",
    },
    "R018": {
        "name": "Single bid received",
        "function": flag_single_bid,
        "description": "Competitive tender with only 1 valid bid.",
    },
    "R024": {
        "name": "Price close to winning bid",
        "function": flag_price_close_to_winning,
        "description": "Winning bid is within 5% of the second-lowest bid.",
    },
    "R028": {
        "name": "Identical bid prices",
        "function": flag_identical_bid_prices,
        "description": "Different tenderers submitted bids with the same price.",
    },
    "R058": {
        "name": "Heavily discounted bid",
        "function": flag_heavily_discounted_bid,
        "description": "Winning bid is far below the second-lowest bid (dataset outlier).",
    },
}


def run_all_flags(
    release,
    flag_ids: Optional[list[str]] = None,
) -> list[FlagResult]:
    """Run all (or specified) red flags on a single release.

    Args:
        release: A CompiledRelease.
        flag_ids: List of flag IDs to run. If None, runs all.

    Returns:
        List of FlagResult objects (one per flag run).
    """
    if flag_ids is None:
        flag_ids = list(RED_FLAG_REGISTRY.keys())

    results = []
    for flag_id in flag_ids:
        if flag_id not in RED_FLAG_REGISTRY:
            continue
        flag_fn = RED_FLAG_REGISTRY[flag_id]["function"]
        try:
            result = flag_fn(release)
            results.append(result)
        except Exception as e:
            # Don't let one bad flag kill the whole run
            results.append(
                FlagResult(
                    ocid=release.ocid,
                    flag_id=flag_id,
                    value=0.0,
                    skipped=True,
                    skip_reason=f"error:{type(e).__name__}",
                )
            )
    return results


def run_all_flags_on_dataset(
    releases: list,
    flag_ids: Optional[list[str]] = None,
) -> list[FlagResult]:
    """Run all (or specified) red flags on a list of releases.

    For R058, pre-computes dataset-level differences for IQR-based outlier detection.

    Args:
        releases: List of CompiledRelease.
        flag_ids: List of flag IDs to run. If None, runs all.

    Returns:
        List of FlagResult objects (one per release per flag).
    """
    if flag_ids is None:
        flag_ids = list(RED_FLAG_REGISTRY.keys())

    # Pre-compute dataset differences for R058
    dataset_differences = None
    if "R058" in flag_ids:
        from .R058 import compute_differences_across_dataset
        dataset_differences = compute_differences_across_dataset(releases)

    all_results = []
    for release in releases:
        for flag_id in flag_ids:
            if flag_id not in RED_FLAG_REGISTRY:
                continue
            flag_fn = RED_FLAG_REGISTRY[flag_id]["function"]
            try:
                if flag_id == "R058":
                    result = flag_fn(release, dataset_differences=dataset_differences)
                else:
                    result = flag_fn(release)
                all_results.append(result)
            except Exception as e:
                all_results.append(
                    FlagResult(
                        ocid=release.ocid,
                        flag_id=flag_id,
                        value=0.0,
                        skipped=True,
                        skip_reason=f"error:{type(e).__name__}",
                    )
                )
    return all_results


def summarize_flag_results(results: list[FlagResult]) -> dict:
    """Summarize a list of FlagResults into counts per flag.

    Returns:
        {
            "R003": {"flagged": 12, "not_flagged": 100, "skipped": 5, "total": 117},
            ...
            "total_flagged": 23,
            "total": 350,
        }
    """
    summary: dict = {"total_flagged": 0, "total": 0}
    for r in results:
        fid = r.flag_id
        if fid not in summary:
            summary[fid] = {"flagged": 0, "not_flagged": 0, "skipped": 0, "total": 0}
        summary[fid]["total"] += 1
        summary["total"] += 1
        if r.skipped:
            summary[fid]["skipped"] += 1
        elif r.value >= 1.0:
            summary[fid]["flagged"] += 1
            summary["total_flagged"] += 1
        else:
            summary[fid]["not_flagged"] += 1
    return summary
