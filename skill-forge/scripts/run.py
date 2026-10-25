"""skill-forge main entry: 6-phase pipeline + argparse CLI."""
from __future__ import annotations
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence
from scripts.audit import audit
from scripts.author import author_skill, load_spec
from scripts.bootstrap_benchmark import bootstrap as bootstrap_benchmark
from scripts._lib.baseline_log import race, write_baseline
from scripts._lib.bundle import is_bundled
from scripts._lib.sha import content_hash
from scripts.judge_triple import judge
from scripts._lib.token_cost import measure_skill
from scripts._lib.snapshot import (
    clear_snapshot,
    diff_bodies,
    read_snapshot,
    snapshot_skill,
)
from scripts._lib.llm_channel import (
    discover_rubric_script,
    http_channel_from_env,
    make_llm_call,
)
from scripts.router import DEFAULT_MAX_USD, DEFAULT_SPLIT, RouteResult, route

PHASES = ("audit", "scope", "bootstrap", "forward", "verify", "materialize")

# P0-1: the gbrain subprocess runs against an isolated brain by default so a
# skillopt run never touches the user's real ~/.gbrain (which may be locked
# by a live `gbrain serve`). Lives under the system temp dir per the
# host's temp convention. Override with --gbrain-home.
DEFAULT_GBRAIN_HOME = Path(tempfile.gettempdir()) / "skill-forge-gbrain-home"

# Per Perplexity's gotcha flywheel: when the audit returns a non-trivial
# root_cause, the audit-report.md should suggest 1-2 gotchas the author
# should add to the target skill's Red Flags / Anti-Patterns. Without
# this, the flywheel has no fuel — gotchas stay frozen at v0.2.0 instead
# of growing from observed failures.
#
# The mapping is deliberately small and curated. Each suggestion must be:
# (a) actionable — the author can copy it into Red Flags as a bullet
# (b) root-cause specific — it should help with THIS root_cause, not be
#     generic "always test your skill"
# (c) rooted in Perplexity or skill-forge's own principles, not invented
#
# `missing` (no SKILL.md → create scope) and `other` (FrontmatterError /
# no branch matched → audit-only scope) deliberately have no suggestions:
# the verdict is non-actionable at the gotcha level.
_SUGGESTED_GOTCHAS: dict[str, tuple[str, ...]] = {
    "prompt": (
        "Body under 60 chars gives the agent nothing to anchor on. "
        "Add an explicit Phases section and a Common Rationalizations table.",
        "Thin bodies are usually a sign the SKILL.md was authored from the "
        "audit output, not from the position statement. Re-author from the "
        "top — 'What this is' first, gotchas last.",
    ),
    "routing": (
        "Description does not start with 'Use when …' or 'Load when …'; "
        "the resolver's short-circuit fails and the skill is matched by "
        "similarity, not by routing.",
        "Add 3+ concrete trigger phrases to the `triggers:` list (5-7 is the "
        "sweet spot). The validator warns on < 3 and on descriptions > 50 words.",
    ),
    "contract": (
        "`scripts/*.py` contains the substring `does_not_exist` — an "
        "unresolvable import. The skill cannot run; the agent will throw "
        "before producing output.",
        "Audit bundled scripts for missing imports before shipping. Add an "
        "ImportError pattern to the skill's Anti-Patterns section so this "
        "fails loudly next time.",
    ),
    # 'missing' and 'other' deliberately omitted — non-actionable verdicts.
}


def _suggested_gotchas(root_cause: str) -> list[str]:
    """Return the suggested gotchas for `root_cause`, or [] if the verdict
    is non-actionable (missing / other). Pure helper, easy to unit-test."""
    return list(_SUGGESTED_GOTCHAS.get(root_cause, ()))


def _emit(phase: int, name: str, msg: str) -> None:
    print(f"[phase {phase}] {name}: {msg}", flush=True)


def _cost_section(skill_dir: Path) -> str:
    """Render the measured token cost of the target skill.

    This is the section that makes the cost axis matter. Perplexity's
    three tiers, each with its own budget and its own pain:

      index  ~100 tok  paid by EVERY session, EVERY user, always
      load   ~5,000 tok  paid on every trigger
      files  unlimited  paid only when the agent reads one

    A number in the report is what makes the problem visible. A rule
    without a number is a rule nobody applies.
    """
    cost = measure_skill(skill_dir)
    if cost.index_tokens == 0 and cost.load_tokens == 0:
        return ""
    lines = [
        "## Cost",
        "",
        "| tier | used | budget | status |",
        "|---|---|---|---|",
    ]
    for tier, used, budget, status in cost.as_report_rows():
        budget_s = f"~{budget}" if budget else "unlimited"
        lines.append(f"| {tier} | {used} tok | {budget_s} | {status} |")
    lines.append("")
    if cost.index_over_budget:
        lines.append(
            f"index tier is {cost.index_tokens - cost.index_budget} tokens over "
            f"budget — it is paid by every session whether or not this skill is "
            f"invoked, and it stacks across the whole installed portfolio."
        )
    if cost.load_over_budget:
        lines.append(
            f"load tier is {cost.load_tokens - cost.load_budget} tokens over "
            f"budget — paid on every trigger. Move the heavy detail into "
            f"references/ and state the read condition in the body."
        )
    if cost.files_breakdown:
        lines.append("")
        lines.append("Files tier (unlimited, paid only when read):")
        for rel, n in sorted(cost.files_breakdown.items(), key=lambda kv: -kv[1])[:12]:
            lines.append(f"- `{rel}` — {n} tok")
    lines.append("")
    return "\n".join(lines)


def _change_section(skill_dir: Path) -> str:
    """Render the before/after delta of SKILL.md.

    This is what the real baseline buys: the report can now say WHAT
    changed, not just whether a gate passed. With `baseline = candidate`
    (the pre-P0 placeholder) there was no before to compare against, so
    a run could report "accept" without anyone knowing what it accepted.
    """
    snap = read_snapshot(skill_dir)
    cur = skill_dir / "SKILL.md"
    if snap is None or not cur.is_file():
        return ""
    try:
        before = snap.read_text(encoding="utf-8")
        after = cur.read_text(encoding="utf-8")
    except OSError:
        return ""
    delta = diff_bodies(before, after)
    if not delta["changed"]:
        return ""
    lines = [
        "## Change",
        "",
        f"SKILL.md vs the pre-run snapshot: "
        f"**+{delta['added']} / -{delta['removed']}** lines.",
        "",
    ]
    if delta["lines"]:
        lines.append("```diff")
        lines.extend(delta["lines"])
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def _materialize(skill_dir: Path, verdict: bool, root_cause: str, *, bundled: bool = False, candidate: Path | None = None) -> Path:
    out = skill_dir / "audit-report.md"
    gotchas = _suggested_gotchas(root_cause)
    body = (
        f"# skill-forge audit\n\n"
        f"root_cause: {root_cause}\n"
        f"verdict: {'accept' if verdict else 'refuse'}\n"
    )
    if gotchas:
        # Markdown bullet list — each line is directly copy-pasteable into
        # the target skill's Red Flags / Anti-Patterns section.
        bullets = "\n".join(f"- {g}" for g in gotchas)
        body += f"\n## Suggested gotchas\n\n{bullets}\n"
    cost = _cost_section(skill_dir)
    if cost:
        body += f"\n{cost}\n"
    change = _change_section(skill_dir)
    if change:
        body += f"\n{change}\n"
    out.write_text(body, encoding="utf-8")
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

def _run_author(args, skill_dir: Path) -> int:
    """The WRITE lane: author a new skill from a spec.

    Reports the measured cost of what it just produced, so the author
    is held to the same standard as an audited skill.
    """
    try:
        spec = load_spec(args.spec)
    except (OSError, ValueError) as e:
        print(f"error: invalid spec {args.spec}: {e}", file=sys.stderr)
        return 2
    try:
        result = author_skill(spec, skill_dir)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    for w in result.warnings:
        print(f"[WARN] {w}", file=sys.stderr)
    c = result.cost
    _emit(0, "author", f"wrote {result.skill_md_path.name} "
                      f"index={c.index_tokens}tok load={c.load_tokens}tok "
                      f"files={c.files_tokens}tok")
    for rel in result.written:
        _emit(1, "write", rel)
    return 0


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
    # P0-1: forward-phase levers. gbrain skillopt's own defaults are wrong
    # for skill-forge's 15-row benchmark (split 4:1:5 refuses at D_sel < 5)
    # and the spend cap should be visible in the argv, not implicit.
    p.add_argument("--split", default=DEFAULT_SPLIT,
                   help=f"TRAIN:SEL:TEST split for gbrain skillopt (default {DEFAULT_SPLIT}; "
                        f"gbrain refuses when the selection set has < 5 rows).")
    p.add_argument("--max-usd", default=DEFAULT_MAX_USD,
                   help=f"Spend cap for the gbrain forward (default {DEFAULT_MAX_USD}; "
                        f"pass 'off' to disable).")
    p.add_argument("--gbrain-home", type=Path, default=None,
                   help="Isolated GBRAIN_HOME for the gbrain subprocess "
                        f"(default: {DEFAULT_GBRAIN_HOME}). Pass 'inherit' to use the parent's.")
    # P0-2: the rubric judge. The judge must be a DIFFERENT source from
    # whoever authored the candidate, so the model is named explicitly and
    # echoed in the Phase 4 marker. Omit --rubric-model to keep the
    # rubric skipped (RULING-1: absent rubric != failure).
    p.add_argument("--rubric-model", default=None,
                   help="Model that judges the candidate (e.g. minimax/MiniMax-M3). "
                        "Omit to skip the rubric entirely.")
    p.add_argument("--rubric-script", type=Path, default=None,
                   help="llm-call script that performs the judge call "
                        "(default: auto-discover the llm-call skill).")
    p.add_argument("--rubric-timeout", type=int, default=180,
                   help="Seconds the judge may take before it is treated as errored.")
    p.add_argument("--rubric-transport", choices=["auto", "http", "script"], default="auto",
                   help="How the judge is reached: 'http' uses the ambient "
                        "Anthropic-compatible endpoint, 'script' uses the llm-call "
                        "script, 'auto' prefers http and falls back to script.")
    # P0-1 follow-up: gbrain addresses the skill as `<skills-dir>/<name>/SKILL.md`.
    # The default is the skill's own parent directory, which contains
    # `<skill_dir.name>/SKILL.md`.
    p.add_argument("--skills-dir", type=Path, default=None,
                   help="Directory that contains the skill dir, passed to gbrain as "
                        "--skills-dir (default: the skill's parent directory).")
    # P1: the WRITE lane. --scope create with a spec authors a NEW skill
    # with skill-forge's own author, which applies the token rubric and
    # the progressive-disclosure structure at generation time. This is
    # the lane that replaces Anthropic's skill-creator for authoring.
    p.add_argument("--spec", type=Path, default=None,
                   help="Author spec (JSON) for --scope create: name, description, "
                        "triggers, intent, gotchas, references, assets, scripts.")
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
    # P1: the WRITE lane short-circuits the audit/judge pipeline. A new
    # skill has nothing to audit, and the author's own output IS the
    # deliverable. The rubric is applied at generation time, so the
    # result comes out inside the budgets rather than being reported
    # as over-budget afterwards.
    if args.scope == "create" and args.spec is not None:
        return _run_author(args, skill_dir)
    if not skill_dir.exists():
        print(f"error: {skill_dir} does not exist", file=sys.stderr)
        return 2
    bundled = is_bundled(skill_dir)  # v2-T4: computed once, reused by _materialize
    report = audit(skill_dir)
    # P0: the cost axis starts at Phase 0. The index tier is the one that
    # is paid by every session whether or not the skill is invoked, so
    # the number belongs in the first marker, not only in the report.
    _cost = measure_skill(skill_dir)
    # P0: capture the BEFORE state, before the forward phase can touch the
    # skill. This is the real baseline: the rubric compares the candidate
    # against this snapshot, not against itself (the pre-P0 placeholder
    # was `baseline = candidate`, so the judge compared the candidate to
    # its own reflection and no before/after was measurable).
    _snapshot = snapshot_skill(skill_dir)
    _emit(0, "audit", f"root_cause={report.root_cause} scope={report.recommend_scope} "
                      f"index={_cost.index_tokens}tok load={_cost.load_tokens}tok")
    if args.scope != report.recommend_scope and report.confidence >= 0.85 and report.root_cause != "missing":
        print(f"warning: requested scope '{args.scope}' differs from recommended '{report.recommend_scope}'", file=sys.stderr)
    _emit(1, "scope", f"user chose {args.scope}")
    # v2-T8: --held-out threads n_tasks through to the bootstrap generator;
    # bootstrap's own n_tasks=15 default is preserved when the flag is absent.
    n_tasks = args.held_out if args.held_out is not None else 15
    # v2-T8 M-3: an explicit --benchmark short-circuits the bootstrap call, so
    # n_tasks (and therefore --held-out) is silently discarded. Warn instead of
    # dropping the user's intent on the floor.
    if args.benchmark is not None and args.held_out is not None:
        print(
            f"[WARN] --held-out {args.held_out} ignored: "
            f"--benchmark <{args.benchmark}> takes precedence (no bootstrap run)",
            file=sys.stderr,
        )
    bench = args.benchmark or bootstrap_benchmark(skill_dir, report, n_tasks=n_tasks)
    _emit(2, "bootstrap", f"benchmark={bench}")
    # RULING-9: route()'s subprocess.run is unguarded (router.py ~L23/L27), so
    # TimeoutExpired / OSError / FileNotFoundError propagate. Wrap the call site and
    # degrade to diagnose-only rather than changing the 6-phase / rc contract.
    # P0-1: the forward now carries the Phase 2 benchmark, an explicit
    # split + spend cap, and an isolated GBRAIN_HOME. Without the benchmark
    # gbrain has nothing to optimize against (its CLI makes a benchmark
    # REQUIRED); without an explicit split its default 4:1:5 refuses on a
    # 15-row benchmark at D_sel < 5; without isolation the run writes into
    # the user's real ~/.gbrain.
    gbrain_home = args.gbrain_home if args.gbrain_home is not None else DEFAULT_GBRAIN_HOME
    skills_dir = args.skills_dir if args.skills_dir is not None else skill_dir.parent
    try:
        rresult = route(
            skill_dir, args.scope, report,
            benchmark=bench,
            split=args.split,
            max_usd=args.max_usd,
            gbrain_home=gbrain_home,
            skills_dir=skills_dir,
        )
    except (OSError, subprocess.SubprocessError) as e:
        rresult = RouteResult("diagnose-only", 2, str(e), degraded=True)
    _emit(3, "forward", f"target={rresult.forwarded_to} degraded={rresult.degraded} exit={rresult.exit_code} reason={rresult.reason or '—'}")
    candidate = skill_dir / "SKILL.md"
    # P0: a REAL baseline. The pre-run snapshot of SKILL.md, so the rubric
    # compares the candidate against what it was BEFORE this run. The old
    # `baseline = candidate` placeholder meant Phase 4 compared the
    # candidate with itself — no before/after was measurable, and
    # best.md had nothing to diff against. When no snapshot exists (no
    # SKILL.md, or a malformed one) we fall back to the candidate so the
    # pipeline still runs; the report then shows no Change section.
    baseline = _snapshot if (_snapshot and _snapshot.exists()) else candidate
    # v1 wires no rubric; RULING-8: rubric state is derived from llm_call at the call
    # site, never inferred from v.llm_score (0.0 both when skipped and when clamped).
    # P0-2: when --rubric-model is given, a real judge is wired in. The judge
    # is a different source from the candidate's author, so the model is named
    # in the Phase 4 marker. A judge that ERRORS is reported, not hidden, and
    # is treated as skipped rather than as a "no".
    llm_call = None
    rubric_errors: list[str] = []
    if args.rubric_model:
        if args.rubric_transport in ("auto", "http"):
            llm_call = http_channel_from_env(args.rubric_model)
        if llm_call is None and args.rubric_transport in ("auto", "script"):
            rubric_script = args.rubric_script or discover_rubric_script()
            llm_call = make_llm_call(
                model=args.rubric_model, script=rubric_script, timeout=args.rubric_timeout,
            )
        if llm_call is None:
            print(
                f"[WARN] rubric judge requested ({args.rubric_model}) but no judge "
                f"channel is available; the rubric will be skipped",
                file=sys.stderr,
            )
    v = judge(candidate, baseline, report, llm_call=llm_call,
              spot_input=None if args.spot_check == 0 else {"verdict": True},
              on_rubric_error=rubric_errors.append)
    for err in rubric_errors:
        print(
            f"[WARN] rubric judge errored ({err}); treating the rubric as "
            f"skipped, not failed",
            file=sys.stderr,
        )
    if llm_call is None or rubric_errors:
        rubric = "rubric-skipped"
    else:
        rubric = f"llm={v.llm_score:.2f}@{args.rubric_model}"
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
    # The snapshot has served its purpose: it was the before state for
    # this run's comparison and the report's Change section. Leaving it
    # behind would make the NEXT run's snapshot a no-op (snapshot_skill
    # refuses to overwrite), so the next run would compare against a
    # two-runs-old state.
    clear_snapshot(skill_dir)
    return 0 if v.accept else 2

if __name__ == "__main__":
    raise SystemExit(main())
