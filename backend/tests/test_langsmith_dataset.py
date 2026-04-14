"""Tests for evaluate/langsmith_dataset.py."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from evaluate.langsmith_dataset import (
    _apply_dataset_schemas,
    _example_content_diff,
    _experiment_scores,
    _extract_rubric,
    _git_is_clean,
    _load_dataset_schemas,
    _load_examples,
    _read_jsonl,
    _scenario_id,
    _tabulate,
    _Validate,
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
    cmd_experiment_show,
    cmd_experiment_stats,
    cmd_run_exemplars,
    cmd_run_show,
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
_json_primitive = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(),
)
_json_value = st.recursive(
    _json_primitive,
    lambda children: st.one_of(
        st.lists(children),
        st.dictionaries(st.text(), children),
    ),
    max_leaves=10,
)


@pytest.mark.property
@given(records=st.lists(_json_value.filter(lambda v: isinstance(v, dict)), max_size=20))
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
@given(st.text())
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

    assert "[42]" in capsys.readouterr().out


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
