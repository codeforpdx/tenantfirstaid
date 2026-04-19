"""Tests for evaluate/eval_history.py."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from evaluate.eval_history import (
    _capture_env,
    _is_ancestor,
    _results_table,
    _sanitize,
    append_section,
    find_baseline,
    find_entry,
    parse_frontmatter,
    write_run_entry,
    write_variance_entry,
)
from evaluate.results_display import ScenarioResult

# ── _sanitize ──────────────────────────────────────────────────────────────────


def test_sanitize_replaces_special_chars():
    assert _sanitize("my exp 2026!") == "my-exp-2026-"


def test_sanitize_truncates_to_80():
    assert len(_sanitize("x" * 100)) == 80


def test_sanitize_preserves_valid_chars():
    assert _sanitize("abc-123_XYZ") == "abc-123_XYZ"


# ── _capture_env ───────────────────────────────────────────────────────────────


def test_capture_env_includes_model_name(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "gemini-test")
    result = _capture_env()
    assert result["MODEL_NAME"] == "gemini-test"


def test_capture_env_includes_vertex_prefix(monkeypatch):
    monkeypatch.setenv("VERTEX_AI_DATASTORE_LAWS", "datastore-123")
    result = _capture_env()
    assert result["VERTEX_AI_DATASTORE_LAWS"] == "datastore-123"


def test_capture_env_excludes_sensitive_keys(monkeypatch):
    monkeypatch.setenv("LANGSMITH_API_KEY", "secret")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/creds.json")
    result = _capture_env()
    assert "LANGSMITH_API_KEY" not in result
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in result


# ── _results_table ─────────────────────────────────────────────────────────────


def test_results_table_empty():
    assert _results_table([]) == ["_(no results)_"]


def test_results_table_formats_mean_and_sigma():
    scenario = ScenarioResult(
        label="test", scenario_id=0, scores={"legal correctness": [1.0, 0.5, 1.0]}
    )
    rows = _results_table([scenario])
    # Header + separator + one data row.
    assert len(rows) == 3
    data_row = rows[2]
    assert "S0" in data_row
    assert "0.83" in data_row  # mean
    assert "0.24" in data_row  # pstdev


def test_results_table_handles_missing_evaluator():
    s1 = ScenarioResult(label="a", scenario_id=0, scores={"legal correctness": [1.0]})
    s2 = ScenarioResult(label="b", scenario_id=1, scores={"legal correctness": []})
    rows = _results_table([s1, s2])
    assert "—" in rows[3]  # empty scores render as em-dash


# ── parse_frontmatter ─────────────────────────────────────────────────────────


def testparse_frontmatter_extracts_keys(tmp_path):
    f = tmp_path / "entry.md"
    f.write_text("---\nexperiment: my-exp\ngit_dirty: false\n---\n\nbody\n")
    fm = parse_frontmatter(f)
    assert fm["experiment"] == "my-exp"
    assert fm["git_dirty"] == "false"


def testparse_frontmatter_ignores_indented_lines(tmp_path):
    f = tmp_path / "entry.md"
    f.write_text("---\nenv:\n  MODEL_NAME: gemini\ngit_commit: abc\n---\n")
    fm = parse_frontmatter(f)
    assert "MODEL_NAME" not in fm
    assert fm["git_commit"] == "abc"


def testparse_frontmatter_returns_empty_if_no_delimiter(tmp_path):
    f = tmp_path / "entry.md"
    f.write_text("no frontmatter here\n")
    assert parse_frontmatter(f) == {}


# ── append_section ─────────────────────────────────────────────────────────────


def _make_entry(tmp_path: Path, name: str = "entry.md") -> Path:
    f = tmp_path / name
    f.write_text(
        "---\nexperiment: test\n---\n\n"
        "## Results\n\nsome results\n\n"
        "## Triage\n\n_(to be filled by /analyze-experiment)_\n\n"
        "## Hypotheses\n\n_(to be filled by /analyze-experiment)_\n"
    )
    return f


def test_append_section_replaces_placeholder(tmp_path):
    f = _make_entry(tmp_path)
    append_section(f, "Triage", "S0: reasoning failure")
    text = f.read_text()
    assert "S0: reasoning failure" in text
    assert (
        "_(to be filled by /analyze-experiment)_"
        not in text.split("## Triage")[1].split("## Hypotheses")[0]
    )


def test_append_section_does_not_clobber_other_section(tmp_path):
    f = _make_entry(tmp_path)
    append_section(f, "Triage", "triage content")
    text = f.read_text()
    # Hypotheses placeholder must still be present.
    assert "_(to be filled by /analyze-experiment)_" in text.split("## Hypotheses")[1]


def test_append_section_appends_if_placeholder_already_replaced(tmp_path):
    f = _make_entry(tmp_path)
    append_section(f, "Triage", "first triage")
    append_section(f, "Triage", "second triage")
    text = f.read_text()
    assert "first triage" in text
    assert "second triage" in text


def test_append_section_creates_missing_section(tmp_path):
    f = tmp_path / "entry.md"
    f.write_text("---\nexperiment: test\n---\n\n## Results\n\nresults\n")
    append_section(f, "Triage", "added late")
    text = f.read_text()
    assert "## Triage" in text
    assert "added late" in text


# ── write_run_entry / write_variance_entry ────────────────────────────────────


def _fake_git_state() -> dict:
    return {
        "commit": "abc1234",
        "branch": "main",
        "dirty": False,
        "prompt_diff": "",
        "status": "",
    }


def _scenarios() -> list[ScenarioResult]:
    return [
        ScenarioResult(
            label="test scenario",
            scenario_id=0,
            scores={"legal correctness": [1.0, 0.5]},
        )
    ]


def test_write_run_entry_creates_gitignore(tmp_path):
    history_dir = tmp_path / "eval_history"
    with (
        patch("evaluate.eval_history.HISTORY_DIR", history_dir),
        patch("evaluate.eval_history._git_state", _fake_git_state),
        patch("evaluate.eval_history._capture_env", return_value={}),
    ):
        write_run_entry(
            experiment_name="my-exp",
            scenarios=[],
            dataset_name="ds",
            dataset_version="v1",
            num_repetitions=1,
        )

    gitignore = history_dir / ".gitignore"
    assert gitignore.exists()
    assert "!.gitignore" in gitignore.read_text()


def test_write_run_entry_creates_file(tmp_path):
    with (
        patch("evaluate.eval_history.HISTORY_DIR", tmp_path),
        patch("evaluate.eval_history._git_state", _fake_git_state),
        patch(
            "evaluate.eval_history._capture_env",
            return_value={"MODEL_NAME": "test-model"},
        ),
    ):
        path = write_run_entry(
            experiment_name="my-exp",
            scenarios=_scenarios(),
            dataset_name="tenant-legal-qa-scenarios",
            dataset_version="2026-01-01T00:00:00",
            num_repetitions=5,
        )

    assert path.exists()
    text = path.read_text()
    fm = parse_frontmatter(path)
    assert fm["experiment"] == "my-exp"
    assert fm["type"] == "evaluation"
    assert fm["git_commit"] == "abc1234"
    assert fm["git_dirty"] == "false"
    assert fm["dataset"] == "tenant-legal-qa-scenarios"
    assert fm["num_repetitions"] == "5"
    assert "## Triage" in text
    assert "## Hypotheses" in text
    assert "_(to be filled by /analyze-experiment)_" in text


def test_write_variance_entry_creates_file(tmp_path):
    with (
        patch("evaluate.eval_history.HISTORY_DIR", tmp_path),
        patch("evaluate.eval_history._git_state", _fake_git_state),
        patch("evaluate.eval_history._capture_env", return_value={}),
    ):
        path = write_variance_entry(
            experiment_name="my-exp",
            scenarios=_scenarios(),
            k=5,
        )

    assert path.exists()
    fm = parse_frontmatter(path)
    assert fm["type"] == "variance_measurement"
    assert fm["source_experiment"] == "my-exp"
    assert fm["k"] == "5"


def test_write_run_entry_includes_prompt_diff_section(tmp_path):
    git = {**_fake_git_state(), "prompt_diff": "- old line\n+ new line"}
    with (
        patch("evaluate.eval_history.HISTORY_DIR", tmp_path),
        patch("evaluate.eval_history._git_state", return_value=git),
        patch("evaluate.eval_history._capture_env", return_value={}),
    ):
        path = write_run_entry(
            experiment_name="dirty-exp",
            scenarios=[],
            dataset_name="ds",
            dataset_version="v1",
            num_repetitions=1,
        )

    text = path.read_text()
    assert "```diff" in text
    assert "- old line" in text


# ── find_entry ─────────────────────────────────────────────────────────────────


def test_find_entry_locates_matching_file(tmp_path):
    f = tmp_path / "20260101T000000Z-my-exp.md"
    f.write_text("---\nexperiment: my-exp\n---\n")
    with patch("evaluate.eval_history.HISTORY_DIR", tmp_path):
        result = find_entry("my-exp")
    assert result == f


def test_find_entry_returns_none_when_missing(tmp_path):
    with patch("evaluate.eval_history.HISTORY_DIR", tmp_path):
        assert find_entry("nonexistent") is None


def test_find_entry_returns_most_recent_when_multiple(tmp_path):
    older = tmp_path / "20260101T000000Z-my-exp.md"
    newer = tmp_path / "20260102T000000Z-my-exp.md"
    older.write_text("old")
    newer.write_text("new")
    with patch("evaluate.eval_history.HISTORY_DIR", tmp_path):
        result = find_entry("my-exp")
    assert result == newer


# ── find_baseline ──────────────────────────────────────────────────────────────


def _write_history_entry(
    path: Path,
    *,
    entry_type: str = "evaluation",
    dirty: bool = False,
    branch: str = "main",
    commit: str = "abc",
) -> None:
    path.write_text(
        f"---\n"
        f"experiment: {path.stem}\n"
        f"type: {entry_type}\n"
        f"git_commit: {commit}\n"
        f"git_branch: {branch}\n"
        f"git_dirty: {'true' if dirty else 'false'}\n"
        f"---\n"
    )


def test_find_baseline_returns_none_when_no_history(tmp_path):
    with patch("evaluate.eval_history.HISTORY_DIR", tmp_path):
        assert find_baseline() is None


def test_find_baseline_prefers_clean_main_ancestor(tmp_path):
    dirty = tmp_path / "20260103T000000Z-dirty-exp.md"
    feature = tmp_path / "20260102T000000Z-feature-exp.md"
    clean_main = tmp_path / "20260101T000000Z-clean-main-exp.md"

    _write_history_entry(dirty, dirty=True, branch="main", commit="abc")
    _write_history_entry(feature, dirty=False, branch="feature", commit="abc")
    _write_history_entry(clean_main, dirty=False, branch="main", commit="abc")

    with (
        patch("evaluate.eval_history.HISTORY_DIR", tmp_path),
        patch("evaluate.eval_history._is_ancestor", return_value=True),
    ):
        result = find_baseline()

    assert result == clean_main


def test_find_baseline_falls_back_to_clean_ancestor(tmp_path):
    dirty = tmp_path / "20260102T000000Z-dirty.md"
    clean_feature = tmp_path / "20260101T000000Z-feature.md"

    _write_history_entry(dirty, dirty=True, branch="main", commit="abc")
    _write_history_entry(clean_feature, dirty=False, branch="feature", commit="abc")

    with (
        patch("evaluate.eval_history.HISTORY_DIR", tmp_path),
        patch("evaluate.eval_history._is_ancestor", return_value=True),
    ):
        result = find_baseline()

    assert result == clean_feature


def test_find_baseline_skips_variance_entries(tmp_path):
    variance = tmp_path / "20260102T000000Z-variance-my-exp.md"
    eval_entry = tmp_path / "20260101T000000Z-my-exp.md"

    _write_history_entry(
        variance,
        entry_type="variance_measurement",
        dirty=False,
        branch="main",
        commit="abc",
    )
    _write_history_entry(eval_entry, dirty=False, branch="main", commit="abc")

    with (
        patch("evaluate.eval_history.HISTORY_DIR", tmp_path),
        patch("evaluate.eval_history._is_ancestor", return_value=True),
    ):
        result = find_baseline()

    assert result == eval_entry


def test_find_baseline_falls_back_to_any_entry(tmp_path):
    entry = tmp_path / "20260101T000000Z-exp.md"
    _write_history_entry(entry, dirty=True, branch="feature", commit="abc")

    with (
        patch("evaluate.eval_history.HISTORY_DIR", tmp_path),
        patch("evaluate.eval_history._is_ancestor", return_value=False),
    ):
        result = find_baseline()

    assert result == entry


# ── _is_ancestor ───────────────────────────────────────────────────────────────


def test_is_ancestor_returns_false_for_empty_commit():
    assert _is_ancestor("") is False


def test_is_ancestor_returns_true_for_head():
    # HEAD is always its own ancestor via merge-base.
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    if result.returncode == 0:
        head = result.stdout.strip()
        assert _is_ancestor(head) is True
