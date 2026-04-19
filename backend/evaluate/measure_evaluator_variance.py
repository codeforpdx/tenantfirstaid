"""Measure LLM judge variance on fixed agent outputs.

Re-runs evaluators k times on the same fixed inputs/outputs from an existing
LangSmith experiment to isolate evaluator stochasticity from agent stochasticity.

Total observed variance decomposes as:
    σ²_total = σ²_agent + σ²_evaluator

Run this script against an existing experiment to measure σ_evaluator directly.
If σ_evaluator << σ_total, the noise is agent-side and more agent samples are
the right fix. If σ_evaluator is comparable to σ_total, fix the judge first.

Pass --show-delta to compare re-evaluated scores against the scores already stored
in the experiment. This is useful when you have updated an evaluator rubric and
want to see which scenarios moved up or down without running a full new experiment.

Usage:
    uv run python -m evaluate.measure_evaluator_variance --experiment <name>
    uv run python -m evaluate.measure_evaluator_variance --experiment <name> -k 10
    uv run python -m evaluate.measure_evaluator_variance --experiment <name> --show-delta
    uv run python -m evaluate.measure_evaluator_variance --experiment <name> --runs-per-scenario 3
"""

import argparse
import statistics
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from langsmith import Client

from evaluate.eval_history import write_variance_entry
from evaluate.langsmith_evaluators import (
    legal_correctness_evaluator,
    tone_evaluator,
)
from evaluate.results_display import ScenarioResult, print_consistency_stats
from tenantfirstaid.constants import LANGSMITH_API_KEY

# All available evaluators, keyed by their feedback_key.
_ALL_EVALUATORS = {
    "legal correctness": legal_correctness_evaluator,
    "appropriate tone": tone_evaluator,
}


def _fetch_runs_and_examples(
    client: Client,
    experiment_name: str,
) -> List[Tuple[Any, Any]]:
    """Return (run, example) pairs for all root runs in an experiment."""
    runs = list(
        client.list_runs(
            project_name=experiment_name,
            is_root=True,
        )
    )

    pairs = []
    for run in runs:
        if run.reference_example_id is None:
            continue
        example = client.read_example(run.reference_example_id)
        pairs.append((run, example))

    return pairs


def _fetch_stored_scores(
    client: Client,
    runs: List[Any],
    evaluator_keys: List[str],
) -> Dict[str, List[float]]:
    """Return stored feedback scores keyed by evaluator name.

    Fetches feedback for all runs in a single batch and filters to the
    requested evaluator feedback keys. Only scores (not comments) are included.
    """
    run_ids = [str(r.id) for r in runs]
    scores: Dict[str, List[float]] = defaultdict(list)
    for feedback in client.list_feedback(run_ids=run_ids):
        if feedback.key in evaluator_keys and feedback.score is not None:
            scores[feedback.key].append(float(feedback.score))
    return dict(scores)


def _evaluate_once(
    evaluator: Any,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    reference_outputs: Dict[str, Any],
) -> Optional[float]:
    """Call an evaluator once and return the float score, or None on failure."""
    try:
        result = evaluator(
            inputs=inputs,
            outputs=outputs,
            reference_outputs=reference_outputs,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"    [evaluator error: {exc}]")
        return None

    if isinstance(result, dict):
        score = result.get("score")
    else:
        score = getattr(result, "score", None)

    return float(score) if score is not None else None


def measure_evaluator_variance(
    experiment_name: str,
    k: int = 5,
    runs_per_scenario: Optional[int] = None,
    evaluator_names: Optional[List[str]] = None,
    scenario_ids_filter: Optional[List[int]] = None,
    show_delta: bool = False,
    max_workers: int = 10,
) -> None:
    """Fetch runs from an experiment, re-evaluate each k times, and report σ.

    Args:
        experiment_name: LangSmith project/experiment name to pull runs from.
        k: Number of times to re-run each evaluator on each fixed output.
        runs_per_scenario: If set, limit how many runs per scenario are probed.
            Useful when an experiment has many repetitions and you only need a
            representative sample.
        evaluator_names: Names of evaluators to run (keys from _ALL_EVALUATORS).
            Defaults to all evaluators when None.
        scenario_ids_filter: If set, only probe scenarios whose scenario_id is
            in this list. Useful for drilling into a single noisy scenario.
        show_delta: If True, fetch stored feedback from the experiment and show
            how the re-evaluated scores compare to the originally recorded scores.
            Useful for testing whether an updated evaluator rubric changes scores.
        max_workers: Thread pool size for concurrent evaluator calls.
    """
    if evaluator_names is not None:
        unknown = set(evaluator_names) - set(_ALL_EVALUATORS)
        if unknown:
            raise ValueError(
                f"Unknown evaluator(s): {unknown}. Available: {list(_ALL_EVALUATORS)}"
            )
        evaluators = {name: _ALL_EVALUATORS[name] for name in evaluator_names}
    else:
        evaluators = _ALL_EVALUATORS

    client = Client(api_key=LANGSMITH_API_KEY)

    print(f"Fetching runs from experiment: {experiment_name}")
    pairs = _fetch_runs_and_examples(client, experiment_name)

    if not pairs:
        print("No runs found. Check the experiment name.")
        return

    # Group runs by scenario (example_id) and pull scenario metadata.
    runs_by_example: Dict[str, List[Any]] = defaultdict(list)
    examples_by_id: Dict[str, Any] = {}
    for run, example in pairs:
        eid = str(example.id)
        runs_by_example[eid].append(run)
        examples_by_id[eid] = example

    scenario_ids: Dict[str, int] = {}
    queries: Dict[str, str] = {}
    for eid, example in examples_by_id.items():
        scenario_ids[eid] = (example.metadata or {}).get("scenario_id", 0)
        queries[eid] = (example.inputs or {}).get("query", "")

    if scenario_ids_filter is not None:
        filter_set = set(scenario_ids_filter)
        runs_by_example = {
            eid: runs
            for eid, runs in runs_by_example.items()
            if scenario_ids.get(eid) in filter_set
        }
        if not runs_by_example:
            print(f"No runs found for scenario_id(s) {scenario_ids_filter}.")
            return

    total_runs = sum(
        min(len(r), runs_per_scenario) if runs_per_scenario else len(r)
        for r in runs_by_example.values()
    )
    total_evals = total_runs * k * len(evaluators)
    print(
        f"Found {len(pairs)} runs across {len(runs_by_example)} scenarios. "
        f"Will make {total_evals} evaluator calls ({total_runs} runs × {k} repeats × {len(evaluators)} evaluators)."
    )

    # Optionally fetch stored scores from the experiment for delta display.
    # stored_scores[eid][eval_name] = [score, ...]
    stored_scores: Dict[str, Dict[str, List[float]]] = {}
    if show_delta:
        print("Fetching stored feedback scores for delta comparison...")
        for eid, runs in runs_by_example.items():
            probe_runs = runs[:runs_per_scenario] if runs_per_scenario else runs
            stored_scores[eid] = _fetch_stored_scores(
                client, probe_runs, list(evaluators.keys())
            )

    # Re-evaluate each run k times and collect per-scenario scores.
    # Build a flat list of (eid, run_idx, run, eval_name, repeat) tasks and
    # submit them all to a thread pool for concurrency.
    scenarios: List[ScenarioResult] = []
    # results[eid][eval_name][run_idx][repeat] = score
    all_results: Dict[str, Dict[str, Dict[int, Dict[int, Optional[float]]]]] = {}

    tasks = []
    for eid in runs_by_example:
        runs = runs_by_example[eid]
        if runs_per_scenario is not None:
            runs = runs[:runs_per_scenario]
        example = examples_by_id[eid]
        ref_outputs = example.outputs or {}
        all_results[eid] = {
            name: {i: {} for i in range(len(runs))} for name in evaluators
        }

        for run_idx, run in enumerate(runs):
            run_inputs = run.inputs or {}
            run_outputs = run.outputs or {}
            for eval_name, evaluator in evaluators.items():
                for repeat in range(k):
                    tasks.append(
                        (
                            eid,
                            run_idx,
                            eval_name,
                            evaluator,
                            run_inputs,
                            run_outputs,
                            ref_outputs,
                            repeat,
                        )
                    )

    completed = 0
    total_tasks = len(tasks)
    print(f"Submitting {total_tasks} evaluator calls with {max_workers} workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_task = {
            pool.submit(
                _evaluate_once, evaluator, run_inputs, run_outputs, ref_outputs
            ): (eid, run_idx, eval_name, repeat)
            for eid, run_idx, eval_name, evaluator, run_inputs, run_outputs, ref_outputs, repeat in tasks
        }

        for future in as_completed(future_to_task):
            eid, run_idx, eval_name, repeat = future_to_task[future]
            score = future.result()
            all_results[eid][eval_name][run_idx][repeat] = score
            completed += 1
            if completed % max(1, total_tasks // 20) == 0 or completed == total_tasks:
                print(f"  {completed}/{total_tasks} done...", flush=True)

    # Assemble per-scenario results and print σ breakdown.
    for eid in sorted(runs_by_example, key=lambda e: scenario_ids.get(e, 0)):
        runs = runs_by_example[eid]
        if runs_per_scenario is not None:
            runs = runs[:runs_per_scenario]
        sid = scenario_ids.get(eid, 0)
        query = queries.get(eid, "")
        label = f'"{query[:68]}{"..." if len(query) > 68 else ""}"'

        # per_run_scores[eval_name][run_idx] = [score_1, ..., score_k]
        per_run_scores: Dict[str, List[List[float]]] = {name: [] for name in evaluators}

        for run_idx in range(len(runs)):
            for eval_name in evaluators:
                scores_for_run = [
                    s
                    for repeat in range(k)
                    if (s := all_results[eid][eval_name][run_idx].get(repeat))
                    is not None
                ]
                per_run_scores[eval_name].append(scores_for_run)

        flat_scores: Dict[str, List[float]] = {
            name: [s for run_scores in per_run_scores[name] for s in run_scores]
            for name in evaluators
        }
        scenarios.append(
            ScenarioResult(label=label, scenario_id=sid, scores=flat_scores)
        )

        # Per-run σ breakdown for this scenario.
        print(f"\n  Per-run evaluator σ for S{sid}:")
        for eval_name in evaluators:
            run_sigmas = [
                statistics.pstdev(run_scores)
                for run_scores in per_run_scores[eval_name]
                if len(run_scores) >= 2
            ]
            if run_sigmas:
                mean_sigma = statistics.mean(run_sigmas)
                print(
                    f"    {eval_name}: mean σ = {mean_sigma:.3f}  (per-run: {[f'{s:.2f}' for s in run_sigmas]})"
                )

    # Build baseline dict for delta display: (scenario_id, eval_name) -> (old_mean, old_σ).
    baseline = None
    if show_delta and stored_scores:
        baseline_map: Dict[Tuple[int, str], Tuple[float, float]] = {}
        # Aggregate stored scores across all eids that share the same scenario_id.
        stored_by_sid: Dict[int, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for eid, eval_scores in stored_scores.items():
            sid = scenario_ids.get(eid, 0)
            for eval_name, scores in eval_scores.items():
                stored_by_sid[sid][eval_name].extend(scores)
        for sid, eval_scores in stored_by_sid.items():
            for eval_name, scores in eval_scores.items():
                if scores:
                    baseline_map[(sid, eval_name)] = (
                        statistics.mean(scores),
                        statistics.pstdev(scores),
                    )
        baseline = baseline_map if baseline_map else None

    print_consistency_stats(scenarios, baseline=baseline)

    # Summary: mean evaluator σ across all scenarios and runs.
    print("\n=== Evaluator Variance Summary ===")
    print("(σ is computed per individual run across k re-evaluations of fixed output)")
    for eval_name in evaluators:
        all_run_sigmas = []
        for scenario in scenarios:
            per_run = _per_run_sigmas_from_scenario(scenario, eval_name, k)
            all_run_sigmas.extend(per_run)
        if all_run_sigmas:
            mean_sigma = statistics.mean(all_run_sigmas)
            max_sigma = max(all_run_sigmas)
            print(f"  {eval_name}:")
            print(f"    mean σ = {mean_sigma:.3f}  (max = {max_sigma:.3f})")
    print()
    print(
        "Compare these σ values against the per-scenario σ in your experiment results.\n"
        "If evaluator σ << experiment σ, variance is agent-side → increase --num-repetitions.\n"
        "If evaluator σ ≈ experiment σ, judge stochasticity dominates → improve the judge."
    )

    write_variance_entry(
        experiment_name=experiment_name,
        scenarios=scenarios,
        k=k,
    )


def _per_run_sigmas_from_scenario(
    scenario: ScenarioResult, eval_name: str, k: int
) -> List[float]:
    """Re-derive per-run σ values from a flattened score list.

    Since the flat list in ScenarioResult interleaves k scores per run in order,
    we can recover per-run groups by chunking by k.
    """
    flat = scenario.scores.get(eval_name, [])
    # Chunk into groups of k (last group may be smaller if some scores failed).
    sigmas = []
    for i in range(0, len(flat), k):
        chunk = flat[i : i + k]
        if len(chunk) >= 2:
            sigmas.append(statistics.pstdev(chunk))
    return sigmas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Measure LLM judge variance on fixed agent outputs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--experiment",
        required=True,
        help="LangSmith experiment name to pull runs from",
    )
    parser.add_argument(
        "-k",
        type=int,
        default=5,
        help="Number of times to re-run each evaluator per fixed output",
    )
    parser.add_argument(
        "--runs-per-scenario",
        type=int,
        default=None,
        help="Limit how many runs per scenario are probed (default: all)",
    )
    parser.add_argument(
        "--evaluator",
        dest="evaluators",
        nargs="+",
        default=None,
        metavar="NAME",
        help=f"Evaluator(s) to run. Available: {list(_ALL_EVALUATORS)}. Defaults to all.",
    )
    parser.add_argument(
        "--scenario",
        dest="scenarios",
        nargs="+",
        type=int,
        default=None,
        metavar="ID",
        help="Scenario ID(s) to probe (e.g. --scenario 2). Defaults to all.",
    )
    parser.add_argument(
        "--show-delta",
        action="store_true",
        default=False,
        help=(
            "Compare re-evaluated scores against the scores already stored in the "
            "experiment. Useful for testing whether an updated evaluator rubric "
            "changes scores without running a full new experiment."
        ),
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Thread pool size for concurrent evaluator calls.",
    )

    args = parser.parse_args()

    measure_evaluator_variance(
        experiment_name=args.experiment,
        k=args.k,
        runs_per_scenario=args.runs_per_scenario,
        evaluator_names=args.evaluators,
        scenario_ids_filter=args.scenarios,
        show_delta=args.show_delta,
        max_workers=args.max_workers,
    )
