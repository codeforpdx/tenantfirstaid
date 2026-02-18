"""Run automated evaluation of LangChain agent using LangSmith.

This script replaces the manual conversation generation workflow with
automated quality evaluation.
"""

import argparse
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langsmith import Client, evaluate

from scripts.langsmith_evaluators import (
    # citation_accuracy_evaluator,
    # citation_format_evaluator,
    # completeness_evaluator,
    legal_correctness_evaluator,
    # performance_evaluator,
    tone_evaluator,
    # tool_usage_evaluator,
)
from tenantfirstaid.constants import SINGLETON
from tenantfirstaid.langchain_chat_manager import (
    LangChainChatManager,
    OregonCity,
    UsaState,
)


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
        ),
        "Model-Under-Test System Prompt": chat_manager.system_prompt.content
        if isinstance(chat_manager.system_prompt.content, str)
        else "",
        # TODO: figure out how to return ToolMessage content blocks for evaluation of tool calls and outputs
        #       since these are not currently included in the output stream from generate_streaming_response()
    }


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
    ls_client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))

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
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=experiment_prefix,
        # max_concurrency=5,  # Run 5 evaluations in parallel.
        num_repetitions=num_repetitions,
        metadata={
            "LLM model name": SINGLETON.MODEL_NAME,
            "LLM model temperature": SINGLETON.MODEL_TEMPERATURE,
        },
        max_concurrency=max_concurrency,
    )

    # Print summary.
    print("\n=== Evaluation Results ===")
    print(f"Experiment: {results.experiment_name}")
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

    env_path = Path(__file__).parent / "../.env"
    if env_path.exists():
        from dotenv import load_dotenv

        load_dotenv(override=True)
    else:
        raise FileNotFoundError(f".env file not found at {env_path}")

    args = parser.parse_args()

    run_evaluation(
        dataset_name=args.dataset,
        experiment_prefix=args.experiment,
        num_repetitions=args.num_repetitions,
        max_concurrency=args.max_concurrency,
    )
