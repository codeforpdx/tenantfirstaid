"""CLI for manipulating LangSmith datasets, scenarios, experiments, and runs.

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
"""

import argparse
import json
import os
import sys
from pathlib import Path

import jsonschema
from langsmith import Client
from langsmith import utils as langsmith_utils

EVALUATE_DIR = Path(__file__).parent
DEFAULT_SCHEMA = EVALUATE_DIR / "langsmith_dataset_schema.json"


def make_client() -> Client:
    # The Client targets the workspace associated with LANGSMITH_API_KEY.
    # To target a different workspace, pass its UUID via the workspace_id
    # parameter — there is no name-based workspace resolution in the SDK.
    import dotenv

    dotenv.load_dotenv(override=True)
    return Client(api_key=os.getenv("LANGSMITH_API_KEY"))


# ── dataset subcommands ────────────────────────────────────────────────────────


def cmd_dataset_list(args: argparse.Namespace) -> None:
    client = make_client()
    datasets = list(client.list_datasets())
    if not datasets:
        print("No datasets found.")
        return
    for ds in datasets:
        print(f"  {ds.name}   (id: {ds.id})")


def cmd_dataset_create(args: argparse.Namespace) -> None:
    client = make_client()
    if client.has_dataset(dataset_name=args.name):
        print(f"Dataset '{args.name}' already exists.")
        sys.exit(1)
    else:
        ds = client.create_dataset(dataset_name=args.name)
        print(f"Created '{args.name}' (id: {ds.id}).")


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

    examples = [
        json.loads(line)
        for line in local.read_text().splitlines()
        if line.strip() and not line.startswith("//")
    ]

    try:
        ds = client.read_dataset(dataset_name=args.remote)
    except Exception:
        ds = client.create_dataset(dataset_name=args.remote)

    for ex in examples:
        client.create_example(
            inputs=ex["inputs"],
            outputs=ex["outputs"],
            metadata=ex.get("metadata"),
            dataset_id=ds.id,
        )
    print(f"Pushed {len(examples)} examples to '{args.remote}'.")


def cmd_dataset_pull(args: argparse.Namespace) -> None:
    local: Path = args.file
    client = make_client()

    ds = client.read_dataset(dataset_name=args.remote)
    examples = list(client.list_examples(dataset_id=ds.id))

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
        return [
            json.loads(line)
            for line in ref.read_text().splitlines()
            if line.strip() and not line.startswith("//")
        ]
    ds = client.read_dataset(dataset_name=ref)
    return [
        {"metadata": ex.metadata, "inputs": ex.inputs, "outputs": ex.outputs}
        for ex in client.list_examples(dataset_id=ds.id)
    ]


def _scenario_id(example: dict) -> int | None:
    return (example.get("metadata") or {}).get("scenario_id")


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
    for i, line in enumerate(args.file.read_text().splitlines(), 1):
        if not line.strip() or line.startswith("//"):
            continue
        for error in validator.iter_errors(json.loads(line)):
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
    for ex in sorted(examples, key=lambda e: (e.metadata or {}).get("scenario_id", 0)):
        sid = (ex.metadata or {}).get("scenario_id", "?")
        tags = (ex.metadata or {}).get("tags", [])
        query = (ex.inputs or {}).get("query", "")[:80]
        print(f"  {sid:>4}  {str(tags):<40}  {query}")


def cmd_scenario_show(args: argparse.Namespace) -> None:
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
    ex = matches[0]
    print(
        json.dumps(
            {"metadata": ex.metadata, "inputs": ex.inputs, "outputs": ex.outputs},
            indent=2,
        )
    )


def cmd_scenario_append(args: argparse.Namespace) -> None:
    local: Path = args.file
    client = make_client()
    ds = client.read_dataset(dataset_name=args.dataset)

    examples = [
        json.loads(line)
        for line in local.read_text().splitlines()
        if line.strip() and not line.startswith("//")
    ]
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
    for p in projects:
        print(f"  {p.name}  (id: {p.id})")


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
    projects = [
        client.read_project(project_name=name)
        for name in (args.experiment1, args.experiment2)
    ]
    for p in projects:
        print(f"\n{p.name}")
        print(f"  runs:     {p.run_count}")
        for key, stats in (p.feedback_stats or {}).items():
            print(f"  {key}: {stats}")


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
    for run in client.list_runs(project_id=p.id, execution_order=1):
        print(f"  {run.id}  {run.name}  status={run.status}")


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
    p.set_defaults(func=cmd_dataset_list)

    p = ds_sub.add_parser("create", help="Create a new empty dataset.")
    p.add_argument("name", metavar="name")
    p.set_defaults(func=cmd_dataset_create)

    p = ds_sub.add_parser("delete", help="Delete a dataset.")
    p.add_argument("name", metavar="name")
    p.set_defaults(func=cmd_dataset_delete)

    p = ds_sub.add_parser("push", help="Upload a local JSONL file to a dataset.")
    p.add_argument("file", type=Path, metavar="file.jsonl")
    p.add_argument("remote", metavar="name")
    p.set_defaults(func=cmd_dataset_push)

    p = ds_sub.add_parser("pull", help="Download a dataset to a local JSONL file.")
    p.add_argument("remote", metavar="name")
    p.add_argument("file", type=Path, metavar="file.jsonl")
    p.set_defaults(func=cmd_dataset_pull)

    p = ds_sub.add_parser("diff", help="Diff two datasets by scenario_id.")
    p.add_argument("left", type=local_or_remote, metavar="name|file.jsonl")
    p.add_argument("right", type=local_or_remote, metavar="name|file.jsonl")
    p.set_defaults(func=cmd_dataset_diff)

    p = ds_sub.add_parser("merge", help="Copy new scenarios from source into target.")
    p.add_argument("source", type=local_or_remote, metavar="name|file.jsonl")
    p.add_argument("target", metavar="name")
    p.set_defaults(func=cmd_dataset_merge)

    p = ds_sub.add_parser(
        "validate", help="Validate a local JSONL file against the schema."
    )
    p.add_argument("file", type=Path, metavar="file.jsonl")
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
    p.add_argument("dataset", metavar="name")
    p.set_defaults(func=cmd_scenario_list)

    p = sc_sub.add_parser("show", help="Print a single scenario.")
    p.add_argument("dataset", metavar="name")
    p.add_argument("scenario_id", type=int)
    p.set_defaults(func=cmd_scenario_show)

    p = sc_sub.add_parser(
        "append", help="Append scenarios from a JSONL file to a dataset."
    )
    p.add_argument("dataset", metavar="name")
    p.add_argument("file", type=Path, metavar="file.jsonl")
    p.set_defaults(func=cmd_scenario_append)

    p = sc_sub.add_parser("remove", help="Remove a scenario by scenario_id.")
    p.add_argument("dataset", metavar="name")
    p.add_argument("scenario_id", type=int)
    p.set_defaults(func=cmd_scenario_remove)

    p = sc_sub.add_parser("update", help="Update a scenario from a JSONL file.")
    p.add_argument("dataset", metavar="name")
    p.add_argument("scenario_id", type=int)
    p.add_argument("file", type=Path, metavar="file.jsonl")
    p.set_defaults(func=cmd_scenario_update)

    # ── experiment ───────────────────────────────────────────────────────────
    ex_parser = nouns.add_parser("experiment", help="Inspect experiments.")
    ex_sub = ex_parser.add_subparsers(dest="verb", metavar="SUBCOMMAND")
    ex_sub.required = True

    p = ex_sub.add_parser("list", help="List experiments run against a dataset.")
    p.add_argument("dataset", metavar="name")
    p.set_defaults(func=cmd_experiment_list)

    p = ex_sub.add_parser("show", help="Print aggregate results for an experiment.")
    p.add_argument("experiment", metavar="name")
    p.set_defaults(func=cmd_experiment_show)

    p = ex_sub.add_parser("compare", help="Compare scores for two experiments.")
    p.add_argument("experiment1", metavar="name")
    p.add_argument("experiment2", metavar="name")
    p.set_defaults(func=cmd_experiment_compare)

    p = ex_sub.add_parser("results", help="Print per-scenario results as JSONL.")
    p.add_argument("experiment", metavar="name")
    p.set_defaults(func=cmd_experiment_results)

    # ── run ──────────────────────────────────────────────────────────────────
    run_parser = nouns.add_parser("run", help="Inspect individual runs.")
    run_sub = run_parser.add_subparsers(dest="verb", metavar="SUBCOMMAND")
    run_sub.required = True

    p = run_sub.add_parser("list", help="List runs in an experiment.")
    p.add_argument("experiment", metavar="name")
    p.set_defaults(func=cmd_run_list)

    p = run_sub.add_parser("show", help="Print inputs, outputs, and status for a run.")
    p.add_argument("run_id")
    p.set_defaults(func=cmd_run_show)

    p = run_sub.add_parser("feedback", help="Print evaluator scores for a run.")
    p.add_argument("run_id")
    p.set_defaults(func=cmd_run_feedback)

    p = run_sub.add_parser("trace", help="Print the full call tree for a run.")
    p.add_argument("run_id")
    p.set_defaults(func=cmd_run_trace)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
