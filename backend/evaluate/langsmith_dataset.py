"""CLI for manipulating LangSmith datasets, examples, experiments, runs, and evaluators.

Remote references are bare dataset/experiment names as they appear in LangSmith.
Local references are file paths ending in .jsonl.

Usage examples:
    dataset list
    dataset push ./my-dataset.jsonl my-dataset
    dataset pull my-dataset ./my-dataset.jsonl
    dataset diff ./my-dataset.jsonl my-dataset
    dataset validate ./my-dataset.jsonl
    example list my-dataset
    experiment list my-dataset
    experiment show <name-or-uuid>
    experiment stats <name-or-uuid>
    runs exemplars <name-or-uuid> <scenario-id> --evaluator "legal correctness"
    runs show <run-id>
    runs trace <run-id>
    runs trace <run-id> --verbose
    prompt list
    prompt pull tfa-legal-correctness evaluators/legal_correctness.md
    prompt pull tfa-tone evaluators/tone.md --dry-run
"""

import argparse
import difflib
import json
import math
import re
import statistics
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import jsonschema
from langchain_core.prompts import (
    ChatPromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import RunnableSequence
from langsmith import Client
from langsmith import utils as langsmith_utils

from evaluate.eval_history import (
    HISTORY_DIR,
    append_section,
    find_baseline,
    find_entry,
    parse_frontmatter,
)
from evaluate.results_display import ScenarioResult, print_consistency_stats
from tenantfirstaid.constants import LANGSMITH_API_KEY

EVALUATE_DIR = Path(__file__).parent
DEFAULT_SCHEMA = EVALUATE_DIR / "langsmith_example_schema.json"
DEFAULT_DATASET_NAME = "tenant-legal-qa-scenarios"
DEFAULT_JSONL = EVALUATE_DIR / "dataset-tenant-legal-qa-examples.jsonl"


@dataclass(frozen=True)
class _Validate:
    """Validation configuration for _read_jsonl.

    mode="error"  raises ValueError listing all violations with line numbers.
    mode="warn"   prints the same information to stderr and continues.
    """

    mode: Literal["error", "warn"]
    schema: Path = field(default_factory=lambda: DEFAULT_SCHEMA)


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


def _read_jsonl(
    path: Path,
    *,
    with_line_numbers: bool = False,
    validate: _Validate | None = None,
) -> list:
    """Parse a JSONL file, skipping blank lines and // comments.

    Pass a Validate instance to check records against a schema.  Validate("error")
    raises ValueError listing all violations with line numbers; Validate("warn")
    prints the same information to stderr and continues.
    When with_line_numbers=True, returns list of (line_number, dict) tuples
    so callers can report errors with file positions.
    """
    numbered: list[tuple[int, dict]] = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.startswith("//"):
            continue
        numbered.append((i, json.loads(line)))

    if validate is not None:
        schema_obj = json.loads(validate.schema.read_text())
        validator = jsonschema.Draft7Validator(schema_obj)
        errors = [
            f"Line {i}: {error.message}"
            for i, record in numbered
            for error in validator.iter_errors(record)
        ]
        if errors:
            msg = "\n".join(errors)
            if validate.mode == "warn":
                print(
                    f"warning: {path.name} has schema violations:\n{msg}",
                    file=sys.stderr,
                )
            else:
                raise ValueError(msg)

    return numbered if with_line_numbers else [record for _, record in numbered]


def _git_is_clean(path: Path) -> bool:
    """Return True if path has no uncommitted changes according to git."""
    result = subprocess.run(
        ["git", "status", "--porcelain", str(path.resolve())],
        capture_output=True,
        text=True,
        cwd=EVALUATE_DIR,
    )
    return result.returncode == 0 and not result.stdout.strip()


def _load_dataset_schemas() -> tuple[dict, dict]:
    """Return (inputs_schema, outputs_schema) extracted from DEFAULT_SCHEMA."""
    props = json.loads(DEFAULT_SCHEMA.read_text()).get("properties", {})
    return props["inputs"], props["outputs"]


def _apply_dataset_schemas(client: Client, dataset_id: Any) -> None:
    """Attach inputs/outputs schemas from DEFAULT_SCHEMA to an existing dataset."""
    inputs_schema, outputs_schema = _load_dataset_schemas()
    response = client.request_with_retries(
        "PATCH",
        f"/datasets/{dataset_id}",
        headers={**client._headers, "Content-Type": "application/json"},
        data=json.dumps(
            {
                "inputs_schema_definition": inputs_schema,
                "outputs_schema_definition": outputs_schema,
            }
        ).encode(),
    )
    langsmith_utils.raise_for_status_with_text(response)


def make_client() -> Client:
    # The Client targets the workspace associated with LANGSMITH_API_KEY.
    # To target a different workspace, pass its UUID via the workspace_id
    # parameter — there is no name-based workspace resolution in the SDK.
    if LANGSMITH_API_KEY is None:
        raise RuntimeError(
            "LANGSMITH_API_KEY environment variable not set. Cannot create LangSmith Client."
        )
    return Client(api_key=LANGSMITH_API_KEY)


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


def _read_project(client: Client, name_or_id: str) -> Any:
    """Read a LangSmith project by name or UUID."""
    if _UUID_RE.match(name_or_id):
        return client.read_project(project_id=name_or_id)
    return client.read_project(project_name=name_or_id)


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
        inputs_schema, outputs_schema = _load_dataset_schemas()
        ds = client.create_dataset(
            dataset_name=args.name,
            inputs_schema=inputs_schema,
            outputs_schema=outputs_schema,
        )
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

    try:
        examples = _read_jsonl(local, validate=_Validate("error"))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    try:
        ds = client.read_dataset(dataset_name=args.remote)
    except langsmith_utils.LangSmithNotFoundError:
        inputs_schema, outputs_schema = _load_dataset_schemas()
        ds = client.create_dataset(
            dataset_name=args.remote,
            inputs_schema=inputs_schema,
            outputs_schema=outputs_schema,
        )
    _apply_dataset_schemas(client, ds.id)

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


def _load_examples(
    ref: str | Path,
    client: Client,
    *,
    validate: _Validate | None = None,
) -> list[dict]:
    """Load examples from a remote dataset name or local JSONL file."""
    if isinstance(ref, Path):
        return _read_jsonl(ref, validate=validate)
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


_EXAMPLE_DIFF_FIELDS = ("inputs", "outputs", "metadata")


def _example_content_diff(left: dict, right: dict) -> list[str]:
    """Return unified diff lines for every field that differs between two example dicts.

    Compares inputs, outputs, and metadata field by field so that callers can see
    exactly what changed rather than diffing a serialised blob.  Returns an empty
    list when the examples are content-identical.
    """
    lines: list[str] = []
    for key in _EXAMPLE_DIFF_FIELDS:
        left_val = left.get(key)
        right_val = right.get(key)
        if left_val == right_val:
            continue
        left_text = json.dumps(left_val, indent=2, sort_keys=True)
        right_text = json.dumps(right_val, indent=2, sort_keys=True)
        lines.extend(
            difflib.unified_diff(
                left_text.splitlines(keepends=True),
                right_text.splitlines(keepends=True),
                fromfile=f"left/{key}",
                tofile=f"right/{key}",
            )
        )
    return lines


def cmd_dataset_diff(args: argparse.Namespace) -> None:
    client = make_client()
    try:
        left = _load_examples(args.left, client, validate=_Validate("error"))
        right = _load_examples(args.right, client, validate=_Validate("error"))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    left_by_id = {_scenario_id(ex): ex for ex in left}
    right_by_id = {_scenario_id(ex): ex for ex in right}

    only_left = sorted(left_by_id.keys() - right_by_id.keys())
    only_right = sorted(right_by_id.keys() - left_by_id.keys())
    common = sorted(left_by_id.keys() & right_by_id.keys())

    found_diff = False
    for sid in only_left:
        print(f"< scenario_id={sid}")
        found_diff = True
    for sid in only_right:
        print(f"> scenario_id={sid}")
        found_diff = True
    for sid in common:
        diff_lines = _example_content_diff(left_by_id[sid], right_by_id[sid])
        if diff_lines:
            print(f"~ scenario_id={sid}  [content differs]")
            for line in diff_lines:
                print("  " + line.rstrip("\n"))
            found_diff = True

    if not found_diff:
        print("No differences.")


def cmd_dataset_merge(args: argparse.Namespace) -> None:
    client = make_client()
    try:
        source_examples = _load_examples(
            args.source, client, validate=_Validate("error")
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    target_ds = client.read_dataset(dataset_name=args.target)
    _apply_dataset_schemas(client, target_ds.id)
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
    try:
        _read_jsonl(args.file, validate=_Validate("error", schema=args.schema))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    print(f"All records in {args.file} are valid.")


# ── example subcommands ───────────────────────────────────────────────────────


def cmd_example_list(args: argparse.Namespace) -> None:
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


def cmd_example_show(args: argparse.Namespace) -> None:
    ref = args.dataset
    if isinstance(ref, Path):
        examples = _read_jsonl(ref, validate=_Validate("warn"))
    else:
        examples = _load_examples(ref, make_client())

    matches = [ex for ex in examples if _scenario_id(ex) == args.scenario_id]
    if not matches:
        print(f"Example {args.scenario_id} not found.", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(matches[0], indent=2))


def cmd_example_append(args: argparse.Namespace) -> None:
    local: Path = args.file
    client = make_client()
    ds = client.read_dataset(dataset_name=args.dataset)

    try:
        examples = _read_jsonl(local, validate=_Validate("error"))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    for ex in examples:
        client.create_example(
            inputs=ex["inputs"],
            outputs=ex["outputs"],
            metadata=ex.get("metadata"),
            dataset_id=ds.id,
        )
    print(f"Appended {len(examples)} examples to '{args.dataset}'.")


def cmd_example_remove(args: argparse.Namespace) -> None:
    client = make_client()
    ds = client.read_dataset(dataset_name=args.dataset)
    examples = list(client.list_examples(dataset_id=ds.id))
    matches = [
        ex
        for ex in examples
        if (ex.metadata or {}).get("scenario_id") == args.scenario_id
    ]
    if not matches:
        print(f"Example {args.scenario_id} not found.", file=sys.stderr)
        sys.exit(1)
    client.delete_example(matches[0].id)
    print(f"Removed example {args.scenario_id} from '{args.dataset}'.")


def cmd_example_update(args: argparse.Namespace) -> None:
    local_examples = {
        _scenario_id(ex): ex
        for ex in _read_jsonl(args.file, validate=_Validate("warn"))
    }
    if args.scenario_id not in local_examples:
        print(f"Example {args.scenario_id} not found in {args.file}.", file=sys.stderr)
        sys.exit(1)
    patch = local_examples[args.scenario_id]

    client = make_client()
    ds = client.read_dataset(dataset_name=args.dataset)
    remote = list(client.list_examples(dataset_id=ds.id))
    matches = [
        ex
        for ex in remote
        if (ex.metadata or {}).get("scenario_id") == args.scenario_id
    ]
    if not matches:
        print(
            f"Example {args.scenario_id} not found in '{args.dataset}'.",
            file=sys.stderr,
        )
        sys.exit(1)
    client.update_example(
        example_id=matches[0].id,
        inputs=patch.get("inputs"),
        outputs=patch.get("outputs"),
        metadata=patch.get("metadata"),
    )
    print(f"Updated example {args.scenario_id} in '{args.dataset}'.")


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


def _index_feedback_by_run(client: Any, run_ids: list) -> dict[str, list]:
    """Return {str(run_id): [feedback, ...]} for the given run IDs."""
    fb_by_run: dict[str, list] = {}
    for fb in client.list_feedback(run_ids=run_ids):
        fb_by_run.setdefault(str(fb.run_id), []).append(fb)
    return fb_by_run


def _index_scenario_ids(
    client: Any, example_ids: list, default: int = -1
) -> dict[str, int]:
    """Return {str(example_id): scenario_id} fetched from example metadata."""
    return {
        str(ex.id): (ex.metadata or {}).get("scenario_id", default)
        for ex in client.list_examples(example_ids=example_ids)
    }


def _experiment_scores(
    client: Any, project_id: Any
) -> tuple[int, dict[str, tuple[float, float]]]:
    """Return (run_count, {evaluator_key: (mean, pstdev)}) for an experiment.

    read_project does not reliably populate run_count or feedback_stats, so
    we count runs and aggregate scores directly from list_runs/list_feedback.
    """

    runs = list(client.list_runs(project_id=project_id, execution_order=1))
    if not runs:
        return 0, {}
    run_ids = [r.id for r in runs]
    raw: dict[str, list[float]] = {}
    for fb in client.list_feedback(run_ids=run_ids):
        if fb.score is not None:
            raw.setdefault(fb.key, []).append(float(fb.score))
    return len(runs), {
        k: (statistics.mean(v), statistics.pstdev(v)) for k, v in raw.items()
    }


def cmd_experiment_show(args: argparse.Namespace) -> None:
    client = make_client()
    p = _read_project(client, args.experiment)
    run_count, scores = _experiment_scores(client, p.id)
    print(
        json.dumps(
            {
                "name": p.name,
                "id": str(p.id),
                "start_time": str(p.start_time),
                "end_time": str(p.end_time),
                "run_count": run_count,
                "feedback_stats": {
                    k: {"mean": round(mean, 4), "std": round(std, 4)}
                    for k, (mean, std) in scores.items()
                },
            },
            indent=2,
        )
    )


def cmd_experiment_compare(args: argparse.Namespace) -> None:
    client = make_client()
    p1, p2 = [
        _read_project(client, name) for name in (args.experiment1, args.experiment2)
    ]
    (n1, scores1), (n2, scores2) = [_experiment_scores(client, p.id) for p in (p1, p2)]

    def fmt(entry: tuple[float, float] | None) -> str:
        if entry is None:
            return "—"
        mean, std = entry
        return f"{mean:.1%} (σ={std:.1%})"

    all_keys = sorted(scores1.keys() | scores2.keys())
    rows: list[tuple[str, ...]] = [("runs", str(n1), str(n2))]
    for key in all_keys:
        rows.append((key, fmt(scores1.get(key)), fmt(scores2.get(key))))

    _tabulate(
        rows,
        headers=("METRIC", p1.name or args.experiment1, p2.name or args.experiment2),
    )


def cmd_experiment_results(args: argparse.Namespace) -> None:
    client = make_client()
    p = _read_project(client, args.experiment)
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


def cmd_experiment_stats(args: argparse.Namespace) -> None:
    """Print per-scenario consistency stats with ASCII score distributions."""
    client = make_client()
    p = _read_project(client, args.experiment)
    runs = list(client.list_runs(project_id=p.id, execution_order=1))
    if not runs:
        print("No runs found.")
        return

    run_ids = [run.id for run in runs]
    fb_by_run = _index_feedback_by_run(client, run_ids)

    runs_by_example: dict[str, list] = {}
    for run in runs:
        runs_by_example.setdefault(str(run.reference_example_id), []).append(run)

    scenario_id_by_example = _index_scenario_ids(
        client, list(runs_by_example.keys()), default=-1
    )

    scenarios = []
    for example_id, example_runs in sorted(
        runs_by_example.items(),
        key=lambda item: scenario_id_by_example.get(item[0], 0),
    ):
        q = str((example_runs[0].inputs or {}).get("query", ""))
        sc_id = scenario_id_by_example.get(example_id, 0)
        label = f'"{q[:68]}{"..." if len(q) > 68 else ""}"'
        scores: dict[str, list[float]] = {}
        for run in example_runs:
            for fb in fb_by_run.get(str(run.id), []):
                if fb.score is not None:
                    scores.setdefault(fb.key, []).append(float(fb.score))
        scenarios.append(
            ScenarioResult(label=label, scenario_id=int(sc_id), scores=scores)
        )

    print_consistency_stats(scenarios, evaluators=args.evaluator or None)


# ── run subcommands ────────────────────────────────────────────────────────────


def cmd_run_list(args: argparse.Namespace) -> None:
    client = make_client()
    p = _read_project(client, args.experiment)
    headers = None if args.no_header else ("UUID", "NAME", "STATUS")
    _tabulate(
        [
            (str(run.id), run.name or "", run.status or "")
            for run in client.list_runs(project_id=p.id, execution_order=1)
        ],
        headers=headers,
    )


def cmd_run_exemplars(args: argparse.Namespace) -> None:
    """List runs for a specific scenario, sorted by evaluator score.

    Designed to replace the manual loop of:
      runs scores → runs show (to check scenario) → runs trace --verbose.

    Prints one row per run in the target scenario, sorted from lowest to highest
    score for the chosen evaluator, so the worst and best exemplars are easy to
    pick for 'runs trace --verbose'.
    """
    client = make_client()
    p = _read_project(client, args.experiment)
    runs = list(client.list_runs(project_id=p.id, execution_order=1))
    if not runs:
        print("No runs found.")
        return

    run_ids = [run.id for run in runs]
    fb_by_run = _index_feedback_by_run(client, run_ids)

    example_ids = list(
        {str(run.reference_example_id) for run in runs if run.reference_example_id}
    )
    # Use -1 as sentinel so scenario_id=0 is not confused with "unknown".
    scenario_id_by_example = _index_scenario_ids(client, example_ids, default=-1)

    target = args.scenario_id
    scenario_runs = [
        run
        for run in runs
        if scenario_id_by_example.get(str(run.reference_example_id)) == target
    ]
    if not scenario_runs:
        print(f"No runs found for scenario_id={target}.")
        return

    evaluator_key: str = args.evaluator

    def _score(run: Any) -> float:
        for fb in fb_by_run.get(str(run.id), []):
            if fb.key == evaluator_key and fb.score is not None:
                return float(fb.score)
        return float("inf")  # Sort unevaluated runs after all scored runs.

    scores_by_run = {run.id: _score(run) for run in scenario_runs}
    scenario_runs.sort(key=lambda r: scores_by_run[r.id])

    rows: list[tuple[str, ...]] = []
    for run in scenario_runs:
        score = scores_by_run[run.id]
        score_str = f"{score:.2f}" if math.isfinite(score) else "N/A"
        query = str((run.inputs or {}).get("query", ""))
        rows.append(
            (score_str, str(run.id), query[:60] + ("…" if len(query) > 60 else ""))
        )

    headers = None if args.no_header else (evaluator_key, "RUN UUID", "QUERY")
    _tabulate(rows, headers=headers)


def cmd_run_show(args: argparse.Namespace) -> None:
    client = make_client()
    for run_id in args.run_id:
        run = client.read_run(run_id)
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


_TRACE_SNIP = 5000  # max chars shown per tool/llm content block before truncation


def cmd_run_trace(args: argparse.Namespace) -> None:
    client = make_client()
    run = client.read_run(args.run_id, load_child_runs=True)
    verbose: bool = args.verbose

    def _snip(text: str) -> str:
        if len(text) > _TRACE_SNIP:
            return (
                text[:_TRACE_SNIP] + f"\n… [{len(text) - _TRACE_SNIP} chars truncated]"
            )
        return text

    def print_run(r: Any, depth: int = 0) -> None:
        indent = "  " * depth
        print(f"{indent}{r.name}  ({r.run_type})  status={r.status}")
        if verbose:
            if r.run_type == "tool":
                for k, v in (r.inputs or {}).items():
                    print(f"{indent}  in  {k}: {v!r}")
                raw = (r.outputs or {}).get("output", r.outputs)
                text = raw if isinstance(raw, str) else json.dumps(raw)
                print(f"{indent}  out {_snip(text)}")
            elif r.run_type == "llm":
                # Show the last message in the output (the model reply).
                generations = (r.outputs or {}).get("generations", [[]])
                for gen_list in generations:
                    for gen in gen_list:
                        text = gen.get("text") or json.dumps(gen.get("message", {}))
                        print(f"{indent}  out {_snip(text)}")
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


# ---------------------------------------------------------------------------
# history commands
# ---------------------------------------------------------------------------


def _require_entry(experiment: str) -> Path:
    path = find_entry(experiment)
    if path is None:
        print(f"No history entry found for experiment: {experiment}", file=sys.stderr)
        sys.exit(1)
    return path


def cmd_history_baseline(args: argparse.Namespace) -> None:  # noqa: ARG001
    """Print the best prior history entry to use as a regression baseline."""

    baseline = find_baseline()
    if baseline is None:
        print("No baseline found. Run an evaluation first.")
        return

    fm = parse_frontmatter(baseline)
    print(f"Baseline: {baseline}")
    print(f"  experiment:      {fm.get('experiment', '?')}")
    print(f"  timestamp:       {fm.get('timestamp', '?')}")
    print(f"  git_commit:      {fm.get('git_commit', '?')}")
    print(f"  git_branch:      {fm.get('git_branch', '?')}")
    print(f"  git_dirty:       {fm.get('git_dirty', '?')}")
    print(f"  dataset:         {fm.get('dataset', '?')}")
    print(f"  dataset_version: {fm.get('dataset_version', '?')}")

    entries = sorted(HISTORY_DIR.glob("*.md"), reverse=True)
    print(f"\nAll history entries ({len(entries)} total):")
    for e in entries:
        tag = " ← baseline" if e == baseline else ""
        efm = parse_frontmatter(e)
        print(
            f"  {e.name}  "
            f"[{efm.get('git_branch', '?')}  dirty={efm.get('git_dirty', '?')}]{tag}"
        )


def cmd_history_find(args: argparse.Namespace) -> None:
    """Print the path of the history entry for a specific experiment."""
    print(_require_entry(args.experiment))


def cmd_history_append(args: argparse.Namespace) -> None:
    """Append triage or hypotheses content to a history entry."""
    path = _require_entry(args.experiment)
    section = args.section.capitalize()
    append_section(path, section, args.content)
    print(f"Updated {section} in {path}")


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

    p = ds_sub.add_parser("merge", help="Copy new examples from source into target.")
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

    # ── example ──────────────────────────────────────────────────────────────
    example_parser = nouns.add_parser(
        "example", help="Manage examples within a dataset."
    )
    example_sub = example_parser.add_subparsers(dest="verb", metavar="SUBCOMMAND")
    example_sub.required = True

    p = example_sub.add_parser("list", help="List examples in a dataset.")
    p.add_argument(
        "dataset",
        nargs="?",
        default=DEFAULT_DATASET_NAME,
        metavar="name",
        help=f"LangSmith dataset name (default: {DEFAULT_DATASET_NAME})",
    )
    p.add_argument("--no-header", action="store_true", help="Suppress column headers.")
    p.set_defaults(func=cmd_example_list)

    p = example_sub.add_parser("show", help="Print a single example.")
    p.add_argument(
        "dataset",
        type=local_or_remote,
        nargs="?",
        default=DEFAULT_JSONL,
        metavar="name|file.jsonl",
        help=f"Dataset name or local JSONL file (default: {DEFAULT_JSONL.name})",
    )
    p.add_argument("scenario_id", type=int, help="scenario_id from metadata.")
    p.set_defaults(func=cmd_example_show)

    p = example_sub.add_parser(
        "append", help="Append examples from a JSONL file to a dataset."
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
        help=f"Local JSONL file containing examples to append (default: {DEFAULT_JSONL.name})",
    )
    p.set_defaults(func=cmd_example_append)

    p = example_sub.add_parser("remove", help="Remove an example by scenario_id.")
    p.add_argument(
        "dataset",
        nargs="?",
        default=DEFAULT_DATASET_NAME,
        metavar="name",
        help=f"LangSmith dataset name (default: {DEFAULT_DATASET_NAME})",
    )
    p.add_argument("scenario_id", type=int, help="scenario_id from metadata.")
    p.set_defaults(func=cmd_example_remove)

    p = example_sub.add_parser("update", help="Update an example from a JSONL file.")
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
        help=f"Local JSONL file to read the updated example from (default: {DEFAULT_JSONL.name})",
    )
    p.set_defaults(func=cmd_example_update)

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

    p = ex_sub.add_parser(
        "show",
        help="Print run count and mean/stdev per evaluator for an experiment.",
        description=(
            "Print a JSON summary of an experiment: run count, start/end time, "
            "and mean/stdev for each evaluator key. "
            "Scores are aggregated directly from stored runs and feedback rather "
            "than the cached project metadata, which is not always populated."
        ),
    )
    p.add_argument(
        "experiment", metavar="name-or-uuid", help="LangSmith experiment name or UUID."
    )
    p.set_defaults(func=cmd_experiment_show)

    p = ex_sub.add_parser(
        "compare",
        help="Compare two experiments side-by-side: run count and mean (with σ) per evaluator.",
        description=(
            "Print a side-by-side table of run count and mean with standard deviation per evaluator "
            "for two experiments run against the same dataset. "
            "Useful for measuring the effect of a prompt or model change."
        ),
    )
    p.add_argument(
        "experiment1", metavar="name-or-uuid", help="First experiment name or UUID."
    )
    p.add_argument(
        "experiment2", metavar="name-or-uuid", help="Second experiment name or UUID."
    )
    p.set_defaults(func=cmd_experiment_compare)

    p = ex_sub.add_parser(
        "results",
        help="Print per-run inputs, outputs, and evaluator scores as JSONL.",
        description=(
            "Stream one JSON object per run to stdout: inputs, model outputs, "
            "and evaluator feedback scores. "
            "Useful for inspecting individual results or piping to jq / other tools."
        ),
    )
    p.add_argument(
        "experiment", metavar="name-or-uuid", help="LangSmith experiment name or UUID."
    )
    p.set_defaults(func=cmd_experiment_results)

    p = ex_sub.add_parser(
        "stats",
        help=(
            "Print per-evaluator consistency tables: one row per scenario showing "
            "mean, stdev, and score frequency (0.0 / 0.5 / 1.0) across repetitions. "
            "Followed by a scenario key mapping S1, S2, ... to full example queries."
        ),
        description=(
            "Print per-evaluator consistency tables for an experiment. "
            "Each table has one row per scenario showing mean, stdev, and the count "
            "of runs that scored 0.0, 0.5, or 1.0. "
            "Non-standard scores (if any) appear in separate columns to the right. "
            "A scenario key at the end maps S1, S2, ... to the full example query "
            "and repetition count. "
            "Use --evaluator to restrict output to specific evaluators."
        ),
    )
    p.add_argument(
        "experiment", metavar="name-or-uuid", help="LangSmith experiment name or UUID."
    )
    p.add_argument(
        "--evaluator",
        metavar="name",
        action="append",
        help=(
            "Show only this evaluator. Repeatable: "
            "--evaluator 'legal correctness' --evaluator tone."
        ),
    )
    p.set_defaults(func=cmd_experiment_stats)

    # ── runs ──────────────────────────────────────────────────────────────────
    runs_parser = nouns.add_parser("runs", help="Inspect individual runs.")
    runs_sub = runs_parser.add_subparsers(dest="verb", metavar="SUBCOMMAND")
    runs_sub.required = True

    p = runs_sub.add_parser("list", help="List runs in an experiment.")
    p.add_argument(
        "experiment", metavar="name-or-uuid", help="LangSmith experiment name or UUID."
    )
    p.add_argument("--no-header", action="store_true", help="Suppress column headers.")
    p.set_defaults(func=cmd_run_list)

    p = runs_sub.add_parser(
        "exemplars",
        help=(
            "List runs for a specific scenario sorted by evaluator score — "
            "worst to best — so you can pick UUIDs for 'runs trace --verbose'."
        ),
    )
    p.add_argument(
        "experiment", metavar="name-or-uuid", help="LangSmith experiment name or UUID."
    )
    p.add_argument(
        "scenario_id",
        type=int,
        metavar="scenario-id",
        help="scenario_id from 'experiment stats' (the number in brackets, e.g. 3 for [3]).",
    )
    p.add_argument(
        "--evaluator",
        metavar="key",
        required=True,
        help="Evaluator key to sort by (e.g. 'legal correctness').",
    )
    p.add_argument("--no-header", action="store_true", help="Suppress column headers.")
    p.set_defaults(func=cmd_run_exemplars)

    p = runs_sub.add_parser(
        "show", help="Print inputs, outputs, and status for one or more runs."
    )
    p.add_argument("run_id", nargs="+", help="One or more LangSmith run UUIDs.")
    p.set_defaults(func=cmd_run_show)

    p = runs_sub.add_parser("feedback", help="Print evaluator scores for a run.")
    p.add_argument("run_id", help="LangSmith run UUID.")
    p.set_defaults(func=cmd_run_feedback)

    p = runs_sub.add_parser("trace", help="Print the full call tree for a run.")
    p.add_argument("run_id", help="LangSmith run UUID.")
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Include tool call arguments, tool responses, and LLM output at each node.",
    )
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

    hist_parser = nouns.add_parser("history", help="Manage local eval run history.")
    hist_sub = hist_parser.add_subparsers(dest="verb", metavar="SUBCOMMAND")
    hist_sub.required = True

    p = hist_sub.add_parser(
        "baseline",
        help="Print the best prior history entry to use as a regression baseline.",
    )
    p.set_defaults(func=cmd_history_baseline)

    p = hist_sub.add_parser(
        "find",
        help="Print the path of the history entry for a specific experiment.",
    )
    p.add_argument("experiment", help="Experiment name or unique fragment.")
    p.set_defaults(func=cmd_history_find)

    p = hist_sub.add_parser(
        "append",
        help="Append triage or hypotheses content to a history entry.",
    )
    p.add_argument("experiment", help="Experiment name or unique fragment.")
    p.add_argument(
        "--section",
        choices=["triage", "hypotheses"],
        required=True,
        help="Section to update.",
    )
    p.add_argument("--content", required=True, help="Markdown content to write.")
    p.set_defaults(func=cmd_history_append)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
