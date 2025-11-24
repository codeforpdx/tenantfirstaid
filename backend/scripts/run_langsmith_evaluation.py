"""Run automated evaluation of LangChain agent using LangSmith.

This script replaces the manual conversation generation workflow with
automated quality evaluation.
"""

import argparse

from langsmith import Client
from langsmith.evaluation import evaluate

from tenantfirstaid.langchain_chat import LangChainChatManager
from scripts.langsmith_evaluators import (
    citation_accuracy_evaluator,
    citation_format_evaluator,
    completeness_evaluator,
    legal_correctness_evaluator,
    performance_evaluator,
    tone_evaluator,
    tool_usage_evaluator,
)


def agent_wrapper(inputs):
    """Wrapper function that runs the LangChain agent on a single test case.

    This is what LangSmith will call for each evaluation example.

    Args:
        inputs: Dictionary with test inputs (first_question, city, state, facts)

    Returns:
        Dictionary with agent output
    """
    chat_manager = LangChainChatManager()
    agent = chat_manager.create_agent_for_session(
        city=inputs["city"], state=inputs["state"]
    )

    # Run agent on the first question.
    response = agent.invoke(
        {
            "input": inputs["first_question"],
            "chat_history": [],
            "city": inputs["city"],
            "state": inputs["state"],
        }
    )

    return {"output": response["output"]}


def run_evaluation(
    dataset_name="tenant-legal-qa-scenarios",
    experiment_prefix="langchain-agent",
    num_samples=None,
):
    """Run automated evaluation on LangSmith dataset.

    Args:
        dataset_name: Name of LangSmith dataset to evaluate
        experiment_prefix: Name for this evaluation run
        num_samples: Number of examples to evaluate (None = all)

    Returns:
        Evaluation results object
    """
    client = Client()

    # Get dataset.
    dataset = client.read_dataset(dataset_name=dataset_name)

    print(f"Running evaluation on dataset: {dataset_name}")
    print(f"Total examples: {dataset.example_count}")

    # Run evaluation with all evaluators.
    results = evaluate(
        agent_wrapper,
        data=dataset_name,
        evaluators=[
            citation_accuracy_evaluator,
            legal_correctness_evaluator,
            completeness_evaluator,
            tone_evaluator,
            citation_format_evaluator,
            tool_usage_evaluator,
            performance_evaluator,
        ],
        experiment_prefix=experiment_prefix,
        max_concurrency=5,  # Run 5 evaluations in parallel.
        num_samples=num_samples,
    )

    # Print summary.
    print("\n=== Evaluation Results ===")
    print(f"Experiment: {results.experiment_name}")
    print(f"Examples evaluated: {results.example_count}")
    print("\nAggregate Scores:")
    for metric, score in results.aggregate_metrics.items():
        print(f"  {metric}: {score:.2f}")

    print(f"\nView full results at: {results.experiment_url}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LangSmith evaluation")
    parser.add_argument("--dataset", default="tenant-legal-qa-scenarios")
    parser.add_argument("--experiment", default="langchain-agent")
    parser.add_argument("--num-samples", type=int, default=None)
    args = parser.parse_args()

    run_evaluation(
        dataset_name=args.dataset,
        experiment_prefix=args.experiment,
        num_samples=args.num_samples,
    )
