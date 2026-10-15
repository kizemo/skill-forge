"""Phase 4: three-judge gate. Deterministic + LLM rubric + user spot-check.

When llm_call is None the rubric gate is SKIPPED (RULING-1 in
.superpowers/sdd/plans/2026-10-14-skill-forge/progress.md), not defaulted
to a passive 0.5. Absent != failure.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from scripts._lib.frontmatter import load, body_of, FrontmatterError
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
    # v2-T2 (RULING-8 v2 item 1): a non-string `description` (e.g. a YAML
    # list) would raise AttributeError on .lower(). A gate must never raise;
    # refuse instead. Same total-gate guarantee as the v2-T1 try/except
    # around body_of() below — see review-v2-task-1.md § 7 carry-forward #3.
    if not isinstance(desc, str) or not desc.lower().startswith("use when"):
        return False
    # body_of() re-uses the load() fence rule (v2-T1). A gate must never
    # raise, so any structural error degrades to False just like load() does.
    try:
        body = body_of(path)
    except FrontmatterError:
        return False
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
        # v2-T2 (RULING-8 v2 item 2): `baseline` is now consumed. The rubric
        # prompt carries both candidate and baseline paths so a real llm_call
        # can perform the candidate-vs-baseline comparison. We pass paths only;
        # the downstream llm_call reads the files itself. Reading the bodies
        # here would be a second I/O path that must stay total; the path-only
        # form keeps the call site a single try/except-free line.
        prompt = f"score candidate={candidate} baseline={baseline}"
        llm_score = max(0.0, min(1.0, llm_call(prompt)))
        rubric_pass = llm_score >= 0.6
    if spot_input is None:
        spot = None
    else:
        spot = bool(spot_input.get("verdict"))
    accept = det and rubric_pass and (spot is not False)
    return TripleVerdict(det, llm_score, spot, accept)
