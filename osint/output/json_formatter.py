import json
from osint.core.result import OsintResult


def format_results(results: list[OsintResult]) -> str:
    """
    Serialize OsintResults to a pretty JSON string.

    Args:
        results: List of OsintResults to serialize

    Returns:
        Pretty-printed JSON string representation of results
    """
    # Convert results to dictionaries
    data = [
        {
            "agent": r.agent,
            "target": r.target,
            "ai_used": r.ai_used,
            "success": r.success,
            "data": r.data,
            "pivots": [
                {
                    "type": pivot.type,
                    "value": pivot.value
                }
                for pivot in r.pivots
            ],
            "raw_response": r.raw_response,
            "error": r.error,
            "timestamp": r.timestamp
        }
        for r in results
    ]

    return json.dumps(data, indent=2)


def save_results(results: list[OsintResult], filepath: str) -> None:
    """
    Write JSON serialized results to a file.

    Args:
        results: List of OsintResults to save
        filepath: Path where the JSON file should be written
    """
    json_string = format_results(results)
    with open(filepath, 'w') as f:
        f.write(json_string)
