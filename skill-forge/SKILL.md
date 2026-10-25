---
name: skill-forge
version: 0.2.0
description: >-
  Use when a skill is not producing the quality you want, when you want to
  bootstrap a benchmark for a new skill, when an existing skill needs
  measurable improvement against a frozen baseline, or when retiring a
  skill that has outlived its purpose.
triggers:
  - "improve this skill"
  - "skill won't trigger"
  - "audit skill quality"
  - "fix skill underperformance"
  - "make a skill benchmark"
  - "retire old skill"
  - "skill produces shallow output"
tools:
  - bash
  - read
  - write
  - edit
  - grep
  - glob
mutating: true
brain_first: exempt
when_to_use: >-
  Use when the user asks: "improve this skill", "skill won't trigger",
  "audit skill quality", "fix skill underperformance", "make a skill benchmark",
  "retire old skill", or "skill produces shallow output".
---

# skill-forge

**Violating the letter of these rules is violating the spirit of these rules.**

## What this is

A meta-skill that turns "this skill could be better" into a measured,
verifiable improvement — or an honest decision to retire it. Routes work
to `skill-creator` / `gbrain:skill-optimizer`; uses a three-judge gate
before any change ships.

## When NOT to use

- You have not identified a specific failing skill and an observable symptom.
- "Improve" means you want to change taste or style, not quality.
- The skill already passes a deterministic trace + LLM rubric + spot check.

## Core Process

| Phase | Verb | What happens |
|---|---|---|
| 0 | audit | Static scan the target SKILL.md → root cause: prompt / routing / contract / missing / other; prints the measured index/load token cost |
| 1 | scope | You pick: create / improve / audit-only / retire |
| 2 | bootstrap | Generate 15 benchmark rows by default (RULING-7) — override with `--held-out N`; refuses if `N < 5` — plus sentinel |
| 3 | forward | `gbrain skillopt X --benchmark … --split 1:1:1 --max-usd 5.00` in an isolated `GBRAIN_HOME` |
| 4 | verify | Deterministic trace + LLM rubric + spot check against a REAL baseline (the pre-run snapshot); absent rubric ≠ failure (RULING-1); any regression refuses |
| 5 | materialize | `audit-report.md` (always, with a `## Cost` section and a `## Change` diff) + `best.md` (non-bundled accept) or `proposed.md` (bundled accept); bundled `SKILL.md` is never overwritten |

**Authoring** is a separate lane: `--scope create --spec <file.json>` generates a
new skill that is already inside the token budget, with its read-conditions table
and gotchas in place — the rubric applied at generation time, not reported afterwards.

Bundled skills (one registered in `~/.gbrain/install.json`) get `proposed.md` only; the bundled `SKILL.md` is never touched.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Audit passed, must be ready to optimize" | Audit names root cause; optimizer still needs benchmark + judges. |
| "Rule judges are cheap, skip the LLM rubric" | Model can game rule judges by emitting the literal keywords. |
| "Triple judge is overkill, two is enough" | Three judges cover three failure modes: shape (deterministic), intent (rubric), acceptance (spot). Drop one, lose one. |
| "Skip Phase 5 to ship faster" | Materialize is what makes the run auditable. No materialize, no run. |

## Red Flags

- Phase 0 says "no benchmark" but Phase 1 chose improve.
- Deterministic trace 100% pass, LLM rubric 0% pass.
- best.md older than SKILL.md at end of Phase 5.
- gbrain missing → still tried to call `gbrain skillopt`.

## Verification

- [ ] `wc -w SKILL.md` ≤ 1000 (this file is the gate — heavy reference lives in `docs/SKILL_REFERENCE.md`, not here)
- [ ] Each phase prints its verb on stdout
- [ ] Bundled-skill runs emit `proposed.md`, not `SKILL.md`
- [ ] Triple-judge summary lists all three judges with scores
- [ ] `validate_skill_frontmatter()` returns `[]` (no principle violations in this SKILL.md) — see PRINCIPLES.md § 1
- [ ] `audit-report.md` shows a `## Cost` section — index ≤ ~100 tok, load ≤ ~5,000 tok
- [ ] `audit-report.md` shows a `## Change` diff when the forward phase edited the skill

The v0 gate was 500 words; the v2 frontmatter layout lifts the natural size to 800-1000. Below 800 the SKILL.md is probably missing reference material; above 1000 it duplicates `docs/SKILL_REFERENCE.md`.

## v2 specifics (post v0.2.0)

- **Exit codes** — `0` accept · `2` refuse · `3` race (a bundled skill's `SKILL.md` SHA drifted between audit and materialize). Distinct codes for distinct failure modes so CI can route them differently.
- **Race check** — `.skill-forge-baseline.json` records the `SKILL.md` SHA from the last successful run. A drift on a bundled install refuses with exit `3`; a non-bundled drift warns and proceeds. `SKILL.md` is untouched either way.
- **Bundled-skill safety** — `is_bundled(skill_dir)` reads `~/.gbrain/install.json` and short-circuits the route phase for marketplace installs. **Fails open** if `install.json` is missing — copy the skill to a scratch dir before iterating.
- **`--held-out N`** — overrides the default 15-row benchmark; refuses with exit `2` when `N < 5` (gbrain hard-refuses <5 internally).
- **Triple-judge details** — `description` must be a YAML block scalar (RULING-5); YAML-list `description` refuses instead of raising; `baseline` is consumed in the rubric prompt so a real LLM call can compare candidate vs. baseline; rubric-skipped is invisible in `verdict.llm_score` — branch on `llm_call is None` at the call site, never on the verdict (RULING-8).
- **Skip optional deps gracefully** — without `pyyaml` the frontmatter loader raises; without `gbrain` the pipeline degrades to `diagnose-only.
