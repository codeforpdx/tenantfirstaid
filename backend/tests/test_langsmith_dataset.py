"""Tests for evaluate/langsmith_dataset.py."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from evaluate.langsmith_dataset import (
    RETENTION_DAYS,
    _apply_dataset_schemas,
    _as_utc,
    _check_retrieval_from_traces,
    _collect_tool_responses_by_run,
    _datastore_unchanged_since_experiment,
    _experiment_latest_run_time,
    _example_content_diff,
    _experiment_scores,
    _extract_rubric,
    _git_is_clean,
    _load_dataset_schemas,
    _load_examples,
    _message_text,
    _read_jsonl,
    _render_transcript,
    _scan_pii,
    _scenario_id,
    _tabulate,
    _Validate,
    _warn_pii,
    build_parser,
    cmd_dataset_create,
    cmd_dataset_delete,
    cmd_dataset_diff,
    cmd_dataset_list,
    cmd_dataset_merge,
    cmd_dataset_pull,
    cmd_dataset_push,
    cmd_dataset_validate,
    cmd_example_append,
    cmd_example_list,
    cmd_example_remove,
    cmd_example_show,
    cmd_example_update,
    cmd_experiment_compare,
    cmd_experiment_markdown,
    cmd_experiment_show,
    cmd_experiment_stats,
    cmd_run_exemplars,
    cmd_run_show,
    cmd_run_trace,
    local_or_remote,
    make_client,
)

# ── helpers ────────────────────────────────────────────────────────────────────


def _make_valid_record(scenario_id: int = 1) -> dict:
    return {
        "metadata": {
            "scenario_id": scenario_id,
            "city": "Portland",
            "state": "OR",
            "tags": ["city-Portland", "state-OR"],
            "dataset_split": ["train"],
        },
        "inputs": {
            "city": "Portland",
            "state": "OR",
            "query": "Can my landlord evict me?",
        },
        "outputs": {
            "facts": ["ORS 90.394 requires written notice."],
            "reference_conversation": [
                {
                    "type": "human",
                    "content": "Can my landlord evict me?",
                    "additional_kwargs": {},
                    "response_metadata": {},
                }
            ],
        },
    }


def _make_scenario(scenario_id: int = 1, query: str = "test query") -> dict:
    return {
        "metadata": {"scenario_id": scenario_id, "city": "Portland", "state": "OR"},
        "inputs": {"query": query, "city": "Portland", "state": "OR"},
        "outputs": {"facts": ["fact 1"], "reference_conversation": []},
    }


def _make_remote_example(scenario_id: int):
    ex = MagicMock()
    ex.id = uuid4()
    ex.metadata = {"scenario_id": scenario_id}
    return ex


# ── _read_jsonl ────────────────────────────────────────────────────────────────


def test_read_jsonl_parses_records(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text('{"a": 1}\n{"a": 2}\n')
    assert _read_jsonl(f) == [{"a": 1}, {"a": 2}]


def test_read_jsonl_skips_blank_lines(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text('{"a": 1}\n\n{"a": 2}\n')
    assert _read_jsonl(f) == [{"a": 1}, {"a": 2}]


def test_read_jsonl_skips_comment_lines(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text('// this is a comment\n{"a": 1}\n')
    assert _read_jsonl(f) == [{"a": 1}]


def test_read_jsonl_with_line_numbers(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text('// comment\n\n{"a": 1}\n{"a": 2}\n')
    result = _read_jsonl(f, with_line_numbers=True)
    assert result == [(3, {"a": 1}), (4, {"a": 2})]


def test_read_jsonl_empty_file(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text("")
    assert _read_jsonl(f) == []


def test_read_jsonl_validate_valid(tmp_path):
    from evaluate.langsmith_dataset import DEFAULT_SCHEMA

    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record()) + "\n")
    _read_jsonl(f, validate=_Validate("error", schema=DEFAULT_SCHEMA))


def test_read_jsonl_validate_error_raises(tmp_path):
    from evaluate.langsmith_dataset import DEFAULT_SCHEMA

    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps({"metadata": {"scenario_id": 1}, "outputs": {}}) + "\n")
    with pytest.raises(ValueError, match="Line 1"):
        _read_jsonl(f, validate=_Validate("error", schema=DEFAULT_SCHEMA))


def test_read_jsonl_validate_reports_all_errors(tmp_path):
    """All invalid records are reported, not just the first."""
    from evaluate.langsmith_dataset import DEFAULT_SCHEMA

    f = tmp_path / "data.jsonl"
    bad = {"metadata": {"scenario_id": 1}, "outputs": {}}
    f.write_text(
        json.dumps(bad)
        + "\n"
        + json.dumps({**bad, "metadata": {"scenario_id": 2}})
        + "\n"
    )
    with pytest.raises(ValueError) as exc:
        _read_jsonl(f, validate=_Validate("error", schema=DEFAULT_SCHEMA))
    msg = str(exc.value)
    assert "Line 1" in msg
    assert "Line 2" in msg


def test_read_jsonl_validate_warn_continues(tmp_path, capsys):
    """validate='warn' prints to stderr but still returns all records."""
    from evaluate.langsmith_dataset import DEFAULT_SCHEMA

    f = tmp_path / "data.jsonl"
    bad = {"metadata": {"scenario_id": 1}, "outputs": {}}
    f.write_text(json.dumps(bad) + "\n")
    result = _read_jsonl(f, validate=_Validate("warn", schema=DEFAULT_SCHEMA))
    err = capsys.readouterr().err
    assert result == [bad]
    assert "warning" in err
    assert "Line 1" in err


# ── _scenario_id ───────────────────────────────────────────────────────────────


def test_scenario_id_returns_id():
    assert _scenario_id({"metadata": {"scenario_id": 42}}) == 42


def test_scenario_id_raises_on_missing():
    with pytest.raises(ValueError, match="missing scenario_id"):
        _scenario_id({"metadata": {}})


def test_scenario_id_raises_on_missing_metadata():
    with pytest.raises(ValueError, match="missing scenario_id"):
        _scenario_id({})


# ── _tabulate ──────────────────────────────────────────────────────────────────


def test_tabulate_prints_rows(capsys):
    _tabulate([("a", "bb"), ("ccc", "d")])
    out = capsys.readouterr().out
    assert "a" in out
    assert "ccc" in out


def test_tabulate_prints_headers(capsys):
    _tabulate([("val1", "val2")], headers=("COL1", "COL2"))
    out = capsys.readouterr().out
    assert "COL1" in out
    assert "COL2" in out
    assert "---" in out


def test_tabulate_empty_rows_no_output(capsys):
    _tabulate([])
    assert capsys.readouterr().out == ""


# ── _extract_rubric ────────────────────────────────────────────────────────────


def test_extract_rubric_returns_content():
    text = "Some preamble\n<Rubric>\nScore 1-5 based on accuracy.\n</Rubric>\nSome postamble"
    assert _extract_rubric(text) == "Score 1-5 based on accuracy.\n"


def test_extract_rubric_raises_when_missing():
    with pytest.raises(ValueError, match="Could not find"):
        _extract_rubric("No rubric tags here.")


def test_extract_rubric_strips_surrounding_whitespace():
    text = "<Rubric>\n\n  Be accurate.  \n\n</Rubric>"
    assert _extract_rubric(text) == "Be accurate.\n"


# ── local_or_remote ────────────────────────────────────────────────────────────


def test_local_or_remote_jsonl_returns_path():
    result = local_or_remote("my-dataset.jsonl")
    assert isinstance(result, Path)
    assert result == Path("my-dataset.jsonl")


def test_local_or_remote_name_returns_str():
    result = local_or_remote("my-remote-dataset")
    assert isinstance(result, str)
    assert result == "my-remote-dataset"


# ── _git_is_clean ──────────────────────────────────────────────────────────────


def test_git_is_clean_returns_true_when_no_output(tmp_path):
    f = tmp_path / "clean.jsonl"
    f.touch()
    mock_result = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", return_value=mock_result):
        assert _git_is_clean(f) is True


def test_git_is_clean_returns_false_when_dirty(tmp_path):
    f = tmp_path / "dirty.jsonl"
    f.touch()
    mock_result = MagicMock(returncode=0, stdout=" M dirty.jsonl\n")
    with patch("subprocess.run", return_value=mock_result):
        assert _git_is_clean(f) is False


def test_git_is_clean_returns_false_on_nonzero_exit(tmp_path):
    f = tmp_path / "file.jsonl"
    f.touch()
    mock_result = MagicMock(returncode=1, stdout="")
    with patch("subprocess.run", return_value=mock_result):
        assert _git_is_clean(f) is False


# ── _load_dataset_schemas ──────────────────────────────────────────────────────


def test_load_dataset_schemas_returns_dicts():
    inputs_schema, outputs_schema = _load_dataset_schemas()
    assert isinstance(inputs_schema, dict)
    assert isinstance(outputs_schema, dict)


def test_load_dataset_schemas_inputs_has_query():
    inputs_schema, _ = _load_dataset_schemas()
    assert "query" in inputs_schema.get("properties", {})


# ── _apply_dataset_schemas ─────────────────────────────────────────────────────


def test_apply_dataset_schemas_sends_patch():
    from langsmith import utils as langsmith_utils

    mock_client = MagicMock()
    mock_client._headers = {"Authorization": "Bearer test"}
    mock_client.request_with_retries.return_value = MagicMock()

    with patch.object(langsmith_utils, "raise_for_status_with_text"):
        _apply_dataset_schemas(mock_client, "abc-123")

    call_args = mock_client.request_with_retries.call_args
    assert call_args[0][0] == "PATCH"
    assert "/datasets/abc-123" in call_args[0][1]
    payload = json.loads(call_args[1]["data"])
    assert "inputs_schema_definition" in payload
    assert "outputs_schema_definition" in payload


# ── make_client ────────────────────────────────────────────────────────────────


def test_make_client_raises_without_api_key():
    with patch("evaluate.langsmith_dataset.LANGSMITH_API_KEY", None):
        with pytest.raises(RuntimeError, match="LANGSMITH_API_KEY"):
            make_client()


# ── _load_examples ─────────────────────────────────────────────────────────────


def test_load_examples_from_path(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record()) + "\n")
    mock_client = MagicMock()
    result = _load_examples(f, mock_client)
    assert result == [_make_valid_record()]
    mock_client.read_dataset.assert_not_called()


def test_load_examples_from_remote():
    remote_ex = _make_remote_example(1)
    remote_ex.inputs = {"query": "test"}
    remote_ex.outputs = {"facts": []}
    mock_client = MagicMock()
    mock_ds = MagicMock(id=uuid4())
    mock_client.read_dataset.return_value = mock_ds
    mock_client.list_examples.return_value = [remote_ex]
    result = _load_examples("my-dataset", mock_client)
    assert len(result) == 1
    assert result[0]["metadata"] == remote_ex.metadata


# ── build_parser ───────────────────────────────────────────────────────────────


def test_parser_dataset_validate_defaults():
    from evaluate.langsmith_dataset import DEFAULT_JSONL, DEFAULT_SCHEMA

    parser = build_parser()
    args = parser.parse_args(["dataset", "validate"])
    assert args.file == DEFAULT_JSONL
    assert args.schema == DEFAULT_SCHEMA


def test_parser_example_update_routes_correctly():
    parser = build_parser()
    args = parser.parse_args(["example", "update", "42"])
    assert args.scenario_id == 42
    assert args.func.__name__ == "cmd_example_update"


def test_parser_example_update_accepts_custom_file(tmp_path):
    from evaluate.langsmith_dataset import DEFAULT_DATASET_NAME

    f = tmp_path / "custom.jsonl"
    f.write_text("")
    parser = build_parser()
    args = parser.parse_args(["example", "update", DEFAULT_DATASET_NAME, "1", str(f)])
    assert args.scenario_id == 1
    assert args.file == f


def test_parser_dataset_push_defaults():
    from evaluate.langsmith_dataset import DEFAULT_DATASET_NAME, DEFAULT_JSONL

    parser = build_parser()
    args = parser.parse_args(["dataset", "push"])
    assert args.file == DEFAULT_JSONL
    assert args.remote == DEFAULT_DATASET_NAME


# ── cmd_dataset_list ───────────────────────────────────────────────────────────


def test_cmd_dataset_list_no_datasets(capsys):
    mock_client = MagicMock()
    mock_client.list_datasets.return_value = []
    args = MagicMock()
    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        cmd_dataset_list(args)
    assert "No datasets" in capsys.readouterr().out


def test_cmd_dataset_list_shows_names(capsys):
    mock_ds = MagicMock()
    mock_ds.name = "my-dataset"
    mock_ds.id = uuid4()
    mock_client = MagicMock()
    mock_client.list_datasets.return_value = [mock_ds]
    args = MagicMock()
    args.no_header = True
    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        cmd_dataset_list(args)
    assert "my-dataset" in capsys.readouterr().out


# ── cmd_dataset_create ─────────────────────────────────────────────────────────


def test_cmd_dataset_create_new(capsys):
    mock_client = MagicMock()
    mock_client.has_dataset.return_value = False
    mock_ds = MagicMock(id=uuid4())
    mock_client.create_dataset.return_value = mock_ds
    args = MagicMock()
    args.name = "new-dataset"
    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        cmd_dataset_create(args)
    mock_client.create_dataset.assert_called_once()
    assert "Created" in capsys.readouterr().out


def test_cmd_dataset_create_already_exists_exits(capsys):
    mock_client = MagicMock()
    mock_client.has_dataset.return_value = True
    args = MagicMock()
    args.name = "existing-dataset"
    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        with pytest.raises(SystemExit) as exc:
            cmd_dataset_create(args)
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().out


# ── cmd_dataset_delete ─────────────────────────────────────────────────────────


def test_cmd_dataset_delete_found(capsys):
    mock_client = MagicMock()
    mock_ds = MagicMock(id=uuid4())
    mock_client.read_dataset.return_value = mock_ds
    args = MagicMock()
    args.name = "my-dataset"
    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        cmd_dataset_delete(args)
    mock_client.delete_dataset.assert_called_once_with(dataset_id=mock_ds.id)
    assert "Deleted" in capsys.readouterr().out


def test_cmd_dataset_delete_not_found_exits(capsys):
    from langsmith import utils as langsmith_utils

    mock_client = MagicMock()
    mock_client.read_dataset.side_effect = langsmith_utils.LangSmithNotFoundError(
        "not found"
    )
    args = MagicMock()
    args.name = "missing"
    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        with pytest.raises(SystemExit) as exc:
            cmd_dataset_delete(args)
    assert exc.value.code == 1
    assert "not found" in capsys.readouterr().out


# ── cmd_dataset_push ───────────────────────────────────────────────────────────


def test_cmd_dataset_push_creates_and_uploads(tmp_path, capsys):
    from langsmith import utils as langsmith_utils

    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record(1)) + "\n")

    mock_client = MagicMock()
    mock_client.read_dataset.side_effect = langsmith_utils.LangSmithNotFoundError("x")
    mock_ds = MagicMock(id=uuid4())
    mock_client.create_dataset.return_value = mock_ds
    mock_client.list_examples.return_value = []
    mock_client._headers = {}
    mock_client.request_with_retries.return_value = MagicMock()

    args = MagicMock()
    args.file = f
    args.remote = "new-ds"

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        with patch("evaluate.langsmith_dataset.langsmith_utils") as mock_utils:
            mock_utils.LangSmithNotFoundError = langsmith_utils.LangSmithNotFoundError
            cmd_dataset_push(args)

    mock_client.create_dataset.assert_called_once()
    mock_client.create_example.assert_called_once()
    assert "Pushed 1" in capsys.readouterr().out


def test_cmd_dataset_push_skips_existing_examples(tmp_path, capsys):
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record(1)) + "\n")

    existing_ex = _make_remote_example(1)
    mock_client = MagicMock()
    mock_ds = MagicMock(id=uuid4())
    mock_client.read_dataset.return_value = mock_ds
    mock_client.list_examples.return_value = [existing_ex]
    mock_client._headers = {}
    mock_client.request_with_retries.return_value = MagicMock()

    args = MagicMock()
    args.file = f
    args.remote = "my-ds"

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        with patch("evaluate.langsmith_dataset.langsmith_utils"):
            cmd_dataset_push(args)

    mock_client.create_example.assert_not_called()
    assert "0 new" in capsys.readouterr().out


def test_cmd_dataset_push_validation_failure_exits(tmp_path, capsys):
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps({"metadata": {"scenario_id": 1}, "outputs": {}}) + "\n")

    args = MagicMock()
    args.file = f
    args.remote = "my-ds"

    with patch("evaluate.langsmith_dataset.make_client", return_value=MagicMock()):
        with pytest.raises(SystemExit) as exc:
            cmd_dataset_push(args)
    assert exc.value.code == 1
    assert "Line 1" in capsys.readouterr().err


# ── cmd_dataset_pull ───────────────────────────────────────────────────────────


def test_cmd_dataset_pull_writes_file(tmp_path, capsys):
    local = tmp_path / "out.jsonl"
    ex = _make_remote_example(1)
    ex.inputs = {"query": "q", "state": "OR", "city": None}
    ex.outputs = {"facts": [], "reference_conversation": []}

    mock_client = MagicMock()
    mock_ds = MagicMock(id=uuid4())
    mock_client.read_dataset.return_value = mock_ds
    mock_client.list_examples.return_value = [ex]

    args = MagicMock()
    args.file = local
    args.remote = "my-ds"
    args.force = True
    args.dry_run = False

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        cmd_dataset_pull(args)

    assert local.exists()
    records = _read_jsonl(local)
    assert len(records) == 1
    assert "Pulled 1" in capsys.readouterr().out


def test_cmd_dataset_pull_dry_run_does_not_write(tmp_path, capsys):
    local = tmp_path / "out.jsonl"

    mock_client = MagicMock()
    mock_ds = MagicMock(id=uuid4())
    mock_client.read_dataset.return_value = mock_ds
    mock_client.list_examples.return_value = [_make_remote_example(1)]

    args = MagicMock()
    args.file = local
    args.remote = "my-ds"
    args.force = True
    args.dry_run = True

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        cmd_dataset_pull(args)

    assert not local.exists()
    assert "Would pull" in capsys.readouterr().out


def test_cmd_dataset_pull_dirty_file_exits(tmp_path, capsys):
    local = tmp_path / "out.jsonl"
    local.write_text("{}")

    args = MagicMock()
    args.file = local
    args.force = False
    args.dry_run = False

    with patch("evaluate.langsmith_dataset.make_client", return_value=MagicMock()):
        with patch("evaluate.langsmith_dataset._git_is_clean", return_value=False):
            with pytest.raises(SystemExit) as exc:
                cmd_dataset_pull(args)
    assert exc.value.code == 1
    assert "uncommitted" in capsys.readouterr().err


# ── cmd_dataset_validate ───────────────────────────────────────────────────────


def test_cmd_dataset_validate_valid_file(tmp_path, capsys):
    from evaluate.langsmith_dataset import DEFAULT_SCHEMA

    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record()) + "\n")

    args = MagicMock()
    args.file = f
    args.schema = DEFAULT_SCHEMA

    cmd_dataset_validate(args)
    assert "valid" in capsys.readouterr().out


def test_cmd_dataset_validate_invalid_file_exits(tmp_path, capsys):
    from evaluate.langsmith_dataset import DEFAULT_SCHEMA

    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps({"metadata": {"scenario_id": 1}, "outputs": {}}) + "\n")

    args = MagicMock()
    args.file = f
    args.schema = DEFAULT_SCHEMA

    with pytest.raises(SystemExit) as exc:
        cmd_dataset_validate(args)
    assert exc.value.code == 1
    assert "Line 1" in capsys.readouterr().err


# ── cmd_dataset_merge ──────────────────────────────────────────────────────────


def test_cmd_dataset_merge_adds_new(tmp_path, capsys):
    f = tmp_path / "source.jsonl"
    f.write_text(json.dumps(_make_valid_record(1)) + "\n")

    mock_client = MagicMock()
    mock_ds = MagicMock(id=uuid4())
    mock_client.read_dataset.return_value = mock_ds
    mock_client.list_examples.return_value = []
    mock_client._headers = {}
    mock_client.request_with_retries.return_value = MagicMock()

    args = MagicMock()
    args.source = f
    args.target = "target-ds"

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        with patch("evaluate.langsmith_dataset.langsmith_utils"):
            cmd_dataset_merge(args)

    mock_client.create_example.assert_called_once()
    assert "Merged 1" in capsys.readouterr().out


def test_cmd_dataset_merge_skips_existing(tmp_path, capsys):
    f = tmp_path / "source.jsonl"
    f.write_text(json.dumps(_make_valid_record(1)) + "\n")

    mock_client = MagicMock()
    mock_ds = MagicMock(id=uuid4())
    mock_client.read_dataset.return_value = mock_ds
    mock_client.list_examples.return_value = [_make_remote_example(1)]
    mock_client._headers = {}
    mock_client.request_with_retries.return_value = MagicMock()

    args = MagicMock()
    args.source = f
    args.target = "target-ds"

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        with patch("evaluate.langsmith_dataset.langsmith_utils"):
            cmd_dataset_merge(args)

    mock_client.create_example.assert_not_called()
    assert "0 new" in capsys.readouterr().out


def test_cmd_dataset_merge_validation_failure_exits(tmp_path, capsys):
    f = tmp_path / "source.jsonl"
    f.write_text(json.dumps({"metadata": {"scenario_id": 1}, "outputs": {}}) + "\n")

    args = MagicMock()
    args.source = f
    args.target = "target-ds"

    with patch("evaluate.langsmith_dataset.make_client", return_value=MagicMock()):
        with pytest.raises(SystemExit) as exc:
            cmd_dataset_merge(args)
    assert exc.value.code == 1
    assert "Line 1" in capsys.readouterr().err


# ── cmd_example_list ──────────────────────────────────────────────────────────


def test_cmd_example_list_shows_examples(capsys):
    ex = _make_remote_example(5)
    ex.inputs = {"query": "Is this legal?", "state": "OR", "city": None}

    mock_client = MagicMock()
    mock_ds = MagicMock(id=uuid4())
    mock_client.read_dataset.return_value = mock_ds
    mock_client.list_examples.return_value = [ex]

    args = MagicMock()
    args.dataset = "my-ds"
    args.no_header = True

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        cmd_example_list(args)

    out = capsys.readouterr().out
    assert "5" in out
    assert "Is this legal?" in out


# ── cmd_example_show ──────────────────────────────────────────────────────────


def test_cmd_example_show_local_found(tmp_path, capsys):
    f = tmp_path / "data.jsonl"
    record = _make_valid_record(7)
    f.write_text(json.dumps(record) + "\n")

    args = MagicMock()
    args.dataset = f
    args.scenario_id = 7

    cmd_example_show(args)

    out = capsys.readouterr().out
    assert '"scenario_id": 7' in out


def test_cmd_example_show_local_not_found_exits(tmp_path, capsys):
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record(1)) + "\n")

    args = MagicMock()
    args.dataset = f
    args.scenario_id = 99

    with pytest.raises(SystemExit) as exc:
        cmd_example_show(args)
    assert exc.value.code == 1
    assert "99" in capsys.readouterr().err


def test_cmd_example_show_remote(capsys):
    remote_ex = _make_remote_example(3)
    remote_ex.inputs = {"query": "q"}
    remote_ex.outputs = {"facts": []}

    mock_client = MagicMock()
    mock_ds = MagicMock(id=uuid4())
    mock_client.read_dataset.return_value = mock_ds
    mock_client.list_examples.return_value = [remote_ex]

    args = MagicMock()
    args.dataset = "my-remote-ds"
    args.scenario_id = 3

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        cmd_example_show(args)

    assert "scenario_id" in capsys.readouterr().out


# ── cmd_example_append ────────────────────────────────────────────────────────


def test_cmd_example_append_uploads_all(tmp_path, capsys):
    f = tmp_path / "new.jsonl"
    f.write_text(
        json.dumps(_make_valid_record(10))
        + "\n"
        + json.dumps(_make_valid_record(11))
        + "\n"
    )

    mock_client = MagicMock()
    mock_ds = MagicMock(id=uuid4())
    mock_client.read_dataset.return_value = mock_ds

    args = MagicMock()
    args.file = f
    args.dataset = "my-ds"

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        cmd_example_append(args)

    assert mock_client.create_example.call_count == 2
    assert "Appended 2" in capsys.readouterr().out


def test_cmd_example_append_validation_failure_exits(tmp_path, capsys):
    f = tmp_path / "bad.jsonl"
    f.write_text(json.dumps({"metadata": {"scenario_id": 1}, "outputs": {}}) + "\n")

    args = MagicMock()
    args.file = f
    args.dataset = "my-ds"

    with patch("evaluate.langsmith_dataset.make_client", return_value=MagicMock()):
        with pytest.raises(SystemExit) as exc:
            cmd_example_append(args)
    assert exc.value.code == 1
    assert "Line 1" in capsys.readouterr().err


# ── cmd_example_remove ────────────────────────────────────────────────────────


def test_cmd_example_remove_found(capsys):
    ex = _make_remote_example(7)

    mock_client = MagicMock()
    mock_ds = MagicMock(id=uuid4())
    mock_client.read_dataset.return_value = mock_ds
    mock_client.list_examples.return_value = [ex]

    args = MagicMock()
    args.dataset = "my-ds"
    args.scenario_id = 7

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        cmd_example_remove(args)

    mock_client.delete_example.assert_called_once_with(ex.id)
    assert "Removed" in capsys.readouterr().out


def test_cmd_example_remove_not_found_exits(capsys):
    mock_client = MagicMock()
    mock_ds = MagicMock(id=uuid4())
    mock_client.read_dataset.return_value = mock_ds
    mock_client.list_examples.return_value = []

    args = MagicMock()
    args.dataset = "my-ds"
    args.scenario_id = 42

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        with pytest.raises(SystemExit) as exc:
            cmd_example_remove(args)
    assert exc.value.code == 1
    assert "42" in capsys.readouterr().err


# ── cmd_example_update ────────────────────────────────────────────────────────


def test_cmd_example_update_applies_patch(tmp_path, capsys):
    record = _make_valid_record(3)
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(record) + "\n")

    remote_ex = _make_remote_example(3)

    args = MagicMock()
    args.file = f
    args.scenario_id = 3
    args.dataset = "my-dataset"

    mock_client = MagicMock()
    mock_client.read_dataset.return_value = MagicMock(id=uuid4())
    mock_client.list_examples.return_value = [remote_ex]

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        cmd_example_update(args)

    assert "Updated example 3" in capsys.readouterr().out
    mock_client.update_example.assert_called_once_with(
        example_id=remote_ex.id,
        inputs=record["inputs"],
        outputs=record["outputs"],
        metadata=record["metadata"],
    )


def test_cmd_example_update_not_in_local_file_exits(tmp_path, capsys):
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record(1)) + "\n")

    args = MagicMock()
    args.file = f
    args.scenario_id = 99
    args.dataset = "my-dataset"

    with pytest.raises(SystemExit) as exc:
        cmd_example_update(args)
    assert exc.value.code == 1
    assert "99" in capsys.readouterr().err


def test_cmd_example_update_not_in_remote_exits(tmp_path, capsys):
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record(5)) + "\n")

    args = MagicMock()
    args.file = f
    args.scenario_id = 5
    args.dataset = "my-dataset"

    mock_client = MagicMock()
    mock_client.read_dataset.return_value = MagicMock(id=uuid4())
    mock_client.list_examples.return_value = []

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        with pytest.raises(SystemExit) as exc:
            cmd_example_update(args)
    assert exc.value.code == 1
    assert "5" in capsys.readouterr().err


# ── _example_content_diff ────────────────────────────────────────────────────


def test_example_content_diff_identical():
    assert _example_content_diff(_make_scenario(), _make_scenario()) == []


def test_example_content_diff_inputs_differ():
    left = _make_scenario(query="old query")
    right = _make_scenario(query="new query")
    combined = "".join(_example_content_diff(left, right))
    assert "old query" in combined
    assert "new query" in combined
    assert "left/inputs" in combined
    assert "right/inputs" in combined


def test_example_content_diff_outputs_differ():
    left = {
        **_make_scenario(),
        "outputs": {"facts": ["fact A"], "reference_conversation": []},
    }
    right = {
        **_make_scenario(),
        "outputs": {"facts": ["fact B"], "reference_conversation": []},
    }
    combined = "".join(_example_content_diff(left, right))
    assert "fact A" in combined
    assert "fact B" in combined
    assert "left/outputs" in combined


def test_example_content_diff_metadata_differ():
    left = _make_scenario()
    right = {
        **_make_scenario(),
        "metadata": {"scenario_id": 1, "city": "Eugene", "state": "OR"},
    }
    combined = "".join(_example_content_diff(left, right))
    assert "left/metadata" in combined
    assert "Eugene" in combined


def test_example_content_diff_multiple_fields():
    left = _make_scenario(query="old")
    right = {
        **_make_scenario(query="new"),
        "outputs": {"facts": ["changed"], "reference_conversation": []},
    }
    combined = "".join(_example_content_diff(left, right))
    assert "left/inputs" in combined
    assert "left/outputs" in combined


# ── cmd_dataset_diff ──────────────────────────────────────────────────────────


def test_cmd_dataset_diff_no_differences(tmp_path, capsys):
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record()) + "\n")

    args = MagicMock()
    args.left = f
    args.right = f

    with patch("evaluate.langsmith_dataset.make_client", return_value=MagicMock()):
        cmd_dataset_diff(args)

    assert "No differences." in capsys.readouterr().out


def test_cmd_dataset_diff_invalid_file_exits(tmp_path, capsys):
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps({"metadata": {"scenario_id": 1}, "outputs": {}}) + "\n")

    args = MagicMock()
    args.left = f
    args.right = f

    with patch("evaluate.langsmith_dataset.make_client", return_value=MagicMock()):
        with pytest.raises(SystemExit) as exc:
            cmd_dataset_diff(args)
    assert exc.value.code == 1
    assert "Line 1" in capsys.readouterr().err


def test_cmd_dataset_diff_existence_only(tmp_path, capsys):
    left_file = tmp_path / "left.jsonl"
    right_file = tmp_path / "right.jsonl"
    left_file.write_text(json.dumps(_make_valid_record(1)) + "\n")
    right_file.write_text(json.dumps(_make_valid_record(2)) + "\n")

    args = MagicMock()
    args.left = left_file
    args.right = right_file

    with patch("evaluate.langsmith_dataset.make_client", return_value=MagicMock()):
        cmd_dataset_diff(args)

    out = capsys.readouterr().out
    assert "< scenario_id=1" in out
    assert "> scenario_id=2" in out


def test_cmd_dataset_diff_content_change(tmp_path, capsys):
    left_record = _make_valid_record(1)
    right_record = _make_valid_record(1)
    right_record["inputs"]["query"] = "updated question"

    left_file = tmp_path / "left.jsonl"
    right_file = tmp_path / "right.jsonl"
    left_file.write_text(json.dumps(left_record) + "\n")
    right_file.write_text(json.dumps(right_record) + "\n")

    args = MagicMock()
    args.left = left_file
    args.right = right_file

    with patch("evaluate.langsmith_dataset.make_client", return_value=MagicMock()):
        cmd_dataset_diff(args)

    out = capsys.readouterr().out
    assert "~ scenario_id=1" in out
    assert "[content differs]" in out
    assert "updated question" in out


def test_cmd_dataset_diff_mixed(tmp_path, capsys):
    """Left-only, right-only, and content-changed scenarios all appear together."""
    only_left = _make_valid_record(1)
    changed_left = _make_valid_record(2)
    changed_right = _make_valid_record(2)
    changed_right["inputs"]["query"] = "changed"
    only_right = _make_valid_record(3)

    left_file = tmp_path / "left.jsonl"
    right_file = tmp_path / "right.jsonl"
    left_file.write_text(json.dumps(only_left) + "\n" + json.dumps(changed_left) + "\n")
    right_file.write_text(
        json.dumps(changed_right) + "\n" + json.dumps(only_right) + "\n"
    )

    args = MagicMock()
    args.left = left_file
    args.right = right_file

    with patch("evaluate.langsmith_dataset.make_client", return_value=MagicMock()):
        cmd_dataset_diff(args)

    out = capsys.readouterr().out
    assert "< scenario_id=1" in out
    assert "~ scenario_id=2" in out
    assert "> scenario_id=3" in out


# ── property-based tests ───────────────────────────────────────────────────────

# JSON-serializable values: booleans must come before integers in st.one_of
# because bool is a subclass of int and Hypothesis would otherwise generate
# True/False as integers.
#
# Surrogate characters (Unicode category Cs, U+D800–U+DFFF) are excluded from
# all text strategies: json.dumps raises UnicodeEncodeError for lone surrogates,
# so they would abort the test before reaching the assertion.
_json_text = st.text(alphabet=st.characters(blacklist_categories=("Cs",)))
_json_primitive = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    _json_text,
)
_json_value = st.recursive(
    _json_primitive,
    lambda children: st.one_of(
        st.lists(children),
        st.dictionaries(_json_text, children),
    ),
    max_leaves=10,
)
# Use a direct dict strategy rather than filtering _json_value, which would
# reject most generated values (primitives/lists) and trigger filter_too_much.
_json_dict = st.dictionaries(_json_text, _json_value)


@pytest.mark.property
@given(records=st.lists(_json_dict, max_size=20))
@settings(max_examples=200)
def test_read_jsonl_roundtrip(records):
    """Any list of dicts written as JSONL should parse back to the same list."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in records))
        tmp = Path(fh.name)
    try:
        assert _read_jsonl(tmp) == records
    finally:
        tmp.unlink()


@pytest.mark.property
@given(
    before=st.text(alphabet=st.characters(exclude_characters="<>")),
    rubric=st.text(alphabet=st.characters(exclude_characters="<>")),
    after=st.text(alphabet=st.characters(exclude_characters="<>")),
)
def test_extract_rubric_roundtrip(before, rubric, after):
    """Any text wrapped in <Rubric> tags should be extractable."""
    text = f"{before}<Rubric>\n{rubric}\n</Rubric>{after}"
    result = _extract_rubric(text)
    assert result == rubric.strip() + "\n"


@pytest.mark.property
@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",))))
def test_local_or_remote_classification(value):
    """Strings ending in .jsonl always return Path; all others return str."""
    result = local_or_remote(value)
    if value.endswith(".jsonl"):
        assert isinstance(result, Path)
    else:
        assert isinstance(result, str)


# ── _experiment_scores ─────────────────────────────────────────────────────────


def _make_run(run_id=None, example_id=None, query=None):
    r = MagicMock()
    r.id = run_id or uuid4()
    r.reference_example_id = example_id or uuid4()
    r.inputs = {"query": query or ""}
    return r


def _make_example(example_id, scenario_id):
    ex = MagicMock()
    ex.id = example_id
    ex.metadata = {"scenario_id": scenario_id}
    return ex


def _make_feedback(run_id, key, score):
    fb = MagicMock()
    fb.run_id = run_id
    fb.key = key
    fb.score = score
    return fb


def test_experiment_scores_no_runs():
    client = MagicMock()
    client.list_runs.return_value = []
    count, scores = _experiment_scores(client, "proj-id")
    assert count == 0
    assert scores == {}


def test_experiment_scores_aggregates_mean_and_pstdev():
    run = _make_run()
    client = MagicMock()
    client.list_runs.return_value = [run]
    client.list_feedback.return_value = [
        _make_feedback(run.id, "legal correctness", 1.0),
        _make_feedback(run.id, "legal correctness", 0.5),
        _make_feedback(run.id, "legal correctness", 0.5),
    ]
    count, scores = _experiment_scores(client, "proj-id")
    assert count == 1
    mean, std = scores["legal correctness"]
    assert round(mean, 4) == round(2.0 / 3.0, 4)
    assert std > 0


def test_experiment_scores_ignores_none_score():
    run = _make_run()
    client = MagicMock()
    client.list_runs.return_value = [run]
    client.list_feedback.return_value = [
        _make_feedback(run.id, "tone", None),
        _make_feedback(run.id, "tone", 1.0),
    ]
    _, scores = _experiment_scores(client, "proj-id")
    mean, _ = scores["tone"]
    assert mean == 1.0


def test_experiment_scores_multiple_evaluator_keys():
    run = _make_run()
    client = MagicMock()
    client.list_runs.return_value = [run]
    client.list_feedback.return_value = [
        _make_feedback(run.id, "legal correctness", 1.0),
        _make_feedback(run.id, "tone", 0.5),
    ]
    _, scores = _experiment_scores(client, "proj-id")
    assert set(scores.keys()) == {"legal correctness", "tone"}


# ── cmd_experiment_show ────────────────────────────────────────────────────────


def _make_project(proj_name: str, proj_id: str = "proj-id"):
    """MagicMock project with a real .name attribute (name= is reserved in MagicMock)."""
    p = MagicMock()
    p.name = proj_name
    p.id = proj_id
    p.start_time = None
    p.end_time = None
    return p


def test_cmd_experiment_show_outputs_json(capsys):
    run = _make_run()
    mock_client = MagicMock()
    mock_client.read_project.return_value = _make_project("my-exp")
    mock_client.list_runs.return_value = [run]
    mock_client.list_feedback.return_value = [
        _make_feedback(run.id, "legal correctness", 1.0),
    ]

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        args = MagicMock(experiment="my-exp")
        cmd_experiment_show(args)

    out = json.loads(capsys.readouterr().out)
    assert out["run_count"] == 1
    assert "legal correctness" in out["feedback_stats"]
    assert "mean" in out["feedback_stats"]["legal correctness"]
    assert "std" in out["feedback_stats"]["legal correctness"]


# ── cmd_experiment_compare ─────────────────────────────────────────────────────


def _mock_client_for_compare(runs1, feedback1, runs2, feedback2):
    """Return a client whose list_runs/list_feedback alternate between two experiments."""
    client = MagicMock()
    client.read_project.side_effect = [_make_project("exp-A"), _make_project("exp-B")]
    client.list_runs.side_effect = [runs1, runs2]
    client.list_feedback.side_effect = [feedback1, feedback2]
    return client


def test_cmd_experiment_compare_shows_run_counts(capsys):
    r1, r2 = _make_run(), _make_run()
    client = _mock_client_for_compare(
        [r1],
        [_make_feedback(r1.id, "tone", 1.0)],
        [r2],
        [_make_feedback(r2.id, "tone", 0.5)],
    )
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        args = MagicMock(experiment1="exp-A", experiment2="exp-B")
        cmd_experiment_compare(args)

    out = capsys.readouterr().out
    assert "runs" in out
    assert "1" in out


def test_cmd_experiment_compare_shows_evaluator_scores(capsys):
    r1, r2 = _make_run(), _make_run()
    client = _mock_client_for_compare(
        [r1],
        [_make_feedback(r1.id, "legal correctness", 1.0)],
        [r2],
        [_make_feedback(r2.id, "legal correctness", 0.5)],
    )
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        args = MagicMock(experiment1="exp-A", experiment2="exp-B")
        cmd_experiment_compare(args)

    out = capsys.readouterr().out
    assert "legal correctness" in out
    assert "100.0%" in out
    assert "50.0%" in out


def test_cmd_experiment_compare_shows_sigma(capsys):
    r1, r2 = _make_run(), _make_run()
    client = _mock_client_for_compare(
        [r1],
        [_make_feedback(r1.id, "tone", 1.0), _make_feedback(r1.id, "tone", 0.5)],
        [r2],
        [_make_feedback(r2.id, "tone", 1.0)],
    )
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        args = MagicMock(experiment1="exp-A", experiment2="exp-B")
        cmd_experiment_compare(args)

    assert "σ=" in capsys.readouterr().out


def test_cmd_experiment_compare_missing_key_shows_dash(capsys):
    r1, r2 = _make_run(), _make_run()
    client = _mock_client_for_compare(
        [r1],
        [_make_feedback(r1.id, "legal correctness", 1.0)],
        [r2],
        [],  # exp-B has no feedback
    )
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        args = MagicMock(experiment1="exp-A", experiment2="exp-B")
        cmd_experiment_compare(args)

    assert "—" in capsys.readouterr().out


# ── cmd_experiment_stats ────────────────────────────────────────────────────────


def _mock_client_for_stats(runs, feedback, examples):
    """Build a mock LangSmith client for cmd_experiment_stats tests."""
    client = MagicMock()
    p = MagicMock()
    p.id = "proj-id"
    client.read_project.return_value = p
    client.list_runs.return_value = iter(runs)
    client.list_feedback.return_value = iter(feedback)
    client.list_examples.return_value = iter(examples)
    return client


def test_cmd_experiment_stats_no_runs(capsys):
    """Stats command prints a message and exits cleanly when no runs exist."""
    client = _mock_client_for_stats([], [], [])
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_experiment_stats(MagicMock(experiment="exp", evaluator=[]))
    assert "No runs found" in capsys.readouterr().out


def test_cmd_experiment_stats_sorted_by_scenario_id(capsys):
    """Scenarios appear sorted by scenario_id, not insertion order."""
    ex_id_a, ex_id_b = uuid4(), uuid4()
    r_a = _make_run(example_id=ex_id_a, query="question A")
    r_b = _make_run(example_id=ex_id_b, query="question B")
    fb_a = _make_feedback(r_a.id, "tone", 1.0)
    fb_b = _make_feedback(r_b.id, "tone", 0.5)
    # example B has lower scenario_id (3) than example A (7) — B should sort first.
    examples = [_make_example(ex_id_a, 7), _make_example(ex_id_b, 3)]

    client = _mock_client_for_stats([r_b, r_a], [fb_b, fb_a], examples)
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_experiment_stats(MagicMock(experiment="exp", evaluator=[]))

    out = capsys.readouterr().out
    # S1 should correspond to scenario_id=3 (question B), S2 to scenario_id=7 (question A).
    assert out.index("question B") < out.index("question A")


def test_cmd_experiment_stats_label_includes_scenario_id(capsys):
    """Each scenario label includes the dataset scenario_id in brackets."""
    ex_id = uuid4()
    run = _make_run(example_id=ex_id, query="Can my landlord enter?")
    fb = _make_feedback(run.id, "tone", 1.0)
    examples = [_make_example(ex_id, 42)]

    client = _mock_client_for_stats([run], [fb], examples)
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_experiment_stats(MagicMock(experiment="exp", evaluator=[]))

    assert "S42" in capsys.readouterr().out


def test_cmd_experiment_stats_evaluator_filter(capsys):
    """The --evaluator flag restricts which evaluator tables are printed."""
    ex_id = uuid4()
    run = _make_run(example_id=ex_id, query="eviction question")
    feedback = [
        _make_feedback(run.id, "tone", 1.0),
        _make_feedback(run.id, "legal correctness", 0.5),
    ]
    examples = [_make_example(ex_id, 1)]

    client = _mock_client_for_stats([run], feedback, examples)
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_experiment_stats(MagicMock(experiment="exp", evaluator=["tone"]))

    out = capsys.readouterr().out
    assert "tone" in out
    assert "legal correctness" not in out


# ── cmd_run_exemplars ──────────────────────────────────────────────────────────


def _mock_client_for_exemplars(runs, feedback, examples):
    """Build a mock LangSmith client for cmd_run_exemplars tests."""
    client = MagicMock()
    p = MagicMock()
    p.id = "proj-id"
    client.read_project.return_value = p
    client.list_runs.return_value = iter(runs)
    client.list_feedback.return_value = iter(feedback)
    client.list_examples.return_value = iter(examples)
    return client


def test_cmd_run_exemplars_no_runs(capsys):
    """Prints a message and exits cleanly when no runs exist."""
    client = _mock_client_for_exemplars([], [], [])
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_exemplars(
            MagicMock(
                experiment="exp",
                scenario_id=1,
                evaluator="legal correctness",
                no_header=False,
            )
        )
    assert "No runs found" in capsys.readouterr().out


def test_cmd_run_exemplars_no_runs_for_scenario(capsys):
    """Prints a message when no runs match the requested scenario_id."""
    ex_id = uuid4()
    run = _make_run(example_id=ex_id)
    example = _make_example(ex_id, scenario_id=2)
    feedback = [_make_feedback(run.id, "legal correctness", 1.0)]
    client = _mock_client_for_exemplars([run], feedback, [example])
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_exemplars(
            MagicMock(
                experiment="exp",
                scenario_id=99,
                evaluator="legal correctness",
                no_header=False,
            )
        )
    assert "No runs found for scenario_id=99" in capsys.readouterr().out


def test_cmd_run_exemplars_filters_to_scenario(capsys):
    """Only runs belonging to the requested scenario_id appear in output."""
    ex_id_a, ex_id_b = uuid4(), uuid4()
    run_a = _make_run(example_id=ex_id_a, query="scenario 1 question")
    run_b = _make_run(example_id=ex_id_b, query="scenario 2 question")
    examples = [_make_example(ex_id_a, 1), _make_example(ex_id_b, 2)]
    feedback = [
        _make_feedback(run_a.id, "legal correctness", 0.5),
        _make_feedback(run_b.id, "legal correctness", 1.0),
    ]
    client = _mock_client_for_exemplars([run_a, run_b], feedback, examples)
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_exemplars(
            MagicMock(
                experiment="exp",
                scenario_id=1,
                evaluator="legal correctness",
                no_header=True,
            )
        )
    out = capsys.readouterr().out
    assert "scenario 1 question" in out
    assert "scenario 2 question" not in out


def test_cmd_run_exemplars_sorted_worst_to_best(capsys):
    """Runs are printed sorted from lowest to highest evaluator score."""
    ex_id = uuid4()
    run_low = _make_run(example_id=ex_id, query="low score run")
    run_high = _make_run(example_id=ex_id, query="high score run")
    example = _make_example(ex_id, 1)
    feedback = [
        _make_feedback(run_low.id, "legal correctness", 0.0),
        _make_feedback(run_high.id, "legal correctness", 1.0),
    ]
    # Pass high-score run first to confirm sorting is not insertion order.
    client = _mock_client_for_exemplars([run_high, run_low], feedback, [example])
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_exemplars(
            MagicMock(
                experiment="exp",
                scenario_id=1,
                evaluator="legal correctness",
                no_header=True,
            )
        )
    out = capsys.readouterr().out
    assert out.index("low score run") < out.index("high score run")


def test_cmd_run_exemplars_missing_feedback_shows_na(capsys):
    """A run with no feedback for the requested evaluator shows 'N/A' as the score."""
    ex_id = uuid4()
    run = _make_run(example_id=ex_id, query="unevaluated run")
    example = _make_example(ex_id, 1)
    client = _mock_client_for_exemplars([run], [], [example])
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_exemplars(
            MagicMock(
                experiment="exp",
                scenario_id=1,
                evaluator="legal correctness",
                no_header=True,
            )
        )
    assert "N/A" in capsys.readouterr().out


def test_cmd_run_exemplars_truncates_long_query(capsys):
    """Queries longer than 60 characters are truncated with an ellipsis."""
    ex_id = uuid4()
    long_query = "A" * 70
    run = _make_run(example_id=ex_id, query=long_query)
    example = _make_example(ex_id, 1)
    feedback = [_make_feedback(run.id, "legal correctness", 0.5)]
    client = _mock_client_for_exemplars([run], feedback, [example])
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_exemplars(
            MagicMock(
                experiment="exp",
                scenario_id=1,
                evaluator="legal correctness",
                no_header=True,
            )
        )
    out = capsys.readouterr().out
    assert "…" in out
    assert long_query not in out


def test_cmd_run_exemplars_no_header_suppresses_headers(capsys):
    """The --no-header flag omits the column header row."""
    ex_id = uuid4()
    run = _make_run(example_id=ex_id, query="question")
    example = _make_example(ex_id, 1)
    feedback = [_make_feedback(run.id, "legal correctness", 1.0)]
    client = _mock_client_for_exemplars([run], feedback, [example])
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_exemplars(
            MagicMock(
                experiment="exp",
                scenario_id=1,
                evaluator="legal correctness",
                no_header=True,
            )
        )
    assert "RUN UUID" not in capsys.readouterr().out


# ── cmd_run_show ───────────────────────────────────────────────────────────────


def test_cmd_run_show_single_uuid(capsys):
    """Prints JSON for a single run UUID."""
    run_id = uuid4()
    mock_run = MagicMock()
    mock_run.id = run_id
    mock_run.name = "Target"
    mock_run.status = "success"
    mock_run.inputs = {"query": "test"}
    mock_run.outputs = {"answer": "42"}
    mock_run.error = None

    client = MagicMock()
    client.read_run.return_value = mock_run
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_show(MagicMock(run_id=[str(run_id)]))

    out = json.loads(capsys.readouterr().out)
    assert out["id"] == str(run_id)
    assert out["name"] == "Target"
    assert out["inputs"] == {"query": "test"}


def test_cmd_run_show_multiple_uuids(capsys):
    """Prints one JSON object per UUID when multiple are given."""
    id_a, id_b = uuid4(), uuid4()

    def _mock_read_run(run_id):
        r = MagicMock()
        r.id = run_id
        r.name = f"run-{run_id}"
        r.status = "success"
        r.inputs = {}
        r.outputs = {}
        r.error = None
        return r

    client = MagicMock()
    client.read_run.side_effect = _mock_read_run
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_show(MagicMock(run_id=[str(id_a), str(id_b)]))

    capsys.readouterr()
    # Two separate JSON objects means read_run was called twice.
    assert client.read_run.call_count == 2


# ── cmd_run_trace ──────────────────────────────────────────────────────────────


def _make_trace_run(name="root", run_type="chain", status="success", child_runs=None):
    """Build a minimal mock run for cmd_run_trace tests."""
    r = MagicMock()
    r.name = name
    r.run_type = run_type
    r.status = status
    r.child_runs = child_runs or []
    r.inputs = {}
    r.outputs = {}
    return r


def test_cmd_run_trace_non_verbose_prints_name_and_type(capsys):
    """Without --verbose, only the name, run_type, and status are printed."""
    run = _make_trace_run(name="my-chain", run_type="chain", status="success")
    client = MagicMock()
    client.read_run.return_value = run
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_trace(MagicMock(run_id=str(uuid4()), verbose=False))
    out = capsys.readouterr().out
    assert "my-chain" in out
    assert "chain" in out
    assert "success" in out


def test_cmd_run_trace_non_verbose_omits_inputs_outputs(capsys):
    """Without --verbose, tool inputs/outputs are not printed."""
    tool_run = _make_trace_run(name="retrieve", run_type="tool", status="success")
    tool_run.inputs = {"query": "eviction notice"}
    tool_run.outputs = {"output": "ORS 90.394 text"}
    client = MagicMock()
    client.read_run.return_value = tool_run
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_trace(MagicMock(run_id=str(uuid4()), verbose=False))
    out = capsys.readouterr().out
    assert "eviction notice" not in out
    assert "ORS 90.394" not in out


def test_cmd_run_trace_verbose_prints_tool_inputs(capsys):
    """With --verbose, tool run inputs are printed with 'in' prefix."""
    tool_run = _make_trace_run(name="retrieve", run_type="tool", status="success")
    tool_run.inputs = {"query": "eviction notice"}
    tool_run.outputs = {"output": "ORS 90.394 text"}
    client = MagicMock()
    client.read_run.return_value = tool_run
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_trace(MagicMock(run_id=str(uuid4()), verbose=True))
    out = capsys.readouterr().out
    assert "in  query" in out
    assert "eviction notice" in out


def test_cmd_run_trace_verbose_prints_tool_output(capsys):
    """With --verbose, tool run output is printed with 'out' prefix."""
    tool_run = _make_trace_run(name="retrieve", run_type="tool", status="success")
    tool_run.inputs = {}
    tool_run.outputs = {"output": "ORS 90.394 text"}
    client = MagicMock()
    client.read_run.return_value = tool_run
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_trace(MagicMock(run_id=str(uuid4()), verbose=True))
    out = capsys.readouterr().out
    assert "out" in out
    assert "ORS 90.394 text" in out


def test_cmd_run_trace_verbose_prints_llm_generation(capsys):
    """With --verbose, LLM run output generations are printed."""
    llm_run = _make_trace_run(name="ChatVertexAI", run_type="llm", status="success")
    llm_run.inputs = {}
    llm_run.outputs = {
        "generations": [[{"text": "You are protected under ORS 90.453."}]]
    }
    client = MagicMock()
    client.read_run.return_value = llm_run
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_trace(MagicMock(run_id=str(uuid4()), verbose=True))
    out = capsys.readouterr().out
    assert "ORS 90.453" in out


def test_cmd_run_trace_verbose_recurses_into_child_runs(capsys):
    """With --verbose, child runs are printed indented below the parent."""
    child = _make_trace_run(name="child-tool", run_type="tool", status="success")
    child.inputs = {"query": "child input"}
    child.outputs = {"output": "child output"}
    parent = _make_trace_run(
        name="parent-chain", run_type="chain", status="success", child_runs=[child]
    )
    client = MagicMock()
    client.read_run.return_value = parent
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_run_trace(MagicMock(run_id=str(uuid4()), verbose=True))
    out = capsys.readouterr().out
    assert "parent-chain" in out
    assert "child-tool" in out
    assert "child input" in out


# ── _collect_tool_responses_by_run ────────────────────────────────────────────


def _make_root_run(run_id, example_id):
    run = MagicMock()
    run.id = run_id
    run.reference_example_id = example_id
    return run


def _make_tool_run(trace_id, output_text):
    run = MagicMock()
    run.trace_id = trace_id
    run.outputs = {"output": output_text}
    return run


def test_collect_tool_responses_groups_by_run():
    """Responses are grouped under their root run ID, tagged with the example ID."""
    root_id = uuid4()
    example_id = uuid4()
    client = MagicMock()
    client.read_project.return_value = MagicMock(id=uuid4())
    client.list_runs.side_effect = [
        [_make_root_run(root_id, example_id)],
        [_make_tool_run(root_id, "ORS 90.425 text here")],
    ]
    result = _collect_tool_responses_by_run(client, "exp-name")
    assert str(root_id) in result
    assert result[str(root_id)]["example_id"] == str(example_id)
    assert result[str(root_id)]["responses"] == ["ORS 90.425 text here"]


def test_collect_tool_responses_multiple_calls_same_run():
    """Multiple tool calls within the same repetition are all collected."""
    root_id = uuid4()
    example_id = uuid4()
    client = MagicMock()
    client.read_project.return_value = MagicMock(id=uuid4())
    client.list_runs.side_effect = [
        [_make_root_run(root_id, example_id)],
        [
            _make_tool_run(root_id, "first response"),
            _make_tool_run(root_id, "second response"),
        ],
    ]
    result = _collect_tool_responses_by_run(client, "exp-name")
    assert len(result[str(root_id)]["responses"]) == 2


def test_collect_tool_responses_separates_repetitions_of_same_example():
    """Two repetitions of the same example are kept as distinct entries."""
    root_id_a = uuid4()
    root_id_b = uuid4()
    example_id = uuid4()
    client = MagicMock()
    client.read_project.return_value = MagicMock(id=uuid4())
    client.list_runs.side_effect = [
        [
            _make_root_run(root_id_a, example_id),
            _make_root_run(root_id_b, example_id),
        ],
        [
            _make_tool_run(root_id_a, "rep A response"),
            _make_tool_run(root_id_b, "rep B response"),
        ],
    ]
    result = _collect_tool_responses_by_run(client, "exp-name")
    assert len(result) == 2
    assert result[str(root_id_a)]["example_id"] == str(example_id)
    assert result[str(root_id_b)]["example_id"] == str(example_id)


def test_collect_tool_responses_skips_unmatched_trace_id():
    """Tool runs whose trace_id has no matching root run are ignored."""
    root_id = uuid4()
    example_id = uuid4()
    orphan_id = uuid4()
    client = MagicMock()
    client.read_project.return_value = MagicMock(id=uuid4())
    client.list_runs.side_effect = [
        [_make_root_run(root_id, example_id)],
        [
            _make_tool_run(root_id, "matched response"),
            _make_tool_run(orphan_id, "unmatched response"),
        ],
    ]
    result = _collect_tool_responses_by_run(client, "exp-name")
    assert len(result) == 1
    assert result[str(root_id)]["responses"] == ["matched response"]


def test_collect_tool_responses_skips_empty_output():
    """Tool runs with empty or missing output text are skipped."""
    root_id = uuid4()
    example_id = uuid4()
    empty_run = _make_tool_run(root_id, "")
    empty_run.outputs = {}
    client = MagicMock()
    client.read_project.return_value = MagicMock(id=uuid4())
    client.list_runs.side_effect = [
        [_make_root_run(root_id, example_id)],
        [empty_run],
    ]
    result = _collect_tool_responses_by_run(client, "exp-name")
    assert result == {}


def test_collect_tool_responses_accepts_content_key():
    """Output stored under 'content' key (fallback) is also captured."""
    root_id = uuid4()
    example_id = uuid4()
    run = _make_tool_run(root_id, "")
    run.outputs = {"content": "ORS 90.325 content"}
    client = MagicMock()
    client.read_project.return_value = MagicMock(id=uuid4())
    client.list_runs.side_effect = [
        [_make_root_run(root_id, example_id)],
        [run],
    ]
    result = _collect_tool_responses_by_run(client, "exp-name")
    assert result[str(root_id)]["responses"] == ["ORS 90.325 content"]


# ── _check_retrieval_from_traces ───────────────────────────────────────────────


def _make_stopgap(label: str, targets: list[str]) -> dict:
    return {"label": label, "targets": targets}


def _make_run_entry(example_id: str, responses: list[str]) -> dict:
    return {"example_id": example_id, "responses": responses}


def test_check_retrieval_retirement_candidate(caplog):
    """Every relevant repetition contains the target text → retirement candidate."""
    import logging

    eid = str(uuid4())
    stopgaps = [_make_stopgap("ORS 90.425 personal property", ["landlord must give a written notice"])]
    runs_by_id = {
        str(uuid4()): _make_run_entry(eid, ["...landlord must give a written notice to the tenant..."])
    }
    facts_by_example = {eid: ["Question pertains to ORS 90.425"]}
    with caplog.at_level(logging.INFO):
        _check_retrieval_from_traces(stopgaps, runs_by_id, facts_by_example, logging.getLogger("test_retrieval"))
    assert any("retirement candidate" in r.message for r in caplog.records)


def test_check_retrieval_never_retrieved(caplog):
    """No relevant repetition contains the target text → never retrieved."""
    import logging

    eid = str(uuid4())
    stopgaps = [_make_stopgap("ORS 90.425 personal property", ["landlord must give a written notice"])]
    runs_by_id = {str(uuid4()): _make_run_entry(eid, ["completely unrelated retrieved text about rent"])}
    facts_by_example = {eid: ["Question pertains to ORS 90.425"]}
    with caplog.at_level(logging.INFO):
        _check_retrieval_from_traces(stopgaps, runs_by_id, facts_by_example, logging.getLogger("test_retrieval"))
    assert any("never retrieved" in r.message for r in caplog.records)


def test_check_retrieval_partially_retrieved(caplog):
    """Some but not all repetitions of a relevant scenario hit → partially retrieved."""
    import logging

    eid = str(uuid4())
    stopgaps = [_make_stopgap("ORS 90.425 personal property", ["landlord must give a written notice"])]
    # Two repetitions of the same scenario; one retrieves the target, one does not.
    runs_by_id = {
        str(uuid4()): _make_run_entry(eid, ["...landlord must give a written notice..."]),
        str(uuid4()): _make_run_entry(eid, ["unrelated text about security deposits"]),
    }
    facts_by_example = {eid: ["Question pertains to ORS 90.425"]}
    with caplog.at_level(logging.INFO):
        _check_retrieval_from_traces(stopgaps, runs_by_id, facts_by_example, logging.getLogger("test_retrieval"))
    assert any("partially retrieved" in r.message for r in caplog.records)
    assert any("1/2" in r.message for r in caplog.records)


def test_check_retrieval_counts_each_repetition_once(caplog):
    """A repetition with multiple tool calls counts as one hit if any call matches."""
    import logging

    eid = str(uuid4())
    stopgaps = [_make_stopgap("ORS 90.425 personal property", ["landlord must give a written notice"])]
    # A single repetition made two RAG calls; the target appears in only one.
    runs_by_id = {
        str(uuid4()): _make_run_entry(
            eid,
            ["miss on this call", "...landlord must give a written notice..."],
        )
    }
    facts_by_example = {eid: ["Question pertains to ORS 90.425"]}
    with caplog.at_level(logging.INFO):
        _check_retrieval_from_traces(stopgaps, runs_by_id, facts_by_example, logging.getLogger("test_retrieval"))
    # One repetition, one hit — not 1/2 across the two tool calls.
    assert any("retirement candidate" in r.message for r in caplog.records)
    assert any("1/1" in r.message for r in caplog.records)


def test_check_retrieval_filters_to_relevant_examples(caplog):
    """Repetitions of examples whose facts don't mention the ORS are excluded."""
    import logging

    relevant_eid = str(uuid4())
    irrelevant_eid = str(uuid4())
    stopgaps = [_make_stopgap("ORS 90.425 personal property", ["landlord must give a written notice"])]
    runs_by_id = {
        str(uuid4()): _make_run_entry(relevant_eid, ["...landlord must give a written notice..."]),
        str(uuid4()): _make_run_entry(irrelevant_eid, ["unrelated text"]),
    }
    facts_by_example = {
        relevant_eid: ["Question pertains to ORS 90.425"],
        irrelevant_eid: ["Question pertains to ORS 90.394"],
    }
    with caplog.at_level(logging.INFO):
        _check_retrieval_from_traces(stopgaps, runs_by_id, facts_by_example, logging.getLogger("test_retrieval"))
    # The irrelevant repetition missed, but it's excluded — only the relevant one counts.
    assert any("retirement candidate" in r.message for r in caplog.records)
    assert any("1/1" in r.message for r in caplog.records)


def test_check_retrieval_no_relevant_scenarios(caplog):
    """No examples whose facts mention the ORS → logs 'no relevant scenarios'."""
    import logging

    eid = str(uuid4())
    stopgaps = [_make_stopgap("ORS 90.425 personal property", ["landlord must give a written notice"])]
    runs_by_id = {str(uuid4()): _make_run_entry(eid, ["some retrieved text"])}
    facts_by_example = {eid: ["Question pertains to ORS 90.394"]}
    with caplog.at_level(logging.INFO):
        _check_retrieval_from_traces(stopgaps, runs_by_id, facts_by_example, logging.getLogger("test_retrieval"))
    assert any("no relevant scenarios" in r.message for r in caplog.records)


def test_check_retrieval_normalizes_whitespace(caplog):
    """Target phrase with internal newlines in corpus text still matches."""
    import logging

    eid = str(uuid4())
    stopgaps = [_make_stopgap("ORS 90.425 personal property", ["landlord must give a written notice"])]
    # Corpus text has a line break in the middle of the target phrase.
    runs_by_id = {str(uuid4()): _make_run_entry(eid, ["...landlord must give a written\nnotice to the tenant..."])}
    facts_by_example = {eid: ["Question pertains to ORS 90.425"]}
    with caplog.at_level(logging.INFO):
        _check_retrieval_from_traces(stopgaps, runs_by_id, facts_by_example, logging.getLogger("test_retrieval"))
    assert any("retirement candidate" in r.message for r in caplog.records)


def test_check_retrieval_empty_runs_does_not_raise(caplog):
    """Empty runs_by_id is handled gracefully without raising."""
    import logging

    stopgaps = [_make_stopgap("ORS 90.425 personal property", ["some target"])]
    with caplog.at_level(logging.INFO):
        _check_retrieval_from_traces(stopgaps, {}, {}, logging.getLogger("test_retrieval"))
    # No relevant repetitions exist, so the STOPGAP is reported as having no coverage.
    assert any("no relevant scenarios" in r.message for r in caplog.records)


def test_check_retrieval_returns_coverage_gap():
    """A STOPGAP with no relevant repetitions makes the function report a coverage gap."""
    import logging

    eid = str(uuid4())
    stopgaps = [_make_stopgap("ORS 90.425 personal property", ["some target"])]
    runs_by_id = {str(uuid4()): _make_run_entry(eid, ["unrelated"])}
    facts_by_example = {eid: ["Question pertains to ORS 90.394"]}
    gap = _check_retrieval_from_traces(
        stopgaps, runs_by_id, facts_by_example, logging.getLogger("test_retrieval")
    )
    assert gap is True


def test_check_retrieval_no_coverage_gap_when_all_covered():
    """When every STOPGAP has relevant repetitions, no coverage gap is reported."""
    import logging

    eid = str(uuid4())
    stopgaps = [_make_stopgap("ORS 90.425 personal property", ["landlord must give"])]
    runs_by_id = {str(uuid4()): _make_run_entry(eid, ["landlord must give notice"])}
    facts_by_example = {eid: ["Question pertains to ORS 90.425"]}
    gap = _check_retrieval_from_traces(
        stopgaps, runs_by_id, facts_by_example, logging.getLogger("test_retrieval")
    )
    assert gap is False


# ── datastore short-circuit ───────────────────────────────────────────────────


def test_as_utc_naive_assumed_utc():
    """A naive datetime is treated as UTC."""
    from datetime import datetime, timezone

    dt = datetime(2026, 6, 1, 12, 0, 0)
    assert _as_utc(dt) == datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_as_utc_aware_converted():
    """An aware datetime is converted to UTC."""
    from datetime import datetime, timedelta, timezone

    dt = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=-7)))
    assert _as_utc(dt) == datetime(2026, 6, 1, 19, 0, 0, tzinfo=timezone.utc)


def test_experiment_latest_run_time_returns_max():
    """Returns the latest start_time across an experiment's root runs."""
    from datetime import datetime

    client = MagicMock()
    client.read_project.return_value = MagicMock(id=uuid4())
    r1 = MagicMock(start_time=datetime(2026, 6, 1, 10, 0, 0))
    r2 = MagicMock(start_time=datetime(2026, 6, 1, 11, 0, 0))
    client.list_runs.return_value = [r1, r2]
    assert _experiment_latest_run_time(client, "exp") == datetime(2026, 6, 1, 11, 0, 0)


def test_experiment_latest_run_time_none_when_no_runs():
    """Returns None when there are no root runs with start times."""
    client = MagicMock()
    client.read_project.return_value = MagicMock(id=uuid4())
    client.list_runs.return_value = []
    assert _experiment_latest_run_time(client, "exp") is None


def test_datastore_unchanged_true_when_ds_older_than_experiment():
    """Datastore last-update before the experiment ran → unchanged → True."""
    import logging
    from datetime import datetime

    client = MagicMock()
    with (
        patch(
            "evaluate.langsmith_dataset._experiment_latest_run_time",
            return_value=datetime(2026, 6, 10, 12, 0, 0),
        ),
        patch(
            "evaluate.langsmith_dataset._datastore_last_update_time",
            return_value=datetime(2026, 6, 1, 12, 0, 0),
        ),
    ):
        assert (
            _datastore_unchanged_since_experiment(client, "exp", logging.getLogger("t"))
            is True
        )


def test_datastore_unchanged_false_when_reindexed_after_experiment():
    """Datastore reindexed after the experiment ran → changed → False."""
    import logging
    from datetime import datetime

    client = MagicMock()
    with (
        patch(
            "evaluate.langsmith_dataset._experiment_latest_run_time",
            return_value=datetime(2026, 6, 1, 12, 0, 0),
        ),
        patch(
            "evaluate.langsmith_dataset._datastore_last_update_time",
            return_value=datetime(2026, 6, 10, 12, 0, 0),
        ),
    ):
        assert (
            _datastore_unchanged_since_experiment(client, "exp", logging.getLogger("t"))
            is False
        )


def test_datastore_unchanged_false_when_timing_unavailable():
    """Falls open (False) when either timestamp can't be determined."""
    import logging

    client = MagicMock()
    with (
        patch(
            "evaluate.langsmith_dataset._experiment_latest_run_time",
            return_value=None,
        ),
        patch(
            "evaluate.langsmith_dataset._datastore_last_update_time",
            return_value=None,
        ),
    ):
        assert (
            _datastore_unchanged_since_experiment(client, "exp", logging.getLogger("t"))
            is False
        )


# ── _message_text ──────────────────────────────────────────────────────────────


def test_message_text_plain_string():
    assert _message_text("hello") == "hello"


def test_message_text_joins_text_blocks():
    content = [{"type": "text", "text": "one"}, {"type": "text", "text": "two"}]
    assert _message_text(content) == "one\ntwo"


def test_message_text_drops_non_text_blocks():
    # Reasoning signatures and other structured payloads carry no "text" type.
    content = [
        {"type": "reasoning", "signature": "abc"},
        {"type": "text", "text": "kept"},
    ]
    assert _message_text(content) == "kept"


def test_message_text_non_string_non_list_returns_empty():
    assert _message_text(None) == ""
    assert _message_text({"type": "text", "text": "x"}) == ""


# ── _render_transcript ─────────────────────────────────────────────────────────


def test_render_transcript_bolds_roles():
    messages = [
        {"role": "human", "content": "hi"},
        {"role": "ai", "content": "hello"},
    ]
    out = _render_transcript(messages)
    assert "> **User:** hi" in out
    assert "> **Assistant:** hello" in out


def test_render_transcript_drops_tool_and_system_messages():
    messages = [
        {"role": "human", "content": "q"},
        {"role": "tool", "content": "RAG retrieval dump"},
        {"role": "system", "content": "you are a bot"},
        {"role": "ai", "content": "a"},
    ]
    out = _render_transcript(messages)
    assert "RAG retrieval dump" not in out
    assert "you are a bot" not in out
    assert "**User:** q" in out
    assert "**Assistant:** a" in out


def test_render_transcript_reads_type_key():
    # LangChain-serialised messages use "type" rather than "role".
    messages = [{"type": "human", "content": "hi"}]
    assert "> **User:** hi" in _render_transcript(messages)


def test_render_transcript_skips_empty_content():
    messages = [
        {"role": "human", "content": ""},
        {"role": "ai", "content": "only this"},
    ]
    out = _render_transcript(messages)
    assert "only this" in out
    assert "**User:**" not in out


def test_render_transcript_quotes_every_line():
    messages = [{"role": "ai", "content": "line1\nline2"}]
    out = _render_transcript(messages)
    assert "> **Assistant:** line1" in out
    assert "> line2" in out


def test_render_transcript_empty_messages():
    assert _render_transcript([]) == ""
    assert _render_transcript(None) == ""


# ── cmd_experiment_markdown ────────────────────────────────────────────────────


def _make_md_run(messages, city=None, state="or", start_time=None):
    r = MagicMock()
    r.id = uuid4()
    r.inputs = {"city": city, "state": state, "messages": messages}
    r.start_time = start_time or datetime(2026, 6, 20, tzinfo=timezone.utc)
    return r


def _md_args(file, *, days=RETENTION_DAYS, force=False, dry_run=False):
    return MagicMock(
        experiment="tenantfirstaid-prod",
        file=file,
        days=days,
        force=force,
        dry_run=dry_run,
    )


def _md_client(runs):
    client = MagicMock()
    client.read_project.return_value = _make_project("tenantfirstaid-prod", "proj-1")
    client.list_runs.return_value = runs
    return client


def test_cmd_experiment_markdown_writes_transcript(tmp_path):
    out = tmp_path / "traces.md"
    runs = [
        _make_md_run(
            [{"role": "human", "content": "Can I be evicted?"}],
            city="portland",
            state="or",
        )
    ]
    with patch("evaluate.langsmith_dataset.make_client", return_value=_md_client(runs)):
        cmd_experiment_markdown(_md_args(out))

    text = out.read_text()
    assert "# Traces from `tenantfirstaid-prod`" in text
    assert "## Example 1" in text
    assert "- **city:** `portland`" in text
    assert "- **state:** `or`" in text
    assert "> **User:** Can I be evicted?" in text


def test_cmd_experiment_markdown_drops_tool_messages(tmp_path):
    out = tmp_path / "traces.md"
    runs = [
        _make_md_run(
            [
                {"role": "human", "content": "q"},
                {"role": "tool", "content": "internal RAG payload"},
                {"role": "ai", "content": "a"},
            ]
        )
    ]
    with patch("evaluate.langsmith_dataset.make_client", return_value=_md_client(runs)):
        cmd_experiment_markdown(_md_args(out))

    assert "internal RAG payload" not in out.read_text()


def test_cmd_experiment_markdown_dry_run_does_not_write(tmp_path, capsys):
    out = tmp_path / "traces.md"
    runs = [_make_md_run([{"role": "human", "content": "q"}])]
    with patch("evaluate.langsmith_dataset.make_client", return_value=_md_client(runs)):
        cmd_experiment_markdown(_md_args(out, dry_run=True))

    assert not out.exists()
    assert "Would write 1 examples" in capsys.readouterr().out


def test_cmd_experiment_markdown_respects_days(tmp_path):
    out = tmp_path / "traces.md"
    client = _md_client([_make_md_run([{"role": "human", "content": "q"}])])
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_experiment_markdown(_md_args(out, days=3))

    start_time = client.list_runs.call_args.kwargs["start_time"]
    expected = datetime.now(timezone.utc) - timedelta(days=3)
    assert abs((expected - start_time).total_seconds()) < 60
    assert "Window: last 3 days" in out.read_text()


def test_cmd_experiment_markdown_clamps_and_warns(tmp_path, capsys):
    out = tmp_path / "traces.md"
    client = _md_client([_make_md_run([{"role": "human", "content": "q"}])])
    with patch("evaluate.langsmith_dataset.make_client", return_value=client):
        cmd_experiment_markdown(_md_args(out, days=30))

    err = capsys.readouterr().err
    assert "exceeds" in err
    assert f"clamping to {RETENTION_DAYS}" in err

    start_time = client.list_runs.call_args.kwargs["start_time"]
    expected = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    assert abs((expected - start_time).total_seconds()) < 60
    assert f"Window: last {RETENTION_DAYS} days" in out.read_text()


def test_cmd_experiment_markdown_aborts_on_dirty_file(tmp_path, capsys):
    out = tmp_path / "traces.md"
    out.write_text("existing")
    with patch("evaluate.langsmith_dataset._git_is_clean", return_value=False):
        with pytest.raises(SystemExit):
            cmd_experiment_markdown(_md_args(out))

    assert "uncommitted changes" in capsys.readouterr().err
    assert out.read_text() == "existing"


def test_cmd_experiment_markdown_force_overwrites_dirty_file(tmp_path):
    out = tmp_path / "traces.md"
    out.write_text("existing")
    runs = [_make_md_run([{"role": "human", "content": "fresh"}])]
    with (
        patch("evaluate.langsmith_dataset._git_is_clean", return_value=False),
        patch("evaluate.langsmith_dataset.make_client", return_value=_md_client(runs)),
    ):
        cmd_experiment_markdown(_md_args(out, force=True))

    assert "fresh" in out.read_text()


# ── _scan_pii / _warn_pii ──────────────────────────────────────────────────────


def test_scan_pii_detects_common_categories():
    text = (
        "Reach me at jane.doe@example.com or 503-555-0142. "
        "SSN 123-45-6789, I live at 4220 SE Belmont Street."
    )
    findings = _scan_pii(text)
    assert findings["email"] == ["jane.doe@example.com"]
    assert findings["ssn"] == ["123-45-6789"]
    assert "phone" in findings
    assert "street_address" in findings


def test_scan_pii_clean_text_returns_empty():
    assert _scan_pii("Under ORS 90.427 a landlord must give notice.") == {}


def test_scan_pii_dedupes_matches():
    text = "a@b.com then again a@b.com"
    assert _scan_pii(text)["email"] == ["a@b.com"]


def test_scan_pii_picks_up_new_registry_entries():
    # New checks are added by extending the registry; _scan_pii should use them.
    import re as _re

    from evaluate import langsmith_dataset as mod

    with patch.dict(
        mod._PII_PATTERNS, {"zip5": _re.compile(r"\b\d{5}\b")}, clear=False
    ):
        assert _scan_pii("Portland 97214")["zip5"] == ["97214"]


def test_warn_pii_silent_when_no_findings(capsys):
    _warn_pii({}, Path("out.md"))
    assert capsys.readouterr().err == ""


def test_warn_pii_summarizes_findings(capsys):
    _warn_pii({"email": ["a@b.com", "c@d.com"]}, Path("out.md"))
    err = capsys.readouterr().err
    assert "out.md may contain PII" in err
    assert "email: 2 unique" in err


def test_warn_pii_truncates_long_match_lists(capsys):
    emails = [f"user{i}@example.com" for i in range(8)]
    _warn_pii({"email": emails}, Path("out.md"))
    err = capsys.readouterr().err
    assert "(+3 more)" in err


def test_cmd_experiment_markdown_warns_on_pii(tmp_path, capsys):
    out = tmp_path / "traces.md"
    runs = [
        _make_md_run([{"role": "human", "content": "Email me at tenant@example.com"}])
    ]
    with patch("evaluate.langsmith_dataset.make_client", return_value=_md_client(runs)):
        cmd_experiment_markdown(_md_args(out))

    err = capsys.readouterr().err
    assert "may contain PII" in err
    assert "tenant@example.com" in err
    # Warn-only: the file is still written.
    assert out.exists()


def test_cmd_experiment_markdown_no_pii_warning_when_clean(tmp_path, capsys):
    out = tmp_path / "traces.md"
    runs = [_make_md_run([{"role": "human", "content": "Can I be evicted?"}])]
    with patch("evaluate.langsmith_dataset.make_client", return_value=_md_client(runs)):
        cmd_experiment_markdown(_md_args(out))

    assert "may contain PII" not in capsys.readouterr().err
