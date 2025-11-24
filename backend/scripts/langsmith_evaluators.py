"""Custom LangSmith evaluators for legal advice quality assessment.

This module defines automated evaluators that assess the quality of legal
advice responses across multiple dimensions.
"""

import re

from langchain.evaluation import LangChainStringEvaluator
from langchain_google_vertexai import ChatVertexAI

# Evaluator 1: Citation Accuracy (LLM-as-Judge).
citation_accuracy_evaluator = LangChainStringEvaluator(
    evaluator_type="labeled_criteria",
    criteria={
        "citation_accuracy": """
        Does the response include proper citations to Oregon laws?
        - Must cite specific ORS (Oregon Revised Statutes) numbers
        - Must use HTML anchor tags with target="_blank"
        - Citations should link to oregon.public.law or city code websites
        - Score 1.0 if citations are present and properly formatted
        - Score 0.5 if citations present but formatting issues
        - Score 0.0 if no citations or incorrect citations
        """
    },
    llm=ChatVertexAI(model_name="gemini-2.5-pro", temperature=0),
)

# Evaluator 2: Legal Correctness (LLM-as-Judge).
legal_correctness_evaluator = LangChainStringEvaluator(
    evaluator_type="qa",
    criteria={
        "legal_correctness": """
        Is the legal advice correct based on Oregon tenant law?
        - Check if advice aligns with ORS 90 (Landlord-Tenant)
        - Verify city-specific rules are correctly applied
        - Ensure no false statements about tenant rights
        - Score 1.0 if legally accurate
        - Score 0.5 if partially accurate or incomplete
        - Score 0.0 if legally incorrect or misleading
        """
    },
    llm=ChatVertexAI(model_name="gemini-2.5-pro", temperature=0),
)

# Evaluator 3: Response Completeness (LLM-as-Judge).
completeness_evaluator = LangChainStringEvaluator(
    evaluator_type="criteria",
    criteria={
        "completeness": """
        Does the response fully address the user's question?
        - Answers the core legal question
        - Provides relevant context and next steps
        - Includes important caveats or exceptions
        - Score 1.0 if comprehensive answer
        - Score 0.5 if partial answer
        - Score 0.0 if off-topic or unhelpful
        """
    },
    llm=ChatVertexAI(model_name="gemini-2.5-pro", temperature=0),
)

# Evaluator 4: Tone & Professionalism (LLM-as-Judge).
tone_evaluator = LangChainStringEvaluator(
    evaluator_type="criteria",
    criteria={
        "tone": """
        Is the tone appropriate for legal advice?
        - Professional but accessible language
        - Empathetic to tenant's situation
        - Not overly formal or robotic
        - Doesn't start with "As a legal expert..."
        - Score 1.0 if tone is excellent
        - Score 0.5 if tone issues (too formal/casual)
        - Score 0.0 if inappropriate tone
        """
    },
    llm=ChatVertexAI(model_name="gemini-2.5-pro", temperature=0),
)


# Evaluator 5: Citation Format (Heuristic).
def citation_format_evaluator(run, example):
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
def tool_usage_evaluator(run, example):
    """Check if agent used RAG tools appropriately.

    Args:
        run: LangSmith run object containing trace
        example: LangSmith example object (unused)

    Returns:
        Dictionary with evaluation results
    """
    # Access trace to see which tools were called.
    tool_calls = []
    for step in run.trace.get("steps", []):
        if step.get("type") == "tool":
            tool_calls.append(step.get("name"))

    # Legal questions should use retrieval tools.
    used_retrieval = any(
        tool in ["retrieve_city_law", "retrieve_state_law"] for tool in tool_calls
    )

    score = 1.0 if used_retrieval else 0.0

    return {
        "key": "tool_usage",
        "score": score,
        "comment": f"Tools used: {tool_calls}. Retrieval used: {used_retrieval}",
    }


# Evaluator 7: Performance Metrics (Heuristic).
def performance_evaluator(run, example):
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
