from osint.core.run_context import RunContext


def test_defaults():
    ctx = RunContext()
    assert ctx.verbose is False
    assert ctx.timeout == 90.0
    assert ctx.timeout_action == "warn"
    assert ctx.progress is None
    assert ctx._timings == {}


def test_verbose_flag():
    ctx = RunContext(verbose=True)
    assert ctx.verbose is True


def test_custom_timeout():
    ctx = RunContext(timeout=30.0, timeout_action="kill")
    assert ctx.timeout == 30.0
    assert ctx.timeout_action == "kill"


def test_timings_mutable():
    ctx = RunContext()
    ctx._timings["email:foo@bar.com"] = 12.5
    assert ctx._timings["email:foo@bar.com"] == 12.5


def test_two_contexts_dont_share_timings():
    a = RunContext()
    b = RunContext()
    a._timings["x"] = 1.0
    assert "x" not in b._timings
