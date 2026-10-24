"""P0-2: the LLM channel that backs the Phase 4 rubric judge.

The rubric must be able to run against a real model (a judge that is a
different source from the candidate's author), and it must degrade the
way RULING-1 says: an ABSENT rubric is skipped, not a failure.
"""
import subprocess
from pathlib import Path
import pytest
from scripts._lib.llm_channel import (
    RubricError,
    make_llm_call,
    parse_score,
)


# --- parse_score -----------------------------------------------------------

def test_parse_score_reads_a_plain_number():
    assert parse_score("0.85") == pytest.approx(0.85)


def test_parse_score_reads_a_number_with_a_label():
    assert parse_score("SCORE: 0.72") == pytest.approx(0.72)


def test_parse_score_reads_a_number_inside_prose():
    assert parse_score("After review, the score is 0.61 overall.") == pytest.approx(0.61)


def test_parse_score_reads_a_bolded_number():
    assert parse_score("**0.40**") == pytest.approx(0.40)


def test_parse_score_clamps_above_one():
    assert parse_score("1.4") == pytest.approx(1.0)


def test_parse_score_clamps_below_zero():
    assert parse_score("-0.3") == pytest.approx(0.0)


def test_parse_score_raises_on_garbage():
    with pytest.raises(RubricError):
        parse_score("I refuse to score this.")


# --- make_llm_call ---------------------------------------------------------

def _script(tmp_path: Path, body: str = "") -> Path:
    s = tmp_path / "llm_call.py"
    s.write_text(body or "# stub\n", encoding="utf-8")
    return s


def test_make_llm_call_returns_none_when_no_model_configured(tmp_path):
    """No judge configured -> no llm_call -> RULING-1 skip. The channel
    must not fabricate a judge."""
    assert make_llm_call(model=None, script=_script(tmp_path)) is None


def test_make_llm_call_returns_none_when_script_missing(tmp_path):
    """The judge script is not on this host -> no llm_call -> RULING-1 skip."""
    assert make_llm_call(model="minimax/MiniMax-M3", script=tmp_path / "nope.py") is None


def test_make_llm_call_invokes_the_script_with_the_model(tmp_path, monkeypatch):
    seen: list[list[str]] = []

    def fake_run(cmd, **kw):
        seen.append(list(cmd))
        class R:
            returncode = 0
            stdout = b"0.80"
            stderr = b""
        return R()

    monkeypatch.setattr("subprocess.run", fake_run)
    fn = make_llm_call(model="minimax/MiniMax-M3", script=_script(tmp_path))
    assert fn is not None
    score = fn("score this")
    assert score == pytest.approx(0.80)
    assert seen, "the judge script was never invoked"
    cmd = seen[0]
    assert "--model" in cmd
    assert "minimax/MiniMax-M3" in cmd
    assert "score this" in cmd


def test_make_llm_call_passes_the_whole_prompt_to_the_script(tmp_path, monkeypatch):
    """The prompt must reach the judge verbatim — it carries the candidate
    and baseline bodies, so truncation here would silently blind the judge."""
    seen: list[list[str]] = []

    def fake_run(cmd, **kw):
        seen.append(list(cmd))
        class R:
            returncode = 0
            stdout = b"0.5"
            stderr = b""
        return R()

    monkeypatch.setattr("subprocess.run", fake_run)
    fn = make_llm_call(model="m/x", script=_script(tmp_path))
    prompt = "CANDIDATE BODY\nline1\nline2\nBASELINE BODY\nline3"
    fn(prompt)
    assert prompt in " ".join(seen[0]), seen[0]


def test_make_llm_call_raises_rubric_error_on_nonzero_exit(tmp_path, monkeypatch):
    def fake_run(cmd, **kw):
        class R:
            returncode = 1
            stdout = b""
            stderr = b"401 token is required"
        return R()

    monkeypatch.setattr("subprocess.run", fake_run)
    fn = make_llm_call(model="m/x", script=_script(tmp_path))
    with pytest.raises(RubricError):
        fn("prompt")


def test_make_llm_call_raises_rubric_error_on_timeout(tmp_path, monkeypatch):
    def fake_run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=1)

    monkeypatch.setattr("subprocess.run", fake_run)
    fn = make_llm_call(model="m/x", script=_script(tmp_path))
    with pytest.raises(RubricError):
        fn("prompt")


def test_make_llm_call_raises_rubric_error_on_unparseable_output(tmp_path, monkeypatch):
    def fake_run(cmd, **kw):
        class R:
            returncode = 0
            stdout = b"I will not answer that."
            stderr = b""
        return R()

    monkeypatch.setattr("subprocess.run", fake_run)
    fn = make_llm_call(model="m/x", script=_script(tmp_path))
    with pytest.raises(RubricError):
        fn("prompt")
