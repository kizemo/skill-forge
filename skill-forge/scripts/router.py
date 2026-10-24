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

# P0-1: gbrain skillopt's default split is "4:1:5" and it refuses when
# D_sel < 5. On skill-forge's default 15-row benchmark that yields
# D_sel < 5, so the run refuses before doing any work. gbrain's own
# documented 15-task recipe is "--split 1:1:1" (5 train / 5 sel / 5
# test) — D_sel = 5, exactly at the gate.
DEFAULT_SPLIT = "1:1:1"

# P0-1: gbrain's own spend cap defaults to 5.00. skill-forge passes it
# explicitly so the budget is visible in the argv (and therefore in the
# phase marker) instead of being an invisible default.
DEFAULT_MAX_USD = "5.00"


@dataclass
class RouteResult:
    forwarded_to: Target
    exit_code: int
    stdout: str
    degraded: bool = False
    # v2-T4: machine-readable degradation cause. Backwards-compatible
    # widening — existing positional/keyword construction is unaffected.
    reason: str | None = None


def _ensure_brain(gbrain_bin: str, home: Path, env: dict[str, str], timeout: int = 180) -> bool:
    """Ensure the isolated GBRAIN_HOME has a usable brain.

    gbrain refuses with `Error [no_brain]: No brain configured. Run: gbrain
    init` when the home it points at has no brain. An isolated home starts
    empty, so the router bootstraps it once with `gbrain init --pglite
    --no-embedding` (~14s on this host). A warm home is left alone.

    Returns True when the home carries a brain config afterwards.
    """
    config = home / ".gbrain" / "config.json"
    if config.exists():
        return True
    try:
        home.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [gbrain_bin, "init", "--pglite", "--no-embedding"],
            capture_output=True, timeout=timeout, env=env,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return config.exists()


def route(skill_dir: Path, scope: str, report: AuditReport, *, gbrain_bin: str = "gbrain",
          benchmark: Path | None = None,
          split: str | None = DEFAULT_SPLIT,
          max_usd: str | None = DEFAULT_MAX_USD,
          gbrain_home: Path | None = None) -> RouteResult:
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
        # P0-1 defect 1: Phase 2 generated a 15-row benchmark but gbrain
        # never received it. gbrain's CLI makes a benchmark REQUIRED
        # ("Required (one of): --benchmark <path> | --bootstrap-from-skill
        # | --bootstrap-from-routing"), so the forward was guaranteed to
        # fail on a missing benchmark.
        if benchmark is not None:
            cmd += ["--benchmark", str(benchmark)]
        # P0-1 defect 2: explicit split (gbrain's default 4:1:5 refuses at
        # D_sel < 5 on a 15-row benchmark) and explicit spend cap.
        if split:
            cmd += ["--split", split]
        if max_usd:
            cmd += ["--max-usd", str(max_usd)]
        env: dict[str, str] | None = None
        if gbrain_home is not None:
            # P0-1 defect 3: isolate the child's brain from the user's real
            # ~/.gbrain (which may be locked by a live `gbrain serve`).
            # **os.environ is spread FIRST so the router's GBRAIN_HOME wins
            # over any ambient value (same last-wins rule as SKILL_DIR in
            # v2-T7), and the spread itself stays load-bearing because
            # subprocess.run(env=...) REPLACES the child environment.
            env = {**os.environ, "GBRAIN_HOME": str(gbrain_home)}
            _ensure_brain(gbrain_bin, gbrain_home, env)
        r = subprocess.run(cmd, capture_output=True, timeout=120, env=env)
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
