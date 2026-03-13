import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from osint.core.ai_runner import AIRunner, AgentError
from osint.core.run_context import RunContext


@pytest.fixture
def mock_process_fast():
    """Subprocess that returns immediately."""
    proc = MagicMock()
    proc.returncode = 0
    proc.kill = MagicMock()
    proc.communicate = AsyncMock(return_value=(b'{"found": true}', b""))
    return proc


@pytest.fixture
def mock_process_slow():
    """Subprocess that hangs forever."""
    call_n = 0

    async def communicate_se(*args, **kwargs):
        nonlocal call_n
        call_n += 1
        if call_n == 1:
            await asyncio.sleep(999)
        return b"", b""

    proc = MagicMock()
    proc.returncode = 0
    proc.kill = MagicMock()
    # First call hangs, second call (reap after kill) returns immediately
    proc.communicate = AsyncMock(side_effect=communicate_se)
    return proc


async def test_run_no_context_succeeds(mock_process_fast):
    with patch("asyncio.create_subprocess_exec", return_value=mock_process_fast):
        runner = AIRunner()
        result = await runner.run("gemini", "test prompt")
    assert '{"found": true}' in result


async def test_timeout_kill_raises_agent_error(mock_process_slow):
    ctx = RunContext(timeout=0.01, timeout_action="kill")
    with patch("asyncio.create_subprocess_exec", return_value=mock_process_slow):
        runner = AIRunner()
        with pytest.raises(AgentError, match="TIMEOUT"):
            await runner.run("gemini", "test prompt", context=ctx)
    mock_process_slow.kill.assert_called_once()
    # Reap step must be called — "must not be omitted" per spec
    assert mock_process_slow.communicate.call_count == 2


async def test_timeout_warn_also_kills_process(mock_process_slow):
    """warn mode must still kill the OS process — distinction is cosmetic."""
    ctx = RunContext(timeout=0.01, timeout_action="warn")
    with patch("asyncio.create_subprocess_exec", return_value=mock_process_slow):
        runner = AIRunner()
        with pytest.raises(AgentError, match="TIMEOUT"):
            await runner.run("gemini", "test prompt", context=ctx)
    mock_process_slow.kill.assert_called_once()
    # Reap step must be called — "must not be omitted" per spec
    assert mock_process_slow.communicate.call_count == 2


async def test_unsupported_ai_raises():
    runner = AIRunner()
    with pytest.raises(AgentError, match="Unsupported AI"):
        await runner.run("gpt4", "prompt")


async def test_subprocess_nonzero_raises(mock_process_fast):
    mock_process_fast.returncode = 1
    mock_process_fast.communicate = AsyncMock(return_value=(b"", b"error msg"))
    with patch("asyncio.create_subprocess_exec", return_value=mock_process_fast):
        runner = AIRunner()
        with pytest.raises(AgentError, match="subprocess failed"):
            await runner.run("gemini", "prompt")
