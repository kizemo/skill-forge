# Token budget tiers

**Purpose:** Perplexity's three-tier token model in detail. The
`PRINCIPLES.md § 12` summary table is the TL;DR; this file is the
author-side checklist with concrete numbers, common pitfalls, and
mitigation patterns.

---

## The three tiers

| Tier | Content | When paid | Perplexity guidance |
|---|---|---|---|
| **Index** | `name` + `description` per skill | Every session, every user, always | ~100 tokens/skill |
| **Load** | full `SKILL.md` body | When the resolver triggers the skill | ~5,000 tokens (target) |
| **Runtime** | files in `scripts/` `references/` `assets/` | Only when the agent actually reads a file | unlimited |

The tiers are independent and additive. An agent with 20 installed
skills pays 20 × ~100 = ~2,000 tokens in index fees before doing any
work, even if it never invokes a single one.

---

## Index tier (~100 tokens / skill)

**What it costs:** every session, every user. A description that grows
from 30 words to 60 words doesn't help much but costs every other
skill's context real estate.

**Common pitfalls:**

- **Trigger duplication.** Listing the same phrases in `description`,
  `triggers:`, and `when_to_use:` triples the cost without tripling the
  match rate.
- **Vague self-introduction.** "This skill helps you with skill things."
  The resolver cannot short-circuit on it.
- **Workflow summary.** "Loads X, runs Y, writes Z." Workflow is body
  material; the description is the routing phrase.
- **Mismatched prefix.** Perplexity: descriptions should start with
  "Use when" or "Load when". `validate_skill_frontmatter()` warns on
  the absence.

**Author checklist (per description):**

- [ ] Starts with "Use when" or "Load when"
- [ ] ≤ 50 words
- [ ] ≤ 1024 characters (the looser cap, kept for backwards compat)
- [ ] No trigger duplication with `triggers:` or `when_to_use:`
- [ ] Targets user intent, not workflow

## Load tier (~5,000 tokens / body)

**What it costs:** every time the skill triggers. Body content is
loaded into the agent's active context, displacing other content.

**Common pitfalls:**

- **Inline tutorials.** The Pascal test ("would the agent fail without
  this?") catches most of these.
- **Reference material in body.** Heavy detail belongs in
  `references/`, not body. Skill-forge itself moved Output Format /
  Anti-Patterns / When it fails / Tools Used to `docs/SKILL_REFERENCE.md`
  for this reason.
- **Single-file bloat.** A 1,945-section reference document does not
  belong in a single SKILL.md body — split by sub-skill (e.g. 300
  topics → 20 domains → 15 subtopics → 1).

**Author checklist (per body):**

- [ ] ≤ 1,000 words (skill-forge's `wc -w SKILL.md` gate)
- [ ] Pascal test applied to every sentence
- [ ] Heavy detail moved to `references/` or external files
- [ ] Cross-references use relative paths, not full content embeds

## Runtime tier (unlimited, but lazy)

**What it costs:** only when the agent reads a file. As long as the
agent is selective about file reads, runtime is unbounded.

**Common pitfalls:**

- **Eager loading.** A skill that says "Read all files in `assets/`
  before responding" defeats the lazy-loading contract.
- **Hidden coupling.** Cross-references that pull in another file's
  full body in a single Read call can quietly exceed the load budget.
- **Misdirected assets.** Putting JSON schemas or large data tables in
  `SKILL.md` body instead of `assets/schema.json` bloats the load tier.

**Author checklist (per runtime file):**

- [ ] File is only read on demand (no auto-load at trigger)
- [ ] Path is announced before it's read (let the agent choose)
- [ ] Heavy data tables live in `assets/`, not body

---

## Mitigation patterns

| Symptom | Mitigation |
|---|---|
| Index tier too high | Tighten `description` to ≤ 50 words; remove duplicate trigger phrases |
| Load tier too high | Move heavy content to `references/`; apply Pascal test |
| Runtime tier bloated | Add explicit "read only X" guidance in body; never auto-load |
| Hub-and-spoke missing | Add `references/` and/or `assets/` directories; `validate_skill_body()` warns when body > 150 lines without them |
| Description > 50 words | The `validate_skill_frontmatter()` word-cap check (50-word warning) |

## Cross-references

- `PRINCIPLES.md` § 12 — the TL;DR table.
- `SKILL.md` — the body itself (load tier).
- `docs/foundry-overview.md` — the "load on first trigger" page (load
  tier, but lighter than the full `foundry-details.md`).
- `references/hero-queries.md` — eval set, indexed by intent.