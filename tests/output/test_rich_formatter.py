from io import StringIO
from rich.console import Console
from osint.output.rich_formatter import format_result, format_results
from osint.core.result import OsintResult, PivotEntity


def make_result(**kwargs):
    defaults = dict(
        agent="email", target="foo@bar.com", ai_used="gemini",
        success=True, data={}, pivots=[], raw_response="", error=None,
        timestamp="2026-03-13T00:00:00+00:00",
    )
    defaults.update(kwargs)
    return OsintResult(**defaults)


def capture(fn, *args, **kwargs) -> str:
    buf = StringIO()
    console = Console(file=buf, no_color=True)
    fn(*args, console=console, **kwargs)
    return buf.getvalue()


def test_format_result_shows_agent_and_target():
    r = make_result()
    out = capture(format_result, r)
    assert "email" in out
    assert "foo@bar.com" in out


def test_format_result_shows_elapsed():
    r = make_result()
    out = capture(format_result, r, elapsed=12.4)
    assert "12.4s" in out


def test_format_result_list_data_as_bullets():
    r = make_result(data={"communities": ["Hak5", "Netgear"]})
    out = capture(format_result, r)
    assert "Hak5" in out
    assert "Netgear" in out


def test_format_result_dict_data_indented():
    r = make_result(data={"meta": {"key": "val"}})
    out = capture(format_result, r)
    assert "key" in out
    assert "val" in out


def test_format_result_pivots_grouped():
    r = make_result(pivots=[
        PivotEntity(type="domain", value="github.com"),
        PivotEntity(type="username", value="johndoe"),
    ])
    out = capture(format_result, r)
    assert "github.com" in out
    assert "johndoe" in out


def test_format_results_shows_summary_table():
    results = [make_result(), make_result(agent="domain", target="github.com")]
    buf = StringIO()
    console = Console(file=buf, no_color=True)
    format_results(results, console=console)
    out = buf.getvalue()
    assert "Agent" in out or "email" in out  # table header or row


def test_format_results_with_timings():
    results = [make_result()]
    buf = StringIO()
    console = Console(file=buf, no_color=True)
    from osint.core.run_context import RunContext
    ctx = RunContext()
    ctx._timings["email:foo@bar.com"] = 8.3
    format_results(results, console=console, context=ctx)
    out = buf.getvalue()
    assert "8.3" in out
