"""Query the Vertex AI Search datastore directly, bypassing LangChain/LangGraph.

Useful for debugging retrieval quality independently of the agent framework:
what passages does the datastore actually return for a given query and filter?

Usage:
    uv run python -m scripts.vertex_ai_search search "security deposit interest" --state or
    uv run python -m scripts.vertex_ai_search search "ORS 90.155 notice delivery" --state or --city portland
    uv run python -m scripts.vertex_ai_search search "nonpayment notice timing" --state or --max-results 10
    uv run python -m scripts.vertex_ai_search search "ORS 90.427" --state or --raw

    # Sweep extraction params to find diminishing returns:
    uv run python -m scripts.vertex_ai_search shmoo \\
        "72 hour nonpayment notice week-to-week ORS 90.394" \\
        --target "fifth day" --state or
"""

import argparse
import json
import textwrap
from typing import TypedDict

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1beta as discoveryengine

from tenantfirstaid.constants import SINGLETON, DatastoreKey
from tenantfirstaid.google_auth import load_gcp_credentials
from tenantfirstaid.langchain_tools import filter_builder, repair_mojibake
from tenantfirstaid.location import OregonCity, UsaState

SearchResult = discoveryengine.SearchResponse.SearchResult


class Passage(TypedDict):
    doc_id: str
    type: str
    content: str


class SearchResults(TypedDict):
    corrected_query: str
    results: list[SearchResult]


def search(
    query: str,
    *,
    state: UsaState,
    city: OregonCity | None = None,
    max_results: int = 5,
    max_extractive_answer_count: int = 5,
    max_extractive_segment_count: int = 3,
    spell_correction: discoveryengine.SearchRequest.SpellCorrectionSpec.Mode = discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO,
    datastore_override: str | None = None,
) -> SearchResults:
    """Run a search against the Vertex AI Search datastore and return results."""
    credentials = load_gcp_credentials(SINGLETON.GOOGLE_APPLICATION_CREDENTIALS)

    location = SINGLETON.GOOGLE_CLOUD_LOCATION
    # https://cloud.google.com/generative-ai-app-builder/docs/locations#specify_a_multi-region_for_your_data_store
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    client = discoveryengine.SearchServiceClient(
        credentials=credentials,
        client_options=client_options,
    )

    datastore = datastore_override or SINGLETON.VERTEX_AI_DATASTORES[DatastoreKey.LAWS]
    serving_config = (
        f"projects/{SINGLETON.GOOGLE_CLOUD_PROJECT}"
        f"/locations/{location}"
        f"/collections/default_collection"
        f"/dataStores/{datastore}"
        f"/servingConfigs/default_serving_config"
    )

    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
            max_extractive_answer_count=max_extractive_answer_count,
            max_extractive_segment_count=max_extractive_segment_count,
        ),
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True,
        ),
    )

    spell_correction_spec = discoveryengine.SearchRequest.SpellCorrectionSpec(
        mode=spell_correction,
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=max_results,
        filter=filter_builder(state, city),
        content_search_spec=content_search_spec,
        spell_correction_spec=spell_correction_spec,
    )

    pager = client.search(request)
    return SearchResults(
        corrected_query=pager.corrected_query,
        results=list(pager),
    )


def _collect_passages(response: SearchResults) -> list[Passage]:
    """Collect all extractive answers and segments from a search response."""
    passages: list[Passage] = []
    for result in response["results"]:
        doc = result.document
        struct = doc.derived_struct_data
        if not struct:
            continue
        doc_id = doc.id or "(no id)"
        for answer in struct.get("extractive_answers", []):
            content = repair_mojibake(answer.get("content", ""))
            passages.append({"doc_id": doc_id, "type": "answer", "content": content})
        for segment in struct.get("extractive_segments", []):
            content = repair_mojibake(segment.get("content", ""))
            passages.append({"doc_id": doc_id, "type": "segment", "content": content})
    return passages


def _print_results(
    response: SearchResults,
    *,
    raw: bool = False,
    width: int = 100,
) -> None:
    """Pretty-print search results to stdout."""
    if response["corrected_query"]:
        print(f"Spell-corrected query: {response['corrected_query']}\n")

    count = 0
    for i, result in enumerate(response["results"], 1):
        count = i
        doc = result.document
        struct = doc.derived_struct_data

        doc_id = doc.id or "(no id)"
        title = struct.get("title", "(no title)") if struct else "(no struct_data)"

        print(f"── Result {i}: {title} ──")
        print(f"  doc_id: {doc_id}")

        if struct:
            link = struct.get("link", "")
            if link:
                print(f"  link:   {link}")

            for j, answer in enumerate(struct.get("extractive_answers", [])):
                content = repair_mojibake(answer.get("content", ""))
                page = answer.get("pageNumber", "?")
                wrapped = textwrap.fill(
                    content,
                    width=width,
                    initial_indent="    ",
                    subsequent_indent="    ",
                )
                print(f"  extractive_answer[{j}] (page {page}):")
                print(wrapped)

            for j, segment in enumerate(struct.get("extractive_segments", [])):
                content = repair_mojibake(segment.get("content", ""))
                page = segment.get("pageNumber", "?")
                wrapped = textwrap.fill(
                    content,
                    width=width,
                    initial_indent="    ",
                    subsequent_indent="    ",
                )
                print(f"  extractive_segment[{j}] (page {page}):")
                print(wrapped)

            for j, snippet in enumerate(struct.get("snippets", [])):
                text = repair_mojibake(snippet.get("snippet", ""))
                wrapped = textwrap.fill(
                    text,
                    width=width,
                    initial_indent="    ",
                    subsequent_indent="    ",
                )
                print(f"  snippet[{j}]:")
                print(wrapped)

        if raw:
            print("  raw_struct_data:")
            print(
                textwrap.indent(
                    json.dumps(
                        dict(struct) if struct else {},
                        indent=2,
                        default=str,
                    ),
                    "    ",
                )
            )

        print()

    if count == 0:
        print("No results found.")
    else:
        print(f"({count} results)")


def _shmoo(
    query: str,
    *,
    state: UsaState,
    city: OregonCity | None = None,
    max_results: int = 5,
    targets: list[str],
    max_answer_sweep: int = 5,
    max_segment_sweep: int = 10,
    datastore_override: str | None = None,
) -> None:
    """Sweep extractive answer and segment counts, reporting where targets appear."""
    targets_lower = [t.lower() for t in targets]

    def _check(passages: list[Passage]) -> list[str]:
        """Return deduplicated list of strings of the form "doc_id:type" where any target matched."""
        seen: set[str] = set()
        hits = []
        for p in passages:
            key = f"{p['doc_id']}:{p['type']}"
            content_lower = p["content"].lower()
            if key not in seen and any(t in content_lower for t in targets_lower):
                seen.add(key)
                hits.append(key)
        return hits

    print(f"Query:   {query}")
    print(f"Filter:  {filter_builder(state, city)}")
    print(f"Targets: {targets}")
    print(f"Docs:    {max_results}")
    print()

    # Each axis is swept independently with the other fixed at 1, avoiding O(m×n)
    # API calls. The independent maxima are sufficient for tuning each parameter.

    # Sweep extractive answers (segments fixed at 1).
    print(f"{'answers':>8}  {'hits':>4}  where")
    print(f"{'-------':>8}  {'----':>4}  -----")
    prev_hit_count = 0
    for n in range(1, max_answer_sweep + 1):
        response = search(
            query,
            state=state,
            city=city,
            max_results=max_results,
            max_extractive_answer_count=n,
            max_extractive_segment_count=1,
            datastore_override=datastore_override,
        )
        passages = _collect_passages(response)
        hits = _check(passages)
        marker = "  <-- new" if len(hits) > prev_hit_count else ""
        locations = ", ".join(hits) if hits else "(none)"
        print(f"{n:>8}  {len(hits):>4}  {locations}{marker}")
        prev_hit_count = len(hits)

    print()

    # Sweep extractive segments (answers fixed at 1).
    print(f"{'segments':>8}  {'hits':>4}  where")
    print(f"{'--------':>8}  {'----':>4}  -----")
    prev_hit_count = 0
    for n in range(1, max_segment_sweep + 1):
        response = search(
            query,
            state=state,
            city=city,
            max_results=max_results,
            max_extractive_answer_count=1,
            max_extractive_segment_count=n,
            datastore_override=datastore_override,
        )
        passages = _collect_passages(response)
        hits = _check(passages)
        marker = "  <-- new" if len(hits) > prev_hit_count else ""
        locations = ", ".join(hits) if hits else "(none)"
        print(f"{n:>8}  {len(hits):>4}  {locations}{marker}")
        prev_hit_count = len(hits)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query Vertex AI Search directly, bypassing LangChain",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # Shared arguments.
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--state", type=str, default="or", help="State filter (e.g. 'or')"
    )
    shared.add_argument(
        "--city", type=str, default=None, help="City filter (e.g. 'portland', 'eugene')"
    )
    shared.add_argument(
        "--max-results", type=int, default=5, help="Maximum number of documents"
    )
    shared.add_argument(
        "--datastore",
        type=str,
        default=None,
        metavar="DATASTORE_ID",
        help="Override the VERTEX_AI_DATASTORE from the environment (e.g. to test an alternate corpus)",
    )

    # Default: single search.
    search_parser = subparsers.add_parser(
        "search", parents=[shared], help="Run a single search query"
    )
    search_parser.add_argument("query", help="Search query text")
    search_parser.add_argument(
        "--answers", type=int, default=5, help="Extractive answers per document"
    )
    search_parser.add_argument(
        "--segments", type=int, default=3, help="Extractive segments per document"
    )
    search_parser.add_argument(
        "--raw", action="store_true", help="Print raw struct_data JSON"
    )
    search_parser.add_argument(
        "--width", type=int, default=100, help="Text wrapping width"
    )

    # Shmoo: sweep extraction params.
    shmoo_parser = subparsers.add_parser(
        "shmoo",
        parents=[shared],
        help="Sweep extraction params to find diminishing returns",
    )
    shmoo_parser.add_argument("query", help="Search query text")
    shmoo_parser.add_argument(
        "--target",
        action="append",
        required=True,
        dest="targets",
        help="Substring to look for in results (repeatable)",
    )
    shmoo_parser.add_argument(
        "--max-answer-sweep",
        type=int,
        default=5,
        help="Max extractive answer count to sweep (API caps at 5)",
    )
    shmoo_parser.add_argument(
        "--max-segment-sweep",
        type=int,
        default=10,
        help="Max extractive segment count to sweep",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        raise SystemExit(1)

    state = UsaState.from_maybe_str(args.state)
    city = OregonCity.from_maybe_str(args.city) if args.city else None
    if args.city and city is None:
        print(f"Warning: unrecognized city '{args.city}', no city filter applied.")

    datastore = args.datastore or SINGLETON.VERTEX_AI_DATASTORES[DatastoreKey.LAWS]

    if args.command == "shmoo":
        _shmoo(
            args.query,
            state=state,
            city=city,
            max_results=args.max_results,
            targets=args.targets,
            max_answer_sweep=args.max_answer_sweep,
            max_segment_sweep=args.max_segment_sweep,
            datastore_override=args.datastore,
        )
        return

    # "search" command.
    print(f"Query:     {args.query}")
    print(f"Filter:    {filter_builder(state, city)}")
    print(f"Datastore: {datastore}")
    print(f"Docs:      {args.max_results}")
    print(f"Answers:   {args.answers}")
    print(f"Segments:  {args.segments}")
    print()

    response = search(
        args.query,
        state=state,
        city=city,
        max_results=args.max_results,
        max_extractive_answer_count=args.answers,
        max_extractive_segment_count=args.segments,
        datastore_override=args.datastore,
    )

    _print_results(response, raw=args.raw, width=args.width)


if __name__ == "__main__":
    main()
