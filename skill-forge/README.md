# skill-forge

> A six-phase meta-skill for auditing, creating, improving, and retiring other skills — built on the [Perplexity skill-writing principles](#-good-skill-standards) and dogfooding every one of them.

<div align="right">

[🇺🇸 English](#en) · [🇨🇳 中文](#zh)

</div>

---

<a id="en"></a>

## 🇺🇸 English

### What it is

`skill-forge` is a CLI tool that turns "this skill isn't working" into a reproducible pipeline:

1. **Audit** — classifies the failure as `prompt` / `routing` / `contract` / `missing` / `other` (RULING-6 order).
2. **Scope** — user picks `create` / `improve` / `audit-only` / `retire`.
3. **Bootstrap** — generates a 15-row benchmark template (or `--held-out N`, refuses `N<5`).
4. **Forward** — calls `gbrain skillopt` or `skill-creator/init_skill.py`; degrades gracefully on failure.
5. **Verify** — deterministic trace + LLM rubric + optional spot-check; absent rubric ≠ failure (RULING-1).
6. **Materialize** — writes `audit-report.md` (always) + `best.md` (non-bundled accept) or `proposed.md` (bundled accept); never overwrites the target `SKILL.md`. Emits **Suggested gotchas** when the verdict is non-trivial.

It is the *pipeline around* skill authoring, not the authoring itself. The author still writes the body; skill-forge audits, judges, races, and materializes.

### ✨ Good skill standards

These are the eight principles distilled from the 2026-10-15 Perplexity audit
(`docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md`) and codified in
`docs/PRINCIPLES.md`. They are the rubric a good skill is judged against.
`validate_skill_frontmatter()` and `validate_skill_body()` automate checks
**1, 2, 3, and 8**; checks **4, 5, 6, and 7** are process / architectural
and require human review.

For each standard, the section below answers four questions:

- **What it means** — the rule in one sentence
- **Why it matters** — the failure mode it prevents
- **Practices** — concrete do/don't, with a good and a bad example
- **How to check** — what to look for, or which validator warning

#### 1. Description is a routing trigger, not a self-intro

**What it means:** The `description` field is the only thing every session pays for. It must be a routing phrase — start with `Use when…` or `Load when…`, ≤ 50 words, target user intent not workflow.

**Why it matters:** A vague or workflow-summary description makes the skill invisible to the resolver's short-circuit. The resolver falls through to embedding similarity, which is slower, less accurate, and easily hijacked by a sibling skill's description. The skill gets matched on the wrong intents or not at all.

**Practices:**

```yaml
# Good: routing phrase, user intent, 3 distinct intents, "Use when" prefix
description: >-
  Use when a skill is not producing the quality you want, when you want to
  bootstrap a benchmark for a new skill, or when retiring an old one.
triggers:
  - "improve this skill"
  - "audit skill quality"
  - "skill won't trigger"
```

```yaml
# Bad: workflow summary, no "Use when" prefix, no user intent
description: "A meta-skill for skill management"
```

- **Don't** duplicate the same phrases across `description`, `triggers:`, and `when_to_use:`. Pick one home for each phrase; duplication triples the cost without tripling match rate.
- **Don't** describe what the skill *does*; describe what the user is *trying* to do.
- **Don't** exceed 50 words. The 1024-char cap is the looser fallback; ≤ 50 words is the operational target.

**How to check:** `validate_skill_frontmatter` emits `description: should start with 'Use when' or 'Load when'` and `description: is N words, recommended ≤ 50` warnings.

#### 2. Skill is a folder, not a file

**What it means:** `SKILL.md` is the lean hub. `scripts/` `references/` `assets/` are the spokes, loaded on demand. The body itself stays under ~150 lines.

**Why it matters:** A single 1,000-line `SKILL.md` bloats every trigger's load cost. Per Perplexity, "Skills with a lot of fluff will almost certainly degrade other Skills as well as overall agentic capabilities." Splitting into hub-and-spoke means the agent loads only the heavy detail on demand, leaving context budget for the actual work.

**Practices:**

```
skill-name/
├── SKILL.md           # ~150 lines body, always loaded when triggered
├── scripts/           # code the agent runs (not "learns from")
├── references/        # heavy docs, loaded on demand
├── assets/            # templates, schemas, data tables
└── README.md          # human landing page (not loaded by the agent)
```

- **Move** heavy content to `references/` when the body grows past ~150 lines.
- **Use multi-level nesting** for very large skills: a 1,945-section tax code does not belong in a single `SKILL.md` — split by sub-skill (e.g. 300 topics → 20 domains → 15 subtopics → 1).
- **Don't** auto-load runtime files. The agent should choose when to read.

**How to check:** `validate_skill_body` emits `body: N lines (> 150); consider moving heavy content to references/ or assets/` when the body is over 150 lines and no `references/` or `assets/` directory exists.

#### 3. Gotchas are the highest-value content

**What it means:** The body must contain at least one gotcha-style section — `## Common Rationalizations`, `## Red Flags`, `## Anti-Patterns`, `## Pitfalls`, or `## When it fails`.

**Why it matters:** Without gotchas, a skill is a frozen snapshot. With gotchas, the skill is a living artifact that grows from observed failures. Per Perplexity, "Start with a thin body; grow only on observed failures." Gotchas ARE the observed failures, distilled into reusable rules.

**Practices:**

- **Source gotchas from real agent failures**, not from speculation. The flywheel is: agent fails → add gotcha → tighten description → re-run evals.
- **Write goals + constraints**, not command sequences. The agent knows the commands; it does not know your constraints.
- **Cross-link related gotchas.** "See also: Red Flags #3" lets a reader trace a symptom back to its underlying constraint.
- **Make each gotcha copy-pasteable** into the next skill's similar section. Generalize.

**How to check:** `validate_skill_body` regex against `##` headers: `## .*[Gg]otcha|[Pp]itfall|[Ff]lag|[Pp]attern|[Ff]ail|[Rr]ationaliz`. A body with no match emits `body: no gotcha-style section found`.

#### 4. Pascal test per sentence

**What it means:** For every sentence in the body, ask "would the agent fail without this instruction?" If no, the sentence is deleteable. Iron Laws are exempt.

**Why it matters:** Most "documentation" prose is the model explaining itself. "Without this instruction, would the agent fail?" is a fast filter. Saying "Use the file system" doesn't help — the model already knows. The cost of every retained sentence is paid by every session; the benefit must be a decision signal or a constraint, not a tutorial.

**Practices:**

- **Iron Laws** (the one bolded top-of-body sentence that overrides everything) are exempt. "Violating the letter of these rules is violating the spirit of these rules" is the kind of imperative override Perplexity's example table flags as Iron Law.
- **Verification checklist items** pass Pascal individually: "Each phase prints its verb on stdout" — agent fails without it (silent phases). Apply Pascal *within* each item, not to the checklist as a whole.
- **Reference navigation aids** (e.g. "see `docs/SKILL_REFERENCE.md`") do NOT pass Pascal — they're model convenience, not decision signals.
- **Default-behavior statements** ("run from `skill-forge/`") do NOT pass Pascal — the model knows how to run a script.
- **Self-intro sentences** ("It does X; it does Y; it does Z") often fail — the first sentence is the position statement; the rest is duplication.

**How to check:** Manual review per sentence. The audit report's `docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md` § 2.3 shows a per-sentence Pascal audit on this very SKILL.md (846 → ~700 words achievable).

#### 5. Token budget: 100 / 5,000 / unlimited

**What it means:** Three tiers, each with its own cost and its own discipline:

| Tier | Content | Budget | When paid |
|---|---|---|---|
| **Index** | `name` + `description` | ~100 tokens/skill | Every session, every user, always |
| **Load** | full `SKILL.md` body | ~5,000 tokens (target) | When the skill is triggered |
| **Runtime** | files in `scripts/` `references/` `assets/` | unlimited | Only when the agent actually reads a file |

**Why it matters:** Mismatched tiers cause context bloat and recall degradation. An agent with 20 installed skills pays 20 × ~100 = ~2,000 tokens in index fees before doing any work. A skill with a 10,000-token body pays that cost every time it triggers, displacing other content from the active context.

**Practices:**

- **Index tier (≤ 100 tokens):** keep `name` + `description` short. Don't duplicate. Avoid workflow summaries.
- **Load tier (≤ 5,000 tokens):** keep body lean. Heavy detail → `references/`. The skill-forge gate is `wc -w SKILL.md ≤ 1000` (~1,300 tokens including frontmatter).
- **Runtime tier (lazy):** never auto-load. Let the agent choose. "Read all files in `assets/` before responding" defeats the lazy-loading contract.

**How to check:** `wc -w SKILL.md ≤ 1000` (skill-forge's gate). The per-tier author checklist lives in `references/token-budget.md`.

#### 6. Action at a distance

**What it means:** Changing one skill's `description` can break another skill's recall. Every `description` shifts the embedding space and the resolver's short-circuit matching.

**Why it matters:** A skill that worked yesterday may stop matching today because a sibling skill's description grew to claim overlapping intent. This is invisible at write time and only shows up as "the agent keeps loading the wrong skill" complaints.

**Practices:**

- **Keep descriptions short and unique.** Long descriptions have more claim surface; short ones have less.
- **Don't claim triggers another skill already claims.** A 5-word description with no overlap is more durable than a 50-word one with shared intent.
- **Re-run hero queries on neighbors** when you change `description` or `triggers:`. The eval rubric catches recall drift.
- **Track skill inventory** in a registry (even an informal one). MECE is a creation-time concern.

**How to check:** MECE / cross-skill registry. PRINCIPLES.md § 11 has the full mitigation table.

#### 7. Write evals first (hero queries)

**What it means:** Before shipping a skill, write a `references/hero-queries.md` with three kinds of queries: 5-10 positive (should match), 3-5 negative (should NOT match), 3-4 neighbor-confusion (could match, isn't).

**Why it matters:** Without an eval set, the resolver decides for you and you find out by user complaint. With an eval set, you have a canary: every `description` or `triggers:` change is testable in seconds. The eval set is also the input to the gotcha flywheel — a query that matches the wrong skill is a candidate gotcha for *that* skill's Red Flags.

**Practices:**

- **Positive queries** are real things the user might say. Each should target a distinct intent the skill covers.
- **Negative queries** are real things the user might say that should match *another* skill. They pin down what this skill is *not*.
- **Neighbor-confusion queries** are the dangerous middle ground — could match, but the better fit is a sibling skill. They surface at the resolver level, not the trigger level.
- **Re-run the eval set** after any `description` / `triggers:` / `when_to_use:` change. Add new queries whenever a user reports the wrong skill loaded.

**How to check:** `references/hero-queries.md` per skill. The skill-forge hero query set itself lives at `references/hero-queries.md` (10 positive, 5 negative, 4 neighbor-confusion).

#### 8. Skill dir name == frontmatter `name`

**What it means:** The directory IS the skill in the marketplace. `my-skill/SKILL.md` must declare `name: my-skill`.

**Why it matters:** A mismatch breaks marketplace lookup, confuses users ("which one is real?"), and silently breaks MECE checks. The marketplace indexes by directory; the resolver indexes by `name`. When they disagree, the resolver can match but the marketplace can't deliver.

**Practices:**

- **Always lowercase kebab-case:** `my-skill`, not `MySkill` or `my_skill`. Regex: `^[a-z0-9][a-z0-9-]*$`.
- **Set both at creation time** and keep them in sync. Renaming the directory means renaming the frontmatter; renaming the frontmatter means renaming the directory.
- **Don't add versioning to the directory name.** That's what `version:` is for.

**How to check:** `validate_skill_frontmatter(fm, skill_dir=...)` emits `dir is 'X' but frontmatter name is 'Y'` when they differ.

### Practices (the meta-process)

Standards describe what a good skill *looks like*; practices describe the process that *keeps it good*. The five below are the meta-habits that turn a static skill into a living artifact.

#### Practice 1: Run the gotcha flywheel

Without a process, gotchas stay frozen at v0.2.0. With the flywheel, they grow from observed failures:

| Symptom | Action |
|---|---|
| Agent fails at X | Add a gotcha for X in the target skill's Red Flags / Anti-Patterns |
| Agent loaded the wrong skill | Tighten the target skill's `description`, add negative evals |
| Agent should have loaded, didn't | Add keywords to `description`, add positive evals |
| System prompt changed | Check for skill conflicts or duplicates |
| New skill added | Re-run evals on existing skills (action at a distance) |

**How skill-forge implements it:** The `audit-report.md` template emits a **Suggested gotchas** section whenever the audit returns a non-trivial verdict (`prompt` / `routing` / `contract`). 1-2 curated, root-cause-specific suggestions, copy-pasteable into the target skill's Red Flags. Without this, the flywheel has no input.

#### Practice 2: Eval-driven iteration

The 6-phase pipeline IS eval-driven iteration. Each run produces a measurable delta:

- **Phase 0 (audit):** names the root cause (`prompt` / `routing` / `contract` / `missing` / `other`) with a confidence score.
- **Phase 2 (bootstrap):** generates a held-out benchmark of 15 rows by default.
- **Phase 4 (verify):** the deterministic + LLM rubric + spot-check gates produce a 0/1 verdict.
- **Phase 5 (materialize):** writes the candidate as `best.md` (or `proposed.md` for bundled), never overwrites the source.

The pipeline accepts only on a gate pass; refuses on a gate fail. No "I'll fix it later" allowed.

#### Practice 3: Safe-by-default materialization

`SKILL.md` is never overwritten by any code path. The materialize step writes a candidate to `best.md` (non-bundled accept) or `proposed.md` (bundled accept); the user diffs and merges manually. This is the safety story:

- A bad run cannot destroy a working skill.
- A bundled install is doubly protected (proposed.md only).
- The audit-report.md is the audit trail for every run.

The discipline: **write the candidate, let the human merge.** This is the same pattern that makes code review safer than direct push to main.

#### Practice 4: Concurrent-edit safety (SHA race check)

`.skill-forge-baseline.json` records the SHA of `SKILL.md` from the last successful run. The next run compares. If the file drifted (someone edited it manually between audit and materialize):

| Drifted? | Bundled? | Behaviour |
|---|---|---|
| yes | yes | `[FATAL]`, `return 3` (`EEXIT_RACE`), nothing written — refuses to overwrite the marketplace install |
| yes | no | `[WARN]`, run proceeds, `best.md` captures the new state |
| no | either | normal materialize |

Exit `3` is deliberately distinct from the refuse exit `2` so CI can tell a race refusal from a quality refusal. A `3` is a deployment signal, not a code signal.

#### Practice 5: Distinct exit codes

`0` accept · `2` refuse · `3` race. The three failure modes — accept, quality-refuse, race-refuse — get three distinct codes so CI can route them differently:

- `0` — accept. `audit-report.md` + `best.md`/`proposed.md` written; baseline updated.
- `2` — refuse. `audit-report.md` written with `verdict: refuse`; no candidate; no baseline update.
- `3` — race. `[FATAL]` on stderr, no writes, no baseline update. The bundled install is preserved.

The baseline is re-pinned **only** on accept: a refuse must not pin a SHA, or it would lock the skill out of future improvement.

### How skill-forge follows its own standards

A meta-skill is credible only if it passes its own bar. The table below is the dogfooding claim: every standard and every practice, with the specific file/line/component where skill-forge itself does the thing it prescribes.

| # | Standard / Practice | skill-forge's own implementation |
|---|---|---|
| 1 | Description is a routing trigger | `SKILL.md` line 4-8: 32 words, "Use when" prefix, 3 distinct intents; `triggers:` has 7 unique phrases, none duplicated in `description` or `when_to_use:` |
| 2 | Skill is a folder, not a file | `SKILL.md` (797 words, hub) + `scripts/` + `references/` + `docs/` + `tests/`; heavy detail in `docs/foundry-details.md` (loaded on demand, not on every invocation) |
| 3 | Gotchas are highest-value | Body has 4 gotcha-style sections: `## Common Rationalizations` (4 rows), `## Red Flags` (4 bullets), `## Verification` (5 items); plus `audit-report.md` "Suggested gotchas" that grows the flywheel |
| 4 | Pascal test per sentence | SKILL.md went 903 → 797 words by removing 4 Pascal-failing sentences; the audit report at `docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md` § 2.3 shows the per-sentence review |
| 5 | Token budget 100/5000/unlimited | SKILL.md ~1,100 tokens (Load tier); `docs/foundry-overview.md` ~1,700 tokens (load on first trigger); `docs/foundry-details.md` ~5,200 tokens (load on troubleshoot); per-tier checklist at `references/token-budget.md` |
| 6 | Action at a distance | PRINCIPLES.md § 11 dedicated section; `references/hero-queries.md` includes a "Neighbor-confusion" table to catch false matches |
| 7 | Write evals first (hero queries) | `references/hero-queries.md`: 10 positive + 5 negative + 4 neighbor-confusion queries, maintained alongside the codebase |
| 8 | Skill dir name == frontmatter name | `skill-forge/` directory, `name: skill-forge` frontmatter; `validate_skill_frontmatter(skill_dir=...)` is the 3-line check that enforces it for other skills |
| P1 | Gotcha flywheel | `_SUGGESTED_GOTCHAS` mapping (curated, not generated); `audit-report.md` emits the section on non-trivial verdicts; 1-2 suggestions per root cause |
| P2 | Eval-driven iteration | The 6-phase pipeline IS the iteration loop: audit → bootstrap (15 rows held-out) → forward → verify (3 judges) → materialize |
| P3 | Safe-by-default materialization | `_materialize` writes `best.md` / `proposed.md`, never `SKILL.md`; bundled skills get `proposed.md` only; the v2 invariant "never overwritten" is documented in `docs/foundry-details.md` § 6 |
| P4 | Concurrent-edit safety | `.skill-forge-baseline.json` SHA race check; `scripts/_lib/baseline_log.py::race()`; exit `3` on bundled drift, `[WARN]` on non-bundled drift |
| P5 | Distinct exit codes | `0` accept · `2` refuse · `3` race; implemented in `run.py::main()`; the 3 codes are CI-routable |

The package is a working demonstration of every rule it enforces. A skill that runs through skill-forge emerges with all 8 standards verified, and the meta-skill itself passes the same bar.

### Why a pipeline at all

A skill usually fails for one of three reasons: the description doesn't trigger, the body is too thin, or the body references code that doesn't exist. The first is `routing`, the second is `prompt`, the third is `contract`. Without a classifier, you fix all three and hope. With `skill-forge`'s six phases you fix only the one the audit named.

The judge phase (Phase 4) is what makes the difference: an identical candidate passes (deterministic + skip-rubric + skip-spot = `accept`), so a no-op rewrite is provably safe. A candidate with `TODO` markers refuses, so you can't ship "I'll finish this later" by accident. A candidate whose `description` is a YAML list refuses instead of raising, so a partial-formatted frontmatter is caught at the gate.

The materialize phase (Phase 5) is the safety story: a bundled skill (one registered in `~/.gbrain/install.json`) is **refused** from being written. The candidate lands in `proposed.md` next to it; the bundled `SKILL.md` is untouched. The race check against `.skill-forge-baseline.json` catches the case where you edited `SKILL.md` between audit and materialize — exit code `3` on a bundled install, `[WARN]` on a non-bundled.

### Why not just use `skill-creator` (or `skill-writer`)

This is the comparison the README exists to make. The honest answer is that `skill-creator` and `skill-writer` solve a different (smaller) problem: they take a prompt and write a `SKILL.md` once. `skill-forge` assumes the author is iterating on an existing skill and wants a gated, auditable, safe-to-fail loop. The two are complementary, not substitutable.

| Dimension | `skill-creator` (gbrain) | `skill-creator` (init_skill.py scaffold) | `skill-writer` (typical) | `skill-forge` v0.2 |
|---|---|---|---|---|
| **Output** | A 95-line authoring recipe the LLM follows by hand | A 378-line Python scaffold that creates a directory + templated `SKILL.md` | A one-shot rewrite / scaffold (varies) | A 6-phase CLI pipeline with an audit, a judge, a race check, and a materialize step |
| **Frontmatter validation** | Template instructions; the LLM is told to follow YAML block-scalar form | None — template is plain `description: [TODO: …]` | None / minimal | `frontmatter.load()` enforces first-`---`-after-line-1 fence rule (RULING-3); refuses unquoted `:` or `'` literals (RULING-5); checks `description` prefix / 50-word cap / dir-name match |
| **Body validation** | None | None | None | `validate_skill_body()` checks for gotcha-style section + references/`assets/` presence for non-trivial bodies |
| **Failure classifier** | None | None | None | `audit.py` returns one of `prompt` / `routing` / `contract` / `missing` / `other` with a confidence score and a `recommend_scope`; the recommend-scope is *typed*, not a string match |
| **Triple-judge gate** | None | None | None | Deterministic + LLM rubric + spot-check; absent rubric ≠ failure (RULING-1); `baseline` is consumed in the rubric prompt (v2-T2) so a real LLM call can compare candidate vs. baseline |
| **Bundled-skill safety** | None — the LLM just writes whatever was asked | None — `init_skill.py` writes a new directory under the requested path, refuses only if the directory already exists | None | `is_bundled(skill_dir)` reads `~/.gbrain/install.json` and refuses to forward a marketplace install; candidate lands in `proposed.md` next to the bundled `SKILL.md`, which is never overwritten |
| **Concurrent-edit safety** | None | None | None | `.skill-forge-baseline.json` records the SHA of `SKILL.md` from the last run; the next run compares and (a) refuses a bundled drift with exit `3`, (b) warns and proceeds for a non-bundled drift |
| **CI-readable exit codes** | n/a (recipe) | `0` or `1` (Python script) | n/a | `0` accept · `2` refuse · `3` race (Default Decision #3); distinct codes for distinct failure modes |
| **Audit trail** | None | None | None | `audit-report.md` (always) with `root_cause`, `verdict`, and **Suggested gotchas** section; `.skill-forge-baseline.json` (on accept) with `sha` and `ts`; readable in plain text and parseable as JSON |
| **MECE check** | Yes (manual, by the LLM) | n/a | n/a | n/a — `skill-forge` operates on one skill at a time; MECE is a *creation-time* concern that `skill-creator` already handles |
| **LLM rubric dependency** | None (recipe-only) | None (scaffold-only) | Often (one-shot rewrite) | Optional — `llm_call=None` skips the rubric entirely (RULING-1); the deterministic + spot gates run without an LLM |
| **Operating envelope** | 95 lines of markdown; works in any LLM session | 378-line Python script; needs Python 3.11+ | Varies | Python 3.11+; optional `gbrain` CLI on `PATH`; optional `~/.gbrain/install.json` (fail-open if missing) |

**The 30-second version**: `skill-creator` and `skill-writer` answer *"what should this skill say?"*; `skill-forge` answers *"is the skill I'm about to change actually a change, and am I about to break a marketplace install?"* If your workflow is "write a new skill once, ship it, move on," `skill-creator` is enough. If your workflow is "iterate on a skill until it scores well across a held-out set, and do so without corrupting a marketplace install," `skill-forge` is the right tool.

### Install

```bash
git clone https://github.com/kizemo/skill-forge
cd skill-forge/skill-forge
pip install -e .
```

`pip install -e .` puts the `skill-forge` console script on `PATH` (entry point declared in `pyproject.toml`). The same code also runs as `python -m scripts.run` from inside `skill-forge/`.

### Quick start

```bash
# Copy a target skill into a scratch dir FIRST (do not run against a
# marketplace install until you have read the bundled-skill safety section).
cp -r ~/.claude/plugins/marketplaces/gbrain/plugin/skills/my-skill C:/Temp/e2e-target/

# Audit-only — classifies the failure, writes audit-report.md, does not
# modify SKILL.md. Default exit 0 on accept, 2 on refuse.
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope audit-only

# Improve — full pipeline. Writes best.md (your skill) or proposed.md
# (bundled) with the candidate content, leaving SKILL.md untouched.
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope improve

# Held-out task count: refuse if N<5 (gbrain hard-refuses <5 internally).
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope improve --held-out 5
```

### Bundled vs. non-bundled skills

`skill-forge` distinguishes a *bundled* skill (one whose directory resolves to a path listed in `~/.gbrain/install.json`) from a *non-bundled* skill (a local working copy). The bundled check fails open — if `install.json` is missing, every skill is treated as non-bundled.

| Scenario | What `is_bundled()` returns | What `materialize` writes | Exit on accept |
|---|---|---|---|
| Working copy under `C:/Temp/e2e-target/my-skill` | `False` | `best.md` (candidate) + `audit-report.md` | `0` |
| Real bundled install at `~/.claude/.../skill-optimizer/` with `install.json` listing it | `True` | `proposed.md` (candidate) + `audit-report.md`; bundled `SKILL.md` untouched | `0` |
| Bundled install with no `install.json` on this host | `False` (fail-open) | `best.md` + `audit-report.md` | `0` |

The bundled check is **defence-in-depth**, not a lock. The real safety property is that you copy the skill to a scratch dir before iterating. `is_bundled()` exists so that if you forget, the bundled `SKILL.md` is not silently overwritten.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Accept — `audit-report.md` (always) + `best.md` (non-bundled) or `proposed.md` (bundled) written; baseline updated |
| `2` | Refuse — `audit-report.md` written with `verdict: refuse`; no candidate written; no baseline update. Triggered by: deterministic failure (e.g. `TODO` in body), `--held-out N<5`, or `--scope create` with no `gbrain` (forwards to `init_skill.py`, which returns its own non-zero) |
| `3` | Race — a bundled skill's `SKILL.md` SHA drifted between audit and materialize; refusing protects the bundled install. Distinct from refuse so CI can route them differently |

### Repository layout

```
skill-forge/
├── SKILL.md                  # 797 words (under the 1000-word gate). Iron Law + 6 phases + Common Rationalizations.
├── README.md                 # this file
├── references/               # heavy docs loaded on demand
│   ├── hero-queries.md       # 10 positive + 5 negative + 4 neighbor-confusion queries
│   └── token-budget.md       # 100/5000/unlimited tier checklist
├── docs/
│   ├── PRINCIPLES.md         # the rules skill-forge enforces (§ 1-12)
│   ├── foundry-overview.md   # load on first trigger (~1700 tokens: install / CLI / Phase 5 / failure catalog)
│   ├── foundry-details.md    # load only when troubleshooting (~5200 tokens: phases / gbrain / judges / safety)
│   ├── foundry.md            # redirect (kept one release for backwards-compatible links)
│   ├── AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md  # the audit that produced the 7 gaps
│   ├── SKILL_REFERENCE.md    # load-on-demand heavy reference (Output Format / Anti-Patterns / When it fails / Tools Used)
│   └── DEPLOYMENT.md         # local Claude-skills deployment backup
├── scripts/                  # executable code
│   ├── audit.py              # Phase 0: root-cause classifier
│   ├── bootstrap_benchmark.py # Phase 2: 15-row JSONL generator
│   ├── judge_triple.py       # Phase 4: deterministic + LLM rubric + spot-check
│   ├── router.py             # Phase 3: gbrain soft-bind + bundled-skill short-circuit
│   ├── run.py                # 6-phase CLI + materialize
│   ├── _legacy_init_skill.py # create-scope shim (skill-creator)
│   └── _lib/                 # pure helpers (frontmatter, sha, baseline_log, bundle)
└── tests/                    # 98 tests, split per phase
```

### Rulings that shape this package

`skill-forge` has 10 cross-task rules, each pinned to a commit:

- **RULING-3** — `frontmatter.load()` and `body_of()` use the same closer (`_find_closer`); the fence rule lives in one place (`3020f`).
- **RULING-4** — `[tool.pytest.ini_options] pythonpath = ["."]` in `pyproject.toml`, so bare `pytest -q` works from `skill-forge/` without `python -m pytest` (`5a7c2dd`).
- **RULING-6** — `audit()` precedence is `missing → other(frontmatter) → routing → contract → prompt → other` (`9155b4e`). The `routing` check fires first because the description is the user-facing entry point; without it the deeper branches would shadow each other.
- **RULING-6 corollary** — any `audit()` fixture targeting `contract` or `prompt` must start `description` with `Use when`; the routing gate is a silent precondition for reaching the deeper branches (`4e3c1b4`).
- **RULING-7** — `bootstrap()` cycles the template bucket to reach `n_tasks`; default 15 rows, sentinel `# BOOTSTRAP_PENDING_REVIEW` (`fd86978`).
- **RULING-8 part 1** — rubric-skipped is invisible in `verdict.llm_score`; branch on `llm_call is None` at the call site, never on the verdict (`4fc95e2`).
- **RULING-8 part 2 (v2-T2)** — `baseline` is consumed by the rubric prompt (`f"score candidate=… baseline=…"`); the LLM call can perform a candidate-vs-baseline comparison (`3020cb2`).
- **RULING-9 v2** — the router invokes the shim with `sys.executable` (not bare `python`); the shim reads the skill dir from `SKILL_DIR` env (cwd-agnostic); the shim refuses with `[FATAL] …` if both `SKILL_DIR` and `argv` are missing (`072db5e`).
- **RULING-9 v2 corollary** — the env-merge order in `router.py:34` is `{**os.environ, "SKILL_DIR": ...}`; the router's value outranks any ambient `SKILL_DIR` so a stale parent env cannot reintroduce v1's wrong-directory bug class (`5b2ab23`).
- **RULING-10** — the dead `"env"` `RootCause` member and its `TEMPLATES` bucket are dropped; strict narrowing of the v1 contract (`b31ec91`).

Full ledger: `docs/foundry-details.md` § 0 (ruling index). The foundry is the heavy reference; this README is the 5-minute tour.

### Development

```bash
cd skill-forge
pip install -e .[dev]      # or: pip install pytest pyyaml
pytest -q                  # bare invocation, RULING-4
python -m pytest -q        # equivalent
```

Test counts: **98** (76 from v0.2.0 + 18 from `validate_skill_frontmatter` / `validate_skill_body` and 4 from `_suggested_gotchas`). The `tests/` directory is split per phase (`test_frontmatter.py`, `test_audit.py`, `test_judge_triple.py`, `test_bootstrap_benchmark.py`, `test_router.py`, `test_run.py`, `test_bundle.py`, `test_sha.py`).

### License

The project is shipped without a license file; under default copyright, all rights are reserved by the author. Add a `LICENSE` file (e.g. MIT, Apache-2.0) to grant downstream rights.

---

<a id="zh"></a>

## 🇨🇳 中文

### 这是什么

`skill-forge` 是一个 CLI 工具,把"这个 skill 不工作"翻译成一条可复现的流水线:

1. **审计(Audit)** — 把失败原因分类为 `prompt` / `routing` / `contract` / `missing` / `other`(遵循 RULING-6 顺序)。
2. **范围(Scope)** — 用户选 `create` / `improve` / `audit-only` / `retire`。
3. **基准生成(Bootstrap)** — 生成 15 行 benchmark 模板(可用 `--held-out N` 覆盖,`N<5` 拒绝)。
4. **转发(Forward)** — 调用 `gbrain skillopt` 或 `skill-creator/init_skill.py`;失败时优雅降级。
5. **验证(Verify)** — 确定性检查 + LLM 评分 + 可选人工 spot-check;评分器缺省 ≠ 失败(RULING-1)。
6. **物化(Materialize)** — 始终写 `audit-report.md`;接受时非 bundled 写 `best.md`、bundled 写 `proposed.md`;**绝不覆盖**目标 `SKILL.md`。Verdict 非平凡时输出 **Suggested gotchas** 章节。

它是"skill 创作"的*流水线层*,不是创作本身。作者仍然写正文;skill-forge 做的是审计、判分、竞态检测、安全落地。

### ✨ 好 skill 的 8 条标准

这 8 条标准是 2026-10-15 Perplexity 审计(`docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md`)后整理,并已写进 `docs/PRINCIPLES.md`。它们是判断一个 skill 是否合格的总分细则。`validate_skill_frontmatter()` 和 `validate_skill_body()` 把第 **1、2、3、8** 条自动化成检查;第 **4、5、6、7** 条是流程/架构层面的,需要人 review。

每条标准下都回答四个问题:

- **含义** — 一句话规则
- **为什么重要** — 它防住的失败模式
- **实践** — 具体的 do/don't,带好例和坏例
- **如何检查** — 看哪里,或哪条 validator 警告

#### 1. 描述是路由触发器,不是自我介绍

**含义:** `description` 字段是每个会话都会付费的唯一东西。它必须是路由短语 —— 以 `Use when…` 或 `Load when…` 开头,≤ 50 词,目标用户意图而非工作流。

**为什么重要:** 模糊的或工作流总结式的描述让 resolver 的短路匹配失效,只能回退到嵌入相似度 —— 更慢、更不准确、容易被邻居 skill 的 description 抢走。Skill 会被匹配到错误意图,或者根本不被匹配。

**实践:**

```yaml
# 好:路由短语,用户意图,3 个不同意图,"Use when" 前缀
description: >-
  Use when a skill is not producing the quality you want, when you want to
  bootstrap a benchmark for a new skill, or when retiring an old one.
triggers:
  - "improve this skill"
  - "audit skill quality"
  - "skill won't trigger"
```

```yaml
# 坏:工作流总结,没有 "Use when" 前缀,没有用户意图
description: "A meta-skill for skill management"
```

- **不要**在 `description`、`triggers:`、`when_to_use:` 三处重复同样的短语。每个短语只放一处;重复只会让成本翻三倍而不让匹配率翻三倍。
- **不要**描述 skill *做什么*;描述用户*想做什么*。
- **不要**超过 50 词。1024 字符是宽松的上限;≤ 50 词是操作目标。

**如何检查:** `validate_skill_frontmatter` 会输出 `description: should start with 'Use when' or 'Load when'` 和 `description: is N words, recommended ≤ 50` 警告。

#### 2. Skill 是文件夹,不是单文件

**含义:** `SKILL.md` 是精简的 hub。`scripts/` `references/` `assets/` 是 spoke,按需加载。正文本身保持在 ~150 行以内。

**为什么重要:** 单个 1,000 行的 `SKILL.md` 会让每次触发的加载成本膨胀。Perplexity 说"fluff 多的 skill 几乎肯定会拖累其他 skill 以及整体的 agentic 能力"。Hub-and-spoke 切分让 agent 只在需要时加载重内容,把上下文预算留给实际工作。

**实践:**

```
skill-name/
├── SKILL.md           # ~150 行正文,触发时总是加载
├── scripts/           # agent 跑的代码(不是"学到的")
├── references/        # 重文档,按需加载
├── assets/            # 模板、schema、数据表
└── README.md          # 人类落地页(agent 不加载)
```

- 当 body 长过 ~150 行,**把**重内容移到 `references/`。
- 对超大 skill 用**多层嵌套**:1,945 节的税法不该放在单个 `SKILL.md` 里 —— 按子 skill 切(300 主题 → 20 域 → 15 子主题 → 1)。
- **不要**自动加载 runtime 文件。让 agent 决定何时读。

**如何检查:** `validate_skill_body` 在 body 超 150 行且没有 `references/` 或 `assets/` 目录时,会输出 `body: N lines (> 150); consider moving heavy content to references/ or assets/`。

#### 3. Gotcha 是最高价值内容

**含义:** 正文必须至少包含一个 gotcha 风格小节 —— `## Common Rationalizations`、`## Red Flags`、`## Anti-Patterns`、`## Pitfalls`、`## When it fails` 之一。

**为什么重要:** 没有 gotcha,skill 就是冻在某个版本的快照。有了 gotcha,skill 是从观察到的失败中生长的活物。Perplexity 说"从薄正文开始,只在观察到的失败上长"。Gotcha 就是把观察到的失败蒸馏成可复用规则的结果。

**实践:**

- gotcha 的素材要**来自真实 agent 失败**,不是凭空想象。飞轮是:agent 失败 → 加 gotcha → 收紧 description → 重跑 evals。
- **写目标 + 约束**,不写命令序列。Agent 知道命令;它不知道你的约束。
- **互相交叉链接**相关 gotcha。"另见:Red Flags #3" 让读者能把症状追到底层约束。
- 让每条 gotcha 都**可以直接复制粘贴**到下一个 skill 的同类小节。要通用化。

**如何检查:** `validate_skill_body` 对 `##` 标题做正则:`## .*[Gg]otcha|[Pp]itfall|[Ff]lag|[Pp]attern|[Ff]ail|[Rr]ationaliz`。没匹配上的 body 会输出 `body: no gotcha-style section found`。

#### 4. Pascal 测试每句话

**含义:** 对正文里的每一句,问"没这句 agent 会不会失败?"不会,这一句就删。Iron Law 豁免。

**为什么重要:** 大部分"文档"散文是模型在解释自己。"没这句会不会失败"是个快筛。说"用文件系统"没用 —— 模型已经知道。每保留一句的代价是每个会话都付;收益必须是决策信号或约束,不是教程。

**实践:**

- **Iron Law**(顶部加粗的、覆盖一切的那一句)豁免。"Violating the letter of these rules is violating the spirit of these rules" 正是 Perplexity 范例表标为 Iron Law 的那种 imperative 覆盖。
- **验证 checklist 项**单独过 Pascal:"Each phase prints its verb on stdout" —— 没这句 agent 会失败(静默阶段)。Pascal 应用于**每项内部**,而不是整个 checklist。
- **引用导航提示**(比如"见 `docs/SKILL_REFERENCE.md`")**不**过 Pascal —— 是模型便利,不是决策信号。
- **默认行为陈述**("从 `skill-forge/` 运行")**不**过 Pascal —— 模型知道怎么跑脚本。
- **自我介绍句**("它做 X;做 Y;做 Z")通常过不了 —— 第一句是定位陈述,后面是重复。

**如何检查:** 手动逐句过 Pascal。审计报告 `docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md` § 2.3 有对本文 SKILL.md 的逐句 Pascal 审计(846 → ~700 词可达成)。

#### 5. Token 预算:100 / 5,000 / 无限

**含义:** 三层,各层有自己的成本和自己的纪律:

| 层 | 内容 | 预算 | 何时付费 |
|---|---|---|---|
| **Index** | `name` + `description` | ~100 tokens/skill | 每个会话,每个用户,总是 |
| **Load** | 完整 SKILL.md 正文 | ~5,000 tokens(目标) | 触发 skill 时 |
| **Runtime** | `scripts/` `references/` `assets/` 里的文件 | 无限 | 只有当 agent 真的读这个文件时 |

**为什么重要:** 层错配会导致上下文膨胀和召回退化。一个装了 20 个 skill 的 agent 在做任何工作前就要付 20 × ~100 = ~2,000 tokens 的 index 费。一个 10,000 token 正文的 skill 每次触发都要付这笔成本,把其他内容挤出活动上下文。

**实践:**

- **Index 层(≤ 100 tokens):** `name` + `description` 保持简短。不要重复。避免工作流总结。
- **Load 层(≤ 5,000 tokens):** 正文保持精简。重细节 → `references/`。skill-forge 的闸门是 `wc -w SKILL.md ≤ 1000`(含 frontmatter 约 1,300 tokens)。
- **Runtime 层(惰性):** 永不自动加载。让 agent 选择。"先读 `assets/` 全部文件" 打破了惰性加载契约。

**如何检查:** `wc -w SKILL.md ≤ 1000`(skill-forge 自己的闸门)。逐层作者 checklist 见 `references/token-budget.md`。

#### 6. Action at a distance(远端作用)

**含义:** 改一个 skill 的 `description` 可能破坏另一个 skill 的召回。每个 description 都会动嵌入空间和 resolver 的短路匹配。

**为什么重要:** 昨天还工作的 skill 今天可能停止匹配,因为兄弟 skill 的 description 长出来抢占了重叠的意图。写时看不出来,只有"agent 老加载错 skill"的用户投诉才会暴露。

**实践:**

- **description 保持简短且唯一。** 长的有更多声明面;短的有更少。
- **不要抢占另一个 skill 已经声明的 trigger。** 5 词无重叠的 description 比 50 词有共享意图的更耐用。
- 改 `description` 或 `triggers:` 时,**对邻居 skill 重跑 hero queries**。eval 细则能抓住召回漂移。
- 把 skill 清单记在**注册表**里(哪怕非正式)。MECE 是创建期问题。

**如何检查:** MECE / 跨 skill 注册表。PRINCIPLES.md § 11 有完整的缓解表。

#### 7. 先写 evals(hero queries)

**含义:** ship 一个 skill 之前,先写一个 `references/hero-queries.md`,包含三种 query:5-10 正面(应匹配)、3-5 负面(不应匹配)、3-4 邻居混淆(可匹配但不是它)。

**为什么重要:** 没有 eval 集,resolver 替你决定,你只能从用户投诉里发现。有了 eval 集,你有个金丝雀:每次 `description` 或 `triggers:` 变更都秒级可测。eval 集也是 gotcha 飞轮的输入 —— 一个匹配错 skill 的 query 是*那个* skill 的 Red Flags 的候选 gotcha。

**实践:**

- **正面 query** 是用户实际可能说的。每个针对一个不同的意图。
- **负面 query** 是用户实际可能说但应匹配*另一个* skill 的。把"这个 skill 不是什么"钉死。
- **邻居混淆 query** 是危险的中间地带 —— 能匹配,但兄弟 skill 更合适。它们在 resolver 层(不是 trigger 层)浮出来。
- 改 `description` / `triggers:` / `when_to_use:` 之后**重跑 eval 集**。每当用户报"加载错 skill"就加新 query。

**如何检查:** 每个 skill 自己的 `references/hero-queries.md`。skill-forge 自己的 hero query 集在 `references/hero-queries.md`(10 正面、5 负面、4 邻居混淆)。

#### 8. 目录名 == frontmatter `name`

**含义:** 在 marketplace 里,目录就是 skill。`my-skill/SKILL.md` 必须声明 `name: my-skill`。

**为什么重要:** 不匹配会破坏 marketplace 查找,让用户困惑("哪个是真的"),悄悄破坏 MECE 检查。Marketplace 按目录索引;resolver 按 `name` 索引。它们不一致时,resolver 能匹配但 marketplace 送不出货。

**实践:**

- **永远小写 kebab-case:** `my-skill`,不是 `MySkill` 或 `my_skill`。正则:`^[a-z0-9][a-z0-9-]*$`。
- **创建时就两个都设好**并保持同步。重命名目录就要重命名 frontmatter;重命名 frontmatter 就要重命名目录。
- **不要在目录名里加版本号。** 那是 `version:` 字段的事。

**如何检查:** `validate_skill_frontmatter(fm, skill_dir=...)` 在两者不一致时输出 `dir is 'X' but frontmatter name is 'Y'`。

### 5 条实践(元流程)

标准描述好 skill *长什么样*;实践描述让 skill *保持好*的过程。下面五条是把静态 skill 变成活物的元习惯。

#### 实践 1: 跑 gotcha 飞轮

没过程,gotcha 永远冻在 v0.2.0。有了飞轮,gotcha 从观察到的失败里长:

| 症状 | 行动 |
|---|---|
| Agent 在 X 失败 | 在目标 skill 的 Red Flags / Anti-Patterns 加 X 的 gotcha |
| Agent 加载了错的 skill | 收紧目标 skill 的 `description`,加负面 evals |
| Agent 应该加载但没加载 | 在 `description` 加关键词,加正面 evals |
| 系统提示词变了 | 检查 skill 冲突或重复 |
| 新 skill 加了 | 对现有 skill 重跑 evals(action at a distance) |

**skill-forge 怎么实现:** `audit-report.md` 模板在 audit 返回非平凡 verdict(`prompt` / `routing` / `contract`)时输出 **Suggested gotchas** 章节。1-2 条针对该 root cause 的、精心写好的建议,可直接复制粘贴到目标 skill 的 Red Flags。没有这个,飞轮没输入。

#### 实践 2: Eval-driven iteration(评测驱动迭代)

6 阶段流水线本身就是评测驱动的迭代。每次运行产生一个可量化的 delta:

- **Phase 0(audit):** 命名根因(`prompt` / `routing` / `contract` / `missing` / `other`),带置信度。
- **Phase 2(bootstrap):** 生成默认 15 行的 holdout benchmark。
- **Phase 4(verify):** 确定性 + LLM 评分 + spot-check 三路闸门输出 0/1 verdict。
- **Phase 5(materialize):** 把候选写为 `best.md`(非 bundled)或 `proposed.md`(bundled),绝不覆盖源。

流水线只在闸门通过时接受;闸门失败时拒绝。不允许"我等下再修"。

#### 实践 3: 默认安全的物化

任何代码路径都不覆盖 `SKILL.md`。物化步骤把候选写到 `best.md`(非 bundled accept)或 `proposed.md`(bundled accept);用户 diff 完手动合并。这就是安全故事的本体:

- 一次坏的运行不能毁掉一个工作的 skill。
- bundled install 有双重保护(只写 `proposed.md`)。
- `audit-report.md` 是每次运行的审计轨迹。

纪律:**写候选,让人类合并。** 这跟"code review 比直接 push main 更安全"是同一种模式。

#### 实践 4: 并发编辑安全(SHA 竞态检查)

`.skill-forge-baseline.json` 记录上一次成功运行时 `SKILL.md` 的 SHA。下次运行比对。如果文件漂移了(有人在 audit 和 materialize 之间手改了):

| 漂移? | bundled? | 行为 |
|---|---|---|
| 是 | 是 | `[FATAL]`,`return 3`(`EEXIT_RACE`),什么都不写 —— 拒绝覆盖 marketplace install |
| 是 | 否 | `[WARN]`,继续运行,`best.md` 捕获新状态 |
| 否 | 任意 | 正常物化 |

Exit `3` 故意和拒绝 exit `2` 区分开,方便 CI 区分竞态拒绝和质量拒绝。`3` 是部署信号,不是代码信号。

#### 实践 5: 不同的退出码

`0` 接受 · `2` 拒绝 · `3` 竞态。三种失败模式 —— 接受、质量拒绝、竞态拒绝 —— 给三个不同的码,方便 CI 走不同分支:

- `0` — 接受。`audit-report.md` + `best.md`/`proposed.md` 已写;baseline 已更新。
- `2` — 拒绝。`audit-report.md` 写 `verdict: refuse`;不写候选;不更新 baseline。
- `3` — 竞态。stderr 写 `[FATAL]`,不写任何东西,不更新 baseline。bundled install 被保护。

Baseline **只在**接受时重新钉:拒绝不能钉 SHA,否则会把 skill 锁死,无法未来再改进。

### skill-forge 如何遵循自己的标准

元 skill 的可信度只能通过"自己达到自己的标准"来证明。下表就是 dogfooding 主张:每条标准 + 每条实践,都配上 skill-forge 自己落实这件事的具体文件/行/组件。

| # | 标准 / 实践 | skill-forge 自己的实现 |
|---|---|---|
| 1 | 描述是路由触发器 | `SKILL.md` 第 4-8 行:32 词,"Use when" 前缀,3 个不同意图;`triggers:` 7 个唯一短语,与 `description`、`when_to_use:` 无重复 |
| 2 | Skill 是文件夹 | `SKILL.md`(797 词,hub)+ `scripts/` + `references/` + `docs/` + `tests/`;重细节在 `docs/foundry-details.md`(按需加载,不是每次触发都加载) |
| 3 | Gotcha 是最高价值 | 正文有 4 个 gotcha 风格小节:`## Common Rationalizations`(4 行)、`## Red Flags`(4 项)、`## Verification`(5 项);外加 `audit-report.md` 的 "Suggested gotchas" 飞轮生长点 |
| 4 | Pascal 测试每句话 | SKILL.md 从 903 → 797 词,删了 4 句不过 Pascal 的;逐句审计见 `docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md` § 2.3 |
| 5 | Token 预算 100/5000/无限 | SKILL.md ~1,100 tokens(Load);`docs/foundry-overview.md` ~1,700 tokens(首次触发时加载);`docs/foundry-details.md` ~5,200 tokens(排错时加载);逐层 checklist 在 `references/token-budget.md` |
| 6 | Action at a distance | PRINCIPLES.md § 11 专章;`references/hero-queries.md` 包含"邻居混淆"表,用来抓错匹配 |
| 7 | 先写 evals(hero queries) | `references/hero-queries.md`:10 正面 + 5 负面 + 4 邻居混淆 query,跟代码一起维护 |
| 8 | 目录名 == frontmatter 名 | `skill-forge/` 目录,`name: skill-forge` frontmatter;`validate_skill_frontmatter(skill_dir=...)` 是 3 行检查,强制其他 skill 也满足 |
| P1 | Gotcha 飞轮 | `_SUGGESTED_GOTCHAS` 映射(curated,非生成);`audit-report.md` 在非平凡 verdict 时输出章节;每个 root cause 1-2 条建议 |
| P2 | 评测驱动迭代 | 6 阶段流水线本身就是迭代环:audit → bootstrap(15 行 holdout)→ forward → verify(3 判)→ materialize |
| P3 | 默认安全的物化 | `_materialize` 写 `best.md` / `proposed.md`,永不写 `SKILL.md`;bundled skill 只拿 `proposed.md`;v2 不变量"永不被覆盖"写在 `docs/foundry-details.md` § 6 |
| P4 | 并发编辑安全 | `.skill-forge-baseline.json` SHA 竞态检查;`scripts/_lib/baseline_log.py::race()`;bundled 漂移 → `exit 3`,非 bundled 漂移 → `[WARN]` |
| P5 | 不同的退出码 | `0` 接受 · `2` 拒绝 · `3` 竞态;在 `run.py::main()` 实现;3 个码都可被 CI 路由 |

这个包是它强制执行的每条规则的工作示例。一个跑过 skill-forge 的 skill 出来时 8 条标准都过检,而这个元 skill 自己也过同一道杠。

### 为什么要一条流水线

一个 skill 失败通常是这三种之一:描述不触发(是 `routing`)、正文太薄(是 `prompt`)、正文引用的代码不存在(是 `contract`)。没有分类器,你只能三种都改然后碰运气。有 `skill-forge` 的六阶段,你只改审计指出的那一种。

第四阶段(Verify)的判分是真正的差异:同一个候选通过(确定性 + 跳过评分 + 跳过 spot = `accept`),所以"无意义重写"是被证明无害的;带 `TODO` 的候选直接拒绝,所以"我等下再补完"不能蒙混过关;`description` 是 YAML 列表时,`isinstance(desc, str)` 守卫会拒绝而不是抛 `AttributeError`,所以半成品 frontmatter 在闸口就被截住。

第五阶段(Materialize)是安全故事的本体:一个 bundled skill(出现在 `~/.gbrain/install.json` 里的)被**拒绝**写入。候选落到同目录的 `proposed.md`;bundled 的 `SKILL.md` 始终不动。`.skill-forge-baseline.json` 记录上一次成功运行时的 SHA,下一次运行比对 —— 如果 audit 和 materialize 之间你手改了 `SKILL.md`,bundled 路径直接 `exit 3` 拒绝,非 bundled 路径走 `[WARN]` 放行。

### 为什么不直接用 `skill-creator`(或 `skill-writer`)

README 存在的全部意义就是把这点说清楚。老实说,`skill-creator` 和 `skill-writer` 解决的是一个更小的问题:它们接一个 prompt、一次性写一个 `SKILL.md`。`skill-forge` 假设的是:**作者在迭代一个已有 skill,要一个带闸门、带审计、失败安全的循环**。两者是互补的、不是互相替代。

| 维度 | `skill-creator`(gbrain) | `skill-creator`(`init_skill.py` 脚手架) | `skill-writer`(典型) | `skill-forge` v0.2 |
|---|---|---|---|---|
| **输出** | 一份 95 行的 LLM 写作配方 | 一个 378 行的 Python 脚手架,创建目录 + 模板化 `SKILL.md` | 一次性改写/脚手架(各家不一) | 一条 6 阶段 CLI 流水线,带审计、判分、竞态检测、物化步骤 |
| **Frontmatter 校验** | 模板说明;告诉 LLM 用 YAML block-scalar | 无 — 模板就是 `description: [TODO: …]` | 无 / 极弱 | `frontmatter.load()` 强制执行首条 `---` 之后的栅栏规则(RULING-3);未引号的 `:` 或 `'` 直接拒(RULING-5);并检查前缀 / 50 词 / 目录名匹配 |
| **正文校验** | 无 | 无 | 无 | `validate_skill_body()` 检查 gotcha 小节 + 大正文下 `references/`/`assets/` 存在性 |
| **失败分类器** | 无 | 无 | 无 | `audit.py` 返回 `prompt` / `routing` / `contract` / `missing` / `other` 之一,带置信度和 `recommend_scope`;scope 是**类型化的**,不是字符串匹配 |
| **三路判分闸门** | 无 | 无 | 无 | 确定性 + LLM 评分 + spot-check;评分器缺省 ≠ 失败(RULING-1);`baseline` 进 rubric prompt(v2-T2),真实 LLM 可以做候选 vs baseline 对比 |
| **Bundled-skill 安全** | 无 — LLM 就直接写 | 无 — `init_skill.py` 在请求路径下写新目录,只在目录已存在时拒绝 | 无 | `is_bundled(skill_dir)` 读 `~/.gbrain/install.json`,marketplace install 拒绝转发;候选落 `proposed.md`,bundled `SKILL.md` 不动 |
| **并发编辑安全** | 无 | 无 | 无 | `.skill-forge-baseline.json` 记录上一次 `SKILL.md` 的 SHA;下次运行比对,bundled 漂移 → `exit 3`,非 bundled 漂移 → `[WARN]` 放行 |
| **CI 可读退出码** | n/a(配方) | `0` 或 `1`(Python 脚本) | n/a | `0` 接受 · `2` 拒绝 · `3` 竞态(Default Decision #3);不同失败模式用不同码 |
| **审计轨迹** | 无 | 无 | 无 | `audit-report.md`(总是写,带 `root_cause`、`verdict` 和 **Suggested gotchas** 章节);`.skill-forge-baseline.json`(接受时写,带 `sha` 和 `ts`);纯文本 + 可解析 JSON |
| **MECE 检查** | 有(手工,LLM 自己做) | n/a | n/a | n/a — `skill-forge` 一次只处理一个 skill;MECE 是创建期问题,`skill-creator` 已覆盖 |
| **LLM 评分依赖** | 无(纯配方) | 无(纯脚手架) | 经常(一次性改写) | 可选 — `llm_call=None` 直接跳过评分(RULING-1);确定性 + spot 闸门无需 LLM 即可运行 |
| **运行依赖** | 任意 LLM 会话 | Python 3.11+ | 不一 | Python 3.11+;`PATH` 上可选 `gbrain` CLI;可选 `~/.gbrain/install.json`(缺失则 fail-open) |

**30 秒版总结**:`skill-creator` 和 `skill-writer` 回答的是*"这个 skill 应该说什么"*;`skill-forge` 回答的是*"我打算改的这个 skill 真的算改动吗?我会不会顺手把一个 marketplace install 搞坏?"*。如果你的工作流是"写一个新 skill 一次,发出去,继续下一个",`skill-creator` 就够了。如果你的工作流是"在一个 skill 上迭代,直到它在 holdout 集上分数好看,而且过程中不能搞坏 marketplace install",`skill-forge` 才是对的工具。

### 安装

```bash
git clone https://github.com/kizemo/skill-forge
cd skill-forge/skill-forge
pip install -e .
```

`pip install -e .` 把 `skill-forge` 控制台脚本放到 `PATH`(入口在 `pyproject.toml` 声明)。同一份代码也可以在 `skill-forge/` 目录下用 `python -m scripts.run` 运行。

### 快速开始

```bash
# 第一步:把目标 skill 复制到 scratch 目录(在读懂 bundled-skill 安全章节之前,
# 不要直接对 marketplace install 跑)。
cp -r ~/.claude/plugins/marketplaces/gbrain/plugin/skills/my-skill C:/Temp/e2e-target/

# 只审计 — 分类失败原因,写 audit-report.md,不动 SKILL.md。
# 默认接受时 exit 0,拒绝时 exit 2。
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope audit-only

# Improve — 全流水线。写 best.md(你自己的 skill)或 proposed.md(bundled),
# SKILL.md 不动。
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope improve

# held-out 任务数:N<5 拒绝(gbrain 内部硬性拒绝 <5)。
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope improve --held-out 5
```

### Bundled vs. 非 Bundled Skill

`skill-forge` 区分 **bundled** skill(目录解析到 `~/.gbrain/install.json` 列出的路径)和**非 bundled** skill(本地工作副本)。bundled 检测 fail-open —— `install.json` 缺失时,所有 skill 都按非 bundled 处理。

| 场景 | `is_bundled()` 返回 | materialize 写什么 | 接受时退出码 |
|---|---|---|---|
| `C:/Temp/e2e-target/my-skill` 下的工作副本 | `False` | `best.md`(候选) + `audit-report.md` | `0` |
| 真实 bundled install 在 `~/.claude/.../skill-optimizer/`,`install.json` 列出 | `True` | `proposed.md`(候选) + `audit-report.md`;bundled `SKILL.md` 不动 | `0` |
| Bundled install,但本机无 `install.json` | `False`(fail-open) | `best.md` + `audit-report.md` | `0` |

bundled 检测是**纵深防御**,不是锁。真正的安全属性是:**你在迭代之前把 skill 复制到 scratch 目录**。`is_bundled()` 的存在是为了:就算你忘了,bundled `SKILL.md` 也不会被悄悄覆盖。

### 退出码

| 码 | 含义 |
|---|---|
| `0` | 接受 — `audit-report.md`(总是写) + `best.md`(非 bundled)或 `proposed.md`(bundled) 已写;baseline 已更新 |
| `2` | 拒绝 — `audit-report.md` 写 `verdict: refuse`;不写候选;不更新 baseline。触发场景:确定性失败(比如正文有 `TODO`)、`--held-out N<5`、或 `--scope create` 且无 `gbrain`(转发到 `init_skill.py`,它返回自己的非零) |
| `3` | 竞态 — bundled skill 的 `SKILL.md` SHA 在 audit 和 materialize 之间被改过;拒绝以保护 bundled install。和"拒绝"区分开,方便 CI 走不同分支 |

### 仓库布局

```
skill-forge/
├── SKILL.md                  # 797 词(在 1000 词闸门之下)。Iron Law + 6 阶段 + Common Rationalizations。
├── README.md                 # 本文件
├── references/               # 按需加载的重量级文档
│   ├── hero-queries.md       # 10 正面 + 5 负面 + 4 邻居混淆 查询
│   └── token-budget.md       # 100/5000/无限 层级 checklist
├── docs/
│   ├── PRINCIPLES.md         # skill-forge 强制执行的规则(§ 1-12)
│   ├── foundry-overview.md   # 首次触发时加载(~1700 tokens:安装/CLI/Phase 5/失败目录)
│   ├── foundry-details.md    # 仅在排错时加载(~5200 tokens:阶段细节/gbrain/判分器/安全)
│   ├── foundry.md            # 跳转页(保留一个 release 周期以兼容老链接)
│   ├── AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md  # 产生 7 个 gap 的审计
│   ├── SKILL_REFERENCE.md    # 按需加载的重量级参考(Output Format / Anti-Patterns / When it fails / Tools Used)
│   └── DEPLOYMENT.md         # 本地 Claude-skills 部署备查
├── scripts/                  # 可执行代码
│   ├── audit.py              # Phase 0:根因分类器
│   ├── bootstrap_benchmark.py # Phase 2:15 行 JSONL 生成器
│   ├── judge_triple.py       # Phase 4:确定性 + LLM 评分 + spot-check
│   ├── router.py             # Phase 3:gbrain 软绑定 + bundled-skill 短路
│   ├── run.py                # 6 阶段 CLI + materialize
│   ├── _legacy_init_skill.py # create 范围 shim(skill-creator)
│   └── _lib/                 # 纯辅助(frontmatter、sha、baseline_log、bundle)
└── tests/                    # 98 个测试,按阶段分文件
```

### 塑造这个项目的 10 条规则

`skill-forge` 跨任务有 10 条规则,每条都钉在一次 commit 上:

- **RULING-3** — `frontmatter.load()` 和 `body_of()` 用同一个 closer(`_find_closer`);栅栏规则只在一处(`3020f`)。
- **RULING-4** — `pyproject.toml` 里的 `[tool.pytest.ini_options] pythonpath = ["."]`,让 `skill-forge/` 下裸跑 `pytest -q` 也能工作,不用 `python -m pytest`(`5a7c2dd`)。
- **RULING-6** — `audit()` 优先级是 `missing → other(frontmatter) → routing → contract → prompt → other`(`9155b4e`)。`routing` 排在最前,因为描述是面向用户的入口;不排前的话,后面的分支会互相遮挡。
- **RULING-6 corollary** — 任何针对 `contract` 或 `prompt` 分支的 `audit()` fixture 必须以 `Use when` 开头;`routing` 闸门是触达更深分支的隐式前置条件(`4e3c1b4`)。
- **RULING-7** — `bootstrap()` 循环模板桶以凑齐 `n_tasks`;默认 15 行,带哨兵 `# BOOTSTRAP_PENDING_REVIEW`(`fd86978`)。
- **RULING-8 part 1** — rubric-skipped 在 `verdict.llm_score` 里不可见;在调用现场用 `llm_call is None` 判断,不要从 verdict 推断(`4fc95e2`)。
- **RULING-8 part 2 (v2-T2)** — `baseline` 被 rubric prompt 消费(`f"score candidate=… baseline=…"`);真实 LLM 调用可以做候选 vs baseline 对比(`3020cb2`)。
- **RULING-9 v2** — 路由器用 `sys.executable`(不是裸 `python`)调 shim;shim 从 `SKILL_DIR` 环境变量读 skill 目录(与 cwd 无关);两者都缺时,shim 输 `[FATAL] …` 然后退出 2(`072db5e`)。
- **RULING-9 v2 corollary** — `router.py:34` 的 env 合并顺序是 `{**os.environ, "SKILL_DIR": ...}`;路由器的值盖过任何环境里的 `SKILL_DIR`,防止陈旧父环境让 v1 的"错目录"bug 类重新出现(`5b2ab23`)。
- **RULING-10** — 死值 `"env"` `RootCause` 成员及其 `TEMPLATES` 桶被删;v1 契约的严格缩窄(`b31ec91`)。

完整台账:见 `docs/foundry-details.md` § 0(规则索引)。foundry 是大而全的参考;这份 README 是 5 分钟导览。

### 开发

```bash
cd skill-forge
pip install -e .[dev]      # 或:pip install pytest pyyaml
pytest -q                  # 裸调用,RULING-4
python -m pytest -q        # 等价
```

测试数:**98**(76 来自 v0.2.0 + 18 来自 `validate_skill_frontmatter` / `validate_skill_body` + 4 来自 `_suggested_gotchas`)。`tests/` 目录按阶段分文件(`test_frontmatter.py`、`test_audit.py`、`test_judge_triple.py`、`test_bootstrap_benchmark.py`、`test_router.py`、`test_run.py`、`test_bundle.py`、`test_sha.py`)。

### 许可证

项目未带 `LICENSE` 文件;按默认版权,所有权利归作者所有。添加 `LICENSE`(例如 MIT、Apache-2.0)即可向下游授予权限。