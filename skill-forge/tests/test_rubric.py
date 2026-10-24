"""P0-2: the rubric judge must actually READ the candidate and the baseline.

Before P0-2 the rubric prompt carried only the two PATHS
(`f"score candidate={candidate} baseline={baseline}"`), so a judge that
has no filesystem access — which is every remote model — was scoring
nothing. The prompt must carry the bodies.
"""
from pathlib import Path
import pytest
from scripts.audit import AuditReport
from scripts.judge_triple import judge, rubric_prompt
from scripts._lib.llm_channel import RubricError


def _pair(tmp_path: Path) -> tuple[Path, Path]:
    base = tmp_path / "base.md"
    cand = tmp_path / "cand.md"
    base.write_text(
        "---\nname: x\ndescription: Use when A or B.\n---\n# BASELINE-BODY-MARKER\n",
        encoding="utf-8",
    )
    cand.write_text(
        "---\nname: x\ndescription: Use when A or B.\n---\n# CANDIDATE-BODY-MARKER\n",
        encoding="utf-8",
    )
    return base, cand


def test_rubric_prompt_carries_the_candidate_body(tmp_path: Path):
    base, cand = _pair(tmp_path)
    p = rubric_prompt(cand, base)
    assert "CANDIDATE-BODY-MARKER" in p


def test_rubric_prompt_carries_the_baseline_body(tmp_path: Path):
    base, cand = _pair(tmp_path)
    p = rubric_prompt(cand, base)
    assert "BASELINE-BODY-MARKER" in p


def test_rubric_prompt_carries_both_paths_too(tmp_path: Path):
    base, cand = _pair(tmp_path)
    p = rubric_prompt(cand, base)
    assert str(cand) in p
    assert str(base) in p


def test_rubric_prompt_truncates_oversized_bodies(tmp_path: Path):
    base, cand = _pair(tmp_path)
    cand.write_text("X" * 50_000, encoding="utf-8")
    p = rubric_prompt(cand, base, limit=500)
    assert len(p) < 5_000, len(p)
    assert "truncated" in p


def test_rubric_prompt_survives_an_unreadable_baseline(tmp_path: Path):
    base, cand = _pair(tmp_path)
    base.unlink()
    p = rubric_prompt(cand, base)
    assert "CANDIDATE-BODY-MARKER" in p


def test_judge_passes_the_bodies_to_the_llm_call(tmp_path: Path):
    """The prompt handed to llm_call must contain the bodies, not paths."""
    base, cand = _pair(tmp_path)
    seen: list[str] = []

    def llm_call(prompt: str) -> float:
        seen.append(prompt)
        return 0.9

    judge(cand, base, AuditReport("prompt", 0.8, [], "improve"), llm_call=llm_call)
    assert seen, "llm_call was never invoked"
    assert "CANDIDATE-BODY-MARKER" in seen[0]
    assert "BASELINE-BODY-MARKER" in seen[0]


def test_judge_skips_the_rubric_when_the_channel_errors(tmp_path: Path):
    """A configured-but-broken judge is an infrastructure failure, not a
    quality verdict. It must NOT become a score of 0.0 (which would read
    as "the judge said no"). The rubric is skipped and the error is
    reported to the caller's sink."""

    def llm_call(_prompt: str) -> float:
        raise RubricError("401 token is required")

    errors: list[str] = []
    v = judge(
        cand := _pair(tmp_path)[1], _pair(tmp_path)[0],
        AuditReport("prompt", 0.8, [], "improve"),
        llm_call=llm_call, on_rubric_error=errors.append,
    )
    assert v.llm_score == 0.0
    assert v.accept is True, "an errored judge must not block the run"
    assert errors, "the rubric error must be reported, not swallowed"
    assert "401" in errors[0]


def test_judge_reraises_the_channel_error_without_a_sink(tmp_path: Path):
    """Without a sink there is nowhere to report the error, so it must
    propagate rather than vanish."""

    def llm_call(_prompt: str) -> float:
        raise RubricError("boom")

    base, cand = _pair(tmp_path)
    with pytest.raises(RubricError):
        judge(cand, base, AuditReport("prompt", 0.8, [], "improve"), llm_call=llm_call)
