"""Tests for IP agent entries in prompt_builder.py."""
import pytest
from osint.core.prompt_builder import RESEARCH_TASKS, PIVOT_HINTS, PromptBuilder


def test_research_tasks_ip_exists():
    """RESEARCH_TASKS must have a non-empty entry for 'ip'."""
    assert "ip" in RESEARCH_TASKS
    assert RESEARCH_TASKS["ip"].strip() != ""


def test_pivot_hints_ip_is_empty_string():
    """PIVOT_HINTS['ip'] must be empty string — IP is a research endpoint."""
    assert "ip" in PIVOT_HINTS
    assert PIVOT_HINTS["ip"] == ""


def test_pivot_hints_domain_contains_ip_type():
    """Updated domain pivot hint must reference 'ip' pivot type."""
    assert "ip" in PIVOT_HINTS["domain"]


def test_pivot_hints_domain_contains_domain_type():
    """Updated domain pivot hint must still reference 'domain' pivot type."""
    assert "domain" in PIVOT_HINTS["domain"]


def test_pivot_hints_domain_mentions_cdn_exclusion():
    """Domain pivot hint must mention CDN/shared-infrastructure exclusion."""
    hint = PIVOT_HINTS["domain"].lower()
    # Should mention at least one CDN provider to guide the AI
    assert any(cdn in hint for cdn in ["cloudflare", "fastly", "akamai", "cloudfront"])


def test_build_ip_prompt_contains_target():
    """PromptBuilder.build() for ip/gemini must include the target in the prompt."""
    builder = PromptBuilder()
    prompt = builder.build("ip", "gemini", "1.2.3.4")
    assert "1.2.3.4" in prompt


def test_build_ip_prompt_is_nonempty_string():
    """PromptBuilder.build() for ip/gemini must return a non-empty string."""
    builder = PromptBuilder()
    prompt = builder.build("ip", "gemini", "1.2.3.4")
    assert isinstance(prompt, str)
    assert len(prompt) > 0
