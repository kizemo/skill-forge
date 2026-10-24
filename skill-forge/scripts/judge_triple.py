"""Phase 4: three-judge gate. Deterministic + LLM rubric + user spot-check.

When llm_call is None the rubric gate is SKIPPED (RULING-1 in
.superpowers/sdd/plans/2026-10-14-skill-forge/progress.md), not defaulted
to a passive 0.5. Absent != failure.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from scripts._lib.frontmatter import load, body_of, FrontmatterError
from scripts._lib.llm_channel import RubricError
from scripts.audit import AuditReport

# P0-2: the rubric prompt must carry the candidate and baseline BODIES.
# v2-T2 (RULING-8 part 2) deliberately passed only the paths, on the
# theory that the downstream llm_call would read the files itself. That
# works only for a judge with filesystem access — a remote model sees
# two paths and nothing else, and scores nothing. P0-2 supersedes that
# decision: the bodies travel in the prompt, so any judge that can read
# text can judge.
RUBRIC_TEMPLATE = """You are an independent reviewer of Agent Skills.
Compare the CANDIDATE skill against the BASELINE skill.

Score the candidate from 0.0 to 1.0 on how much better it is as a skill:
- Is the description a clear routing trigger ("Use when ...", <= 50 words)?
- Does the body have substance (phases, gotchas, red flags) rather than
  filler?
- Is it free of unresolved placeholders (TODO / TBD)?

Reply with ONLY a single number between 0.0 and 1.0. No explanation.

--- BASELINE ({baseline_path}) ---
{baseline_body}

--- CANDIDATE ({candidate_path}) ---
{candidate_body}
"""

# Each body is capped so the prompt stays inside the OS command-line
# limit on Windows (32,767 chars) and inside a sane token budget.
DEFAULT_BODY_LIMIT = 12_000


@dataclass
class TripleVerdict:
    deterministic_pass: bool
    llm_score: float
    spot_accepted: bool | None
    accept: bool


def _read_for_rubric(path: Path, limit: int) -> str:
    """Read a SKILL.md body for the rubric prompt, truncated to `limit`."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "(unreadable)"
    if len(text) > limit:
        return text[:limit] + f"\n... [truncated; {len(text)} chars total]"
    return text


def rubric_prompt(candidate: Path, baseline: Path, *, limit: int = DEFAULT_BODY_LIMIT) -> str:
    """Build the rubric prompt: candidate body + baseline body + both paths."""
    return RUBRIC_TEMPLATE.format(
        candidate_path=candidate,
        baseline_path=baseline,
        candidate_body=_read_for_rubric(candidate, limit),
        baseline_body=_read_for_rubric(baseline, limit),
    )

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
          spot_input: dict | None = None,
          on_rubric_error: Callable[[str], None] | None = None) -> TripleVerdict:
    """Run the three gates.

    RULING-1: `llm_call is None` means the rubric is SKIPPED, not failed.

    P0-2: a rubric that is configured but ERRORS (network, auth, an
    unreadable answer) is an infrastructure failure, not a quality
    verdict. It is reported through `on_rubric_error` and the rubric is
    skipped — it must not become a score of 0.0, because 0.0 reads as
    "the judge said no". Without a sink there is nowhere to report the
    error, so it propagates rather than vanishing.
    """
    det = _deterministic_trace(candidate)
    if llm_call is None:
        llm_score = 0.0  # RULING-1: rubric absent → score 0, gate SKIPPED
        rubric_pass = True
    else:
        # P0-2: the prompt carries the candidate and baseline BODIES (not
        # just their paths), so a judge without filesystem access can still
        # compare the two skills. v2-T2 (RULING-8 v2 item 2) deliberately
        # passed paths only, on the theory that the llm_call would read the
        # files itself — true only for an in-process judge. P0-2 supersedes
        # that: any judge that can read text can judge.
        prompt = rubric_prompt(candidate, baseline)
        try:
            raw = llm_call(prompt)
        except RubricError as e:
            if on_rubric_error is None:
                raise
            on_rubric_error(str(e))
            llm_score = 0.0
            rubric_pass = True  # skipped, not failed
        else:
            llm_score = max(0.0, min(1.0, raw))
            rubric_pass = llm_score >= 0.6
    if spot_input is None:
        spot = None
    else:
        spot = bool(spot_input.get("verdict"))
    accept = det and rubric_pass and (spot is not False)
    return TripleVerdict(det, llm_score, spot, accept)
