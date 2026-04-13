"""Tests for evaluate/results_display.py."""

import pytest

from evaluate.results_display import (
    ScenarioResult,
    _keep,
    _to_bucket,
    print_consistency_stats,
)

# ── _to_bucket ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("score", [0.0, 0.5, 1.0])
def test_to_bucket_standard_levels(score):
    assert _to_bucket(score) == score


@pytest.mark.parametrize("score", [0.005, 0.495, 0.996])
def test_to_bucket_within_tolerance(score):
    assert _to_bucket(score) is not None


@pytest.mark.parametrize("score", [0.3, 0.7, 0.25, 0.99])
def test_to_bucket_nonstandard_returns_none(score):
    assert _to_bucket(score) is None


# ── _keep ──────────────────────────────────────────────────────────────────────


def test_keep_no_filter_allows_all():
    assert _keep("legal correctness", None) is True
    assert _keep("tone", None) is True


def test_keep_filter_matches():
    f = {"legal correctness"}
    assert _keep("legal correctness", f) is True
    assert _keep("tone", f) is False


def test_keep_filter_is_case_insensitive():
    f = {"legal correctness"}
    assert _keep("Legal Correctness", f) is True


# ── print_consistency_stats ────────────────────────────────────────────────────


def _two_scenarios():
    return [
        ScenarioResult(
            label='"Is a 72-hour notice valid?"',
            scores={
                "legal correctness": [1.0, 0.5, 1.0, 1.0, 0.5],
                "appropriate tone": [1.0, 1.0, 1.0, 1.0, 1.0],
            },
        ),
        ScenarioResult(
            label='"Can my landlord evict me for a pet?"',
            scores={
                "legal correctness": [0.5, 1.0, 1.0, 0.0, 1.0],
                "appropriate tone": [1.0, 1.0, 0.5, 1.0, 1.0],
            },
        ),
    ]


def test_print_consistency_stats_empty_produces_no_output(capsys):
    print_consistency_stats([])
    assert capsys.readouterr().out == ""


def test_print_consistency_stats_no_matching_evaluator(capsys):
    print_consistency_stats(_two_scenarios(), evaluators=["nonexistent"])
    assert "No matching evaluators found" in capsys.readouterr().out


def test_print_consistency_stats_header_uses_sigma(capsys):
    print_consistency_stats(_two_scenarios())
    out = capsys.readouterr().out
    assert "σ" in out


def test_print_consistency_stats_evaluators_sorted(capsys):
    print_consistency_stats(_two_scenarios())
    out = capsys.readouterr().out
    assert out.index("appropriate tone") < out.index("legal correctness")


def test_print_consistency_stats_scenario_key_present(capsys):
    print_consistency_stats(_two_scenarios())
    out = capsys.readouterr().out
    assert "Scenario Key:" in out
    assert "S1" in out
    assert "S2" in out


def test_print_consistency_stats_scenario_labels_in_key(capsys):
    print_consistency_stats(_two_scenarios())
    out = capsys.readouterr().out
    assert "72-hour notice" in out
    assert "pet" in out


def test_print_consistency_stats_repetition_count_in_key(capsys):
    print_consistency_stats(_two_scenarios())
    out = capsys.readouterr().out
    assert "(n=5)" in out


def test_print_consistency_stats_standard_score_counts(capsys):
    scenarios = [
        ScenarioResult(
            label='"q"',
            scores={"legal correctness": [0.0, 0.5, 0.5, 1.0, 1.0, 1.0]},
        )
    ]
    print_consistency_stats(scenarios)
    out = capsys.readouterr().out
    # Data rows contain the mean value; key rows contain "(n=".
    # 0.0 count=1, 0.5 count=2, 1.0 count=3 — all should appear in the data row.
    data_lines = [
        line for line in out.splitlines() if "S1" in line and "(n=" not in line
    ]
    assert len(data_lines) == 1
    assert "1" in data_lines[0]
    assert "2" in data_lines[0]
    assert "3" in data_lines[0]


def test_print_consistency_stats_no_exclamation_mark(capsys):
    scenarios = [
        ScenarioResult(
            label='"q"',
            scores={"legal correctness": [0.0, 0.0, 1.0]},
        )
    ]
    print_consistency_stats(scenarios)
    assert "!" not in capsys.readouterr().out


def test_print_consistency_stats_evaluator_filter(capsys):
    print_consistency_stats(_two_scenarios(), evaluators=["appropriate tone"])
    out = capsys.readouterr().out
    assert "appropriate tone" in out
    assert "legal correctness" not in out


def test_print_consistency_stats_nonstandard_scores_get_own_columns(capsys):
    scenarios = [
        ScenarioResult(
            label='"q"',
            scores={"legal correctness": [0.0, 0.3, 0.5, 0.7, 1.0]},
        )
    ]
    print_consistency_stats(scenarios)
    out = capsys.readouterr().out
    assert "0.30" in out
    assert "0.70" in out
    # Separator between standard and non-standard columns.
    assert "|" in out


def test_print_consistency_stats_no_nonstandard_column_when_clean(capsys):
    print_consistency_stats(_two_scenarios())
    out = capsys.readouterr().out
    assert "|" not in out


def test_print_consistency_stats_mean_and_sigma_values(capsys):
    scenarios = [
        ScenarioResult(
            label='"q"',
            scores={"tone": [1.0, 1.0, 1.0, 1.0]},
        )
    ]
    print_consistency_stats(scenarios)
    out = capsys.readouterr().out
    # mean=1.0, pstdev=0.0
    assert "1.00" in out
    assert "0.00" in out
