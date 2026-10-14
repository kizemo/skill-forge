"""Phase 4: three-judge gate. Deterministic + LLM rubric + user spot-check.

When llm_call is None the rubric gate is SKIPPED (RULING-1 in
.superpowers/sdd/plans/2026-10-14-skill-forge/progress.md), not defaulted
to a passive 0.5. Absent != failure.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from scripts._lib.frontmatter import load, FrontmatterError
from scripts.audit import AuditReport

@dataclass
class TripleVerdict:
    deterministic_pass: bool
    llm_score: float
    spot_accepted: bool | None
    accept: bool

def _deterministic_trace(path: Path) -> bool:
    try:
        fm = load(path)
    except FrontmatterError:
        return False
    name = fm.get("name")
    desc = fm.get("description", "")
    if not isinstance(name, str) or not name:
        return False
    if not desc.lower().startswith("use when"):
        return False
    body = path.read_text(encoding="utf-8").split("---", 2)[-1]
    if "TODO" in body or "TBD" in body:
        return False
    return True

def judge(candidate: Path, baseline: Path, report: AuditReport, *,
          llm_call: Callable[[str], float] | None = None,
          spot_input: dict | None = None) -> TripleVerdict:
    det = _deterministic_trace(candidate)
    if llm_call is None:
        llm_score = 0.0  # RULING-1: rubric absent → score 0, gate SKIPPED
        rubric_pass = True
    else:
        llm_score = max(0.0, min(1.0, llm_call(f"score {candidate}")))
        rubric_pass = llm_score >= 0.6
    if spot_input is None:
        spot = None
    else:
        spot = bool(spot_input.get("verdict"))
    accept = det and rubric_pass and (spot is not False)
    return TripleVerdict(det, llm_score, spot, accept)
