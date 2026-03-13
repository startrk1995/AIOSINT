import asyncio

from osint.config import settings
from osint.core.run_context import RunContext


class AgentError(Exception):
    pass


class AIRunner:
    """Dispatches prompts to AI CLI subprocesses (gemini, claude, codex)."""

    def _get_commands(self) -> dict[str, list[str]]:
        return {
            "gemini": [settings.gemini_path, "-p"],
            "claude": [settings.claude_path, "-p"],
            "codex": [settings.codex_path, "exec", "--full-auto", "--skip-git-repo-check"],
        }

    async def run(self, ai: str, prompt: str, context: RunContext | None = None) -> str:
        """Run the given AI CLI with the prompt and return stdout as a string.

        Args:
            ai: One of "gemini", "claude", or "codex".
            prompt: The prompt string to pass to the AI CLI.
            context: Optional RunContext carrying timeout, verbose flag, and progress handle.

        Returns:
            The decoded stdout from the subprocess.

        Raises:
            AgentError: If the AI name is unsupported, the subprocess times out, or exits non-zero.
        """
        commands = self._get_commands()
        if ai not in commands:
            raise AgentError(f"Unsupported AI: {ai!r}. Must be one of {list(commands)}")

        # Verbose: log the prompt being sent
        if context and context.verbose:
            _verbose_print(context, f"[dim cyan]→ [{ai}] prompt:[/dim cyan]\n{prompt}")

        cmd = commands[ai] + [prompt]
        timeout = context.timeout if context else None

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            if timeout is not None:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            else:
                stdout, stderr = await process.communicate()
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass  # process already exited before we could kill it
            await process.communicate()  # reap zombie — must not be omitted
            raise AgentError(f"TIMEOUT after {timeout}s")

        if process.returncode != 0:
            raise AgentError(f"{ai} subprocess failed: {stderr.decode()}")

        result = stdout.decode()

        # Verbose: log the raw response
        if context and context.verbose:
            _verbose_print(context, f"[dim white]← [{ai}] response:[/dim white]\n{result}")

        return result


def _verbose_print(context: RunContext, message: str) -> None:
    """Print verbose output through the shared console, falling back to a new Console."""
    from rich.console import Console
    if context.progress is not None:
        context.progress.console.print(message)
    else:
        Console().print(message)
