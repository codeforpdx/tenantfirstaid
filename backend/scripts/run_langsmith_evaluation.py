"""Run automated evaluation of LangChain agent using LangSmith.

This script replaces the manual conversation generation workflow with
automated quality evaluation.
"""

import argparse
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pprint import pprint

from langchain_core.messages import HumanMessage, AIMessage

from langsmith import Client
from langsmith import evaluate

from tenantfirstaid.langchain_chat_manager import (
    LangChainChatManager,
    # OregonCity,
    # UsaState,
    # _InnerUsaState
)
from scripts.langsmith_evaluators import (
    # citation_accuracy_evaluator,
    # citation_format_evaluator,
    completeness_evaluator,
    # legal_correctness_evaluator,
    # performance_evaluator,
    # tone_evaluator,
    # tool_usage_evaluator,
)


def agent_wrapper(inputs) -> Any:
    """Wrapper function that runs the LangChain agent on a single test case.

    This is what LangSmith will call for each evaluation example.

    Args:
        inputs: Dictionary with test inputs (first_question, city, state, facts)

    Returns:
        Dictionary with agent output
    """
    chat_manager = LangChainChatManager()

    context_state = str(inputs["state"])
    context_city = str(inputs["city"])

    agent = chat_manager.create_agent_for_session(
        city=context_city, state=context_state
    )

    # Run agent on the first question.
    response: Dict[str, Any] = agent.invoke(
        {
            "messages": [HumanMessage(content=inputs["first_question"])],
            "city": context_city,
            "state": context_state,
        }
    )

    # pprint(response)

    return {"output": response["messages"][-1].content_blocks}


def run_evaluation(
    dataset_name="tenant-legal-qa-scenarios",
    experiment_prefix="langchain-agent",
    num_repetitions: int = 1,
):
    """Run automated evaluation on LangSmith dataset.

    Args:
        dataset_name: Name of LangSmith dataset to evaluate
        experiment_prefix: Name for this evaluation run
        num_repetitions: Number of repetitions per example

    Returns:
        Evaluation results object
    """
    client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))

    # Get dataset.
    dataset = client.read_dataset(dataset_name=dataset_name)

    print(f"Running evaluation on dataset: {dataset_name}")
    print(f"Total examples: {dataset.example_count}")

    # Run evaluation with all evaluators.
    results = evaluate(
        agent_wrapper,
        data=dataset_name,
        evaluators=[
            # citation_accuracy_evaluator,
            # legal_correctness_evaluator,
            completeness_evaluator,
            # tone_evaluator,
            # citation_format_evaluator,
            # tool_usage_evaluator,
            # performance_evaluator,
        ],
        # experiment_prefix=experiment_prefix,
        # max_concurrency=5,  # Run 5 evaluations in parallel.
        # num_repetitions=num_repetitions,
    )

    # Print summary.
    print("\n=== Evaluation Results ===")
    print(f"Experiment: {results.experiment_name}")
    # print(f"Examples evaluated: {results}")
    pprint(results)
    print("\nAggregate Scores:")
    # for metric, score in results.aggregate_metrics.items():
    #     print(f"  {metric}: {score:.2f}")

    # print(f"\nView full results at: {results.experiment_url}")

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
        default="langchain-agent",
        help="Experiment prefix for this evaluation run",
    )
    parser.add_argument(
        "--num-repetitions", type=int, default=1, help="Number of examples to evaluate"
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
    )
