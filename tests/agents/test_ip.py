"""Tests for osint/agents/ip.py — IP address OSINT agent."""
import inspect
import pytest
from osint.agents import ip, AGENT_REGISTRY


def test_agent_type_constant():
    assert ip.AGENT_TYPE == "ip"


def test_ai_cli_constant():
    assert ip.AI_CLI == "gemini"


def test_run_is_callable():
    """run must be a callable (coroutine function) returned by make_run_fn."""
    assert callable(ip.run)
    assert inspect.iscoroutinefunction(ip.run)


def test_ip_in_agent_registry():
    """ip agent must be registered in AGENT_REGISTRY."""
    assert "ip" in AGENT_REGISTRY


def test_ip_registry_maps_to_gemini():
    """Registry entry must map to (ip.run, 'gemini')."""
    run_fn, ai_cli = AGENT_REGISTRY["ip"]
    assert ai_cli == "gemini"
    assert run_fn is ip.run
