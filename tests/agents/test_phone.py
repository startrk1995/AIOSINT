import pytest
from osint.agents.phone import normalize_phone


@pytest.mark.parametrize("raw, expected", [
    ("+1-555-999-0202", "555-999-0202"),
    ("1-555-999-0202",  "555-999-0202"),
    ("5559990202",      "555-999-0202"),
    ("555-999-0202",    "555-999-0202"),
    ("(555) 999-0202",  "555-999-0202"),
    ("(555)999-0202",   "555-999-0202"),
    ("555.999.0202",    "555-999-0202"),
    # Non-US: pass through unchanged (>10 significant digits)
    ("+44-20-7946-0958", "+44-20-7946-0958"),
])
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected
