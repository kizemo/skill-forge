# Skill Design Rubric — the 9 standards from Perplexity's agent-skills guide

**Source:** *Designing, Refining, and Maintaining Agent Skills at Perplexity*
(research.perplexity.ai, 2026-05-01) + the zh-Hans translation.
**Extraction method:** book-to-skill, Mode 3 (generate from prior analysis).
**Purpose:** the scoring rubric `skill-forge` audits other skills against.

Distilled with the author's own formulations preserved. Every number below is
the article's, not an estimate.

---

## 1. The three token tiers

| Tier | Content | Budget | When paid |
|---|---|---|---|
| **Index** | `name` + `description` of each non-hidden skill | **~100 tokens / skill** | Every session, every user, always |
| **Load** | the full `SKILL.md` body | **~5,000 tokens** | When the skill is loaded |
| **Files** | `scripts/`, `references/`, `assets/` | unlimited | Only when the agent reads a file |

> "Context is expensive. Maximum signal per token."
> "Runtime may be 20,000 tokens, or it may be 0 tokens."
> "A thread may load 3-5 skills at once, and the costs stack."

**The index tier is the one that hurts most** — it is paid by every user of
every session, whether or not the skill is ever invoked, and it stacks across
the whole installed portfolio.

## 2. Description is a routing trigger, not an introduction

- Prefix: **"Load when…"** (the article's wording; "Use when" is a common equivalent).
- Length: **≤ 50 words**.
- Say **when to load**, not what the skill does. The user intent, not the workflow.
- **2-3 examples usually cover 80/20.** Not a keyword dump.
- The description must let a model decide three things: when to load, when NOT to load, and how it differs from an adjacent skill.

> "A bad description describes what the Skill does."
> "A good description says when the agent should load the Skill."
> "Every sentence has to earn its place."

## 3. What lives where

| Location | Holds | Must not hold |
|---|---|---|
| `SKILL.md` | frontmatter, core instructions, goals + constraints, a few high-value gotchas, **the conditions for reading attached files**, decision info needed immediately | what the model already knows, long tutorials, heavy reference material, logic a script can do, over-specific command sequences |
| `references/` | heavy docs needed only under a condition, special cases, domain detail, error-code/scenario-specific notes | content needed on every run |
| `scripts/` | deterministic logic the agent would otherwise reconstruct each time | — |
| `assets/` | output templates, schemas, fixed content to copy and fill | — |
| `config.json` | first-run user configuration, reusable personal settings | — |

> "You are not writing a sequence of commands."
> "Write the goal and constraints, and let the model plan."
> "Give the model code to compose, not logic to reconstruct."

The body must state the read condition explicitly: *"Read api-errors.md if API returns non-200."*

## 4. Gotchas and anti-patterns

- Naming that works: **`Gotchas`**, **`Common pitfalls`** (body sections);
  **`SPECIAL_CASES.md`**, **`FORMATTING.md`** (on-demand files).
- Every skill should keep **at least one** `Gotchas` / `Common pitfalls` section.
- Start with **2-3** and grow it from real failures. Append-mostly.
- Write each gotcha as: title names the mistake ("Never…", "Avoid…", "Gotcha:…") →
  state the consequence → give the correct action → state the exception →
  resolve exactly one reproducible failure.

> "Gotchas are extremely high-value content."
> "Start thin, grow as the agent fails."

Anti-patterns the article names explicitly: restating standard steps the model
already does; dressing command sequences up as workflows; repeating rules the
system prompt already carries; writing general knowledge that is easy to
explain; constraining the model with absolute flows that block exception
handling; adding a skill without testing neighbouring skills' routing.

> "If it's easy to explain, the model already knows it. Delete it."

## 5. The Pascal test

> "Without this instruction, would the agent get it wrong?"

If no, the sentence cannot pay for itself. Apply it to every word of the
description and every sentence of the body. Delete anything that is merely
decorative, merely slogan, or merely present because it looked complete.

## 6. When a skill should not exist

- The agent gets it right without special context.
- The skill only restates commands the model already knows.
- The content changes faster than the team can maintain it.
- It serves only a **5% edge case** — make that a reference, not a skill.

> "If it's only a 5% edge case, don't make it a Skill."

Conversely, a skill earns its place when the agent errs without special
context, when consistency across runs matters, when the knowledge is not in
training data, or when the domain needs judgment.

## 7. Keeping the body lean — the ten rules

1. Cap the body at ~5,000 tokens.
2. Delete what the model already knows.
3. Goals + constraints instead of command sequences.
4. Conditional content → `references/`.
5. Deterministic logic → `scripts/`.
6. Templates + schemas → `assets/`.
7. Keep only gotchas born of real failures.
8. Pascal-test every sentence.
9. **Go back periodically and delete sentences that are no longer needed.**
10. If it is a 5% edge case, it is a reference, not a skill.

Short skills are harder to write; skills that are quick to write tend to be too
long, or not needed at all.

## 8. Evals — three kinds, not one

**Write the evals before the skill.**

Hero queries: 5-10 per skill, drawn from real user phrasing, containing both
positives and negatives. Maintain a neighbouring-confusion pool. Negatives
correct more than positives do. Always test that adjacent-but-different skills
do **not** load.

Three eval types:

| Type | Checks |
|---|---|
| **Skill-loading test** | precision, recall, forbidden loads |
| **Progressive-loading test** | does the agent actually read the attached files the body told it to read? |
| **End-to-end completion** | run the full agent loop, judge with an LLM against a rubric |

**Description change protocol:** change **1-2 words at a time**, establish a
baseline first, run the evals after each step, never rewrite wholesale.
Adding a skill can break pre-existing skills — re-run their evals.

Run evals across model families; Sonnet and GPT behave differently on skill
routing.

## 9. Maintenance flywheel

| Observation | Action |
|---|---|
| Agent failed at X | append a gotcha for X |
| Wrong skill loaded | tighten the description, add a negative eval |
| Right skill not loaded | add keywords, add a positive eval |
| System prompt changed | check for conflicts and duplicates |
| New skill added | re-run evals on existing skills |

Append-mostly: failures become gotchas; the description is not touched
without eval evidence.

**Pre-release checklist:** positives load correctly · negatives never
false-recall · forbidden-load check passes · progressive file reads match the
stated conditions · end-to-end meets the rubric · ship as one change set with
its eval set.

## 10. Structural conventions

```
skill-name/
├── SKILL.md        # name + description are mandatory; name == directory name
├── scripts/
├── references/
├── assets/
└── config.json
```

- `name` must equal the directory name exactly, lowercase, hyphens allowed.
- `depends:` expresses skill dependency layers; `metadata:` carries review/eval state.
- Large domains use **multi-level nesting** to cut the selection load: 1,945
  tax sections in one folder performed *worse than no skill at all*; selecting
  1 of 20 domains, then 1 of ~15 topics within it, was markedly better.

---

## 11. Scoring sheet (the rubric itself)

| # | Standard | Automated? | Where it should be enforced |
|---|---|---|---|
| 1 | Index tier ≤ ~100 tokens | **yes** | validator: measure `name`+`description` tokens |
| 2 | Description ≤ 50 words, "Load when"/"Use when", no trigger dump | **yes** | validator |
| 3 | No trigger duplication across description / triggers / when_to_use | **yes** | validator |
| 4 | Body ≤ ~5,000 tokens | **yes** | validator: token estimate, not `wc -w` |
| 5 | Body states read-conditions for attached files | **yes** (heuristic) | validator: require a "Read … if …" table |
| 6 | ≥ 1 gotcha / pitfalls section | **yes** | validator (exists) |
| 7 | Conditional content lives in `references/` | **yes** (heuristic) | validator: long body with no `references/` → warn |
| 8 | Pascal test per sentence | no | manual review |
| 9 | Hero queries with positives + negatives | no | process: `references/hero-queries.md` |
| 10 | Progressive-loading eval | no | process: benchmark must contain "read the file" tasks |
| 11 | Description change protocol (1-2 words + baseline) | no | process |
| 12 | Evals across model families | no | process |
| 13 | "5% edge case → reference, not skill" | no | creation-time gate |
| 14 | Multi-level nesting for huge domains | no | design guidance |

**Rows 1-7 are the automatable half — and they are the half that actually
governs token cost.** A validator that implements rows 1-7 catches the bloat
before it ships.
