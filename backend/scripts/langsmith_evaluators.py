"""Custom LangSmith evaluators for legal advice quality assessment.

This module defines automated evaluators that assess the quality of legal
advice responses across multiple dimensions.
"""

import re
from textwrap import dedent
from typing import Any, Dict, Final

from openevals import create_llm_as_judge
from openevals.prompts import CORRECTNESS_PROMPT
from openevals.types import SimpleEvaluator

# NOTE: can (should?) use different models for chatbot LLM & evaluator
# EVALUATOR_MODEL_NAME: Final = "gemini-2.5-pro"
EVALUATOR_MODEL_NAME: Final = "gemini-2.5-flash"

SCORING_GUIDELINES: Final = dedent(
    """
    - Score 1.0 if response is legally correct and complete
    - Score 0.5 if response has minor inaccuracies or omissions
    - Score 0.0 if response is legally incorrect or significantly incomplete
    """
)

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


# Evaluator 1: Citation Accuracy (LLM-as-Judge).
CITATION_PROMPT = dedent(
    f"""
    You are an expert data labeler evaluating model outputs for correctness.
    Your task is to assign a score based on the following rubric:
    <Rubric>
    A correct answer:
    - Include proper citations to applicable state and local laws
    - Must cite specific ORS (Oregon Revised Statutes) numbers
    - Must use HTML anchor tags with target="_blank"
    - Citations should link to oregon.public.law or city code websites
    - Provides accurate and complete information
    - Contains no factual errors
    - Addresses all parts of the question
    - Is logically consistent
    - Uses precise and accurate terminology

    When scoring, you should penalize:
    - Factual errors or inaccuracies
    - Incomplete or partial answers
    - Misleading or ambiguous statements
    - Incorrect terminology
    - Logical inconsistencies
    - Missing key information

    Scoring Guidelines:
    {SCORING_GUIDELINES}
    </Rubric>

    <Instructions>
    - Carefully read the input and output
    - Check for factual accuracy and completeness
    - Focus on correctness of information rather than style or verbosity
    </Instructions>

    <Reminders>
    The goal is to evaluate citation accuracy, formatting and completeness of the citations.
    </Reminders>

    {INPUT_OUTPUT}
    """
)

citation_accuracy_evaluator: SimpleEvaluator = create_llm_as_judge(
    model=EVALUATOR_MODEL_NAME, prompt=CITATION_PROMPT, feedback_key="citation accuracy"
)

# Evaluator 2: Legal Correctness (LLM-as-Judge).
LEGAL_CORRECTNESS_PROMPT_TEMPLATE: Final = dedent(
    f"""
    You are an expert data labeler evaluating model outputs for correctness.
    Your task is to assign a score based on the following rubric:
    <Rubric>
    A correct answer:
    - legal advice correctly based on Oregon tenant law
    - Check if advice aligns with ORS 90 (Landlord-Tenant)
    - Verify city-specific rules are correctly applied
    - Ensure no false statements about tenant rights
    - Provides accurate and complete information
    - Contains no factual errors
    - Addresses all parts of the question
    - Is logically consistent
    - Uses precise and accurate terminology

    When scoring, you should penalize:
    - Factual errors or inaccuracies
    - Incomplete or partial answers
    - Misleading or ambiguous statements
    - Incorrect terminology
    - Logical inconsistencies
    - Missing key information

    Scoring Guidelines:
    {SCORING_GUIDELINES}
    </Rubric>

    <Instructions>
    - Carefully read the input and output
    - Check for factual accuracy and completeness
    - Focus on correctness of information rather than style or verbosity
    </Instructions>

    <Reminders>
    The goal is to evaluate factual correctness and completeness of the response.
    </Reminders>

    {INPUT_OUTPUT}
    """
)

legal_correctness_evaluator: SimpleEvaluator = create_llm_as_judge(
    model=EVALUATOR_MODEL_NAME,
    prompt=LEGAL_CORRECTNESS_PROMPT_TEMPLATE,
    feedback_key="legal correctness",
    continuous=True,
    # choices=[0.0, 0.5, 1.0],
)


# Evaluator 3: Response Completeness (LLM-as-Judge).
completeness_evaluator = create_llm_as_judge(
    model=EVALUATOR_MODEL_NAME,
    prompt=CORRECTNESS_PROMPT,
    feedback_key="general correctness",
)

# Evaluator 4: Tone & Professionalism (LLM-as-Judge).
TONE_PROMPT_TEMPLATE = dedent(
    f"""
    You are an expert data labeler evaluating model outputs for correctness. Your task is to assign a score based on the following rubric:
    <Rubric>
    A good answer:
    - has a tone appropriate for legal advice
    - Professional but accessible language
    - Empathetic to tenant's situation
    - Not overly formal or robotic
    - Doesn't start with "As a legal expert..."

    When scoring, you should penalize:
    - uncommon legal jargon
    - overly casual language

    Scoring Guidelines:
    {SCORING_GUIDELINES}
    </Rubric>

    <Instructions>
    - Check for inappropriate tone or style
    - Focus on tone, style and verbosity rather than correctness of information
    </Instructions>

    <Reminders>
    The goal is to evaluate the tone of the response.
    </Reminders>

    {INPUT_OUTPUT}
    """
)

tone_evaluator: SimpleEvaluator = create_llm_as_judge(
    model=EVALUATOR_MODEL_NAME,
    prompt=TONE_PROMPT_TEMPLATE,
    feedback_key="appropriate tone",
    continuous=True,
    # choices=[0.0, 0.5, 1.0],
)


# Evaluator 5: Citation Format (Heuristic).
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


# Evaluator 6: Tool Usage (Heuristic).
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


# Evaluator 7: Performance Metrics (Heuristic).
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
