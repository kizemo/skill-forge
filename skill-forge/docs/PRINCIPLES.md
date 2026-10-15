# Skill-writing principles

This document is the canonical statement of the principles `skill-forge` follows when writing a skill, and the rules the codebase enforces. If a principle in this file is violated by a target `SKILL.md`, `audit.py` should surface it as evidence in the audit report; if `validate_skill_frontmatter()` returns warnings, the materialize step is still permitted (a skill that *fails* the principles is not necessarily broken, just suboptimal) but the warnings are recorded in `audit-report.md` for the author to review.

Last reviewed: 2026-10-15, against v0.2.0-rc1.

---

## 1. Frontmatter principles (parseable, partly enforced in code)

These are properties the `frontmatter.load()` parser + a `validate_skill_frontmatter()` helper can verify. Code lives in `scripts/_lib/frontmatter.py`.

### 1.1 Concise description (recommended ≤ 1024 chars)

The frontmatter `description:` is the most important field: Claude's skill resolver matches user intent against it. A vague description (e.g. `description: y`) makes the skill essentially invisible.

**Rule**: keep `description` under 1024 characters. Lead with **what** the skill does in one sentence, then a `Triggers:` clause with concrete phrases the user might say. Prefer a YAML block scalar (`>-` or `|`) when the description contains `:`, `'`, or spans multiple lines.

```yaml
# Good
description: >-
  Use when a skill is not producing the quality you want …
  Triggers: "improve this skill", "skill won't trigger", …

# Bad
description: y
description: this skill does skill things
```

### 1.2 YAML block scalar when the description contains `:` or `'`

Per v2 RULING-5: a `description` containing a `:` (YAML mapping marker) or a `'` (YAML quote) **must** be authored as a YAML block scalar — `>-` (folded) or `|` (literal). Single-quoting is *not* sufficient because the standard trigger list contains apostrophes (e.g. `"skill won't trigger"`), and apostrophes terminate single-quoted scalars.

### 1.3 Explicit `triggers:` list

Frontmatter must have a `triggers:` list with at least 3 concrete user phrases. The skill resolver uses these for short-circuit matching before falling back to description-similarity. A skill without triggers is at the resolver's mercy and will match poorly.

### 1.4 `mutating:` boolean

Frontmatter must have `mutating: true` or `mutating: false` explicitly. A skill that creates or rewrites files is `true`; a read-only skill is `false`. This is the contract Claude uses to decide whether to prompt for confirmation before invoking.

### 1.5 `name:` is lowercase kebab-case

`name: My-Skill` will not match how the marketplace expects the directory to be named. Lowercase, kebab-case, no spaces, no underscores, no capitals. Examples: `skill-forge`, `ad-cut`, `codebase-memory`. Regex: `^[a-z0-9][a-z0-9-]*$`.

### 1.6 `brain_first:` declared

`brain_first: exempt` if the skill doesn't need the brain (e.g. pure-prompt recipes); `brain_first: required` if it does; omit the field if it's not relevant. This is a gbrain-marketplace convention.

### 1.7 `when_to_use:` (single-line summary)

A one-line summary that can be shown in marketplace listings. The full `description` can be multi-line; `when_to_use` is the short version. Example: `when_to_use: "Use when the user asks: \"create a skill\", \"new skill\"."`.

### 1.8 `version:` (semver)

`MAJOR.MINOR.PATCH`. Bump MAJOR on breaking changes, MINOR on new features, PATCH on bug fixes. This is a gbrain convention.

---

## 2. Body principles (structure, audited but not enforced in code)

These are properties the body of `SKILL.md` should follow. `audit.py` checks structural presence (does a `## Output Format` section exist?) but does not enforce quality of prose.

### 2.1 Iron Law (one override rule)

A single, bolded, top-of-body sentence that overrides everything else when in conflict. It must be *short*, *imperative*, and *true*. Example:

> **Violating the letter of these rules is violating the spirit of these rules.**

### 2.2 When to use / When NOT to use

Two short sections. `When to use` lists the conditions under which the skill should be invoked. `When NOT to use` lists the conditions under which it must not be (other tools, other skills, ambiguous user intent). The "NOT to use" list is just as important as the "to use" list — it prevents over-triggering.

### 2.3 Phases (numbered workflow)

A `## Core Process` or `## Phases` table with 4-7 numbered steps. Each step has a verb (audit, scope, bootstrap, run, verify, materialize) and a one-line description of what happens. This is the procedural backbone the LLM follows.

### 2.4 Common Rationalizations (table)

A two-column table: rationalization (what the LLM might say to skip a step) → reality (why that rationalization is wrong). This is the gbrain `skill-creator` convention. It pre-empts the most common excuses.

### 2.5 Red Flags

A bulleted list of *observable* signals that the skill is being misused or is failing. Example: *"Phase 0 says 'no benchmark' but Phase 1 chose `improve`."*. Each red flag is something the user (or the LLM) can check from the run's output.

### 2.6 Verification

A checkbox list of how to confirm the skill ran correctly. Example: `[ ] Each phase prints its verb on stdout`. This is the contract between the skill and the user.

### 2.7 Anti-Patterns

A bulleted list of *what NOT to do* when writing or running the skill. Example: *"Skip Phase 5 to ship faster"* — no, materialize is what makes the run auditable. Anti-Patterns are forward-looking; Red Flags are backward-looking.

### 2.8 Output Format

A description of what good output looks like for this skill. For skill-forge, the output is a 6-phase transcript ending in `audit-report.md` and either `best.md` or `proposed.md`. A skill that doesn't describe its output format leaves the user guessing what success looks like.

### 2.9 When it fails

An error-handling section. For skill-forge, the failure modes are documented in the foundry (§ 7) — the SKILL.md section is a short pointer to the foundry. For a self-contained skill, this section enumerates the failure modes inline.

### 2.10 Tools used (in body AND frontmatter)

The `tools:` field in frontmatter declares the gbrain tools the skill uses (`search`, `list_pages`, `read`, `write`, `edit`, etc.). The body should describe how each tool is used, with concrete examples.

---

## 3. Progressive disclosure (file structure)

The principle: **frontmatter is always loaded; body is loaded on demand; references are loaded only when needed**. The file structure should support this.

```
skill-forge/
├── SKILL.md                # frontmatter (always loaded) + lean body (loaded on demand)
├── README.md               # the project-level landing page (GitHub homepage)
├── docs/
│   ├── foundry-overview.md  # load on first trigger (~3000 tokens: install / CLI / Phase 5 / failure catalog)
│   ├── foundry-details.md   # load only when troubleshooting (~4500 tokens: phases / gbrain / judges / safety)
│   ├── foundry.md           # redirect (kept one release for backwards-compatible links)
│   ├── DEPLOYMENT.md        # local deployment notes (loaded only when cc-haha setup breaks)
│   └── PRINCIPLES.md        # this file (loaded when a skill is being authored or audited)
├── references/              # heavy docs loaded on demand
│   ├── hero-queries.md      # eval rubric for the resolver
│   └── token-budget.md      # index/load/runtime tier checklist
├── scripts/                 # executable code (loaded only when actually running the skill)
└── tests/                   # test suite (loaded only by maintainers)
```

A `SKILL.md` body under ~150 lines is the sweet spot. Anything longer belongs in `docs/` or `references/`. The `description` in frontmatter should be loadable in a single screen; if it doesn't fit, it's a sign the skill is doing too many things and should be split.

---

## 4. Triple-judge (skill-forge specific)

Every skill run goes through three independent gates:

| Gate | Question | Implementation |
|---|---|---|
| Deterministic | Does the candidate match the structural rules? (frontmatter valid, name regex, etc.) | `frontmatter.load()` + `_deterministic_trace()` |
| LLM rubric | Does the candidate *intend* the right thing? (semantic match of frontmatter to body) | `llm_call(prompt)` returning a score |
| Spot check | Does the candidate *behave* correctly? (manual or rule-based verification) | `--spot-check N` |

Per RULING-1: **absent rubric ≠ failure**. If `llm_call=None`, the rubric is SKIPPED (not defaulted to 0.5 or any neutral). The deterministic + spot gates still run. This prevents honest local-only runs from being marked as failures just because there's no LLM available.

---

## 5. Safety principles

### 5.1 Bundled skills are read-only

A skill installed via a marketplace plugin (e.g. `gbrain:skill-optimizer` at `~/.claude/plugins/marketplaces/gbrain/plugin/skills/skill-optimizer/`) is treated as read-only by the local agent. skill-forge detects this via `is_bundled()` and writes the candidate to `proposed.md` next to the bundled `SKILL.md`, never to the bundled `SKILL.md` itself.

### 5.2 SHA-baseline race check

`.skill-forge-baseline.json` records the SHA of `SKILL.md` from the last successful run. The next run compares. If the file drifted (someone edited it manually between runs), the bundled path **refuses with exit `3`**, the non-bundled path **warns and proceeds**. `SKILL.md` is never overwritten regardless.

### 5.3 Fail-open on missing `install.json`

If `~/.gbrain/install.json` doesn't exist or is unreadable, `is_bundled()` returns `False` (everything is treated as non-bundled). This is defence-in-depth, not a lock — the user is expected to operate on a scratch copy of any skill, marketplace-installed or not.

### 5.4 Distinct exit codes (0 / 2 / 3)

- `0` — accept (audit-report.md + best.md or proposed.md written; baseline updated)
- `2` — refuse (audit-report.md written with `verdict: refuse`; no candidate; no baseline update)
- `3` — race (a bundled install's `SKILL.md` SHA drifted between audit and materialize; no write)

CI can route these three distinctly. A `3` is a deployment signal, not a code signal.

---

## 6. MECE (Mutually Exclusive, Collectively Exhaustive)

The set of installed skills should be MECE across user intents:
- **Mutually Exclusive** — no two skills should claim the same triggers
- **Collectively Exhaustive** — every common user intent should be covered by some skill

`skill-forge` does not enforce MECE at runtime (it operates on one skill at a time). MECE is a **creation-time** concern handled by `gbrain:skill-creator`. skill-forge's contribution to MECE is: when auditing a target skill, the `triggers:` list in frontmatter is checked for emptiness (a skill with no triggers cannot participate in MECE at all).

---

## 7. What skill-forge does NOT do (negative space)

- **skill-forge does not write skills.** It audits, judges, and materializes. The author still writes the body.
- **skill-forge does not check MECE at runtime.** That's `gbrain:skill-creator`'s job at creation time.
- **skill-forge does not run without a target skill.** `--skill <path>` is required.
- **skill-forge does not bundle an LLM.** The LLM rubric is optional; the deterministic + spot gates work without one (RULING-1).

---

## 8. Enforcement summary

| Principle | Enforced in code? | Where |
|---|---|---|
| Concise description (≤ 1024) | Yes (warning) | `validate_skill_frontmatter()` |
| Block scalar for special chars | Yes (PyYAML already handles) | `load()` |
| Explicit `triggers:` list | Yes (warning if empty) | `validate_skill_frontmatter()` |
| `mutating:` boolean | Yes (warning if missing) | `validate_skill_frontmatter()` |
| `name:` kebab-case | Yes (warning if bad) | `validate_skill_frontmatter()` |
| `brain_first:` declared | No (not validated; convention only) | — |
| `when_to_use:` declared | No (not validated) | — |
| `version:` semver | No (not validated) | — |
| Iron Law (one bolded line) | No (structural) | — |
| When to use / NOT to use | No (structural) | — |
| Phases (4-7 steps) | No (structural) | — |
| Common Rationalizations | No (structural) | — |
| Red Flags | No (structural) | — |
| Verification | No (structural) | — |
| Anti-Patterns | No (structural) | — |
| Output Format | No (structural) | — |
| When it fails | No (structural) | — |
| Progressive disclosure | No (convention only) | — |
| Triple-judge (RULING-1) | Yes (built into `judge_triple.py`) | `judge()` |
| Bundled read-only | Yes (`is_bundled()`) | `bundle.py` |
| SHA-baseline race check | Yes (`race()`) | `baseline_log.py` |
| Fail-open `install.json` | Yes (`is_bundled()`) | `bundle.py` |
| Distinct exit codes (0/2/3) | Yes (in `run.py` `main()`) | `run.py` |
| MECE | No (creation-time concern) | — |

Principles marked "No (structural)" are checked by `audit.py` evidence collection but not enforced as a hard error — a skill that omits an `Anti-Patterns` section is suboptimal, not broken.

---

## 9. References

- `analysis-2026-10-14.md` — the v0 spec that started the project
- `docs/foundry-overview.md` — load-on-first-trigger heavy reference (~3000 tokens)
- `docs/foundry-details.md` — troubleshooting heavy reference (~4500 tokens), especially § 0 (architecture) and § 5 (RULING-8)
- `docs/foundry.md` — redirect to overview + details (kept one release for backwards-compat)
- `docs/DEPLOYMENT.md` — local Claude-skills deployment backup
- `references/hero-queries.md` — the eval rubric for this skill
- `references/token-budget.md` — the index/load/runtime tier checklist
- gbrain:skill-creator — the source of the gbrain conformance conventions
- gbrain:skill-optimizer — the bundled v0 of this skill, kept for back-compat

---

## 10. Gotcha flywheel (maintenance process)

Skills are not write-once documents. The Perplexity article prescribes a flywheel that turns observed failures into higher-value content:

| Symptom | Action |
|---|---|
| Agent fails at X | Add a gotcha for X in the target skill's Red Flags / Anti-Patterns |
| Agent loaded the wrong skill | Tighten the skill's `description`, add negative evals |
| Agent should have loaded, didn't | Add keywords to `description`, add positive evals |
| System prompt changed | Check for skill conflicts or duplicates |
| New skill added | Re-run evals on existing skills (action at a distance) |

skill-forge's contribution to this flywheel is the **audit-report.md "Suggested gotchas" section**: when the audit returns a non-trivial verdict, the materialize step emits 1-2 gotcha suggestions for the target skill's author. Without that feedback loop, the flywheel has no fuel and skill-forge's gotchas become a frozen snapshot instead of a living artifact.

## 11. Action at a distance

Changing one skill's `description` can break another skill's recall. Each `description` occupies the agent's index-token budget (~100 tokens/skill); adding or rewording a description shifts the embedding space and the resolver's short-circuit matching. A skill that worked yesterday may stop matching today because a sibling skill's description grew to claim overlapping intent.

**Mitigations:**

- Keep `description` ≤ 50 words (PRINCIPLES.md § 1.1 + validator check).
- Avoid trigger phrases that two skills could both claim.
- When adding a new skill, re-run hero queries on existing skills to detect drift.
- Track skill inventory (`skills`) in a registry, even if informally.

skill-forge does not enforce MECE at runtime (it operates on one skill at a time). MECE is a **creation-time** concern handled by `gbrain:skill-creator`.

## 12. Token budget (index / load / runtime)

| Tier | Content | Budget | When paid |
|---|---|---|---|
| Index | `name` + `description` per skill | ~100 tokens/skill | Every session, every user, always |
| Load | full `SKILL.md` body | ~5,000 tokens (target) | When the skill is triggered |
| Runtime | files in `scripts/` `references/` `assets/` | unlimited | Only when the agent actually reads a file |

Consequences for the skill author:

- **Index** is always paid. A vague or duplicate description is a hidden cost on every other skill. Keep `description` terse and unique.
- **Load** is paid on each trigger. The body should be lean; heavy detail belongs in `references/`.
- **Runtime** is paid per file read. Large assets (e.g. a 1,945-section code book) are fine as long as the agent only opens them on demand.

skill-forge's own `SKILL.md` is ~700 words; heavy reference lives in `docs/foundry-overview.md` (overview, loaded on first trigger) and `docs/foundry-details.md` (details, loaded only when troubleshooting).
