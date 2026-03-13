"""Tests for osint/agents/base.py — context threading, timing, and progress."""
import pytest
from unittest.mock import AsyncMock, patch
from osint.agents.base import make_run_fn
from osint.core.run_context import RunContext


@pytest.fixture
def mock_ai_response():
    return '{"found": true, "data": {"name": "Test"}, "pivots": []}'


@pytest.mark.asyncio
async def test_run_without_context(mock_ai_response):
    """Test that run() works without a RunContext."""
    run = make_run_fn("email", "gemini")
    with patch("osint.core.ai_runner.AIRunner.run", AsyncMock(return_value=mock_ai_response)):
        result = await run("test@example.com")
    assert result.success is True
    assert result.agent == "email"
    assert result.target == "test@example.com"


@pytest.mark.asyncio
async def test_run_with_context_records_timing(mock_ai_response):
    """Test that run() records timing in context when provided."""
    run = make_run_fn("email", "gemini")
    ctx = RunContext()
    with patch("osint.core.ai_runner.AIRunner.run", AsyncMock(return_value=mock_ai_response)):
        result = await run("test@example.com", context=ctx)
    assert "email:test@example.com" in ctx._timings
    assert ctx._timings["email:test@example.com"] > 0.0


@pytest.mark.asyncio
async def test_run_error_records_timing_too(mock_ai_response):
    """Test that run() records timing even when an error occurs."""
    run = make_run_fn("email", "gemini")
    ctx = RunContext()
    with patch("osint.core.ai_runner.AIRunner.run", AsyncMock(side_effect=Exception("boom"))):
        result = await run("test@example.com", context=ctx)
    assert result.success is False
    assert "email:test@example.com" in ctx._timings


@pytest.mark.asyncio
async def test_run_passes_context_to_ai_runner(mock_ai_response):
    """Test that run() passes context to AIRunner.run()."""
    run = make_run_fn("email", "gemini")
    ctx = RunContext(timeout=30.0)
    with patch("osint.core.ai_runner.AIRunner.run", AsyncMock(return_value=mock_ai_response)) as mock_run:
        await run("test@example.com", context=ctx)
    assert mock_run.call_args.kwargs.get("context") is ctx
