"""Tests for LangSmith evaluators."""

from unittest.mock import Mock

from scripts.langsmith_evaluators import (
    citation_format_evaluator,
    performance_evaluator,
    tool_usage_evaluator,
)


def test_citation_format_evaluator_valid():
    """Test that evaluator correctly scores valid citations."""
    mock_run = Mock()
    mock_run.outputs = {
        "output": 'According to <a href="https://oregon.public.law/statutes/ors_90.427" target="_blank">ORS 90.427</a>, landlords must provide 30 days notice.'
    }

    result = citation_format_evaluator(mock_run, None)

    assert result["score"] == 1.0
    assert "Anchor tags: True" in result["comment"]


def test_citation_format_evaluator_missing_anchor():
    """Test that evaluator penalizes missing anchor tags."""
    mock_run = Mock()
    mock_run.outputs = {
        "output": "According to ORS 90.427, landlords must provide notice."
    }

    result = citation_format_evaluator(mock_run, None)

    assert result["score"] == 0.5  # Has ORS but no anchor tag.


def test_citation_format_evaluator_no_citation():
    """Test that evaluator gives zero score for missing citations."""
    mock_run = Mock()
    mock_run.outputs = {"output": "Landlords must provide notice."}

    result = citation_format_evaluator(mock_run, None)

    assert result["score"] == 0.0


def test_tool_usage_evaluator_with_retrieval():
    """Test that evaluator correctly identifies tool usage."""
    mock_run = Mock()
    mock_run.trace = {
        "steps": [
            {"type": "tool", "name": "retrieve_city_law"},
            {"type": "llm", "name": "generate"},
        ]
    }

    result = tool_usage_evaluator(mock_run, None)

    assert result["score"] == 1.0
    assert "retrieve_city_law" in result["comment"]


def test_tool_usage_evaluator_without_retrieval():
    """Test that evaluator penalizes missing tool usage."""
    mock_run = Mock()
    mock_run.trace = {"steps": [{"type": "llm", "name": "generate"}]}

    result = tool_usage_evaluator(mock_run, None)

    assert result["score"] == 0.0


def test_performance_evaluator_fast_response():
    """Test that evaluator scores fast responses highly."""
    mock_run = Mock()
    mock_run.start_time = 0.0
    mock_run.end_time = 3.0  # 3 second response.
    mock_run.usage = {"total_tokens": 1000}

    result = performance_evaluator(mock_run, None)

    assert result["score"] == 1.0
    assert "Latency: 3.00s" in result["comment"]


def test_performance_evaluator_slow_response():
    """Test that evaluator penalizes slow responses."""
    mock_run = Mock()
    mock_run.start_time = 0.0
    mock_run.end_time = 12.0  # 12 second response.
    mock_run.usage = {"total_tokens": 2000}

    result = performance_evaluator(mock_run, None)

    assert result["score"] == 0.0
    assert "Latency: 12.00s" in result["comment"]
