"""Custom LangSmith evaluators for legal advice quality assessment.

This module defines automated evaluators that assess the quality of legal
advice responses across multiple dimensions.

LLM-as-judge rubrics are loaded from markdown files in the evaluators/
directory so that non-technical contributors can edit the scoring criteria
without touching Python code.
"""

import re
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Final

from openevals import create_llm_as_judge
from openevals.types import SimpleEvaluator

# NOTE: can (should?) use different models for chatbot LLM & evaluator
# EVALUATOR_MODEL_NAME: Final = "gemini-2.5-pro"
EVALUATOR_MODEL_NAME: Final = "gemini-2.5-flash"

EVALUATORS_DIR: Final = Path(__file__).parent / "evaluators"

# NOTE: this is a LITERAL not an f-string, because it is substituted as-is into
#       an f-string which is then used as a template
INPUT_OUTPUT: Final = dedent(
    """
    <input>
    {inputs}
    </input>

    Use the Model-Under-Test Output below to evaluate the response.  Disregard
    other Model-Under-Test sections, which are for evaluation debugging only
    and should not affect the scores.

    <output>
    {outputs}
    </output>

    Use the reference outputs below to help you evaluate the correctness of the response:

    <reference_outputs>
    {reference_outputs}
    </reference_outputs>
    """
)


def _load_rubric(name: str) -> str:
    """Load a rubric from evaluators/{name}.md and return the full judge prompt."""
    rubric_path = EVALUATORS_DIR / f"{name}.md"
    rubric_text = rubric_path.read_text()
    return dedent(
        f"""
        You are an expert data labeler evaluating model outputs.
        Your task is to assign a score based on the following rubric:
        <Rubric>
        {rubric_text}
        </Rubric>

        <Instructions>
        - Carefully read the input and output
        - Check for factual accuracy and completeness
        </Instructions>

        {INPUT_OUTPUT}
        """
    )


# Evaluator: Citation Accuracy (LLM-as-Judge).
citation_accuracy_evaluator: SimpleEvaluator = create_llm_as_judge(
    model=EVALUATOR_MODEL_NAME,
    prompt=_load_rubric("citation_accuracy"),
    feedback_key="citation accuracy",
    continuous=True,
)

# Evaluator: Legal Correctness (LLM-as-Judge).
legal_correctness_evaluator: SimpleEvaluator = create_llm_as_judge(
    model=EVALUATOR_MODEL_NAME,
    prompt=_load_rubric("legal_correctness"),
    feedback_key="legal correctness",
    continuous=True,
)

# Evaluator: Tone & Professionalism (LLM-as-Judge).
tone_evaluator: SimpleEvaluator = create_llm_as_judge(
    model=EVALUATOR_MODEL_NAME,
    prompt=_load_rubric("tone"),
    feedback_key="appropriate tone",
    continuous=True,
)


# Evaluator: Citation Format (Heuristic).
def citation_format_evaluator(run, example) -> Dict[str, Any]:
    """Check if citations use proper HTML anchor tag format.

    Args:
        run: LangSmith run object containing outputs
        example: LangSmith example object (unused)

    Returns:
        Dictionary with evaluation results
    """
    output = run.outputs.get("output", "")

    # Check for HTML anchor tags.
    has_anchor_tags = bool(re.search(r'<a\s+href="[^"]+"\s+target="_blank">', output))

    # Check for ORS citations.
    has_ors_citation = bool(re.search(r"ORS\s+\d+\.\d+", output))

    # Check for proper citation domains.
    valid_domains = [
        "oregon.public.law",
        "portland.gov/code",
        "eugene.municipal.codes",
    ]
    has_valid_domain = any(domain in output for domain in valid_domains)

    score = 0.0
    if has_anchor_tags and has_ors_citation and has_valid_domain:
        score = 1.0
    elif has_ors_citation:
        score = 0.5

    return {
        "key": "citation_format",
        "score": score,
        "comment": f"Anchor tags: {has_anchor_tags}, ORS: {has_ors_citation}, Valid domain: {has_valid_domain}",
    }


# Evaluator: Tool Usage (Heuristic).
def tool_usage_evaluator(run, example) -> Dict[str, Any]:
    """Check if agent used RAG tools appropriately.

    Args:
        run: LangSmith run object containing trace
        example: LangSmith example object (unused)

    Returns:
        Dictionary with evaluation results
    """

    if not hasattr(run, "trace") or not run.trace:
        return {
            "key": "tool_usage",
            "score": 0.0,
            "comment": "No trace available for evaluation",
        }

    # Access trace to see which tools were called.
    tool_calls = []
    for step in run.trace.get("steps", []):
        if step.get("type") == "tool":
            tool_calls.append(step.get("name"))

    # Legal questions should use retrieval tools.
    used_retrieval = any(tool in ["retrieve_city_state_laws"] for tool in tool_calls)

    score = 1.0 if used_retrieval else 0.0

    return {
        "key": "tool_usage",
        "score": score,
        "comment": f"Tools used: {tool_calls}. Retrieval used: {used_retrieval}",
    }


# Evaluator: Performance Metrics (Heuristic).
def performance_evaluator(run, example) -> Dict[str, Any]:
    """Track latency and token usage.

    Args:
        run: LangSmith run object containing timing info
        example: LangSmith example object (unused)

    Returns:
        Dictionary with evaluation results
    """
    latency = run.end_time - run.start_time
    token_usage = run.usage.get("total_tokens", 0) if run.usage else 0

    # Flag if response is too slow (> 5 seconds).
    latency_score = 1.0 if latency < 5.0 else 0.5 if latency < 10.0 else 0.0

    return {
        "key": "performance",
        "score": latency_score,
        "comment": f"Latency: {latency:.2f}s, Tokens: {token_usage}",
        "metadata": {"latency_seconds": latency, "total_tokens": token_usage},
    }
