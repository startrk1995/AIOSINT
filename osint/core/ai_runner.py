import asyncio


class AgentError(Exception):
    pass


class AIRunner:
    """Dispatches prompts to AI CLI subprocesses (gemini, claude, codex)."""

    COMMANDS: dict[str, list[str]] = {
        "gemini": ["gemini", "-p"],
        "claude": ["claude", "-p"],
        "codex": ["codex", "-q", "--json"],
    }

    async def run(self, ai: str, prompt: str) -> str:
        """Run the given AI CLI with the prompt and return stdout as a string.

        Args:
            ai: One of "gemini", "claude", or "codex".
            prompt: The prompt string to pass to the AI CLI.

        Returns:
            The decoded stdout from the subprocess.

        Raises:
            AgentError: If the AI name is unsupported or the subprocess exits non-zero.
        """
        if ai not in self.COMMANDS:
            raise AgentError(f"Unsupported AI: {ai!r}. Must be one of {list(self.COMMANDS)}")

        cmd = self.COMMANDS[ai] + [prompt]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise AgentError(f"{ai} subprocess failed: {stderr.decode()}")

        return stdout.decode()
