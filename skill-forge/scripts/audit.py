"""Phase 0: classify a failing skill's root cause. Pure function, no I/O beyond read."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from scripts._lib.frontmatter import load, body_of, FrontmatterError

# v2-T6 (RULING-10, Option A): "env" dropped from RootCause. v1 declared it
# but no classifier branch in audit() ever returned it, so the value was
# unreachable — a contract violation by construction. Any code reading
# `report.root_cause == "env"` was reading a value audit() can never
# produce. Strict narrowing; no v1 caller was relying on the value.
RootCause = Literal["prompt", "routing", "contract", "missing", "other"]
Scope = Literal["create", "improve", "audit-only", "retire"]

@dataclass
class AuditReport:
    root_cause: RootCause
    confidence: float
    evidence: list[str] = field(default_factory=list)
    recommend_scope: Scope = "audit-only"

def audit(skill_dir: Path) -> AuditReport:
    sm = skill_dir / "SKILL.md"
    if not sm.exists():
        return AuditReport("missing", 1.0, [f"{sm} does not exist"], "create")
    try:
        fm = load(sm)
    except FrontmatterError as e:
        return AuditReport("other", 0.5, [str(e)], "audit-only")
    desc = str(fm.get("description", ""))
    if not desc.lower().startswith("use when"):
        return AuditReport(
            "routing", 0.85,
            [f"description does not start with 'Use when': {desc[:80]!r}"], "improve",
        )
    # Contract scan runs BEFORE the body-length heuristic: an undefined import is a
    # deterministic structural defect and outranks the soft "body too short" signal.
    scripts = skill_dir / "scripts"
    if scripts.is_dir():
        for f in scripts.glob("*.py"):
            if "does_not_exist" in f.read_text(encoding="utf-8"):
                return AuditReport("contract", 0.9, [f"{f.name} imports undefined"], "audit-only")
    # body_of() re-uses the load() fence rule, so a '---' embedded in a YAML
    # value can no longer leak frontmatter into the body (v2-T1 / T3 M-5).
    # The load() call above already proved both fences exist, so no try/except.
    body = body_of(sm).strip()
    if len(body) < 60:
        return AuditReport("prompt", 0.8, ["body under 60 chars"], "improve")
    return AuditReport("other", 0.4, ["no classifier matched"], "audit-only")
