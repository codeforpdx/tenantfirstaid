'''

# This commented code is a script that writes the sections.json file from the statute in our prompt text.

import json
import pathlib
import re
import sys
from . import shared

SECTION_RE = re.compile(r'^\s{2,}(\d+\.\d+)\s+(.*)$')

def parse_sections() -> dict[str, str]:
    """Return {section_number: body_text} for the file at *path*."""
    sections: dict[str, str] = {}
    current_key: str | None = None
    buffer: list[str] = []

    for line in shared.LONG_PROMPT_TEXT.split("\n"):
        # print(line)
        m = SECTION_RE.match(line)
        
        if m:
            if current_key is not None:                     # flush previous
                sections[current_key] = "\n".join(buffer).strip()

            current_key = m.group(1)
            remainder  = m.group(2).rstrip()
            buffer = [remainder] if remainder else []       # new
        else:
            if current_key is not None:
                buffer.append(line)

    # Don’t forget the final section.
    if current_key is not None:
        sections[current_key] = "\n".join(buffer).strip()

    return sections


def main() -> None:
    out = pathlib.Path("sections.json")

    data = parse_sections()
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

main()

'''

import json
import pathlib
from flask import request, jsonify, abort

DATA_PATH = pathlib.Path(__file__).with_name("sections.json")
with DATA_PATH.open(encoding="utf-8") as f:
    SECTIONS = json.load(f)

def get_citation():
    """
    GET /api/citation?section=90.101
    → 200 {"section": "90.101", "text": "..."}
    → 400 if param missing, 404 if unknown
    """
    section = request.args.get("section")
    if not section:
        abort(400, description="missing query param ?section=<number>")

    body = SECTIONS.get(section)
    if body is None:
        abort(404, description=f"section {section} not found")

    return jsonify({"section": section, "text": body})