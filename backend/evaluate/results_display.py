"""ASCII consistency display for evaluation results.

Shared by run_langsmith_evaluation (post-run) and langsmith_dataset
experiment stats (post-hoc, from stored experiment data).
"""

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Rubric scores are expected to be one of these three values.
_STANDARD_LEVELS = (0.0, 0.5, 1.0)
_LEVEL_TOL = 0.01  # tolerance for floating-point comparison
_COL_W = 5  # column width for each count cell


@dataclass
class ScenarioResult:
    """Scores for one example across all repetitions."""

    label: str
    scenario_id: int = 0
    scores: Dict[str, List[float]] = field(default_factory=dict)


def _to_bucket(score: float) -> Optional[float]:
    """Return the matching standard level if close enough, else None."""
    for level in _STANDARD_LEVELS:
        if abs(score - level) <= _LEVEL_TOL:
            return level
    return None


def _keep(key: str, filter_set: Optional[set]) -> bool:
    """Return True if key passes the evaluator filter."""
    return filter_set is None or key.lower() in filter_set


def print_consistency_stats(
    scenarios: List[ScenarioResult],
    evaluators: Optional[List[str]] = None,
    baseline: Optional[Dict[Tuple[int, str], Tuple[float, float]]] = None,
) -> None:
    """Print per-evaluator tables with one row per scenario, then a scenario key.

    Outer loop is evaluators (fewer), inner loop is scenarios (more). Each row
    shows mean, stdev, and how many runs landed at each standard score level
    (0.0, 0.5, 1.0). Non-standard score columns appears only when present in the
    data, and they are visually separated from the standard levels with a vertical
    bar.

    Args:
        scenarios: Per-example results to display.
        evaluators: If given, only show tables whose name is in this list.
            Names are matched case-insensitively against the feedback key.
        baseline: If given, maps (scenario_id, eval_name) -> (old_mean, old_sigma).
            When present, mean and σ columns show "old→new" to surface how an
            updated evaluator rubric shifted scores.
    """
    if not scenarios:
        return

    filter_set = {e.lower() for e in evaluators} if evaluators else None

    all_keys = sorted({k for s in scenarios for k in s.scores if _keep(k, filter_set)})
    if not all_keys:
        print("No matching evaluators found.")
        return

    # Collect any non-standard score values present in the data, sorted.
    nonstandard_levels = sorted(
        {
            s
            for sc in scenarios
            for k, score_list in sc.scores.items()
            if _keep(k, filter_set)
            for s in score_list
            if _to_bucket(s) is None
        }
    )

    std_labels = [f"{lv:.1f}" for lv in _STANDARD_LEVELS]
    ns_labels = [f"{lv:.2f}" for lv in nonstandard_levels]

    # Scenario IDs: S0, S1, ... using the actual scenario_id from metadata.
    sid_w = max((len(f"S{s.scenario_id}") for s in scenarios), default=len("Scenario"))
    sid_w = max(sid_w, len("Scenario"))

    # Build header and separator for count columns, with a visual break before
    # any non-standard columns.
    std_hdr = "  ".join(f"{h:>{_COL_W}}" for h in std_labels)
    ns_hdr = (
        ("  |  " + "  ".join(f"{h:>{_COL_W}}" for h in ns_labels)) if ns_labels else ""
    )
    std_sep = "-" * (len(_STANDARD_LEVELS) * (_COL_W + 2) - 2)
    ns_sep = ("  |  " + "-" * (len(ns_labels) * (_COL_W + 2) - 2)) if ns_labels else ""

    # When baseline is provided, mean/σ columns show "X.XX(±X.XX)" (11 chars each).
    stat_w = 11 if baseline is not None else 6

    print("\n=== Per-Scenario Consistency ===")

    for key in all_keys:
        print(f"\nEvaluator: {key}")
        print(
            f"  {'Scenario':<{sid_w}}  {'mean':>{stat_w}}  {'σ':>{stat_w}}  {std_hdr}{ns_hdr}"
        )
        print(f"  {'-' * sid_w}  {'-' * stat_w}  {'-' * stat_w}  {std_sep}{ns_sep}")

        for scenario in scenarios:
            score_list = scenario.scores.get(key, [])
            if not score_list:
                continue

            sid = f"S{scenario.scenario_id}"
            new_mean = statistics.mean(score_list)
            new_std = statistics.pstdev(score_list)

            if baseline is not None:
                old = baseline.get((scenario.scenario_id, key))
                if old is not None:
                    old_mean, old_std = old
                    mean_str = f"{new_mean:.2f}({new_mean - old_mean:+.2f})"
                    std_str = f"{new_std:.2f}({new_std - old_std:+.2f})"
                else:
                    mean_str = f"{new_mean:.2f}(?)"
                    std_str = f"{new_std:.2f}(?)"
            else:
                mean_str = f"{new_mean:.2f}"
                std_str = f"{new_std:.2f}"

            counts: Dict[float, int] = {lv: 0 for lv in _STANDARD_LEVELS}
            ns_counts: Dict[float, int] = {lv: 0 for lv in nonstandard_levels}
            for s in score_list:
                bucket = _to_bucket(s)
                if bucket is not None:
                    counts[bucket] += 1
                elif s in ns_counts:
                    ns_counts[s] += 1

            std_cells = "  ".join(f"{counts[lv]:>{_COL_W}}" for lv in _STANDARD_LEVELS)
            ns_cells = (
                (
                    "  |  "
                    + "  ".join(
                        f"{ns_counts[lv]:>{_COL_W}}" for lv in nonstandard_levels
                    )
                )
                if nonstandard_levels
                else ""
            )

            print(
                f"  {sid:<{sid_w}}  {mean_str:>{stat_w}}  {std_str:>{stat_w}}  {std_cells}{ns_cells}"
            )

    # Scenario key: map S<scenario_id> to full query text and repetition count.
    print("\nScenario Key:")
    for scenario in scenarios:
        sid = f"S{scenario.scenario_id}"
        n = max((len(v) for v in scenario.scores.values()), default=0)
        print(f"  {sid}  (n={n})  {scenario.label}")
