"""CLI for manipulating LangSmith datasets, scenarios, experiments, runs, and evaluators.

Remote references are bare dataset/experiment names as they appear in LangSmith.
Local references are file paths ending in .jsonl.

Usage examples:
    dataset list
    dataset push ./my-dataset.jsonl my-dataset
    dataset pull my-dataset ./my-dataset.jsonl
    dataset validate ./my-dataset.jsonl
    scenario list my-dataset
    experiment list my-dataset
    run show <run-id>
    prompt list
    prompt pull tfa-legal-correctness evaluators/legal_correctness.md
    prompt pull tfa-tone evaluators/tone.md --dry-run
"""

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import dotenv
import jsonschema
from langchain_core.prompts import (
    ChatPromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import RunnableSequence
from langsmith import Client
from langsmith import utils as langsmith_utils

EVALUATE_DIR = Path(__file__).parent
DEFAULT_SCHEMA = EVALUATE_DIR / "langsmith_scenario_schema.json"
DEFAULT_DATASET_NAME = "tenant-legal-qa-scenarios"
DEFAULT_JSONL = EVALUATE_DIR / "dataset-tenant-legal-qa-scenarios.jsonl"


def _tabulate(
    rows: Sequence[Sequence[str]], headers: Sequence[str] | None = None
) -> None:
    """Print rows in aligned columns, optionally with a header row and separator."""
    all_rows: list[Sequence[str]] = list(([headers] if headers else []) + list(rows))
    if not all_rows:
        return
    ncols = len(all_rows[0])
    widths = [max(len(r[i]) for r in all_rows) for i in range(ncols)]

    def fmt(row: Sequence[str]) -> str:
        return "  " + "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    if headers:
        print(fmt(headers))
        print("  " + "  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt(row))


def _read_jsonl(path: Path, *, with_line_numbers: bool = False) -> list:
    """Parse a JSONL file, skipping blank lines and // comments.

    When with_line_numbers is True, returns list of (line_number, dict) tuples
    so callers can report errors with file positions.
    """
    results = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.startswith("//"):
            continue
        parsed = json.loads(line)
        results.append((i, parsed) if with_line_numbers else parsed)
    return results


def _git_is_clean(path: Path) -> bool:
    """Return True if path has no uncommitted changes according to git."""
    result = subprocess.run(
        ["git", "status", "--porcelain", str(path.resolve())],
        capture_output=True,
        text=True,
        cwd=EVALUATE_DIR,
    )
    return result.returncode == 0 and not result.stdout.strip()


def make_client() -> Client:
    # The Client targets the workspace associated with LANGSMITH_API_KEY.
    # To target a different workspace, pass its UUID via the workspace_id
    # parameter — there is no name-based workspace resolution in the SDK.
    dotenv.load_dotenv(override=True)
    return Client(api_key=os.getenv("LANGSMITH_API_KEY"))


# ── dataset subcommands ────────────────────────────────────────────────────────


def cmd_dataset_list(args: argparse.Namespace) -> None:
    client = make_client()
    datasets = list(client.list_datasets())
    if not datasets:
        print("No datasets found.")
        return
    headers = None if args.no_header else ("NAME", "UUID")
    _tabulate([(ds.name or "", str(ds.id)) for ds in datasets], headers=headers)


def cmd_dataset_create(args: argparse.Namespace) -> None:
    client = make_client()
    if client.has_dataset(dataset_name=args.name):
        print(f"Dataset '{args.name}' already exists.")
        sys.exit(1)
    else:
        ds = client.create_dataset(dataset_name=args.name)
        print(f"Created '{args.name}' (uuid: {ds.id}).")


def cmd_dataset_delete(args: argparse.Namespace) -> None:
    client = make_client()
    try:
        ds = client.read_dataset(dataset_name=args.name)
    except langsmith_utils.LangSmithNotFoundError:
        print(f"Dataset '{args.name}' not found.")
        sys.exit(1)
    client.delete_dataset(dataset_id=ds.id)
    print(f"Deleted '{args.name}'.")


def cmd_dataset_push(args: argparse.Namespace) -> None:
    local: Path = args.file
    client = make_client()

    examples = _read_jsonl(local)

    try:
        ds = client.read_dataset(dataset_name=args.remote)
    except langsmith_utils.LangSmithNotFoundError:
        ds = client.create_dataset(dataset_name=args.remote)

    existing_ids = {
        _scenario_id({"metadata": ex.metadata})
        for ex in client.list_examples(dataset_id=ds.id)
    }
    to_add = [ex for ex in examples if _scenario_id(ex) not in existing_ids]
    for ex in to_add:
        client.create_example(
            inputs=ex["inputs"],
            outputs=ex["outputs"],
            metadata=ex.get("metadata"),
            dataset_id=ds.id,
        )
    print(
        f"Pushed {len(to_add)} new examples to '{args.remote}' ({len(examples) - len(to_add)} already present)."
    )


def cmd_dataset_pull(args: argparse.Namespace) -> None:
    local: Path = args.file

    if local.exists() and not args.force and not _git_is_clean(local):
        print(
            f"error: {local.name} has uncommitted changes. Commit first or pass --force.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = make_client()
    ds = client.read_dataset(dataset_name=args.remote)
    examples = sorted(
        client.list_examples(dataset_id=ds.id),
        key=lambda e: (e.metadata or {}).get("scenario_id", 0),
    )

    if args.dry_run:
        print(f"Would pull {len(examples)} examples from '{args.remote}' to {local}.")
        return

    with local.open("w") as f:
        for ex in examples:
            f.write(
                json.dumps(
                    {
                        "metadata": ex.metadata,
                        "inputs": ex.inputs,
                        "outputs": ex.outputs,
                    }
                )
                + "\n"
            )

    print(f"Pulled {len(examples)} examples from '{args.remote}' to {local}.")


def _load_examples(ref: str | Path, client: Client) -> list[dict]:
    """Load examples from a remote dataset name or local JSONL file."""
    if isinstance(ref, Path):
        return _read_jsonl(ref)
    ds = client.read_dataset(dataset_name=ref)
    return [
        {"metadata": ex.metadata, "inputs": ex.inputs, "outputs": ex.outputs}
        for ex in client.list_examples(dataset_id=ds.id)
    ]


def _scenario_id(example: dict) -> int:
    sc_id = (example.get("metadata") or {}).get("scenario_id")
    if sc_id is None:
        raise ValueError(f"Example is missing scenario_id in metadata: {example}")
    return sc_id


def cmd_dataset_diff(args: argparse.Namespace) -> None:
    client = make_client()
    left = _load_examples(args.left, client)
    right = _load_examples(args.right, client)

    left_by_id = {_scenario_id(ex): ex for ex in left}
    right_by_id = {_scenario_id(ex): ex for ex in right}

    only_left = sorted(left_by_id.keys() - right_by_id.keys())
    only_right = sorted(right_by_id.keys() - left_by_id.keys())

    for sid in only_left:
        print(f"< scenario_id={sid}")
    for sid in only_right:
        print(f"> scenario_id={sid}")
    if not only_left and not only_right:
        print("No differences.")


def cmd_dataset_merge(args: argparse.Namespace) -> None:
    client = make_client()
    source_examples = _load_examples(args.source, client)

    target_ds = client.read_dataset(dataset_name=args.target)
    existing = list(client.list_examples(dataset_id=target_ds.id))
    existing_ids = {_scenario_id({"metadata": ex.metadata}) for ex in existing}

    to_add = [ex for ex in source_examples if _scenario_id(ex) not in existing_ids]
    for ex in to_add:
        client.create_example(
            inputs=ex["inputs"],
            outputs=ex["outputs"],
            metadata=ex.get("metadata"),
            dataset_id=target_ds.id,
        )
    print(
        f"Merged {len(to_add)} new examples into '{args.target}' ({len(source_examples) - len(to_add)} already present)."
    )


def cmd_dataset_validate(args: argparse.Namespace) -> None:
    schema = json.loads(args.schema.read_text())
    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for i, record in _read_jsonl(args.file, with_line_numbers=True):
        for error in validator.iter_errors(record):
            errors.append(f"Line {i}: {error.message}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)
    print(f"All records in {args.file} are valid.")


# ── scenario subcommands ───────────────────────────────────────────────────────


def cmd_scenario_list(args: argparse.Namespace) -> None:
    client = make_client()
    ds = client.read_dataset(dataset_name=args.dataset)
    examples = list(client.list_examples(dataset_id=ds.id))
    rows = []
    for ex in sorted(examples, key=lambda e: (e.metadata or {}).get("scenario_id", 0)):
        sid = str((ex.metadata or {}).get("scenario_id", "?")).rjust(4)
        tags = str((ex.metadata or {}).get("tags", []))
        query = (ex.inputs or {}).get("query", "")[:80]
        rows.append((sid, tags, query))
    headers = None if args.no_header else ("ID", "TAGS", "QUERY")
    _tabulate(rows, headers=headers)


def cmd_scenario_show(args: argparse.Namespace) -> None:
    ref = args.dataset
    if isinstance(ref, Path):
        examples = _read_jsonl(ref)
    else:
        examples = _load_examples(ref, make_client())

    matches = [ex for ex in examples if _scenario_id(ex) == args.scenario_id]
    if not matches:
        print(f"Scenario {args.scenario_id} not found.", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(matches[0], indent=2))


def cmd_scenario_append(args: argparse.Namespace) -> None:
    local: Path = args.file
    client = make_client()
    ds = client.read_dataset(dataset_name=args.dataset)

    examples = _read_jsonl(local)
    for ex in examples:
        client.create_example(
            inputs=ex["inputs"],
            outputs=ex["outputs"],
            metadata=ex.get("metadata"),
            dataset_id=ds.id,
        )
    print(f"Appended {len(examples)} examples to '{args.dataset}'.")


def cmd_scenario_remove(args: argparse.Namespace) -> None:
    client = make_client()
    ds = client.read_dataset(dataset_name=args.dataset)
    examples = list(client.list_examples(dataset_id=ds.id))
    matches = [
        ex
        for ex in examples
        if (ex.metadata or {}).get("scenario_id") == args.scenario_id
    ]
    if not matches:
        print(f"Scenario {args.scenario_id} not found.", file=sys.stderr)
        sys.exit(1)
    client.delete_example(matches[0].id)
    print(f"Removed scenario {args.scenario_id} from '{args.dataset}'.")


def cmd_scenario_update(args: argparse.Namespace) -> None:
    client = make_client()
    ds = client.read_dataset(dataset_name=args.dataset)
    examples = list(client.list_examples(dataset_id=ds.id))
    matches = [
        ex
        for ex in examples
        if (ex.metadata or {}).get("scenario_id") == args.scenario_id
    ]
    if not matches:
        print(f"Scenario {args.scenario_id} not found.", file=sys.stderr)
        sys.exit(1)
    patch = json.loads(args.file.read_text().strip())
    client.update_example(
        example_id=matches[0].id,
        inputs=patch.get("inputs"),
        outputs=patch.get("outputs"),
        metadata=patch.get("metadata"),
    )
    print(f"Updated scenario {args.scenario_id} in '{args.dataset}'.")


# ── experiment subcommands ─────────────────────────────────────────────────────


def cmd_experiment_list(args: argparse.Namespace) -> None:
    client = make_client()
    ds = client.read_dataset(dataset_name=args.dataset)
    projects = list(client.list_projects(reference_dataset_id=ds.id))
    if not projects:
        print("No experiments found.")
        return
    headers = None if args.no_header else ("NAME", "UUID")
    _tabulate([(p.name or "", str(p.id)) for p in projects], headers=headers)


def cmd_experiment_show(args: argparse.Namespace) -> None:
    client = make_client()
    p = client.read_project(project_name=args.experiment)
    print(
        json.dumps(
            {
                "name": p.name,
                "id": str(p.id),
                "start_time": str(p.start_time),
                "end_time": str(p.end_time),
                "run_count": p.run_count,
                "feedback_stats": p.feedback_stats,
            },
            indent=2,
        )
    )


def cmd_experiment_compare(args: argparse.Namespace) -> None:
    client = make_client()
    p1, p2 = [
        client.read_project(project_name=name)
        for name in (args.experiment1, args.experiment2)
    ]

    def fmt_stats(stats: dict | None) -> str:
        if not stats:
            return "—"
        avg = stats.get("avg")
        return f"{avg:.1%}" if avg is not None else str(stats)

    all_keys = sorted(
        set((p1.feedback_stats or {}).keys()) | set((p2.feedback_stats or {}).keys())
    )
    rows: list[tuple[str, ...]] = [
        ("runs", str(p1.run_count or 0), str(p2.run_count or 0))
    ]
    for key in all_keys:
        rows.append(
            (
                key.removeprefix("feedback."),
                fmt_stats((p1.feedback_stats or {}).get(key)),
                fmt_stats((p2.feedback_stats or {}).get(key)),
            )
        )
    _tabulate(
        rows,
        headers=("METRIC", p1.name or args.experiment1, p2.name or args.experiment2),
    )


def cmd_experiment_results(args: argparse.Namespace) -> None:
    client = make_client()
    p = client.read_project(project_name=args.experiment)
    for run in client.list_runs(project_id=p.id, execution_order=1):
        print(
            json.dumps(
                {
                    "run_id": str(run.id),
                    "inputs": run.inputs,
                    "outputs": run.outputs,
                    "feedback": run.feedback_stats,
                }
            )
        )


# ── run subcommands ────────────────────────────────────────────────────────────


def cmd_run_list(args: argparse.Namespace) -> None:
    client = make_client()
    p = client.read_project(project_name=args.experiment)
    headers = None if args.no_header else ("UUID", "NAME", "STATUS")
    _tabulate(
        [
            (str(run.id), run.name or "", run.status or "")
            for run in client.list_runs(project_id=p.id, execution_order=1)
        ],
        headers=headers,
    )


def cmd_run_show(args: argparse.Namespace) -> None:
    client = make_client()
    run = client.read_run(args.run_id)
    print(
        json.dumps(
            {
                "id": str(run.id),
                "name": run.name,
                "status": run.status,
                "inputs": run.inputs,
                "outputs": run.outputs,
                "error": run.error,
            },
            indent=2,
        )
    )


def cmd_run_feedback(args: argparse.Namespace) -> None:
    client = make_client()
    for fb in client.list_feedback(run_ids=[args.run_id]):
        print(
            json.dumps(
                {
                    "key": fb.key,
                    "score": fb.score,
                    "comment": fb.comment,
                },
                indent=2,
            )
        )


def cmd_run_trace(args: argparse.Namespace) -> None:
    client = make_client()
    run = client.read_run(args.run_id, load_child_runs=True)

    def print_run(r, depth: int = 0) -> None:
        indent = "  " * depth
        print(f"{indent}{r.name}  ({r.run_type})  status={r.status}")
        for child in r.child_runs or []:
            print_run(child, depth + 1)

    print_run(run)


# ── evaluator subcommands ─────────────────────────────────────────────────────


def _prompt_columns() -> dict:
    """Return the registry of available columns for 'prompt list'.

    Each entry maps a column key to (header, extractor) where extractor is a
    callable that takes a Prompt object and returns a string.
    """

    def _date(p) -> str:
        dt = p.updated_at
        return dt.strftime("%Y-%m-%d %H:%M") if dt else ""

    return {
        "name": ("NAME", lambda p: str(p.repo_handle or "")),
        "date": ("LATEST COMMIT DATE", _date),
        "commit": ("LATEST COMMIT", lambda p: str(p.last_commit_hash or "")[:8]),
        "type": ("TYPE", lambda p: str(p.tags[0] if p.tags else "")),
        "commits": ("COMMITS", lambda p: str(p.num_commits or 0)),
    }


DEFAULT_PROMPT_COLUMNS = "name,date,commit,type"


def cmd_prompt_list(args: argparse.Namespace) -> None:
    col_registry = _prompt_columns()
    col_keys = [k.strip() for k in args.columns.split(",")]
    unknown = [k for k in col_keys if k not in col_registry]
    if unknown:
        valid = ", ".join(col_registry)
        print(
            f"error: unknown column(s): {', '.join(unknown)}. Valid: {valid}",
            file=sys.stderr,
        )
        sys.exit(1)

    client = make_client()
    # list_prompts yields ('repos', [Prompt, ...]) and ('total', int) tuples.
    all_prompts: list[Any] = []
    for key, val in client.list_prompts(is_public=False):
        if key == "repos":
            all_prompts.extend(val)
    if args.type:
        all_prompts = [p for p in all_prompts if args.type in (p.tags or [])]
    if not all_prompts:
        print("No prompts found.")
        return

    headers = None if args.no_header else tuple(col_registry[k][0] for k in col_keys)
    _tabulate(
        [tuple(col_registry[k][1](p) for k in col_keys) for p in all_prompts],
        headers=headers,
    )


def _extract_rubric(prompt_text: str) -> str:
    """Extract the rubric content from between <Rubric> tags in a full judge prompt."""
    match = re.search(r"<Rubric>\s*\n(.*?)\s*</Rubric>", prompt_text, re.DOTALL)
    if not match:
        raise ValueError("Could not find <Rubric>...</Rubric> tags in the prompt.")
    return match.group(1).strip() + "\n"


def cmd_prompt_pull(args: argparse.Namespace) -> None:
    """Pull rubric text from a Prompt Hub prompt back to a local file.

    The prompt must use <Rubric>…</Rubric> tags around the rubric text.
    Use 'prompt list' to find available prompt names.
    """
    local: Path = args.file

    if local.exists() and not args.force and not _git_is_clean(local):
        print(
            f"error: {local.name} has uncommitted changes. Commit first or pass --force.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = make_client()
    pulled = client.pull_prompt(args.name)

    # pull_prompt returns different types depending on how the prompt was created.
    if isinstance(pulled, RunnableSequence):
        chat_prompt = pulled.first
        if not isinstance(chat_prompt, ChatPromptTemplate):
            print(
                f"error: first step of RunnableSequence for '{args.name}' is"
                f" '{type(chat_prompt).__name__}', expected ChatPromptTemplate.",
                file=sys.stderr,
            )
            sys.exit(1)
    elif isinstance(pulled, ChatPromptTemplate):
        chat_prompt = pulled
    else:
        print(
            f"error: unexpected prompt type '{type(pulled).__name__}' for '{args.name}'."
            " Cannot extract rubric.",
            file=sys.stderr,
        )
        sys.exit(1)

    first_msg = chat_prompt.messages[0]
    if not isinstance(first_msg, SystemMessagePromptTemplate):
        print(
            f"error: first message of '{args.name}' is '{type(first_msg).__name__}',"
            " expected SystemMessagePromptTemplate.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not isinstance(first_msg.prompt, PromptTemplate):
        print(
            f"error: prompt template of '{args.name}' is '{type(first_msg.prompt).__name__}',"
            " expected PromptTemplate.",
            file=sys.stderr,
        )
        sys.exit(1)
    system_msg = first_msg.prompt.template
    rubric_text = _extract_rubric(system_msg)

    if args.dry_run:
        existing = local.read_text() if local.exists() else ""
        diff = list(
            difflib.unified_diff(
                existing.splitlines(keepends=True),
                rubric_text.splitlines(keepends=True),
                fromfile=f"a/{local.name}",
                tofile=f"b/{local.name}",
            )
        )
        if diff:
            print("".join(diff))
        else:
            print(f"{local.name}: no changes")
        return

    local.write_text(rubric_text)
    print(f"Pulled '{args.name}' → {local}")


# ── argument parser ────────────────────────────────────────────────────────────


def local_or_remote(value: str) -> str | Path:
    """argparse type for arguments that accept either a remote name or a local .jsonl path."""
    return Path(value) if value.endswith(".jsonl") else value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    nouns = parser.add_subparsers(dest="noun", metavar="COMMAND")
    nouns.required = True

    # ── dataset ──────────────────────────────────────────────────────────────
    ds_parser = nouns.add_parser("dataset", help="Manage datasets.")
    ds_sub = ds_parser.add_subparsers(dest="verb", metavar="SUBCOMMAND")
    ds_sub.required = True

    p = ds_sub.add_parser("list", help="List datasets.")
    p.add_argument("--no-header", action="store_true", help="Suppress column headers.")
    p.set_defaults(func=cmd_dataset_list)

    p = ds_sub.add_parser("create", help="Create a new empty dataset.")
    p.add_argument(
        "name",
        nargs="?",
        default=DEFAULT_DATASET_NAME,
        help=f"LangSmith dataset name (default: {DEFAULT_DATASET_NAME})",
    )
    p.set_defaults(func=cmd_dataset_create)

    p = ds_sub.add_parser("delete", help="Delete a dataset.")
    p.add_argument(
        "name",
        nargs="?",
        default=DEFAULT_DATASET_NAME,
        help=f"LangSmith dataset name (default: {DEFAULT_DATASET_NAME})",
    )
    p.set_defaults(func=cmd_dataset_delete)

    p = ds_sub.add_parser("push", help="Upload a local JSONL file to a dataset.")
    p.add_argument(
        "file",
        type=Path,
        nargs="?",
        default=DEFAULT_JSONL,
        metavar="file.jsonl",
        help=f"Local JSONL file to upload (default: {DEFAULT_JSONL.name})",
    )
    p.add_argument(
        "remote",
        nargs="?",
        default=DEFAULT_DATASET_NAME,
        metavar="name",
        help=f"LangSmith dataset name (default: {DEFAULT_DATASET_NAME})",
    )
    p.set_defaults(func=cmd_dataset_push)

    p = ds_sub.add_parser("pull", help="Download a dataset to a local JSONL file.")
    p.add_argument(
        "remote",
        nargs="?",
        default=DEFAULT_DATASET_NAME,
        metavar="name",
        help=f"LangSmith dataset name (default: {DEFAULT_DATASET_NAME})",
    )
    p.add_argument(
        "file",
        type=Path,
        nargs="?",
        default=DEFAULT_JSONL,
        metavar="file.jsonl",
        help=f"Local file to write (default: {DEFAULT_JSONL.name})",
    )
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite local file even if it has uncommitted changes.",
    )
    p.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be pulled without writing the file.",
    )
    p.set_defaults(func=cmd_dataset_pull)

    p = ds_sub.add_parser("diff", help="Diff two datasets by scenario_id.")
    p.add_argument(
        "left",
        type=local_or_remote,
        metavar="name|file.jsonl",
        help="Left side: dataset name or local JSONL file.",
    )
    p.add_argument(
        "right",
        type=local_or_remote,
        metavar="name|file.jsonl",
        help="Right side: dataset name or local JSONL file.",
    )
    p.set_defaults(func=cmd_dataset_diff)

    p = ds_sub.add_parser("merge", help="Copy new scenarios from source into target.")
    p.add_argument(
        "source",
        type=local_or_remote,
        metavar="name|file.jsonl",
        help="Source dataset name or local JSONL file to copy from.",
    )
    p.add_argument(
        "target",
        nargs="?",
        default=DEFAULT_DATASET_NAME,
        metavar="name",
        help=f"Target LangSmith dataset name (default: {DEFAULT_DATASET_NAME})",
    )
    p.set_defaults(func=cmd_dataset_merge)

    p = ds_sub.add_parser(
        "validate", help="Validate a local JSONL file against the schema."
    )
    p.add_argument(
        "file",
        type=Path,
        nargs="?",
        default=DEFAULT_JSONL,
        metavar="file.jsonl",
        help=f"Local JSONL file to validate (default: {DEFAULT_JSONL.name})",
    )
    p.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="JSON Schema file (default: %(default)s)",
    )
    p.set_defaults(func=cmd_dataset_validate)

    # ── scenario ─────────────────────────────────────────────────────────────
    sc_parser = nouns.add_parser("scenario", help="Manage scenarios within a dataset.")
    sc_sub = sc_parser.add_subparsers(dest="verb", metavar="SUBCOMMAND")
    sc_sub.required = True

    p = sc_sub.add_parser("list", help="List scenarios in a dataset.")
    p.add_argument(
        "dataset",
        nargs="?",
        default=DEFAULT_DATASET_NAME,
        metavar="name",
        help=f"LangSmith dataset name (default: {DEFAULT_DATASET_NAME})",
    )
    p.add_argument("--no-header", action="store_true", help="Suppress column headers.")
    p.set_defaults(func=cmd_scenario_list)

    p = sc_sub.add_parser("show", help="Print a single scenario.")
    p.add_argument(
        "dataset",
        type=local_or_remote,
        nargs="?",
        default=DEFAULT_JSONL,
        metavar="name|file.jsonl",
        help=f"Dataset name or local JSONL file (default: {DEFAULT_JSONL.name})",
    )
    p.add_argument("scenario_id", type=int, help="scenario_id from metadata.")
    p.set_defaults(func=cmd_scenario_show)

    p = sc_sub.add_parser(
        "append", help="Append scenarios from a JSONL file to a dataset."
    )
    p.add_argument(
        "dataset",
        nargs="?",
        default=DEFAULT_DATASET_NAME,
        metavar="name",
        help=f"LangSmith dataset name (default: {DEFAULT_DATASET_NAME})",
    )
    p.add_argument(
        "file",
        type=Path,
        nargs="?",
        default=DEFAULT_JSONL,
        metavar="file.jsonl",
        help=f"Local JSONL file containing scenarios to append (default: {DEFAULT_JSONL.name})",
    )
    p.set_defaults(func=cmd_scenario_append)

    p = sc_sub.add_parser("remove", help="Remove a scenario by scenario_id.")
    p.add_argument(
        "dataset",
        nargs="?",
        default=DEFAULT_DATASET_NAME,
        metavar="name",
        help=f"LangSmith dataset name (default: {DEFAULT_DATASET_NAME})",
    )
    p.add_argument("scenario_id", type=int, help="scenario_id from metadata.")
    p.set_defaults(func=cmd_scenario_remove)

    p = sc_sub.add_parser("update", help="Update a scenario from a JSONL file.")
    p.add_argument(
        "dataset",
        nargs="?",
        default=DEFAULT_DATASET_NAME,
        metavar="name",
        help=f"LangSmith dataset name (default: {DEFAULT_DATASET_NAME})",
    )
    p.add_argument("scenario_id", type=int, help="scenario_id from metadata.")
    p.add_argument(
        "file",
        type=Path,
        nargs="?",
        default=DEFAULT_JSONL,
        metavar="file.jsonl",
        help=f"Local JSONL file containing the updated scenario (default: {DEFAULT_JSONL.name})",
    )
    p.set_defaults(func=cmd_scenario_update)

    # ── experiment ───────────────────────────────────────────────────────────
    ex_parser = nouns.add_parser("experiment", help="Inspect experiments.")
    ex_sub = ex_parser.add_subparsers(dest="verb", metavar="SUBCOMMAND")
    ex_sub.required = True

    p = ex_sub.add_parser("list", help="List experiments run against a dataset.")
    p.add_argument(
        "dataset",
        nargs="?",
        default=DEFAULT_DATASET_NAME,
        metavar="name",
        help=f"LangSmith dataset name (default: {DEFAULT_DATASET_NAME})",
    )
    p.add_argument("--no-header", action="store_true", help="Suppress column headers.")
    p.set_defaults(func=cmd_experiment_list)

    p = ex_sub.add_parser("show", help="Print aggregate results for an experiment.")
    p.add_argument("experiment", metavar="name", help="LangSmith experiment name.")
    p.set_defaults(func=cmd_experiment_show)

    p = ex_sub.add_parser("compare", help="Compare scores for two experiments.")
    p.add_argument("experiment1", metavar="name", help="First experiment name.")
    p.add_argument("experiment2", metavar="name", help="Second experiment name.")
    p.set_defaults(func=cmd_experiment_compare)

    p = ex_sub.add_parser("results", help="Print per-scenario results as JSONL.")
    p.add_argument("experiment", metavar="name", help="LangSmith experiment name.")
    p.set_defaults(func=cmd_experiment_results)

    # ── runs ──────────────────────────────────────────────────────────────────
    runs_parser = nouns.add_parser("runs", help="Inspect individual runs.")
    runs_sub = runs_parser.add_subparsers(dest="verb", metavar="SUBCOMMAND")
    runs_sub.required = True

    p = runs_sub.add_parser("list", help="List runs in an experiment.")
    p.add_argument("experiment", metavar="name", help="LangSmith experiment name.")
    p.add_argument("--no-header", action="store_true", help="Suppress column headers.")
    p.set_defaults(func=cmd_run_list)

    p = runs_sub.add_parser("show", help="Print inputs, outputs, and status for a run.")
    p.add_argument("run_id", help="LangSmith run UUID.")
    p.set_defaults(func=cmd_run_show)

    p = runs_sub.add_parser("feedback", help="Print evaluator scores for a run.")
    p.add_argument("run_id", help="LangSmith run UUID.")
    p.set_defaults(func=cmd_run_feedback)

    p = runs_sub.add_parser("trace", help="Print the full call tree for a run.")
    p.add_argument("run_id", help="LangSmith run UUID.")
    p.set_defaults(func=cmd_run_trace)

    # ── prompt ───────────────────────────────────────────────────────────────
    pr_parser = nouns.add_parser(
        "prompt", help="Manage Prompt Hub prompts used by bound evaluators."
    )
    pr_sub = pr_parser.add_subparsers(dest="verb", metavar="SUBCOMMAND")
    pr_sub.required = True

    p = pr_sub.add_parser("list", help="List prompts in the Prompt Hub.")
    p.add_argument("--no-header", action="store_true", help="Suppress column headers.")
    p.add_argument(
        "--type",
        metavar="type",
        default=None,
        help="Filter by prompt type (e.g. StructuredPrompt, ChatPromptTemplate).",
    )
    p.add_argument(
        "--columns",
        metavar="cols",
        default=DEFAULT_PROMPT_COLUMNS,
        help=f"Comma-separated columns to show (default: {DEFAULT_PROMPT_COLUMNS})."
        " Available: name, date, commit, type, commits.",
    )
    p.set_defaults(func=cmd_prompt_list)

    p = pr_sub.add_parser(
        "pull",
        help="Pull rubric text from a Prompt Hub prompt to a local file.",
    )
    p.add_argument(
        "name", metavar="hub-name", help="Prompt Hub prompt name (from 'prompt list')."
    )
    p.add_argument("file", type=Path, metavar="file", help="Local file to write.")
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite local file even if it has uncommitted changes.",
    )
    p.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show a diff of what would change without writing the file.",
    )
    p.set_defaults(func=cmd_prompt_pull)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
