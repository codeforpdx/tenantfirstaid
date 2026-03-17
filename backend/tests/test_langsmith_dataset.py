"""Tests for evaluate/langsmith_dataset.py."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from evaluate.langsmith_dataset import (
    _extract_rubric,
    _read_jsonl,
    _scenario_id,
    _tabulate,
    build_parser,
    cmd_dataset_validate,
    cmd_scenario_show,
    cmd_scenario_update,
    local_or_remote,
)

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


# ── build_parser ───────────────────────────────────────────────────────────────


def test_parser_dataset_validate_defaults():
    from evaluate.langsmith_dataset import DEFAULT_JSONL, DEFAULT_SCHEMA

    parser = build_parser()
    args = parser.parse_args(["dataset", "validate"])
    assert args.file == DEFAULT_JSONL
    assert args.schema == DEFAULT_SCHEMA


def test_parser_scenario_update_routes_correctly():
    parser = build_parser()
    args = parser.parse_args(["scenario", "update", "42"])
    assert args.scenario_id == 42
    assert args.func.__name__ == "cmd_scenario_update"


def test_parser_scenario_update_accepts_custom_file(tmp_path):
    from evaluate.langsmith_dataset import DEFAULT_DATASET_NAME

    f = tmp_path / "custom.jsonl"
    f.write_text("")
    parser = build_parser()
    # dataset is an optional positional before scenario_id, so to specify file
    # the dataset name must be provided explicitly as well.
    args = parser.parse_args(["scenario", "update", DEFAULT_DATASET_NAME, "1", str(f)])
    assert args.scenario_id == 1
    assert args.file == f


def test_parser_dataset_push_defaults():
    from evaluate.langsmith_dataset import DEFAULT_DATASET_NAME, DEFAULT_JSONL

    parser = build_parser()
    args = parser.parse_args(["dataset", "push"])
    assert args.file == DEFAULT_JSONL
    assert args.remote == DEFAULT_DATASET_NAME


# ── cmd_dataset_validate ───────────────────────────────────────────────────────


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


def test_cmd_dataset_validate_valid_file(tmp_path):
    from evaluate.langsmith_dataset import DEFAULT_SCHEMA

    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record()) + "\n")

    args = MagicMock()
    args.file = f
    args.schema = DEFAULT_SCHEMA

    # Should not raise or call sys.exit.
    cmd_dataset_validate(args)


def test_cmd_dataset_validate_invalid_file_exits(tmp_path):
    from evaluate.langsmith_dataset import DEFAULT_SCHEMA

    f = tmp_path / "data.jsonl"
    # Missing required 'inputs' key.
    f.write_text(json.dumps({"metadata": {"scenario_id": 1}, "outputs": {}}) + "\n")

    args = MagicMock()
    args.file = f
    args.schema = DEFAULT_SCHEMA

    with pytest.raises(SystemExit) as exc:
        cmd_dataset_validate(args)
    assert exc.value.code == 1


def test_cmd_dataset_validate_multiple_records(tmp_path):
    from evaluate.langsmith_dataset import DEFAULT_SCHEMA

    f = tmp_path / "data.jsonl"
    f.write_text(
        json.dumps(_make_valid_record(1))
        + "\n"
        + json.dumps(_make_valid_record(2))
        + "\n"
    )

    args = MagicMock()
    args.file = f
    args.schema = DEFAULT_SCHEMA

    cmd_dataset_validate(args)


# ── cmd_scenario_show ──────────────────────────────────────────────────────────


def test_cmd_scenario_show_local_found(tmp_path, capsys):
    f = tmp_path / "data.jsonl"
    record = _make_valid_record(7)
    f.write_text(json.dumps(record) + "\n")

    args = MagicMock()
    args.dataset = f
    args.scenario_id = 7

    cmd_scenario_show(args)

    out = capsys.readouterr().out
    assert '"scenario_id": 7' in out


def test_cmd_scenario_show_local_not_found_exits(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record(1)) + "\n")

    args = MagicMock()
    args.dataset = f
    args.scenario_id = 99

    with pytest.raises(SystemExit) as exc:
        cmd_scenario_show(args)
    assert exc.value.code == 1


# ── cmd_scenario_update ────────────────────────────────────────────────────────


def _make_remote_example(scenario_id: int):
    ex = MagicMock()
    ex.id = uuid4()
    ex.metadata = {"scenario_id": scenario_id}
    return ex


def test_cmd_scenario_update_applies_patch(tmp_path):
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
        cmd_scenario_update(args)

    mock_client.update_example.assert_called_once_with(
        example_id=remote_ex.id,
        inputs=record["inputs"],
        outputs=record["outputs"],
        metadata=record["metadata"],
    )


def test_cmd_scenario_update_not_in_local_file_exits(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record(1)) + "\n")

    args = MagicMock()
    args.file = f
    args.scenario_id = 99
    args.dataset = "my-dataset"

    with pytest.raises(SystemExit) as exc:
        cmd_scenario_update(args)
    assert exc.value.code == 1


def test_cmd_scenario_update_not_in_remote_exits(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps(_make_valid_record(5)) + "\n")

    args = MagicMock()
    args.file = f
    args.scenario_id = 5
    args.dataset = "my-dataset"

    mock_client = MagicMock()
    mock_client.read_dataset.return_value = MagicMock(id=uuid4())
    mock_client.list_examples.return_value = []  # scenario not in remote

    with patch("evaluate.langsmith_dataset.make_client", return_value=mock_client):
        with pytest.raises(SystemExit) as exc:
            cmd_scenario_update(args)
    assert exc.value.code == 1


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


@given(st.text())
def test_local_or_remote_classification(value):
    """Strings ending in .jsonl always return Path; all others return str."""
    result = local_or_remote(value)
    if value.endswith(".jsonl"):
        assert isinstance(result, Path)
    else:
        assert isinstance(result, str)
