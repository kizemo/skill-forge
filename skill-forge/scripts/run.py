"""skill-forge main entry: 6-phase pipeline + argparse CLI."""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence
from scripts.audit import audit
from scripts.bootstrap_benchmark import bootstrap as bootstrap_benchmark
from scripts.judge_triple import judge
from scripts.router import RouteResult, route

PHASES = ("audit", "scope", "bootstrap", "forward", "verify", "materialize")

def _emit(phase: int, name: str, msg: str) -> None:
    print(f"[phase {phase}] {name}: {msg}", flush=True)

def _materialize(skill_dir: Path, verdict: bool, root_cause: str) -> Path:
    out = skill_dir / "audit-report.md"
    out.write_text(
        f"# skill-forge audit\n\nroot_cause: {root_cause}\nverdict: {'accept' if verdict else 'refuse'}\n",
        encoding="utf-8",
    )
    return out

def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="skill-forge")
    p.add_argument("--skill", required=True, type=Path)
    p.add_argument("--scope", required=True, choices=["create", "improve", "audit-only", "retire"])
    p.add_argument("--benchmark", type=Path, default=None)
    p.add_argument("--spot-check", type=int, default=0)
    args = p.parse_args(argv)
    skill_dir: Path = args.skill
    if not skill_dir.exists():
        print(f"error: {skill_dir} does not exist", file=sys.stderr)
        return 2
    report = audit(skill_dir)
    _emit(0, "audit", f"root_cause={report.root_cause} scope={report.recommend_scope}")
    if args.scope != report.recommend_scope and report.confidence >= 0.85 and report.root_cause != "missing":
        print(f"warning: requested scope '{args.scope}' differs from recommended '{report.recommend_scope}'", file=sys.stderr)
    _emit(1, "scope", f"user chose {args.scope}")
    bench = args.benchmark or bootstrap_benchmark(skill_dir, report)
    _emit(2, "bootstrap", f"benchmark={bench}")
    # RULING-9: route()'s subprocess.run is unguarded (router.py ~L23/L27), so
    # TimeoutExpired / OSError / FileNotFoundError propagate. Wrap the call site and
    # degrade to diagnose-only rather than changing the 6-phase / rc contract.
    try:
        rresult = route(skill_dir, args.scope, report)
    except (OSError, subprocess.SubprocessError) as e:
        rresult = RouteResult("diagnose-only", 2, str(e), degraded=True)
    _emit(3, "forward", f"target={rresult.forwarded_to} degraded={rresult.degraded} exit={rresult.exit_code}")
    candidate = skill_dir / "SKILL.md"
    baseline = candidate  # RULING-8 part 2: baseline is reserved by T5's signature; T7 v1 passes candidate as both
    # v1 wires no rubric; RULING-8: rubric state is derived from llm_call at the call
    # site, never inferred from v.llm_score (0.0 both when skipped and when clamped).
    llm_call = None
    v = judge(candidate, baseline, report, llm_call=llm_call, spot_input=None if args.spot_check == 0 else {"verdict": True})
    rubric = "rubric-skipped" if llm_call is None else f"llm={v.llm_score:.2f}"
    _emit(4, "verify", f"det={v.deterministic_pass} {rubric} spot={v.spot_accepted} accept={v.accept}")
    materialize_path = _materialize(skill_dir, v.accept, report.root_cause)
    _emit(5, "materialize", f"wrote {materialize_path.name}")
    return 0 if v.accept else 2

if __name__ == "__main__":
    raise SystemExit(main())
