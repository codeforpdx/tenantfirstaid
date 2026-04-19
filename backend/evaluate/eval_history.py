"""Lab notebook for evaluation runs.

One Markdown file per run lives in backend/eval_log/ (gitignored, so it
persists across git switch/rebase). Each file captures git state, env vars,
the command line, and per-scenario results. The analyze-experiment skill reads
these to establish baselines and appends triage and hypothesis sections after
analysis.

Public API
----------
write_run_entry(...)         — called by run_langsmith_evaluation
write_variance_entry(...)    — called by measure_evaluator_variance
find_baseline() -> Path|None — finds the best prior clean-commit log entry
find_entry(experiment) -> Path|None — locates a log file by experiment name
parse_frontmatter(path) -> dict — extracts key: value pairs from YAML frontmatter
append_section(path, section, content) — replaces placeholder or appends content
"""

import os
import re
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from evaluate.results_display import ScenarioResult

HISTORY_DIR = Path(__file__).parent.parent / "eval_history"

# Non-sensitive env var names and prefixes to capture.
_ENV_EXACT = {
    "MODEL_NAME",
    "ROUTER_MODEL_NAME",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "SHOW_MODEL_THINKING",
}
_ENV_PREFIXES = ("VERTEX_AI_DATASTORE",)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _capture_env() -> dict[str, str]:
    result: dict[str, str] = {}
    for key, val in sorted(os.environ.items()):
        if key in _ENV_EXACT or any(key.startswith(p) for p in _ENV_PREFIXES):
            result[key] = val
    return result


def _git_state() -> dict[str, str | bool]:
    """Return git metadata relevant to reproducibility."""

    def run(*cmd: str) -> str:
        try:
            return subprocess.check_output(
                cmd, text=True, stderr=subprocess.DEVNULL, cwd=HISTORY_DIR.parent
            ).strip()
        except subprocess.CalledProcessError:
            return ""

    commit = run("git", "rev-parse", "HEAD")
    branch = run("git", "rev-parse", "--abbrev-ref", "HEAD")
    prompt_diff = run("git", "diff", "HEAD", "--", "tenantfirstaid/system_prompt.md")
    status = run("git", "status", "--short")
    return {
        "commit": commit,
        "branch": branch,
        "dirty": bool(prompt_diff or status),
        "prompt_diff": prompt_diff,
        "status": status,
    }


def _is_ancestor(commit: str) -> bool:
    """Return True if commit is an ancestor of the current HEAD."""
    if not commit:
        return False
    try:
        subprocess.check_call(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=HISTORY_DIR.parent,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def _sanitize(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "-", name)[:80]


def _entry_path(experiment_name: str) -> Path:
    HISTORY_DIR.mkdir(exist_ok=True)
    gitignore = HISTORY_DIR / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n!.gitignore\n", encoding="utf-8")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return HISTORY_DIR / f"{ts}-{_sanitize(experiment_name)}.md"


def _results_table(scenarios: list[ScenarioResult]) -> list[str]:
    """Format scenario results as a Markdown table."""
    if not scenarios:
        return ["_(no results)_"]

    evaluators = list(scenarios[0].scores.keys())
    header = "| Scenario | n |" + "".join(f" {e} mean | σ |" for e in evaluators)
    sep = "| --- | --- |" + " --- | --- |" * len(evaluators)
    rows = [header, sep]
    for s in scenarios:
        n = len(next(iter(s.scores.values()), []))
        row = f"| S{s.scenario_id} | {n} |"
        for e in evaluators:
            vals = s.scores.get(e, [])
            if vals:
                mean = statistics.mean(vals)
                sigma = statistics.pstdev(vals)
                row += f" {mean:.2f} | {sigma:.2f} |"
            else:
                row += " — | — |"
        rows.append(row)
    return rows


def _write_entry(
    path: Path,
    experiment_name: str,
    entry_type: str,
    git: dict,
    env: dict,
    cmdline: str,
    extra_frontmatter: list[str],
    scenarios: list[ScenarioResult],
) -> None:
    lines: list[str] = [
        "---",
        f"experiment: {experiment_name}",
        f"type: {entry_type}",
        f"timestamp: {datetime.now(timezone.utc).isoformat()}",
        f"git_commit: {git['commit']}",
        f"git_branch: {git['branch']}",
        f"git_dirty: {'true' if git['dirty'] else 'false'}",
    ]
    lines += extra_frontmatter
    lines += [f"cmdline: {cmdline}", "env:"]
    for k, v in env.items():
        lines.append(f"  {k}: {v}")
    lines += ["---", ""]

    # Prompt diff.
    lines += ["## Prompt diff (vs HEAD)", ""]
    diff = str(git.get("prompt_diff", ""))
    if diff:
        lines += ["```diff", diff, "```"]
    else:
        lines.append("_(clean — no uncommitted changes to system_prompt.md)_")
    lines.append("")

    # Git status.
    status = str(git.get("status", ""))
    if status:
        lines += ["## Git status", "", "```", status, "```", ""]

    # Results table.
    lines += ["## Results", ""] + _results_table(scenarios) + [""]

    # Placeholder sections for the skill to fill in.
    lines += [
        "## Triage",
        "",
        "_(to be filled by /analyze-experiment)_",
        "",
        "## Hypotheses",
        "",
        "_(to be filled by /analyze-experiment)_",
        "",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_run_entry(
    experiment_name: str,
    scenarios: list[ScenarioResult],
    dataset_name: str,
    dataset_version: str,
    num_repetitions: int,
) -> Path:
    """Write a log entry for a run_langsmith_evaluation run."""
    git = _git_state()
    env = _capture_env()
    path = _entry_path(experiment_name)
    extra = [
        f"dataset: {dataset_name}",
        f"dataset_version: {dataset_version}",
        f"num_repetitions: {num_repetitions}",
    ]
    _write_entry(
        path=path,
        experiment_name=experiment_name,
        entry_type="evaluation",
        git=git,
        env=env,
        cmdline=" ".join(sys.argv),
        extra_frontmatter=extra,
        scenarios=scenarios,
    )
    print(f"\nEval log: {path}")
    return path


def write_variance_entry(
    experiment_name: str,
    scenarios: list[ScenarioResult],
    k: int,
) -> Path:
    """Write a log entry for a measure_evaluator_variance run."""
    git = _git_state()
    env = _capture_env()
    path = _entry_path(f"variance-{experiment_name}")
    extra = [f"source_experiment: {experiment_name}", f"k: {k}"]
    _write_entry(
        path=path,
        experiment_name=f"variance-{experiment_name}",
        entry_type="variance_measurement",
        git=git,
        env=env,
        cmdline=" ".join(sys.argv),
        extra_frontmatter=extra,
        scenarios=scenarios,
    )
    print(f"\nEval log: {path}")
    return path


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Extract key: value pairs from the YAML frontmatter of a log file."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            result[k.strip()] = v.strip()
    return result


def find_baseline() -> Optional[Path]:
    """Find the best prior log entry to use as a regression baseline.

    Preference order:
    1. Most recent evaluation entry where git_dirty=false, commit is a HEAD
       ancestor, and branch is main.
    2. Most recent evaluation entry where git_dirty=false and commit is a HEAD
       ancestor (any branch).
    3. Most recent evaluation entry where git_dirty=false.
    4. Most recent evaluation entry overall.
    """
    if not HISTORY_DIR.exists():
        return None

    entries = sorted(
        (p for p in HISTORY_DIR.glob("*.md") if not p.name.startswith("variance-")),
        reverse=True,
    )
    if not entries:
        return None

    tiers: list[list[Path]] = [[], [], [], []]
    for path in entries:
        fm = parse_frontmatter(path)
        if fm.get("type") != "evaluation":
            continue
        dirty = fm.get("git_dirty", "true").lower() == "true"
        commit = fm.get("git_commit", "")
        branch = fm.get("git_branch", "")
        is_ancestor = _is_ancestor(commit)

        tiers[3].append(path)
        if not dirty:
            tiers[2].append(path)
            if is_ancestor:
                tiers[1].append(path)
                if branch == "main":
                    tiers[0].append(path)

    for tier in tiers:
        if tier:
            return tier[0]
    return None


def find_entry(experiment_name: str) -> Optional[Path]:
    """Find the log file for a specific experiment name."""
    if not HISTORY_DIR.exists():
        return None
    slug = _sanitize(experiment_name)
    matches = sorted(HISTORY_DIR.glob(f"*-{slug}.md"), reverse=True)
    return matches[0] if matches else None


def append_section(log_path: Path, section: str, content: str) -> None:
    """Replace the placeholder in a section with real content.

    section should be one of: "Triage", "Hypotheses".
    """
    text = log_path.read_text(encoding="utf-8")
    placeholder = "_(to be filled by /analyze-experiment)_"
    # Replace only within the named section to avoid clobbering other sections.
    section_header = f"## {section}"
    idx = text.find(section_header)
    if idx == -1:
        # Section missing — append it.
        text = text.rstrip() + f"\n\n## {section}\n\n{content}\n"
    else:
        block_start = idx + len(section_header)
        # Find the next ## heading or end of file.
        next_section = text.find("\n## ", block_start)
        block = (
            text[block_start:next_section] if next_section != -1 else text[block_start:]
        )
        new_block = block.replace(placeholder, content, 1)
        if new_block == block:
            # Placeholder already replaced — append instead of duplicating.
            new_block = block.rstrip() + f"\n\n{content}\n"
        text = (
            text[:block_start]
            + new_block
            + (text[next_section:] if next_section != -1 else "")
        )
    log_path.write_text(text, encoding="utf-8")
