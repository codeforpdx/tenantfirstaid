"""Build a per-section JSONL corpus from the source legal documents.

Instead of uploading large monolithic files to Vertex AI (which causes the
retriever to surface cross-references rather than the actual statute text),
this script splits each document by section and writes one JSON object per
section to a single corpus.jsonl file.

Each line has the shape:
    {
        "id":      "<unique identifier>",
        "title":   "<section title>",
        "content": "<full section text>",
        "state":   "or",
        "city":    "null" | "portland" | "eugene"
    }

Usage:
    uv run python scripts/create_corpus_jsonl.py [--out PATH] [--dry-run]
"""

import argparse
import json
import logging
import re
from collections.abc import Generator
from pathlib import Path

logger = logging.getLogger(__name__)

DOCUMENTS_DIR = Path(__file__).parent / "documents"
DEFAULT_OUT = DOCUMENTS_DIR / "corpus.jsonl"

# --- section splitters ---------------------------------------------------

# ORS/OAR files: "      90.260 Title text..."  (6 leading spaces)
# The 6-space indent is a formatting convention in the downloaded .txt exports
# from the Oregon Legislature website.  If a source document is refreshed and
# the splitter stops producing sections
_ORS_HEADER = re.compile(r"^      (\d+\.\d+) (.+?)(?:\.\s|$)", re.MULTILINE)

# OAR files: "411-054-0000" on its own line, title on the next line
_OAR_HEADER = re.compile(r"^(411-\d+-\d+)\s*$", re.MULTILINE)

# Portland PCC: "30.01.085 Portland Renter Additional Protections."
_PCC_HEADER = re.compile(r"^(30\.\d+\.\d+)\s+(.+?)\.?\s*$", re.MULTILINE)

# Eugene EHC: "8.425" as part of the single-section file — treat as one doc
_EHC_ID = "EHC8.425"


def _split_by_pattern(text: str, pattern: re.Pattern, id_prefix: str) -> list[dict]:
    """Generic splitter: find all header matches, slice content between them."""
    matches = list(pattern.finditer(text))
    if not matches:
        return []

    entries = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        entries.append(
            {
                "id": f"{id_prefix}_{m.group(1)}",
                "title": m.group(2).strip() if m.lastindex >= 2 else m.group(1),
                "content": content,
            }
        )
    return entries


def _split_ors(text: str, stem: str) -> list[dict]:
    return _split_by_pattern(text, _ORS_HEADER, stem)


def _split_oar(text: str, id_prefix: str) -> list[dict]:
    """OAR: section id on its own line, title on the following line."""
    lines = text.splitlines()
    entries = []
    i = 0
    while i < len(lines):
        m = _OAR_HEADER.match(lines[i])
        if m:
            section_id = m.group(1)
            title = lines[i + 1].strip() if i + 1 < len(lines) else section_id
            # Collect content until the next section header or EOF
            body_lines = []
            j = i + 1
            while j < len(lines) and not _OAR_HEADER.match(lines[j]):
                body_lines.append(lines[j])
                j += 1
            entries.append(
                {
                    "id": f"{id_prefix}_{section_id}",
                    "title": title,
                    "content": "\n".join(body_lines).strip(),
                }
            )
            i = j
        else:
            i += 1
    return entries


def _split_pcc(text: str) -> list[dict]:
    """Portland PCC30.01: section headers are 'NN.NN.NNN Title.' lines.

    The file starts with a table-of-contents that lists each section on a
    single line.  The actual content sections appear later with the same
    header followed by substantive text.  We deduplicate by keeping only the
    last occurrence of each section id (the real content beats the TOC entry).
    """
    all_entries = _split_by_pattern(text, _PCC_HEADER, "PCC30.01")
    # Last wins: real sections appear after the TOC
    seen: dict[str, dict] = {}
    for entry in all_entries:
        seen[entry["id"]] = entry
    return list(seen.values())


# --- document registry ---------------------------------------------------


def _iter_documents() -> Generator[tuple[dict, str, str], None, None]:
    """Yield (metadata, text, file_stem) for every source document."""
    or_dir = DOCUMENTS_DIR / "or"

    # State-level ORS / OAR files
    state_files = [
        ("ORS090", "or", "null"),
        ("ORS091", "or", "null"),
        ("ORS105", "or", "null"),
        ("ORS109", "or", "null"),
        ("ORS659A", "or", "null"),
        ("OAR54", "or", "null"),
    ]
    for stem, state, city in state_files:
        path = or_dir / f"{stem}.txt"
        if path.exists():
            yield {"state": state, "city": city}, path.read_text(encoding="utf-8"), stem

    # City files
    city_files = [
        (or_dir / "portland" / "PCC30.01.txt", "or", "portland", "PCC30.01"),
        (or_dir / "eugene" / "EHC8.425.txt", "or", "eugene", "EHC8.425"),
    ]
    for path, state, city, stem in city_files:
        if path.exists():
            yield {"state": state, "city": city}, path.read_text(encoding="utf-8"), stem


def _sections_for(meta: dict, text: str, stem: str) -> list[dict]:
    """Return a list of section dicts for a given source file."""
    if stem.startswith("ORS"):
        sections = _split_ors(text, stem)
    elif stem.startswith("OAR"):
        sections = _split_oar(text, id_prefix=stem)
    elif stem == "PCC30.01":
        sections = _split_pcc(text)
    elif stem == "EHC8.425":
        # Single-section file — emit as one document
        sections = [
            {
                "id": _EHC_ID,
                "title": "Eugene Housing Code 8.425",
                "content": text.strip(),
            }
        ]
    else:
        sections = []

    # Fallback for files where no section headers were detected.
    if not sections:
        logger.warning("No sections parsed for %s — emitting as single document", stem)
        sections = [{"id": stem, "title": stem, "content": text.strip()}]

    # Attach jurisdiction metadata to every section
    for s in sections:
        s["state"] = meta["state"]
        s["city"] = meta["city"]

    return sections


# --- main ----------------------------------------------------------------


def run(out_path: Path, dry_run: bool) -> None:
    all_sections: list[dict] = []

    for meta, text, stem in _iter_documents():
        sections = _sections_for(meta, text, stem)
        print(f"{stem}: {len(sections)} section(s)")
        all_sections.extend(sections)

    print(f"\nTotal: {len(all_sections)} entries")

    if dry_run:
        print(f"[dry-run] would write {out_path}")
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for section in all_sections:
            f.write(json.dumps(section, ensure_ascii=False) + "\n")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run(args.out, args.dry_run)
