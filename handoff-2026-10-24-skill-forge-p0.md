# Handoff: skill-forge P0-1 / P0-2 (router + real AI review)

**Date:** 2026-10-24
**From session:** P0 pass (post-`24a92c0`)
**To session:** fresh
**Trigger:** user reported three router defects from another project, then asked for a real, independently-sourced AI review in the optimization pipeline.

---

## 1. State at handoff

| Field | Value |
|---|---|
| **Repository** | `F:\soft\00selfmade\skill-optimizer` (Windows) |
| **Branch** | `main` |
| **Local HEAD** | `24a92c0` (pushed; local == origin/main) |
| **Tag** | `v0.2.0-rc1` (preserved; do not move) |
| **Tests** | **147 / 147 pass** |
| **Deployed at** | `C:\Users\Duanyi\.claude\skills\skill-forge\` (junction → F: source). Also `E:\Users\Duanyi\.claude\skills\skill-forge` and the gbrain marketplace path (→ user-scope junction). Content is byte-identical to the repo. |

**Verify on session start:**
```bash
cd F:/soft/00selfmade/skill-optimizer && git log --oneline -3 && git status --short
cd skill-forge && python -m pytest -q    # expect: 147 passed
```

---

## 2. What was done

### P0-1 — router forwarded the wrong things (commit `7bdbf85`)

`route()` built `[gbrain, "skillopt", name, "--dry-run", "--bootstrap-reviewed"]`.
Three defects, all verified against `gbrain skillopt --help` (v0.60.287.0) plus live probes:

| Defect | Evidence | Fix |
|---|---|---|
| No `--benchmark` | gbrain CLI: "Required (one of): `--benchmark` / `--bootstrap-from-skill` / `--bootstrap-from-routing`" — the forward was guaranteed to fail | `route(benchmark=...)`; run.py passes Phase 2's path |
| No `--split` / `--max-usd` | gbrain default split `4:1:5` "refuses if D_sel < 5"; 15 rows → D_sel < 5 → refuse. gbrain's own 15-task recipe is `--split 1:1:1` | `DEFAULT_SPLIT="1:1:1"`, `DEFAULT_MAX_USD="5.00"`, both explicit + overridable |
| No `GBRAIN_HOME` isolation | Child inherited `~/.gbrain`, which a live `gbrain serve` holds (PGLite lock) | Isolated `GBRAIN_HOME` (default `<temp>/skill-forge-gbrain-home`), auto-init once via `gbrain init --pglite --no-embedding` (~14s measured) |

New CLI: `--split`, `--max-usd`, `--gbrain-home`.
**os.environ is spread BEFORE the router's GBRAIN_HOME** so the router's value wins (same
last-wins rule as SKILL_DIR in v2-T7), and the spread stays load-bearing because
`subprocess.run(env=...)` replaces the child environment wholesale.

### P0-2 — real AI review (commits `eab33f7`, `24a92c0`)

Two defects:

1. `judge_triple.py:59` built the prompt as `f"score candidate={candidate} baseline={baseline}"` —
   **paths only**. v2-T2 (RULING-8 v2 item 2) did that deliberately, on the theory that the
   llm_call would read the files itself. That holds only for an in-process judge; a remote
   model sees two paths and no skill. **P0-2 supersedes it**: the prompt now carries the
   candidate and baseline **bodies** (each truncated to 12k chars, to stay inside the
   Windows command-line limit).
2. `run.py` hard-wired `llm_call = None`, so the rubric gate never ran.

New: `scripts/_lib/llm_channel.py` (`make_llm_call` over the llm-call script,
`make_http_llm_call` over an Anthropic-compatible endpoint, `parse_score`,
`discover_rubric_script`). New CLI: `--rubric-model`, `--rubric-script`,
`--rubric-timeout`, `--rubric-transport {auto,http,script}`.

**Judge must be independent of the author.** The model is named explicitly and echoed in
the Phase 4 marker (`llm=0.68@MiniMax-M2.7[1m]`) — the author ran on M3, the judge on
M2.7: different weights, separate process, zero shared context.

**Judge errors ≠ judge says "no".** A configured-but-broken judge raises `RubricError`,
is reported to stderr, and the rubric is treated as **skipped** — never converted to a
0.0 score (0.0 reads as "the judge said no"). `judge()` takes an optional
`on_rubric_error` sink; without one the error propagates rather than vanishing.

### The length-bias finding (commit `24a92c0`)

The first rubric template asked *"does the body have substance … rather than filler?"*
and the judge read that as **"longer = better"**. Run against skill-forge's own
optimization:

| Direction | Candidate | Before | After |
|---|---|---|---|
| A | optimized (797 words) | 0.48 | **0.68** |
| B | pre-trim (903 words) | 0.82 | **0.57** |
| | net | **-0.34** (backwards) | **+0.11** (correct) |

Position bias ruled out (the "first body" scored 0.48 and 0.82 in the two directions).
A direct probe of the same model ("is the shorter candidate better?") answered **1.0** —
so the model was right and the **prompt** was wrong. The template now states the rule
explicitly: judge PRINCIPLES not LENGTH; length alone is NEVER a reason to score
higher. A gate that systematically prefers the pre-optimization version is worse than
no gate.

---

## 3. Open Concerns

### C-1 · ~~gbrain resolves the skill by NAME, not by path~~ — **RESOLVED 2026-10-24, do not re-open as "unsolvable"**

This Concern was **wrong**, and it was wrong because the discovery was incomplete: an
earlier grep of `gbrain skillopt --help` for path-like flags missed `--skills-dir`.
`--skills-dir <path>` is a **real, working** gbrain flag — the full pipeline runs with
it (models banner, cost estimate `$3.01 (cap: $5.00)`, "Dry run: no model calls made").

The only problem was **discoverability**, which is now reported upstream in
`skill-forge/docs/GBRAIN_UPSTREAM_FEEDBACK_2026-10-24.md`:
- `--skills-dir` appears **0 times** in `gbrain skillopt --help`
- the `NoSkill` error ("Cannot find SKILL.md for 'x' at <root>/skills/x/SKILL.md")
  points only at `gbrain skillify scaffold x` and never mentions `--skills-dir`,
  while the sibling error ("cannot find skills directory") *does*
- `GBRAIN_SKILLS_DIR` is honored but also undocumented

**Fix landed here (commit `see git log`):** `route()` gained a `skills_dir` parameter and
passes `--skills-dir`; `run.py` defaults it to `skill_dir.parent` (the directory that
contains `<skill_dir.name>/SKILL.md`) and exposes a `--skills-dir` override.

**End-to-end proof** (real gbrain, isolated brain, `improve` scope):

```
[phase 0] audit: root_cause=prompt scope=improve
[phase 1] scope: user chose improve
[phase 2] bootstrap: benchmark=C:\Temp\sf-e2e\skills\probe\skillopt-benchmark.jsonl
[phase 3] forward: target=gbrain-skillopt degraded=False exit=0   <-- was exit=2 (NoSkill)
[phase 4] verify: det=True rubric-skipped spot=None accept=True
[phase 5] materialize: wrote best.md
```

The other project's `gbrain_forward.py` was never needed — it is still not on this
machine (searched `F:/soft` full, `C:/Users/Duanyi` full depth, `E:/` depth 5,
`~/.claude/plugins`). The flag was enough.

### C-2 · Phase 3 still passes `--dry-run`

gbrain defines `--dry-run` as "Models plan, strict verdict + cost estimate, **no LLM
calls**" — so the forward phase never actually optimizes. This is v1-locked pipeline
semantics; it was deliberately not changed.

### C-3 · the rubric only scores the SKILL.md body

It cannot see the code-layer / structure-layer gaps (the 5 new validator checks, the
foundry split, `references/`, the suggested-gotchas section). That is why the judge
scored the improvement at **+0.11** while my own judgment was "clear net win" — a
disagreement recorded honestly in the P0-2 report. The judge may be right for what it
can see; extending the rubric's criteria is a separate decision.

### C-4 · the llm-call script channel is 401

Its MiniMax token is refreshed only by the MiniMax app and expired 2026-09-28.
**Open MiniMax Code once and it refreshes**; the script channel code is already in
place. The HTTP channel works today and is what the live review used.

---

## 4. Conventions (carry verbatim)

- TDD is mandatory: RED test → implement → GREEN → full suite. Every new test in this
  pass was watched fail first.
- One commit per concern; never amend; `<type>(<scope>): <subject>`, ≤ 72 chars.
- `python -m pytest -q` from `skill-forge/` must show ≥ 147 passed.
- Push after every commit. The local network drops TLS intermittently — **retry**.
- `docs/DEPLOYMENT.md` § 6 holds a verbatim snapshot of `SKILL.md`; regenerate it
  whenever `SKILL.md` changes (the doc says so itself).

## 5. Reading order

1. This handoff.
2. `skill-forge/docs/DEPLOYMENT.md` — deployment contract + MiniMax Code section.
3. `skill-forge/docs/PRINCIPLES.md` — the rules skill-forge enforces.
4. `skill-forge/docs/foundry-overview.md` then `foundry-details.md`.
5. `skill-forge/scripts/router.py`, `scripts/_lib/llm_channel.py`, `scripts/judge_triple.py`.
6. `handoff-2026-10-15-post-audit.md` — the 7-gap audit pass (already closed).
