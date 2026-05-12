# Corpus Dataset

Reference for adding or modifying law documents in `backend/scripts/documents/`.

## ASCII requirement

All `.txt` files must be **pure ASCII**. Vertex AI RAG ingestion has produced mojibake when UTF-8 is present. Before committing any `.txt` file, verify:

```bash
LC_ALL=C grep -n '[^[:print:][:space:]]' path/to/file.txt  # must produce no output
```

`make generate-metadata` auto-converts all known offenders in place and warns with a suggested replacement for any it cannot handle.

### Common replacements

| Character | Unicode | Replace with |
|---|---|---|
| `'` | U+2019 right single quote | `'` |
| `"` `"` | U+201C/U+201D double quotes | `"` |
| `§` | U+00A7 section sign | `Section ` |
| `§§` | U+00A7 U+00A7 | `Sections ` |
| `—` | U+2014 em dash | `--` |
| `–` | U+2013 en dash | `-` |
| `•` | U+2022 bullet | `-` |

See `ASCII_REPLACEMENTS` in `backend/scripts/generate_metadata_jsonl.py` for the full list.

## Publication cadence

Oregon publishes statutes and annotations on offset biennial cycles:

- **Statutes** (`ORS*.txt`, `OAR*.txt`) — published in odd years after each long legislative session. [Current edition](https://www.oregonlegislature.gov/bills_laws/pages/ors.aspx).
- **Annotations** (`ORS*_annotations.txt`) — published in the fall of each even-numbered year as a Cumulative Supplement. [Current edition](https://www.oregonlegislature.gov/bills_laws/Pages/Annotations.aspx).

This is why statutes and annotations live in different year subfolders.

## URL patterns

Chapter pages are at predictable URLs (`NNN` = three-digit zero-padded chapter number, lowercase letter suffix for sub-chapters):

- Statutes: `https://www.oregonlegislature.gov/bills_laws/ors/orsNNN.html`
- Annotations: `https://www.oregonlegislature.gov/bills_laws/ors/anoNNN.html`

Examples: chapter 90 → `ors090.html` / `ano090.html`; chapter 659A → `ors659a.html` / `ano659a.html`.
