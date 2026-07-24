"""Validate and rewrite .txt law documents to pure ASCII.

Vertex AI RAG ingestion has produced mojibake when UTF-8 is present, so every
.txt under backend/scripts/documents/ must be pure ASCII before upload. Run
via `make enforce-ascii` (pass `ASCII_OPTIONS=--check` for CI validation).
"""

import argparse
import re
import sys
import unicodedata
from collections.abc import Callable
from pathlib import Path

DOCUMENTS_DIR = Path(__file__).parent / "documents" / "or"


class InvalidUtf8Error(RuntimeError):
    """Raised by enforce_ascii when the file cannot be decoded as UTF-8."""


class UnrecognizedAsciiError(RuntimeError):
    """Raised by enforce_ascii when unrecognized non-ASCII characters remain after substitution."""

    def __init__(
        self, message: str, partial_text: str, unrecognized: dict[str, int]
    ) -> None:
        super().__init__(message)
        self.partial_text = partial_text
        self.unrecognized = unrecognized


# Section sign (§) entries are handled in enforce_ascii via re.sub so that
# trailing whitespace is collapsed: both "§ 90" and "§90" become "Section 90".
ASCII_REPLACEMENTS = [
    # Quotes
    ("‘", "'"),  # left single curly quote
    ("’", "'"),  # right single curly quote
    ("“", '"'),  # left double curly quote
    ("”", '"'),  # right double curly quote
    # Spaces
    (" ", " "),  # non-breaking space
    # Dashes and hyphens
    ("—", "--"),  # em-dash
    ("–", "-"),  # en-dash
    ("‐", "-"),  # hyphen (U+2010)
    ("‑", "-"),  # non-breaking hyphen
    ("‒", "-"),  # figure dash
    # Bullets
    ("•", "-"),  # bullet
    ("‣", "-"),  # triangular bullet
    ("·", "-"),  # middle dot
    # Symbols
    ("©", "(c)"),  # copyright
    ("®", "(R)"),  # registered trademark
    ("™", "(TM)"),  # trademark
    ("…", "..."),  # ellipsis
    ("°", " degrees"),  # degree sign (e.g. minimum heating requirements)
    # Fractions
    ("½", "1/2"),
    ("¼", "1/4"),
    ("¾", "3/4"),
]


def _apply_ascii_replacements(text: str) -> str:
    section_sign = "§"
    text = re.sub(section_sign * 2 + r"\s*", "Sections ", text)
    text = re.sub(section_sign + r"\s*", "Section ", text)
    for orig, repl in ASCII_REPLACEMENTS:
        text = text.replace(orig, repl)
    return text


def _collect_unrecognized(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for i, c in enumerate(text):
        if ord(c) > 127 and c not in result:
            result[c] = i
    return result


def _suggest_ascii(char: str) -> str:
    base = (
        unicodedata.normalize("NFKD", char)
        .encode("ascii", errors="ignore")
        .decode("ascii")
    )
    return base


def enforce_ascii(path: Path) -> str | None:
    """Return ASCII-rewritten text for path, or None if already ASCII. Does not write to disk.

    Raises InvalidUtf8Error or UnrecognizedAsciiError on failure.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise InvalidUtf8Error(
            f"{path.name}: file is not valid UTF-8 -- re-save as UTF-8 before running."
        ) from e

    if text.isascii():
        return None

    text = _apply_ascii_replacements(text)

    unrecognized = _collect_unrecognized(text)
    if unrecognized:
        lines = []
        for char, pos in unrecognized.items():
            suggestion = _suggest_ascii(char)
            if suggestion:
                lines.append(
                    f'    consider adding ("{char}", "{suggestion}") '
                    "to ASCII_REPLACEMENTS in scripts/enforce_ascii.py"
                )
            else:
                lines.append(
                    f"    {repr(char)} ({unicodedata.name(char, repr(char))}, pos {pos})"
                    " -- no obvious replacement, fix the source file"
                )
        n = len(unrecognized)
        raise UnrecognizedAsciiError(
            f"{path.name}: {n} unrecognized non-ASCII character{'s' if n > 1 else ''}:\n"
            + "\n".join(lines),
            partial_text=text,
            unrecognized=unrecognized,
        )

    return text


def print_warning_table(
    file_issues: list[tuple[str, dict[str, int] | None]],
) -> None:
    rows: list[tuple[str, str, str, str]] = []
    for filename, unrecognized in file_issues:
        if unrecognized is None:
            rows.append(
                (filename, "-", "invalid UTF-8", "re-save as UTF-8 before running")
            )
        else:
            for j, (char, _pos) in enumerate(unrecognized.items()):
                fname = filename if j == 0 else ""
                name = unicodedata.name(char, f"U+{ord(char):04X}")
                suggestion = _suggest_ascii(char)
                repl = (
                    f'("{char}", "{suggestion}")'
                    if suggestion
                    else "no obvious replacement -- fix source file"
                )
                rows.append((fname, char, name, repl))

    if not rows:
        return

    headers = ["File", "Char", "Unicode Name", "Add to ASCII_REPLACEMENTS"]
    widths = [max(max(len(r[i]) for r in rows), len(headers[i])) for i in range(4)]
    sep = "  ".join("-" * w for w in widths)
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))

    n = len(file_issues)
    print(
        f"\nWarning: {n} file(s) had unrecognized non-ASCII characters. "
        "Known replacements were applied where possible.\n"
        f"{header_line}\n{sep}",
        file=sys.stderr,
    )
    for row in rows:
        print(
            "  ".join(row[i].ljust(widths[i]) for i in range(4)),
            file=sys.stderr,
        )
    print(
        "To add replacements, edit ASCII_REPLACEMENTS in scripts/enforce_ascii.py.",
        file=sys.stderr,
    )


def validate_and_rewrite_tree(
    root: Path,
    *,
    file_filter: Callable[[Path], bool] | None = None,
    check_only: bool = False,
) -> None:
    """Walk root for .txt files, apply ASCII replacements in place, and validate.

    In check_only mode, raises without writing if any rewrites would be needed.
    Otherwise applies partial rewrites even when some files fail, so the next
    run sees progress.
    """
    file_issues: list[tuple[str, dict[str, int] | None]] = []
    pending_rewrites: list[tuple[Path, str, str]] = []  # (path, text, encoding)

    for txt_file in sorted(root.rglob("*.txt")):
        if file_filter is not None and not file_filter(txt_file):
            continue
        try:
            rewritten = enforce_ascii(txt_file)
            if rewritten is not None:
                pending_rewrites.append((txt_file, rewritten, "ascii"))
        except InvalidUtf8Error:
            file_issues.append((txt_file.name, None))
        except UnrecognizedAsciiError as e:
            pending_rewrites.append((txt_file, e.partial_text, "utf-8"))
            file_issues.append((txt_file.name, e.unrecognized))

    if check_only:
        if pending_rewrites or file_issues:
            print_warning_table(file_issues)
            # Partial rewrites appear in both lists; subtract them out to count
            # only files that would be cleanly rewritten.
            n_rewrites = len(pending_rewrites) - len(
                [f for f in file_issues if f[1] is not None]
            )
            raise RuntimeError(
                f"ASCII validation failed: {len(file_issues)} file(s) with issues, "
                f"{n_rewrites} file(s) would be rewritten."
            )
        return

    for path, text, encoding in pending_rewrites:
        path.write_text(text, encoding=encoding)

    if file_issues:
        print_warning_table(file_issues)
        raise RuntimeError(
            f"{len(file_issues)} file(s) failed ASCII validation -- see warnings above."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=DOCUMENTS_DIR,
        help=f"Directory to walk (default: {DOCUMENTS_DIR}).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate only; do not rewrite files. Exit nonzero if any rewrites would occur.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_and_rewrite_tree(args.root, check_only=args.check)
    if args.check:
        print(f"OK: {args.root} is pure ASCII.")
    else:
        print(f"OK: {args.root} is pure ASCII (rewrites applied where needed).")


if __name__ == "__main__":
    main()
