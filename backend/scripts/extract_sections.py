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