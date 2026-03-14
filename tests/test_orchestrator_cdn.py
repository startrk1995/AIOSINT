"""Tests for CDN IP filtering in the orchestrator BFS pivot queue."""
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

import pytest

from osint.core import OsintResult
from osint.core.result import PivotEntity
from osint.orchestrator import OSINTOrchestrator


def _make_result(agent: str, target: str, pivots: list[PivotEntity], success: bool = True) -> OsintResult:
    return OsintResult(
        agent=agent,
        target=target,
        ai_used="gemini",
        success=success,
        data={},
        pivots=pivots,
        raw_response="",
        error=None,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


CDN_IP = "104.16.0.1"   # in Cloudflare 104.16.0.0/13 range → CDN
REGULAR_IP = "1.2.3.4"  # not in any CDN range


@pytest.mark.asyncio
async def test_orchestrator_filters_cdn_ip_from_pivots():
    """CDN IP pivot must be skipped; regular IP pivot must be queued and executed."""
    domain_result = _make_result(
        agent="domain",
        target="example.com",
        pivots=[
            PivotEntity(type="ip", value=CDN_IP),
            PivotEntity(type="ip", value=REGULAR_IP),
        ],
    )

    ip_mock = AsyncMock(return_value=_make_result("ip", REGULAR_IP, pivots=[]))

    fake_registry = {
        "domain": (AsyncMock(return_value=domain_result), "gemini"),
        "ip": (ip_mock, "gemini"),
    }

    orchestrator = OSINTOrchestrator()
    with patch("osint.orchestrator.AGENT_REGISTRY", fake_registry):
        results = await orchestrator.run("example.com", "domain", max_depth=2)

    # ip agent should have been called exactly once, with the regular IP only
    ip_mock.assert_called_once()
    call_target = ip_mock.call_args[0][0]
    assert call_target == REGULAR_IP, f"Expected ip agent called with {REGULAR_IP!r}, got {call_target!r}"

    # CDN IP should NOT appear as a target in any result
    ip_targets = [r.target for r in results if r.agent == "ip"]
    assert CDN_IP not in ip_targets, f"CDN IP {CDN_IP!r} should have been filtered out"


@pytest.mark.asyncio
async def test_orchestrator_cdn_ip_not_in_results():
    """No result with target == CDN_IP should exist when pivot is CDN-filtered."""
    domain_result = _make_result(
        agent="domain",
        target="example.com",
        pivots=[PivotEntity(type="ip", value=CDN_IP)],
    )

    ip_mock = AsyncMock(return_value=_make_result("ip", CDN_IP, pivots=[]))

    fake_registry = {
        "domain": (AsyncMock(return_value=domain_result), "gemini"),
        "ip": (ip_mock, "gemini"),
    }

    orchestrator = OSINTOrchestrator()
    with patch("osint.orchestrator.AGENT_REGISTRY", fake_registry):
        results = await orchestrator.run("example.com", "domain", max_depth=2)

    ip_mock.assert_not_called()
    assert len(results) == 1, "Only domain result should be present; CDN IP pivot was filtered"


@pytest.mark.asyncio
async def test_orchestrator_non_ip_pivots_not_affected_by_cdn_filter():
    """Non-IP pivot types (e.g., 'email') must still be queued normally."""
    domain_result = _make_result(
        agent="domain",
        target="example.com",
        pivots=[PivotEntity(type="email", value="admin@example.com")],
    )

    email_mock = AsyncMock(return_value=_make_result("email", "admin@example.com", pivots=[]))

    fake_registry = {
        "domain": (AsyncMock(return_value=domain_result), "gemini"),
        "email": (email_mock, "gemini"),
    }

    orchestrator = OSINTOrchestrator()
    with patch("osint.orchestrator.AGENT_REGISTRY", fake_registry):
        results = await orchestrator.run("example.com", "domain", max_depth=2)

    email_mock.assert_called_once()
    assert any(r.agent == "email" for r in results)
