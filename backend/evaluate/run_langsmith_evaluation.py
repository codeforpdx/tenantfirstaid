"""Run automated evaluation of LangChain agent using LangSmith.

This script replaces the manual conversation generation workflow with
automated quality evaluation.
"""

import argparse
import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langsmith import Client, evaluate

from evaluate.eval_history import write_run_entry
from evaluate.langsmith_evaluators import (
    # citation_accuracy_evaluator,
    # citation_format_evaluator,
    # completeness_evaluator,
    legal_correctness_evaluator,
    # performance_evaluator,
    tone_evaluator,
    # tool_usage_evaluator,
)
from evaluate.results_display import ScenarioResult, print_consistency_stats
from tenantfirstaid.constants import LANGSMITH_API_KEY, SINGLETON
from tenantfirstaid.langchain_chat_manager import LangChainChatManager
from tenantfirstaid.location import OregonCity, UsaState

# Suppress the noisy additionalProperties warning from langchain_google_vertexai
# https://github.com/langchain-ai/langchain-google/issues/1038#issuecomment-3707773510
logging.getLogger("langchain_google_vertexai.functions_utils").setLevel(logging.ERROR)


def agent_wrapper(inputs) -> Dict[str, str]:
    """Wrapper function that runs the LangChain agent on a single test case.

    This is what LangSmith will call for each evaluation example.

    Args:
        inputs: Dictionary with test inputs (first_question, city, state, facts)

    Returns:
        Dictionary with Model-under-test output
    """
    chat_manager = LangChainChatManager()

    context_state = UsaState.from_maybe_str(inputs["state"])
    context_city = OregonCity.from_maybe_str(inputs["city"])
    tid: Optional[str] = None

    responses = list(
        chat_manager.generate_streaming_response(
            messages=[HumanMessage(content=inputs["query"])],
            state=context_state,
            city=context_city,
            thread_id=tid,
        )
    )

    return {
        "Model-Under-Test Output": "\n".join(
            [response["text"] for response in responses if ("text" in response)]  # type: ignore bad-typed-dict-key
        ),
        # SHOW_MODEL_THINKING env var controls whether reasoning is included in the output for evaluation debugging.
        "Model-Under-Test Reasoning": "\n".join(
            [
                response["reasoning"]  # type: ignore bad-typed-dict-key
                for response in responses
                if ("reasoning" in response)
            ]
        )
        or "N/A - Set env var `SHOW_MODEL_THINKING=true` to capture reasoning",
        "Model-Under-Test System Prompt": chat_manager.system_prompt.content
        if chat_manager.system_prompt is not None
        and isinstance(chat_manager.system_prompt.content, str)
        else "",
        # TODO: figure out how to return ToolMessage content blocks for evaluation of tool calls and outputs
        #       since these are not currently included in the output stream from generate_streaming_response()
    }


def _df_to_scenario_results(
    df: Any, client: Optional[Any] = None
) -> List[ScenarioResult]:
    """Convert a LangSmith results DataFrame to ScenarioResult list.

    When a LangSmith client is provided, example metadata is fetched to sort
    scenarios by scenario_id and include it in the label so the output can be
    cross-referenced against `langsmith_dataset example list` output.
    """
    score_cols = [c for c in df.columns if c.startswith("feedback.")]
    if not score_cols or "example_id" not in df.columns:
        return []

    # Fetch scenario_ids from example metadata when a client is available.
    scenario_id_by_example: Dict[str, int] = {}
    if client is not None:
        example_ids = df["example_id"].unique().tolist()
        for ex in client.list_examples(example_ids=example_ids):
            scenario_id_by_example[str(ex.id)] = (ex.metadata or {}).get(
                "scenario_id", 0
            )

    query_col = "inputs.query" if "inputs.query" in df.columns else None
    groups = list(df.groupby("example_id", sort=False))
    if scenario_id_by_example:
        groups.sort(key=lambda g: scenario_id_by_example.get(str(g[0]), 0))

    scenarios = []
    for example_id, group in groups:
        q = str(group[query_col].iloc[0]) if query_col else ""
        sc_id = scenario_id_by_example.get(str(example_id))
        label = f'"{q[:68]}{"..." if len(q) > 68 else ""}"'
        scores: Dict[str, List[float]] = {}
        for col in score_cols:
            name = col.removeprefix("feedback.")
            scores[name] = group[col].dropna().tolist()
        scenarios.append(
            ScenarioResult(
                label=label,
                scenario_id=sc_id if sc_id is not None else 0,
                scores=scores,
            )
        )
    return scenarios


# TODO: https://docs.langchain.com/langsmith/multi-turn-simulation
def run_evaluation(
    dataset_name="tenant-legal-qa-scenarios",
    experiment_prefix="tfa-",
    num_repetitions: int = 1,
    max_concurrency: Optional[int] = 1,
):
    """Run automated evaluation on LangSmith dataset.

    Args:
        dataset_name: Name of LangSmith dataset to evaluate
        experiment_prefix: Name for this evaluation run
        num_repetitions: Number of repetitions per example

    Returns:
        Evaluation results object
    """
    ls_client = Client(api_key=LANGSMITH_API_KEY)

    # Get dataset.
    dataset = ls_client.read_dataset(dataset_name=dataset_name)

    print(f"Running evaluation on dataset: {dataset_name}")
    print(f"Total examples: {dataset.example_count}")

    evaluators: List[
        #         Callable[..., Union[Dict[Any, Any], EvaluationResult, EvaluationResults]]
        Any
    ] = [
        # citation_accuracy_evaluator,
        legal_correctness_evaluator,
        # completeness_evaluator,
        tone_evaluator,
        # citation_format_evaluator,
        # tool_usage_evaluator,
        # performance_evaluator,
    ]  # noqa

    # Run evaluation with all evaluators.
    results = evaluate(
        agent_wrapper,
        client=ls_client,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=experiment_prefix,
        # max_concurrency=5,  # Run 5 evaluations in parallel.
        num_repetitions=num_repetitions,
        metadata={
            "LLM model name": SINGLETON.MODEL_NAME,
            "LLM model temperature": SINGLETON.MODEL_TEMPERATURE,
            "RAG Data Stores": SINGLETON.VERTEX_AI_DATASTORES,
        },
        max_concurrency=max_concurrency,
    )

    # Print summary.
    print("\n=== Evaluation Results ===")

    # Print aggregate summary.
    print("\n=== Aggregate Summary ===")
    df = results.to_pandas()
    score_cols = [c for c in df.columns if c.startswith("feedback.")]
    if score_cols:
        scores = df[score_cols].mean() * 100
        scores.index = scores.index.str.removeprefix("feedback.")
        print(scores.to_string(float_format=lambda x: f"{x:.1f}%"))
    else:
        print("No feedback columns found.")

    scenario_results = _df_to_scenario_results(df, client=ls_client)
    print_consistency_stats(scenario_results)

    print(f"\nExperiment: {results.experiment_name}")

    dataset_version = (
        dataset.modified_at.isoformat() if dataset.modified_at else "unknown"
    )
    write_run_entry(
        experiment_name=results.experiment_name,
        scenarios=scenario_results,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        num_repetitions=num_repetitions,
    )

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run LangSmith evaluation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset", default="tenant-legal-qa-scenarios", help="LangSmith dataset name"
    )
    parser.add_argument(
        "--experiment",
        default="tfa-",
        help="Experiment prefix for this evaluation run",
    )
    parser.add_argument(
        "--num-repetitions", type=int, default=1, help="Number of runs for each example"
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=1,
        help="Maximum number of concurrent runs",
    )

    args = parser.parse_args()

    run_evaluation(
        dataset_name=args.dataset,
        experiment_prefix=args.experiment,
        num_repetitions=args.num_repetitions,
        max_concurrency=args.max_concurrency,
    )
