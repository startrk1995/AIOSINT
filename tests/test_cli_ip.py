"""Tests for the `osint ip` CLI command."""
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from osint.cli import app


runner = CliRunner()


def test_ip_command_calls_run_agent():
    """osint ip 1.2.3.4 must call _run_agent('ip', '1.2.3.4')."""
    with patch("osint.cli._run_agent") as mock_run:
        result = runner.invoke(app, ["ip", "1.2.3.4"])
    assert result.exit_code == 0, f"Unexpected exit code: {result.exit_code}\n{result.output}"
    mock_run.assert_called_once_with("ip", "1.2.3.4", verbose=False)


def test_ip_command_verbose_flag():
    """osint ip --verbose 1.2.3.4 must pass verbose=True to _run_agent."""
    with patch("osint.cli._run_agent") as mock_run:
        result = runner.invoke(app, ["ip", "--verbose", "1.2.3.4"])
    assert result.exit_code == 0, f"Unexpected exit code: {result.exit_code}\n{result.output}"
    mock_run.assert_called_once_with("ip", "1.2.3.4", verbose=True)


def test_ip_command_short_verbose_flag():
    """osint ip -v 1.2.3.4 must pass verbose=True to _run_agent."""
    with patch("osint.cli._run_agent") as mock_run:
        result = runner.invoke(app, ["ip", "-v", "1.2.3.4"])
    assert result.exit_code == 0, f"Unexpected exit code: {result.exit_code}\n{result.output}"
    mock_run.assert_called_once_with("ip", "1.2.3.4", verbose=True)


def test_ip_command_help():
    """osint ip --help must display help without error."""
    result = runner.invoke(app, ["ip", "--help"])
    assert result.exit_code == 0
    assert "IP" in result.output or "ip" in result.output.lower()
