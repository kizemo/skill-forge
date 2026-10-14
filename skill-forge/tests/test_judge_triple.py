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
