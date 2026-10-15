# Audit: skill-forge vs. Perplexity skill-writing principles

**Date:** 2026-10-15
**Sources:**
- *如何设计、优化与维护 AI Agent Skills(译)* — translation of Perplexity's *Designing, Refining, and Maintaining Agent Skills at Perplexity* (research.perplexity.ai, 2026-05-01)
- *Skill 不是文档,是上下文:Perplexity 内部手册给 Claude 用户的 5 条*(aiec.fun secondary)

This audit answers two questions:

1. **Does `skill-forge` itself follow these principles?** (skill-forge AS a skill)
2. **Does `skill-forge` enforce these principles when writing/auditing other skills?** (skill-forge AS a tool, via `validate_skill_frontmatter` and `audit()`)

The two questions are independent. A good auditor is not necessarily a good auditee, and vice versa. Both axes need to be checked.

---

## 1. Principles extracted from the articles

### 1.1 The 5 "Zen of Skills" principles (vs. Python Zen)

| # | Python Zen | Skills Zen (Perplexity) | Token-budget implication |
|---|---|---|---|
| 1 | Simple is better than complex | **A Skill is a folder, not a file. Complexity is the feature.** | Hub-and-spoke structure; the directory IS the skill. |
| 2 | Explicit is better than implicit | **Activation is implicit pattern matching. Progressive disclosure.** | description is always loaded (~100 tokens/skill); body loaded on demand (~5,000); files loaded when read (unlimited). |
| 3 | Sparse is better than dense | **Context is expensive. Maximum signal per token.** | "Skills with a lot of fluff will almost certainly degrade other Skills as well as overall agentic capabilities." |
| 4 | Special cases aren't special enough to break the rules | **Gotchas ARE the special cases (they're the highest-value content).** | Start with a thin body; grow only on observed failures. |
| 5 | If the implementation is easy to explain, it may be a good idea | **If it's easy to explain, the model already knows it. Delete it.** | The Pascal test: "without this instruction, would the agent fail?" If no, delete. |

### 1.2 The "5 counterintuitive lessons" (from the secondary article)

1. **Description is a routing trigger, not a self-introduction.** Start with "Load when…", target ≤ 50 words, write user intent not workflow.
2. **Skill is a folder, not a file.** Hub-and-spoke: SKILL.md is the hub, scripts/ references/ assets/ are spokes.
3. **Gotchas are the highest-value content.** Update cycle: agent fails → add gotcha → tighten description. Don't write command sequences; write goals + constraints.
4. **Write evals before the skill.** Hero queries with positive + negative + neighbor-confusion examples. Action at a distance: changing one skill's description can break another skill's recall.
5. **Each skill is a tax.** Every session, every user pays the token cost — even when they never invoke the skill. **The user shouldn't have to pay for content the model already knows.**

### 1.3 Token budget tiers (explicit numbers)

| Tier | Content | Budget | When paid |
|---|---|---|---|
| Index | name + description, per skill | ~100 tokens/skill | Every session, every user, always |
| Load | full SKILL.md body | ~5,000 tokens (target) | When the skill is triggered |
| Runtime | files in scripts/ references/ assets/ | unlimited | Only when the agent actually reads a file |

### 1.4 The Pascal test

> "Without this instruction, would the agent fail?" If no, the sentence is **deleteable**. Every retained sentence must be a *decision signal* or a *constraint*, not a *tutorial*.

### 1.5 The gotcha flywheel

| Symptom | Action |
|---|---|
| Agent fails at X | Add a gotcha for X |
| Agent loaded the wrong skill | Tighten description, add negative evals |
| Agent should have loaded, didn't | Add keywords to description, add positive evals |
| System prompt changed | Check for skill conflicts or duplicates |
| New skill added | Re-run evals on existing skills (action at a distance) |

### 1.6 Hub-and-spoke file structure

```
my-skill/
├── SKILL.md          # frontmatter + core instructions (≤ 5,000 tokens)
├── scripts/          # code the agent runs (not "learns from")
├── references/       # heavy docs, loaded on demand
├── assets/           # templates, schemas, data
└── config.json       # first-run user config
```

For complex skills (e.g. tax code with 1,945 sections), use multi-level nesting to reduce the agent's selection load: 300 topics → 20 domains → 15 subtopics → 1.

---

## 2. Axis 1: `skill-forge` AS a skill

### 2.1 File structure compliance

| Perplexity norm | skill-forge reality | Status |
|---|---|---|
| `SKILL.md` (frontmatter + body) | exists, 846 words | ✓ |
| `scripts/` | exists (`scripts/audit.py`, `bootstrap_benchmark.py`, `judge_triple.py`, `router.py`, `run.py`, `_legacy_init_skill.py`, `_lib/{frontmatter,sha,baseline_log,bundle}.py`) | ✓ |
| `references/` | does **not** exist | **GAP — heavy reference lives in `docs/foundry.md` (670 lines) which is not under the skill directory** |
| `assets/` | does **not** exist | **GAP** |
| `config.json` | does **not** exist (and skill-forge genuinely has no first-run user config — every flag is on the CLI) | n/a — N/A by design |
| `tests/` | exists (76 tests) | ✓ — analogous to "scripts" but tests aren't part of the agent's runtime |

**The `references/` gap is real.** When the LLM needs detail on, say, the bundled-safety model or the SHA-baseline race semantics, it has to read `docs/foundry.md` (which is outside the skill's install directory). For a user-scope junction at `~/.claude/skills/skill-forge/`, the `docs/` subdir is reachable, but for a marketplace install via the `gbrain` plugin, the install path is `gbrain/plugin/skills/skill-forge/` and the `docs/` subdir is bundled *if* the marketplace ships it — which it does (because the v0 was a pure markdown recipe; ours has the docs baked in). **Verdict: functional but not by-design aligned with the hub-and-spoke norm.**

### 2.2 Description compliance

Perplexity: **"Load when [user intent]."** ≤ 50 words. User intent, not workflow summary.

skill-forge frontmatter description:
> "Use when a skill is not producing the quality you want, when you want to bootstrap a benchmark for a new skill, when an existing skill needs measurable improvement against a frozen baseline, or when retiring a skill that has outlived its purpose."

- Starts with "Use when …" — good (matches the spirit, not the literal "Load when" pattern; "Use when" is a valid synonym).
- Word count: ~58 words. **Slightly over Perplexity's 50-word target.**
- Triggers are repeated at the end of the description (inline list), AND repeated again in the `triggers:` list, AND a third time in the `when_to_use` field. **Triple duplication is wasteful by the article's standard** — the description should be "use when", the `triggers:` list should be the routing phrases, and the `when_to_use` field should be the marketplace short summary. Repeating the same phrases three times violates the "sparse is better than dense" principle.

**Status: PARTIAL — meets the "use when" prefix, but exceeds word budget and has trigger duplication.**

### 2.3 Body compliance (Pascal test applied)

Apply "without this instruction, would the agent fail?" to each sentence in `SKILL.md`:

| Section | Sentence | Fails Pascal? | Verdict |
|---|---|---|---|
| Iron Law | "Violating the letter of these rules is violating the spirit of these rules." | NO — the agent would NOT fail without this. | **DELETE per Perplexity** (but: this is convention; see § 2.4) |
| What this is | "A meta-skill that turns 'this skill could be better' into a measured, verifiable improvement — or an honest decision to retire it." | YES — this is the position statement the agent needs. | KEEP |
| What this is | "It does not edit skills directly" | NO — obvious from the position statement. | **DELETE per Pascal** |
| What this is | "it routes work to `skill-creator` (create/edit) and `gbrain:skill-optimizer`" | YES — concrete routing info the agent needs. | KEEP |
| When NOT to use | 3 bullets | YES — negative examples. | KEEP |
| Core Process | 6-row table | YES — the pipeline stages are the contract. | KEEP |
| Default behavior | "Bundled skills get `proposed.md` only; the bundled `SKILL.md` is never touched." | YES — load-bearing safety claim. | KEEP |
| Common Rationalizations | 4-row table | YES — gotchas. | KEEP (this is the article's "highest-value content" pattern) |
| Red Flags | 4 bullets | YES — observable signals. | KEEP |
| Verification | 5 checklist items | YES — contracts. | KEEP |
| v2 specifics | 6 sub-bullets | MOSTLY — but "Skip optional deps gracefully" is tutorial tone, ~25 words, easily deletable per Pascal. | TRIM |
| Reference link | "Output Format, Anti-Patterns, When it fails, and Tools Used live in `docs/SKILL_REFERENCE.md` …" | NO — the agent would not fail without it; it's a navigation aid. | **DELETE per Pascal** (or move to a body element that doesn't load on every invocation) |

**Estimated body tightening: 846 words → ~700 words if Pascal test is applied rigorously. Saves ~146 words / ~200 tokens.**

### 2.4 Where `skill-forge`'s SKILL.md disagrees with Perplexity and the right answer

Two of the gaps the Pascal test flags are actually wrong calls under closer reading:

1. **The Iron Law** ("Violating the letter …") — Perplexity's Pascal test says delete, but this sentence is **the kind of imperative override rule that Perplexity's example table flags as Iron Law**. The article's own example has an Iron Law ("If it's easy to explain, the model already knows it. Delete it."), so the convention is: an Iron Law is **not subject to the Pascal test** — it's a rule-level directive, not a tutorial. KEEP.

2. **The verification checklist** — Perplexity doesn't address this directly, but the gbrain:skill-creator convention (which skill-forge's own lineage follows) treats verification as a contract. The Pascal test should be applied **within** each checklist item, not to the checklist as a whole. The items pass Pascal: "each phase prints its verb on stdout" — agent fails without it (silent phases). KEEP.

### 2.5 Token budget check (5,000-token body cap)

| Asset | Word count | Token estimate (×1.3) |
|---|---|---|
| `SKILL.md` (after v0.2.0 + SKILL_REFERENCE.md split) | 846 | ~1,100 |
| `docs/SKILL_REFERENCE.md` (load only on demand) | ~600 | ~780 |
| `docs/foundry.md` (load only on demand) | ~5,000 | ~6,500 (over budget!) |
| `docs/PRINCIPLES.md` (load only on demand) | ~570 | ~740 |

`SKILL.md` is well under the 5,000-token cap. **`docs/foundry.md` is over the cap by ~1,500 tokens** — this is the "fluff degrades other skills" warning the article issues. A 6,500-token `foundry.md` could squeeze the agent's other-skill recall budget.

**Recommended split:** `foundry.md` should be split into `foundry-overview.md` (~3,000 tokens, the "load on first trigger" page) and `foundry-details.md` (the rest, loaded only when troubleshooting).

### 2.6 Gotcha flywheel — process gap

The article's gotcha flywheel requires **process**:
1. Agent fails → add gotcha
2. Tighten description based on observed failures
3. Re-run evals

skill-forge's SKILL.md has gotchas (`Common Rationalizations`, `Red Flags`, `Anti-Patterns`), but there's **no process** for growing them from observed failures. A skill that's "frozen at v0.2.0 gotchas" is a snapshot, not a flywheel.

**GAP — skill-forge should have a CONTRIBUTING.md (or in `docs/PRINCIPLES.md`) describing the gotcha flywheel. The audit-report.md output is the natural place to record "agent failed at X, candidate suggestion is to add a gotcha" — currently no such feedback loop exists.**

---

## 3. Axis 2: `skill-forge` AS a tool (`validate_skill_frontmatter` and `audit()`)

The validator's job is to enforce Perplexity's principles on **other** skills. Per-principle check:

| Perplexity principle | Currently enforced? | Where | Gap |
|---|---|---|---|
| Description is a routing trigger | PARTIAL | `validate_skill_frontmatter` checks "description: present" | does NOT check `description` starts with "Use when" / "Load when" |
| Description ≤ 50 words | NO | checks ≤ 1024 **chars** (a much looser constraint) | **per-character vs per-word**; Perplexity's 50-word limit is *stricter* than the 1024-char cap on average (50 words ≈ 300-400 chars); the validator accepts descriptions up to 3× the recommended length |
| Triggers: ≥ 3 concrete phrases | YES | `validate_skill_frontmatter` (warning if < 3) | aligned |
| Name is lowercase kebab-case | YES | `validate_skill_frontmatter` (warning if not) | aligned |
| `mutating:` boolean | YES | aligned | aligned |
| `brain_first:` declared | YES | aligned | aligned |
| `when_to_use:` declared | YES | aligned | aligned |
| `version:` semver | YES | aligned | aligned |
| Gotchas section in body | NO | n/a | **GAP — no body validation** |
| Hub-and-spoke structure (presence of `references/`, `assets/`) | NO | n/a | **GAP** |
| Pascal test per sentence | NO (semantic) | n/a | **cannot automate reliably** |
| Skill name matches dir name | NO | `validate_skill_frontmatter` checks name format only | **GAP — easy to add** |
| `evals/` directory present | NO | n/a | **GAP — recommended but not blocking** |
| Action at a distance (cross-skill description conflicts) | NO | n/a | **GAP — hard to automate; should be a process note in PRINCIPLES.md** |
| No command sequences in body (write goals + constraints) | NO (semantic) | n/a | cannot automate reliably |
| Skill invocation pattern (per the article, descriptions should match user intent phrases) | NO | n/a | hard to automate; covered indirectly by `triggers:` check |

**Summary:** the validator covers 6 of the 12 automatable principles. The 6 not covered are: routing-trigger prefix, 50-word cap, gotchas section, hub-and-spoke structure, dir-name match, and evals/ directory.

---

## 4. Gap analysis (consolidated)

### 4.1 High-priority gaps (real, automatable, low risk)

| # | Gap | Effort | Risk | Fix |
|---|---|---|---|---|
| 1 | Description-prefix check (must start with "Use when" / "Load when") | 5 lines | none — adds a warning | Add to `validate_skill_frontmatter` |
| 2 | Description word cap (≤ 50 words) | 3 lines | none | Add to `validate_skill_frontmatter` |
| 3 | Dir-name matches frontmatter name | 5 lines | none | Add a new check (loads the skill's directory, compares `dir.name` to `fm["name"]`) |
| 4 | Body has a gotcha-style section | 5 lines regex | low — could false-positive on "Notes" sections with similar words | Add to validator: regex against the body text for `## .*[Gg]otcha|## .*[Pp]itfall|## .*[Rr]ationaliz|## .*[Ff]ail` |
| 5 | Trim `SKILL.md` per Pascal test (846 → ~700 words) | edit | low | Apply Pascal test to "What this is" + remove navigation-aid block + compress v2 specifics |
| 6 | Add `references/` to `skill-forge/` containing hero queries + token-budget notes | create | none | Move `docs/foundry-overview` excerpts there |

### 4.2 Medium-priority gaps (process, harder to automate)

| # | Gap | Effort | Fix |
|---|---|---|---|
| 7 | Add § "Gotcha flywheel" to `PRINCIPLES.md` describing the maintenance process | small (doc) | New section in PRINCIPLES.md |
| 8 | Add § "Action at a distance" warning to `PRINCIPLES.md` | small (doc) | New section in PRINCIPLES.md |
| 9 | Add § "Token budget: index/load/runtime" with explicit thresholds to `PRINCIPLES.md` | small (doc) | New section in PRINCIPLES.md |
| 10 | Split `foundry.md` (~6,500 tokens) into overview + details | medium (doc) | Create `foundry-overview.md` |
| 11 | Add an eval-driven iteration loop (record "agent failed at X" → gotcha suggestion) | medium (process) | Update `audit-report.md` template to include a "Suggested gotchas" section |

### 4.3 Low-priority gaps (semantic, can't reliably automate)

| # | Gap | Note |
|---|---|---|
| 12 | Pascal test (per-sentence "agent fails without this?") | semantic; cannot automate. Document as a manual review step. |
| 13 | No command sequences in body | semantic; "command sequence" is fuzzy. Best enforced via review. |
| 14 | MECE / cross-skill conflict detection | architectural; needs a separate registry, not a per-skill validator. |

---

## 5. Recommendations (ordered by ROI)

1. **Immediate (1-2 hours):** add to `validate_skill_frontmatter` — description-prefix check, 50-word cap, dir-name match. These are 5+3+5 = 13 lines, all automatable, all load-bearing per Perplexity.
2. **Same session:** trim `SKILL.md` per Pascal test (846 → ~700 words). The "Iron Law" stays; the "What this is" reduces from 60 to 40 words; the v2-specifics drops 1 bullet; the reference-link block moves to `SKILL_REFERENCE.md` (which is reference material anyway).
3. **This week:** add `references/` directory to `skill-forge/`, containing:
   - `references/hero-queries.md` — 5-10 example user queries the skill should match (Perplexity's eval-set pattern)
   - `references/token-budget.md` — the 100/5000/unlimited tier breakdown
4. **This week:** add § "Gotcha flywheel", § "Action at a distance", § "Token budget" to `PRINCIPLES.md` so the principles doc references the Perplexity article.
5. **Next sprint:** split `foundry.md` into `foundry-overview.md` (3K tokens) and `foundry-details.md` (3.5K tokens) so the agent only loads the overview unless it needs detail.
6. **Next sprint:** add an "evals" loop — when the audit returns a non-trivial verdict, the materialize step emits a "Suggested gotchas" section in `audit-report.md` so the gotcha flywheel has a structured input.
7. **Never-automate (semantic):** Pascal test, no-command-sequences, MECE. Document in PRINCIPLES.md as manual review steps.

---

## 6. Conclusion

`skill-forge` v0.2.0 is **mostly aligned** with Perplexity's skill-writing principles. The core architecture (hub-and-spoke-with-docs, progressive disclosure, gotcha-first body, RULING-1 missing-rubric-≠-failure) reflects the Perplexity playbook. Three real gaps need closing:

1. **skill-forge's own description** is 58 words (target: ≤ 50) and has triple-duplicated trigger phrases. Easy fix.
2. **The validator** doesn't check the description prefix or the 50-word cap. Easy fix, ~13 lines.
3. **The hub-and-spoke structure** is partial: `references/` doesn't exist; `docs/foundry.md` is over the 5,000-token body cap. Medium fix, file reorganization.

The article's most important contribution is not any single principle — it's the **Pascal test** as a self-review discipline. Apply it to skill-forge's own `SKILL.md` and you save ~150 words. Apply it to every skill you write thereafter. That's the highest-leverage change.

---

## Appendix: 5 principles applied to `skill-forge`'s existing artifacts

For traceability, the table below maps each of Perplexity's 5 principles to the specific files in skill-forge that implement (or should implement) them.

| Principle | Implemented in | Gap |
|---|---|---|
| Description is a routing trigger | `SKILL.md` frontmatter, `validate_skill_frontmatter` | description should start with "Load when" / "Use when" (it does, but the validator doesn't check) |
| Skill is a folder | `skill-forge/` directory with `scripts/` + `tests/` | no `references/` or `assets/` subdir |
| Gotchas are highest-value | `SKILL.md` "Common Rationalizations" + "Red Flags" + `SKILL_REFERENCE.md` "Anti-Patterns" + "When it fails" | section names don't say "Gotchas" — should rename for cross-skill convention |
| Write evals first | (not implemented) | no `evals/` directory; no hero-query registry; no eval-driven iteration loop |
| Each skill is a tax | implicit in description + body brevity | not explicit in PRINCIPLES.md or SKILL.md as a self-aware statement |
| Pascal test | (not applied rigorously) | Iron Law correctly exempted; ~150 words deletable per test |
| Token budget tiers | implicit in `docs/SKILL_REFERENCE.md` split | no explicit 100/5000/unlimited table; `foundry.md` exceeds 5,000 |
| Action at a distance | (not in PRINCIPLES.md) | should be a § "Action at a distance" warning |
| Gotcha flywheel | (not a process) | should be a CONTRIBUTING.md or PRINCIPLES.md § "Maintenance" |
