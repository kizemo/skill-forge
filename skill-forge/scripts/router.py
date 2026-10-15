"""Phase 3: forward to gbrain or skill-creator, or degrade gracefully."""
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from scripts.audit import AuditReport

Target = Literal["gbrain-skillopt", "skill-creator", "diagnose-only"]

@dataclass
class RouteResult:
    forwarded_to: Target
    exit_code: int
    stdout: str
    degraded: bool = False

def route(skill_dir: Path, scope: str, report: AuditReport, *, gbrain_bin: str = "gbrain") -> RouteResult:
    if scope == "retire":
        return RouteResult("diagnose-only", 0, "retire: no forwarding", degraded=True)
    if shutil.which(gbrain_bin):
        cmd = [gbrain_bin, "skillopt", skill_dir.name, "--dry-run", "--bootstrap-reviewed"]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        return RouteResult("gbrain-skillopt", r.returncode, r.stdout.decode(errors="replace"))
    if scope == "create":
        cmd = ["python", str(Path(__file__).parent / "_legacy_init_skill.py"), skill_dir.name]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        return RouteResult("skill-creator", r.returncode, r.stdout.decode(errors="replace"), degraded=True)
    msg = "gbrain not installed; install gbrain (https://github.com/garrytan/gbrain) to optimize this skill. Audit saved at " + str(skill_dir / "audit-report.md")
    return RouteResult("diagnose-only", 0, msg, degraded=True)
