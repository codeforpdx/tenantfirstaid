"""Query the Vertex AI Search datastore directly, bypassing LangChain/LangGraph.

Useful for debugging retrieval quality independently of the agent framework:
what passages does the datastore actually return for a given query and filter?

Usage:
    uv run python -m scripts.vertex_ai_search "security deposit interest" --state or
    uv run python -m scripts.vertex_ai_search "ORS 90.155 notice delivery" --state or --city portland
    uv run python -m scripts.vertex_ai_search "nonpayment notice timing" --state or --max-results 10
    uv run python -m scripts.vertex_ai_search "ORS 90.427" --state or --raw

    # Sweep extraction params to find diminishing returns:
    uv run python -m scripts.vertex_ai_search shmoo \\
        "72 hour nonpayment notice week-to-week ORS 90.394" \\
        --target "fifth day" --state or
"""

import argparse
import json
import textwrap
from typing import List, Optional

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.cloud.discoveryengine_v1beta.services.search_service.pagers import (
    SearchPager,
)

from tenantfirstaid.constants import SINGLETON
from tenantfirstaid.google_auth import load_gcp_credentials
from tenantfirstaid.langchain_tools import _filter_builder, _repair_mojibake
from tenantfirstaid.location import OregonCity, UsaState


def search(
    query: str,
    *,
    state: UsaState,
    city: Optional[OregonCity] = None,
    max_results: int = 5,
    max_extractive_answer_count: int = 5,
    max_extractive_segment_count: int = 3,
    spell_correction: int = 1,
    datastore_override: Optional[str] = None,
) -> SearchPager:
    """Run a search against the Vertex AI Search datastore and return the raw response."""
    assert SINGLETON.GOOGLE_APPLICATION_CREDENTIALS is not None
    credentials = load_gcp_credentials(SINGLETON.GOOGLE_APPLICATION_CREDENTIALS)

    location = SINGLETON.GOOGLE_CLOUD_LOCATION or "global"
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    client = discoveryengine.SearchServiceClient(
        credentials=credentials,
        client_options=client_options,
    )

    datastore = datastore_override or SINGLETON.VERTEX_AI_DATASTORE
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
        filter=_filter_builder(state, city),
        content_search_spec=content_search_spec,
        spell_correction_spec=spell_correction_spec,
    )

    return client.search(request)


def _collect_passages(response: SearchPager) -> List[dict]:
    """Collect all extractive answers and segments from a search response."""
    passages = []
    for result in response.results:
        doc = result.document
        struct = doc.derived_struct_data
        if not struct:
            continue
        doc_id = doc.id or "(no id)"
        for answer in struct.get("extractive_answers", []):
            content = _repair_mojibake(answer.get("content", ""))
            passages.append({"doc_id": doc_id, "type": "answer", "content": content})
        for segment in struct.get("extractive_segments", []):
            content = _repair_mojibake(segment.get("content", ""))
            passages.append({"doc_id": doc_id, "type": "segment", "content": content})
    return passages


def _print_results(
    response: SearchPager,
    *,
    raw: bool = False,
    width: int = 100,
) -> None:
    """Pretty-print search results to stdout."""
    if hasattr(response, "corrected_query") and response.corrected_query:
        print(f"Spell-corrected query: {response.corrected_query}\n")

    count = 0
    for i, result in enumerate(response.results, 1):
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
                content = _repair_mojibake(answer.get("content", ""))
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
                content = _repair_mojibake(segment.get("content", ""))
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
                text = _repair_mojibake(snippet.get("snippet", ""))
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
    city: Optional[OregonCity] = None,
    max_results: int = 5,
    targets: List[str],
    max_answer_sweep: int = 5,
    max_segment_sweep: int = 10,
    datastore_override: Optional[str] = None,
) -> None:
    """Sweep extractive answer and segment counts, reporting where targets appear."""
    targets_lower = [t.lower() for t in targets]

    def _check(passages: List[dict]) -> List[str]:
        """Return list of (doc_id, type) pairs where any target matched."""
        hits = []
        for p in passages:
            content_lower = p["content"].lower()
            if any(t in content_lower for t in targets_lower):
                hits.append(f"{p['doc_id']}:{p['type']}")
        return hits

    filter_str = _filter_builder(state, city)
    print(f"Query:   {query}")
    print(f"Filter:  {filter_str}")
    print(f"Targets: {targets}")
    print(f"Docs:    {max_results}")
    print()

    # Sweep extractive answers (segments fixed at 1).
    print(f"{'answers':>8}  {'hits':>4}  where")
    print(f"{'-------':>8}  {'----':>4}  -----")
    prev_hit_count = -1
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
    prev_hit_count = -1
    for n in range(1, max_segment_sweep + 1):
        response = search(
            query,
            state=state,
            city=city,
            max_results=max_results,
            max_extractive_answer_count=1,
            max_extractive_segment_count=n,
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

    # Support bare invocation (no subcommand) for backwards compatibility.
    if args.command is None:
        # Re-parse as if "search" was specified.
        parser.parse_args(["search", "--help"])
        return

    state = UsaState.from_maybe_str(args.state)
    city = OregonCity.from_maybe_str(args.city) if args.city else None

    datastore = args.datastore or SINGLETON.VERTEX_AI_DATASTORE

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
    filter_str = _filter_builder(state, city)
    print(f"Query:     {args.query}")
    print(f"Filter:    {filter_str}")
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
