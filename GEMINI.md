# OSINT Project Overview

This workspace is dedicated to **Open Source Intelligence (OSINT)** research and investigations. It is designed to leverage AI-driven research agents, specifically utilizing the Gemini CLI for automated information gathering and analysis.

## Core Agent: gemini-research

The project includes a specialized agent configuration located at `.claude/agents/gemini-research.md`.

### Purpose
The `gemini-research` agent is a specialist designed to:
- Gather accurate, current information from the web.
- Formulate precise search queries.
- Synthesize findings into actionable insights.
- Build persistent memory of research tasks and user preferences.

### Workflow
1.  **Analyze**: Understand the research task.
2.  **Formulate**: Create targeted search queries.
3.  **Execute**: Run searches using the command:
    ```bash
    gemini -p "your search query"
    ```
4.  **Synthesize**: Summarize findings with citations.

## Directory Structure

- **`.claude/agents/`**: Contains the definition and instructions for the `gemini-research` agent.
- **`.claude/agent-memory/gemini-research/`**: Stores persistent memory for the research agent, including user preferences, feedback, and project context.
- **`GEMINI.md`**: (This file) Provides instructional context for interactions within this workspace.

## Usage Guidelines

- **Research Tasks**: When starting a new OSINT investigation, engage the `gemini-research` agent.
- **Persistence**: Encourage the agent to save important findings to its memory at `.claude/agent-memory/gemini-research/` to maintain context across sessions.
- **Search Precision**: Use specific, keyword-rich queries for better results from the Gemini CLI.
