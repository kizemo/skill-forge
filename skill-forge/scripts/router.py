"""Phase 3: forward to gbrain or skill-creator, or degrade gracefully."""
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from scripts.audit import AuditReport
from scripts._lib.bundle import is_bundled

Target = Literal["gbrain-skillopt", "skill-creator", "diagnose-only"]

@dataclass
class RouteResult:
    forwarded_to: Target
    exit_code: int
    stdout: str
    degraded: bool = False
    # v2-T4: machine-readable degradation cause. Backwards-compatible
    # widening — existing positional/keyword construction is unaffected.
    reason: str | None = None

def route(skill_dir: Path, scope: str, report: AuditReport, *, gbrain_bin: str = "gbrain") -> RouteResult:
    if scope == "retire":
        return RouteResult("diagnose-only", 0, "retire: no forwarding", degraded=True)
    # v2-T4: bundled-skill safety — never forward to gbrain or the shim when
    # the skill is part of a gbrain marketplace install. The bundled install
    # is read-only from skill-forge's perspective; proposed changes land in
    # proposed.md (caller's copy), never in the bundled SKILL.md. This
    # short-circuit runs AFTER the retire check and BEFORE any subprocess.
    if is_bundled(skill_dir):
        intended = gbrain_bin if scope == "improve" else "skill-creator"
        msg = (
            f"[bundled-skill-safety] refusing to forward to {intended}: "
            f"skill at {skill_dir} is bundled (write proposed.md only)"
        )
        return RouteResult("diagnose-only", 0, msg, degraded=True, reason="bundled-skill-safety")
    if shutil.which(gbrain_bin):
        cmd = [gbrain_bin, "skillopt", skill_dir.name, "--dry-run", "--bootstrap-reviewed"]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        return RouteResult("gbrain-skillopt", r.returncode, r.stdout.decode(errors="replace"))
    if scope == "create":
        # v2-T3 (RULING-9 v2): use sys.executable (the same interpreter that
        # is running the router) instead of bare "python", so venv-only hosts
        # work. The shim's argv contract now also accepts SKILL_DIR via env
        # (preferred for cwd-agnostic invocation) and falls back to argv[0]
        # for back-compat. See _legacy_init_skill.py for the consumer side.
        cmd = [sys.executable, str(Path(__file__).parent / "_legacy_init_skill.py"), skill_dir.name]
        # v2-T7 (RULING-9 v2 corollary): the router's value is authoritative.
        # Per Python dict-literal **-spread semantics the LAST occurrence of a
        # key wins; spreading os.environ FIRST then setting SKILL_DIR means our
        # computed value outranks any ambient SKILL_DIR. The opposite order
        # would let a stale parent SKILL_DIR override the router's value,
        # reintroducing v1's wrong-directory bug class. **os.environ is still
        # load-bearing on Windows (subprocess.run(env=...) REPLACES the child
        # environment wholesale; dropping the spread would strip
        # SystemRoot/COMSPEC/PATHEXT/TEMP and break subprocess creation), so it
        # cannot be removed — only the order changed.
        env = {**os.environ, "SKILL_DIR": str(skill_dir.resolve())}
        r = subprocess.run(cmd, capture_output=True, timeout=120, env=env)
        return RouteResult("skill-creator", r.returncode, r.stdout.decode(errors="replace"), degraded=True)
    msg = "gbrain not installed; install gbrain (https://github.com/garrytan/gbrain) to optimize this skill. Audit saved at " + str(skill_dir / "audit-report.md")
    return RouteResult("diagnose-only", 0, msg, degraded=True)
