import json


# Research task descriptions keyed by agent type
RESEARCH_TASKS: dict[str, str] = {
    "email": "Find breach data, registrations, associated usernames and domains for target email",
    "domain": "Find WHOIS, DNS records, subdomains, IP addresses, tech stack for target domain",
    "phone": "Validate format, identify carrier/region/country, find any public registrations for target phone",
    "person": "Find public records, social profiles, email addresses, usernames for target person",
    "username": "Check existence across major platforms, find associated profiles for target username",
    "social": "Find cross-platform presence, follower counts, bio info for target social handle",
    "image": "Extract EXIF data, identify GPS coordinates, suggest reverse image search for target image path",
    "location": "Geocode, find nearby landmarks, reverse-lookup address details for target location",
    "ip": "Find geolocation, ASN/ISP, reverse DNS, reputation, blacklists, open ports history, and hosting provider for target IP address",
}

# AI-specific instruction preambles
AI_INSTRUCTIONS: dict[str, str] = {
    "gemini": "Use your web search to look up",
    "claude": "Analyze the following and reason through",
    "codex": "Write and execute Python code to",
}

# Pivot extraction hints keyed by agent type
PIVOT_HINTS: dict[str, str] = {
    "email": 'Extract pivot entities of type "domain" (the email domain) and "username" (the local part or discovered usernames).',
    "domain": 'Extract pivot entities of type "ip" for dedicated server IP addresses found in DNS A/MX records (exclude CDN/shared-infrastructure IPs like Cloudflare, Fastly, Akamai, AWS CloudFront). Also extract pivot entities of type "domain" for related subdomains and associated domains.',
    "username": 'Extract pivot entities of type "social" for each platform profile discovered.',
    "image": 'Extract pivot entities of type "location" for any GPS coordinates found in EXIF data.',
    "phone": 'Extract pivot entities of type "location" for the region or country identified.',
    "person": 'Extract pivot entities of type "email" and "username" for all discovered addresses and handles.',
    "social": 'Extract pivot entities of type "username" for all associated usernames found.',
    "location": "",  # no specific pivot hint
    "ip": "",  # IP is a research endpoint — no further pivots (primary only)
}

# JSON schema example shown in the prompt
_SCHEMA_EXAMPLE = json.dumps(
    {
        "found": True,
        "data": {"...gathered fields...": "..."},
        "pivots": [
            {"type": "domain", "value": "example.com"},
            {"type": "username", "value": "johndoe"},
        ],
    },
    indent=2,
)


class PromptBuilder:
    """Builds structured prompts for OSINT research tasks."""

    def build(self, agent_type: str, ai: str, target: str) -> str:
        """Construct a prompt for the given agent type, AI, and target.

        Args:
            agent_type: One of the supported agent types (email, domain, phone, etc.).
            ai: One of "gemini", "claude", or "codex".
            target: The target value to research.

        Returns:
            A fully-formed prompt string.
        """
        task = RESEARCH_TASKS.get(
            agent_type,
            f"Gather all available public OSINT information for target {agent_type}",
        )
        ai_instruction = AI_INSTRUCTIONS.get(ai, "Research")
        pivot_hint = PIVOT_HINTS.get(agent_type, "")

        pivot_section = f"\n{pivot_hint}" if pivot_hint else ""

        prompt = (
            f"You are an OSINT research assistant.\n"
            f"\n"
            f"Task: {task}.\n"
            f"Target: {target}\n"
            f"\n"
            f"{ai_instruction} the target and gather as much relevant information as possible.\n"
            f"{pivot_section}\n"
            f"You MUST respond ONLY with a JSON object matching this schema — no prose, "
            f"no markdown, no code fences:\n"
            f"{_SCHEMA_EXAMPLE}\n"
        )
        return prompt.strip()


def parse_json_response(response: str) -> dict:
    """Extract first valid JSON object from response string."""
    fallback: dict = {"found": False, "data": {}, "pivots": []}
    try:
        start = response.index("{")
        depth = 0
        for i, ch in enumerate(response[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(response[start : i + 1])
    except (ValueError, json.JSONDecodeError):
        pass
    return fallback
