---
name: skill-forge
description: >-
  Use when a skill is not producing the quality you want, when you want to
  bootstrap a benchmark for a new skill, when an existing skill needs
  measurable improvement against a frozen baseline, or when retiring a
  skill that has outlived its purpose. Triggers: "improve this skill",
  "skill won't trigger", "audit skill quality", "fix skill underperformance",
  "make a skill benchmark", "retire old skill", "skill produces shallow output".
mutating: true
brain_first: exempt
---

# skill-forge

**Violating the letter of these rules is violating the spirit of these rules.**

## What this is

A meta-skill that turns "this skill could be better" into a measured,
verifiable improvement — or an honest decision to retire it. It does not
edit skills directly; it routes work to `skill-creator` (create/edit) and
`gbrain:skill-optimizer` (SkillOpt-paper-driven optimization), and scores
the result with a three-judge gate before letting any change ship.

## When NOT to use

- You have not identified a specific failing skill and an observable symptom.
- "Improve" means you want to change taste or style, not quality.
- The skill already passes a deterministic trace + LLM rubric + spot check.

## Core Process

| Phase | Verb | What happens |
|---|---|---|
| 0 | audit | Static scan the target SKILL.md → root cause: prompt / routing / contract / env |
| 1 | scope | You pick: create / improve / audit / retire |
| 2 | bootstrap | Generate ~15 benchmark tasks with rule + rubric judges |
| 3 | run | `gbrain skillopt X --bootstrap-reviewed` (or skill-creator for create) |
| 4 | verify | Deterministic trace + LLM rubric + spot check; any regression refuses |
| 5 | materialize | best.md / proposed.md / run-report.md |

Default behavior: `--dry-run`. Bundled gbrain skills go to `proposed.md` only.

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

- [ ] `wc -w SKILL.md` ≤ 500 (this file is the gate)
- [ ] Each phase prints its verb on stdout
- [ ] Bundled-skill runs emit `proposed.md`, not `SKILL.md`
- [ ] Triple-judge summary lists all three judges with scores
