"""skill-forge main entry: 6-phase pipeline + argparse CLI."""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence
from scripts.audit import audit
from scripts.bootstrap_benchmark import bootstrap as bootstrap_benchmark
from scripts._lib.baseline_log import race, write_baseline
from scripts._lib.bundle import is_bundled
from scripts._lib.sha import content_hash
from scripts.judge_triple import judge
from scripts.router import RouteResult, route

PHASES = ("audit", "scope", "bootstrap", "forward", "verify", "materialize")

def _emit(phase: int, name: str, msg: str) -> None:
    print(f"[phase {phase}] {name}: {msg}", flush=True)

def _materialize(skill_dir: Path, verdict: bool, root_cause: str, *, bundled: bool = False, candidate: Path | None = None) -> Path:
    out = skill_dir / "audit-report.md"
    out.write_text(
        f"# skill-forge audit\n\nroot_cause: {root_cause}\nverdict: {'accept' if verdict else 'refuse'}\n",
        encoding="utf-8",
    )
    if verdict and not bundled and candidate is not None and candidate.exists():
        # v2-T5: for a non-bundled skill on accept, the candidate SKILL.md
        # content is written to best.md verbatim. SKILL.md is NOT overwritten
        # — the user compares and merges manually. best.md is the "desired
        # overwrite" target that replaces v1's destructive in-place write.
        best = skill_dir / "best.md"
        best.write_text(candidate.read_text(encoding="utf-8"), encoding="utf-8")
        return best  # newest written path, for the phase-5 marker
    if bundled and verdict:
        # v2-T4: bundled skills are read-only from skill-forge's perspective.
        # Write the proposed SKILL.md content to proposed.md (caller-side, for
        # human review before merge); never write to the bundled SKILL.md.
        proposed = skill_dir / "proposed.md"
        # The proposed content is the verdict + root_cause note, because
        # skill-forge has not yet authored a replacement SKILL.md (the
        # audit/bootstrap phases produce diagnostics, not new content). The
        # real "propose" content is authored in a later phase.
        proposed.write_text(
            f"# Proposed changes for bundled skill at {skill_dir}\n\n"
            f"audit root_cause: {root_cause}\nverdict: {'accept' if verdict else 'refuse'}\n\n"
            f"(See audit-report.md for the full audit summary.)\n",
            encoding="utf-8",
        )
        return proposed  # newest written path, for the phase-5 marker
    return out

def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="skill-forge")
    p.add_argument("--skill", required=True, type=Path)
    p.add_argument("--scope", required=True, choices=["create", "improve", "audit-only", "retire"])
    p.add_argument("--benchmark", type=Path, default=None)
    p.add_argument("--spot-check", type=int, default=0)
    # v2-T8: held-out task count is threaded into bootstrap_benchmark as
    # n_tasks. gbrain hard-refuses held-out <5 internally, so the CLI surfaces
    # the constraint up front instead of generating an unusable benchmark.
    p.add_argument("--held-out", type=int, default=None,
                   help="Number of held-out tasks (refuses if <5).")
    args = p.parse_args(argv)
    # v2-T8: early guard, before the skill_dir existence check and before any
    # phase runs — the pipeline is never entered for N<5.
    if args.held_out is not None and args.held_out < 5:
        print(
            f"[FATAL] --held-out must be >= 5 (gbrain hard-refuses held-out <5 "
            f"internally); got {args.held_out}",
            file=sys.stderr,
        )
        return 2  # refuse, per v1's refuse code; race stays 3 (Default Decision #3)
    skill_dir: Path = args.skill
    if not skill_dir.exists():
        print(f"error: {skill_dir} does not exist", file=sys.stderr)
        return 2
    bundled = is_bundled(skill_dir)  # v2-T4: computed once, reused by _materialize
    report = audit(skill_dir)
    _emit(0, "audit", f"root_cause={report.root_cause} scope={report.recommend_scope}")
    if args.scope != report.recommend_scope and report.confidence >= 0.85 and report.root_cause != "missing":
        print(f"warning: requested scope '{args.scope}' differs from recommended '{report.recommend_scope}'", file=sys.stderr)
    _emit(1, "scope", f"user chose {args.scope}")
    # v2-T8: --held-out threads n_tasks through to the bootstrap generator;
    # bootstrap's own n_tasks=15 default is preserved when the flag is absent.
    n_tasks = args.held_out if args.held_out is not None else 15
    bench = args.benchmark or bootstrap_benchmark(skill_dir, report, n_tasks=n_tasks)
    _emit(2, "bootstrap", f"benchmark={bench}")
    # RULING-9: route()'s subprocess.run is unguarded (router.py ~L23/L27), so
    # TimeoutExpired / OSError / FileNotFoundError propagate. Wrap the call site and
    # degrade to diagnose-only rather than changing the 6-phase / rc contract.
    try:
        rresult = route(skill_dir, args.scope, report)
    except (OSError, subprocess.SubprocessError) as e:
        rresult = RouteResult("diagnose-only", 2, str(e), degraded=True)
    _emit(3, "forward", f"target={rresult.forwarded_to} degraded={rresult.degraded} exit={rresult.exit_code} reason={rresult.reason or '—'}")
    candidate = skill_dir / "SKILL.md"
    baseline = candidate  # RULING-8 part 2 (v2-T2 modified): baseline is consumed by the rubric prompt (see judge_triple.py); T7 v1 / v2 pass candidate as both. Phase 5 may also re-pin SHA via the race check.
    # v1 wires no rubric; RULING-8: rubric state is derived from llm_call at the call
    # site, never inferred from v.llm_score (0.0 both when skipped and when clamped).
    llm_call = None
    v = judge(candidate, baseline, report, llm_call=llm_call, spot_input=None if args.spot_check == 0 else {"verdict": True})
    rubric = "rubric-skipped" if llm_call is None else f"llm={v.llm_score:.2f}"
    _emit(4, "verify", f"det={v.deterministic_pass} {rubric} spot={v.spot_accepted} accept={v.accept}")
    # v2-T5: SHA-baseline race check before materialize. If SKILL.md drifted
    # since the last successful run, a bundled skill is refused outright
    # (exit 3, EEXIT_RACE — distinct from the refuse exit 2) and a
    # non-bundled skill warns and proceeds to best.md.
    if v.accept:
        current_sha = content_hash(candidate.read_text(encoding="utf-8")) if candidate.exists() else ""
        if race(skill_dir, current_sha):
            if bundled:
                print(
                    "[FATAL] skill_dir SKILL.md has drifted since the last skill-forge "
                    "run (race condition); refusing to overwrite the bundled install",
                    file=sys.stderr,
                )
                return 3  # EEXIT_RACE per Default Decision #3
            print(
                "[WARN] skill_dir SKILL.md has drifted since the last skill-forge "
                "run; writing best.md to capture the new state, not overwriting",
                file=sys.stderr,
            )
    materialize_path = _materialize(skill_dir, v.accept, report.root_cause, bundled=bundled, candidate=candidate)
    _emit(5, "materialize", f"wrote {materialize_path.name}")
    # v2-T5: pin the baseline on success only. A refuse (rc=2) must not pin a
    # SHA — otherwise a refuse would lock the skill out of future improvement.
    if v.accept:
        write_baseline(skill_dir, current_sha if candidate.exists() else "")
    return 0 if v.accept else 2

if __name__ == "__main__":
    raise SystemExit(main())
