from pathlib import Path
from scripts.audit import AuditReport
from scripts.judge_triple import judge, TripleVerdict

def _pair(tmp_path: Path) -> tuple[Path, Path]:
    base = tmp_path / "base.md"
    cand = tmp_path / "cand.md"
    base.write_text("---\nname: x\ndescription: Use when A or B.\n---\n# body\n", encoding="utf-8")
    cand.write_text(base.read_text(encoding="utf-8"), encoding="utf-8")
    return base, cand

def test_judge_accepts_identical_candidate(tmp_path: Path):
    base, cand = _pair(tmp_path)
    v = judge(cand, base, AuditReport("prompt", 0.8, [], "improve"))
    assert isinstance(v, TripleVerdict)
    assert v.accept is True
    assert v.llm_score == 0.0  # RULING-1: absent → 0.0 (rubric skipped, did not run)

def test_judge_refuses_when_deterministic_fails(tmp_path: Path):
    base, cand = _pair(tmp_path)
    cand.write_text("# no frontmatter at all\n", encoding="utf-8")
    v = judge(cand, base, AuditReport("prompt", 0.8, [], "improve"))
    assert v.deterministic_pass is False
    assert v.accept is False

def test_judge_refuses_when_llm_rubric_below_threshold(tmp_path: Path):
    base, cand = _pair(tmp_path)

    def llm_call(_prompt: str) -> float:
        return 0.2  # simulate model gaming keyword + intent score 0.2

    v = judge(cand, base, AuditReport("prompt", 0.8, [], "improve"), llm_call=llm_call)
    assert v.llm_score == 0.2
    assert v.accept is False

def test_judge_refuses_on_spot_reject(tmp_path: Path):
    base, cand = _pair(tmp_path)
    v = judge(cand, base, AuditReport("prompt", 0.8, [], "improve"), spot_input={"verdict": False})
    assert v.spot_accepted is False
    assert v.accept is False

def test_judge_keeps_spot_optional(tmp_path: Path):
    base, cand = _pair(tmp_path)
    v = judge(cand, base, AuditReport("prompt", 0.8, [], "improve"))
    assert v.spot_accepted is None
    assert v.accept is True  # spot skipped, deterministic passed, llm skipped per RULING-1

# --- v2-T2 (RULING-8 v2 items 1 + 2) ---------------------------------------

def test_judge_refuses_on_non_string_description_without_raising(tmp_path):
    """Regression for T5 RULING-8 v2 item 1: a SKILL.md whose `description`
    is a YAML list (not a string) must cause _deterministic_trace() to
    return False, NOT raise AttributeError. A gate must never raise."""
    cand = tmp_path / "cand.md"
    cand.write_text(
        "---\n"
        "name: x\n"
        "description:\n"
        "  - Use when triggering on a YAML-list description.\n"
        "  - Use when a list-form is parsed as a non-string.\n"
        "---\n"
        "# body\n",
        encoding="utf-8",
    )
    base = tmp_path / "base.md"
    base.write_text(cand.read_text(encoding="utf-8"), encoding="utf-8")
    # No exception should propagate out of judge(); the gate refuses.
    v = judge(cand, base, AuditReport("prompt", 0.8, [], "improve"))
    assert v.deterministic_pass is False
    assert v.accept is False

def test_rubric_prompt_contains_baseline_content(tmp_path):
    """RULING-8 v2 item 2: `baseline` is promoted from reserved to consumed.
    The LLM rubric prompt must reference the baseline body (or path), so a
    real llm_call can perform a candidate-vs-baseline comparison. v1's
    prompt was exactly `f"score {candidate}"`; v2 must include baseline."""
    base = tmp_path / "base.md"
    cand = tmp_path / "cand.md"
    base.write_text(
        "---\nname: x\ndescription: Use when A or B with symptom S.\n---\n# baseline body\n",
        encoding="utf-8",
    )
    cand.write_text(
        "---\nname: x\ndescription: Use when A or B with symptom S.\n---\n# candidate body\n",
        encoding="utf-8",
    )
    seen_prompt: list[str] = []

    def fake_llm(prompt: str) -> float:
        seen_prompt.append(prompt)
        return 0.7

    v = judge(
        cand, base, AuditReport("prompt", 0.8, [], "improve"),
        llm_call=fake_llm,
    )
    assert len(seen_prompt) == 1
    prompt = seen_prompt[0]
    # Baseline content (or path) must appear in the prompt. We accept either:
    #   - the baseline body text "# baseline body", or
    #   - the baseline path's string form (so a downstream consumer can read it).
    assert (
        "baseline body" in prompt
        or str(base) in prompt
        or base.name in prompt
    ), f"rubric prompt lacks baseline content: {prompt!r}"
    # Candidate content must also appear (this is a candidate-vs-baseline comparison).
    assert (
        "candidate body" in prompt
        or str(cand) in prompt
        or cand.name in prompt
    ), f"rubric prompt lacks candidate content: {prompt!r}"

def test_rubric_skipped_path_unchanged_by_baseline_promotion(tmp_path):
    """RULING-1 invariant: when llm_call is None, the rubric is SKIPPED.
    v2-T2's baseline promotion must not introduce any new branching in the
    skipped path; the score stays 0.0 and the gate stays open."""
    base, cand = _pair(tmp_path)
    v = judge(cand, base, AuditReport("prompt", 0.8, [], "improve"))
    assert v.llm_score == 0.0
    assert v.accept is True  # deterministic passed, rubric skipped, spot None

def test_judge_promoted_baseline_does_not_break_identical_pair(tmp_path):
    """v1 T7 stub used `baseline = candidate`; that pattern must still
    accept when both bodies are identical after the baseline promotion."""
    base, cand = _pair(tmp_path)
    v = judge(cand, base, AuditReport("prompt", 0.8, [], "improve"))
    assert v.accept is True
