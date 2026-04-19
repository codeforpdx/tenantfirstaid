"""Tests for evaluate/measure_evaluator_variance.py."""

import statistics
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from evaluate.measure_evaluator_variance import (
    _ALL_EVALUATORS,
    _evaluate_once,
    _per_run_sigmas_from_scenario,
    measure_evaluator_variance,
)
from evaluate.results_display import ScenarioResult

# ── _evaluate_once ─────────────────────────────────────────────────────────────


def _make_evaluator(score: Optional[float]) -> Any:
    """Return a callable evaluator that always returns the given score."""
    if score is None:
        return MagicMock(return_value={"score": None})
    return MagicMock(return_value={"score": score})


def test_evaluate_once_returns_float_from_dict():
    evaluator = _make_evaluator(0.75)
    result = _evaluate_once(evaluator, {"q": "a"}, {"output": "b"}, {"ref": "c"})
    assert result == pytest.approx(0.75)


def test_evaluate_once_passes_kwargs_correctly():
    evaluator = MagicMock(return_value={"score": 1.0})
    inputs = {"query": "test"}
    outputs = {"output": "answer"}
    reference = {"reference": "gold"}
    _evaluate_once(evaluator, inputs, outputs, reference)
    evaluator.assert_called_once_with(
        inputs=inputs, outputs=outputs, reference_outputs=reference
    )


def test_evaluate_once_handles_attribute_result():
    """Result objects with a .score attribute (not dict) are supported."""
    result_obj = MagicMock()
    result_obj.score = 0.5
    evaluator = MagicMock(return_value=result_obj)
    # Make isinstance(result, dict) return False.
    result_obj.__class__ = type("FakeResult", (), {})
    score = _evaluate_once(evaluator, {}, {}, {})
    assert score == pytest.approx(0.5)


def test_evaluate_once_returns_none_when_score_is_none():
    evaluator = _make_evaluator(None)
    result = _evaluate_once(evaluator, {}, {}, {})
    assert result is None


def test_evaluate_once_returns_none_on_exception(capsys):
    evaluator = MagicMock(side_effect=RuntimeError("boom"))
    result = _evaluate_once(evaluator, {}, {}, {})
    assert result is None
    assert "evaluator error" in capsys.readouterr().out


# ── _per_run_sigmas_from_scenario ──────────────────────────────────────────────


def test_per_run_sigmas_uniform_scores():
    """k uniform scores per run → σ = 0.0 for each run."""
    scenario = ScenarioResult(
        label='"q"',
        scores={"legal correctness": [1.0, 1.0, 1.0, 0.5, 0.5, 0.5]},
    )
    sigmas = _per_run_sigmas_from_scenario(scenario, "legal correctness", k=3)
    assert len(sigmas) == 2
    assert all(s == pytest.approx(0.0) for s in sigmas)


def test_per_run_sigmas_mixed_scores():
    """Scores that vary within a run produce non-zero σ."""
    scenario = ScenarioResult(
        label='"q"',
        scores={"legal correctness": [1.0, 0.0, 1.0, 0.0]},
    )
    sigmas = _per_run_sigmas_from_scenario(scenario, "legal correctness", k=2)
    assert len(sigmas) == 2
    expected = statistics.pstdev([1.0, 0.0])
    assert all(s == pytest.approx(expected) for s in sigmas)


def test_per_run_sigmas_missing_evaluator_returns_empty():
    scenario = ScenarioResult(label='"q"', scores={})
    sigmas = _per_run_sigmas_from_scenario(scenario, "nonexistent", k=3)
    assert sigmas == []


def test_per_run_sigmas_single_score_per_run_excluded():
    """Chunks smaller than 2 are skipped (can't compute σ)."""
    scenario = ScenarioResult(
        label='"q"',
        scores={"legal correctness": [1.0]},
    )
    sigmas = _per_run_sigmas_from_scenario(scenario, "legal correctness", k=1)
    assert sigmas == []


def test_per_run_sigmas_partial_last_chunk_excluded():
    """If total scores are not divisible by k, the short last chunk is skipped."""
    # 5 scores with k=3 → chunk [0:3] (size 3, included) + [3:5] (size 2, included)
    scenario = ScenarioResult(
        label='"q"',
        scores={"legal correctness": [1.0, 0.0, 1.0, 0.5, 0.5]},
    )
    sigmas = _per_run_sigmas_from_scenario(scenario, "legal correctness", k=3)
    # First chunk [1.0, 0.0, 1.0], second chunk [0.5, 0.5] (size 2, >= 2 so included)
    assert len(sigmas) == 2


# ── _ALL_EVALUATORS contents ───────────────────────────────────────────────────


def test_all_evaluators_has_legal_correctness():
    assert "legal correctness" in _ALL_EVALUATORS


def test_all_evaluators_has_tone():
    assert "appropriate tone" in _ALL_EVALUATORS


# ── measure_evaluator_variance (unit, no network) ─────────────────────────────


def _fake_run(example_id: str, inputs: Dict, outputs: Dict) -> MagicMock:
    run = MagicMock()
    run.reference_example_id = example_id
    run.inputs = inputs
    run.outputs = outputs
    return run


def _fake_example(example_id: str, scenario_id: int, query: str) -> MagicMock:
    example = MagicMock()
    example.id = example_id
    example.metadata = {"scenario_id": scenario_id}
    example.inputs = {"query": query}
    example.outputs = {"reference": "gold answer"}
    return example


@pytest.fixture()
def fake_pairs():
    """Two runs for scenario 1 and one run for scenario 2."""
    e1 = _fake_example("aaa", 1, "Can I withhold rent?")
    e2 = _fake_example("bbb", 2, "How much notice must I give?")
    run1a = _fake_run("aaa", {"query": "Can I withhold rent?"}, {"output": "Yes"})
    run1b = _fake_run("aaa", {"query": "Can I withhold rent?"}, {"output": "Maybe"})
    run2a = _fake_run("bbb", {"query": "How much notice?"}, {"output": "30 days"})
    return [(run1a, e1), (run1b, e1), (run2a, e2)]


def test_measure_evaluator_variance_calls_evaluator_k_times(fake_pairs):
    """With k=3 and a single evaluator over 3 runs, expect 9 evaluator calls total."""
    mock_evaluator = MagicMock(return_value={"score": 1.0})
    with (
        patch(
            "evaluate.measure_evaluator_variance._fetch_runs_and_examples",
            return_value=fake_pairs,
        ),
        patch(
            "evaluate.measure_evaluator_variance._ALL_EVALUATORS",
            {"legal correctness": mock_evaluator},
        ),
        patch("evaluate.measure_evaluator_variance.Client"),
        patch("evaluate.measure_evaluator_variance.print_consistency_stats"),
        patch("builtins.print"),
    ):
        measure_evaluator_variance("fake-experiment", k=3)

    # 3 runs × 3 repeats = 9 calls.
    assert mock_evaluator.call_count == 9


def test_measure_evaluator_variance_unknown_evaluator_raises():
    with pytest.raises(ValueError, match="Unknown evaluator"):
        measure_evaluator_variance(
            "fake-experiment", evaluator_names=["nonexistent evaluator"]
        )


def test_measure_evaluator_variance_scenario_filter(fake_pairs):
    """scenario_ids_filter limits evaluation to matching scenarios only."""
    mock_evaluator = MagicMock(return_value={"score": 0.5})
    with (
        patch(
            "evaluate.measure_evaluator_variance._fetch_runs_and_examples",
            return_value=fake_pairs,
        ),
        patch(
            "evaluate.measure_evaluator_variance._ALL_EVALUATORS",
            {"legal correctness": mock_evaluator},
        ),
        patch("evaluate.measure_evaluator_variance.Client"),
        patch("evaluate.measure_evaluator_variance.print_consistency_stats"),
        patch("builtins.print"),
    ):
        # Only scenario 1 (2 runs), k=2 → 4 calls.
        measure_evaluator_variance("fake-experiment", k=2, scenario_ids_filter=[1])

    assert mock_evaluator.call_count == 4


def test_measure_evaluator_variance_runs_per_scenario_limit(fake_pairs):
    """runs_per_scenario=1 caps the number of runs processed per scenario."""
    mock_evaluator = MagicMock(return_value={"score": 1.0})
    with (
        patch(
            "evaluate.measure_evaluator_variance._fetch_runs_and_examples",
            return_value=fake_pairs,
        ),
        patch(
            "evaluate.measure_evaluator_variance._ALL_EVALUATORS",
            {"legal correctness": mock_evaluator},
        ),
        patch("evaluate.measure_evaluator_variance.Client"),
        patch("evaluate.measure_evaluator_variance.print_consistency_stats"),
        patch("builtins.print"),
    ):
        # 2 scenarios × 1 run × k=2 = 4 calls.
        measure_evaluator_variance("fake-experiment", k=2, runs_per_scenario=1)

    assert mock_evaluator.call_count == 4


def test_measure_evaluator_variance_no_runs_prints_message(capsys):
    with (
        patch(
            "evaluate.measure_evaluator_variance._fetch_runs_and_examples",
            return_value=[],
        ),
        patch("evaluate.measure_evaluator_variance.Client"),
    ):
        measure_evaluator_variance("fake-experiment")

    assert "No runs found" in capsys.readouterr().out


def test_measure_evaluator_variance_no_matching_scenario_prints_message(
    fake_pairs, capsys
):
    with (
        patch(
            "evaluate.measure_evaluator_variance._fetch_runs_and_examples",
            return_value=fake_pairs,
        ),
        patch("evaluate.measure_evaluator_variance.Client"),
    ):
        measure_evaluator_variance("fake-experiment", scenario_ids_filter=[99])

    assert "No runs found" in capsys.readouterr().out
