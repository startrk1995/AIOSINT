from io import StringIO
from osint.output.report_formatter import format_results
from osint.core.result import OsintResult, PivotEntity
from osint.core.run_context import RunContext


def make_result(**kwargs):
    defaults = dict(
        agent="email", target="foo@bar.com", ai_used="gemini",
        success=True, data={"identity": "Nate", "tags": ["hardware", "rfid"]},
        pivots=[PivotEntity(type="domain", value="github.com")],
        raw_response="", error=None,
        timestamp="2026-03-13T00:00:00+00:00",
    )
    defaults.update(kwargs)
    return OsintResult(**defaults)


def capture_report(results, context=None) -> str:
    buf = StringIO()
    format_results(results, stream=buf, context=context)
    return buf.getvalue()


def test_report_has_header():
    out = capture_report([make_result()])
    assert "OSINT REPORT" in out


def test_report_has_target_summary():
    out = capture_report([make_result()])
    assert "foo@bar.com" in out


def test_report_has_agent_section():
    out = capture_report([make_result()])
    assert "EMAIL" in out.upper()


def test_report_shows_data_fields():
    out = capture_report([make_result()])
    assert "Nate" in out
    assert "hardware" in out


def test_report_shows_pivots():
    out = capture_report([make_result()])
    assert "github.com" in out


def test_report_shows_timeout_label():
    r = make_result(success=False, error="AgentError: TIMEOUT after 90.0s")
    out = capture_report([r])
    assert "[TIMEOUT]" in out


def test_report_timeout_shows_threshold_from_context():
    """context.timeout should appear in the [TIMEOUT] line."""
    r = make_result(success=False, error="AgentError: TIMEOUT after 45.0s")
    ctx = RunContext(timeout=45.0)
    out = capture_report([r], context=ctx)
    assert "45" in out


def test_report_shows_failed_label():
    r = make_result(success=False, error="AgentError: something went wrong")
    out = capture_report([r])
    assert "[FAILED]" in out


def test_report_shows_elapsed_with_context():
    ctx = RunContext()
    ctx._timings["email:foo@bar.com"] = 14.2
    out = capture_report([make_result()], context=ctx)
    assert "14.2" in out


def test_save_results_writes_file(tmp_path):
    from osint.output.report_formatter import save_results
    path = tmp_path / "report.txt"
    save_results([make_result()], str(path))
    assert path.exists()
    assert "OSINT REPORT" in path.read_text()
