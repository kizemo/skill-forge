# Audit: skill-forge's token efficiency — why the skills it makes get expensive to invoke

**Date:** 2026-10-25
**Trigger:** user report — skills produced with skill-forge (`evidence-skill`,
`sql-skill`) show large token-consumption spikes at invocation time.
**Rubric:** `docs/SKILL_DESIGN_RUBRIC.md` (the 9 standards extracted from
Perplexity's agent-skills guide, via book-to-skill).
**Method:** measure first, then read the principles, then find the causal
link back to skill-forge.

---

## 1. Measured baseline

Token estimate: CJK ≈ 1 token/char, latin ≈ 1 token/3.5 chars.

| | Index tier (every session) | Load tier (on trigger) | Files tier |
|---|---|---|---|
| **Budget (article)** | ~100 tok / skill | ~5,000 tok | unlimited |
| `evidence-skill` | description 97 tok + `triggers:` 6 entries → **146 tok** ✗ | 2,431 tok ✓ | `references/` 5 files / 13,683 tok ✓ |
| `sql-skill` | description **221 tok** ✗ (2.2×) | **5,500 tok** ✗ (+500 over) | **no `references/` at all** ✗ |
| `skill-forge` (itself) | **178 tok** ✗ | ~1,100 tok ✓ | `docs/` + `references/` ✓ |

`sql-skill` triggers once → ~5,700 tokens of context, for a skill whose real
payload is three chapters of an Obsidian vault.

**Portfolio effect:** 63 user-scope skills are installed on this machine. At
~100-180 tok of index each, that is **~6,300-11,300 tokens paid by every
session**, by every user, whether or not a skill is ever invoked. The article:
*"A thread may load 3-5 skills at once, and the costs stack."*

---

## 2. Rubric scorecard

| # | Standard | skill-forge today | Verdict |
|---|---|---|---|
| 1 | Index tier ≤ ~100 tok | not measured anywhere | ✗ gap |
| 2 | Description ≤ 50 words, "Use when" prefix | **enforced** (gap 1, 2026-10-15) | ✓ |
| 3 | No trigger duplication | not checked; **prescribed by § 1.1 + § 1.3 + § 1.7** | ✗ **causes the bloat** |
| 4 | Body ≤ ~5,000 tok | `wc -w ≤ 1000` — a word gate, not a token gate | ✗ gap |
| 5 | Body states read-conditions for attached files | never required | ✗ gap |
| 6 | ≥ 1 gotcha section | **enforced** (gap 2) | ✓ |
| 7 | Conditional content in `references/` | only "warn if body > 150 lines" | ~ partial |
| 8 | Pascal test per sentence | documented, not enforced (semantic) | ~ by design |
| 9 | Hero queries (positives + negatives) | `references/hero-queries.md` — one skill only | ~ narrow |
| 10 | Progressive-loading eval | absent | ✗ gap |
| 11 | Description change protocol | absent | ✗ gap |
| 12 | Evals across model families | absent | ✗ gap |
| 13 | "5% edge case → reference, not skill" | absent | ✗ gap |
| 14 | Multi-level nesting for huge domains | absent | ✗ gap |

**Fourteen standards. skill-forge enforces two of them. Both enforced ones are
the ones that are cheap to check — and neither of them is the one that governs
token cost.**

---

## 3. The causal chain: skill-forge's own principles manufacture the bloat

This is the heart of the audit. The bloat is not a coincidence of how the two
skills were written; **skill-forge's principles tell an author to write it
that way.**

### F-1 · § 1.1 prescribes a trigger dump inside the description — the index tier is the one every user pays

`docs/PRINCIPLES.md` § 1.1 currently says:

> keep `description` under 1024 characters. Lead with **what** the skill does in
> one sentence, then a `Triggers:` clause with concrete phrases the user might say.

That single sentence is the instruction that produced both symptoms. It tells
the author to **list trigger phrases inside the description**. Then § 1.3 asks
for a separate `triggers:` list, and § 1.7 asks for `when_to_use:`. Three
homes for one set of phrases.

| Skill | description | phrases in description | separate `triggers:` | `when_to_use:` |
|---|---|---|---|---|
| `sql-skill` | 101 words / 221 tok | **19** | 0 | — |
| `evidence-skill` | 40 words / 97 tok | **9** | 6 (same phrases again) | — |
| `skill-forge` | 43 words / 70 tok | 0 | 7 | **7 — 7/7 verbatim duplicates of `triggers:`** |

The 2026-10-15 audit already noticed this ("triple duplication is wasteful by
the article's standard") and then encoded it as a rule. The gap-1 validator
added a 50-word cap on `description` — which is the right cap, and which
`sql-skill` violates by 2×, but the validator only **warns**, and nothing in
the pipeline ever runs the validator on the target before shipping.

**The article is unambiguous**: *"2-3 examples usually cover 80/20"*; *"A good
description says when the agent should load the Skill"*; the index tier is
~100 tokens.

**Fix**
1. `PRINCIPLES.md` § 1.1 → the description carries **1-2 representative
   queries, not a phrase list**. The `triggers:` list is the only phrase list.
   `when_to_use:` becomes a one-line marketplace summary that must **not**
   restate trigger phrases.
2. New validator checks: (a) `description` contains no `Triggers:` clause;
   (b) `when_to_use` shares no phrase with `triggers`; (c) measured
   index-tier cost (description + triggers + when_to_use) ≤ ~120 tokens.
3. `audit()` must run the validator and put the result in the report, so a
   fat index tier is visible before the skill ships.

### F-2 · § 2.8-2.10 mandate three body sections that belong in `references/`

`PRINCIPLES.md` § 2.8 Output Format, § 2.9 When it fails, § 2.10 Tools used
are all specified as **sections of the body**. The article's split is different:
`SKILL.md` holds *"core instructions, goals and constraints, a few high-value
gotchas, the conditions for reading attached files, and decision info that must
be in context immediately"* — and explicitly not heavy reference material.

`skill-forge` itself already does the right thing: it moved exactly those
four sections into `docs/SKILL_REFERENCE.md` during the 2026-10-15 Pascal pass.
**It then failed to prescribe that to the skills it authors.**

**Fix**: § 2.8 / 2.9 / 2.10 become *"live in `references/`; the body states the
read condition"* — plus a new § 2.11 **Progressive loading table**: a
`Read <file> if <condition>` table in the body. That table is the mechanism
the article relies on ("Read api-errors.md if API returns non-200") and it is
also the only way an agent knows what is *not* already in context.

### F-3 · `wc -w ≤ 1000` is not a token gate, and CJK breaks it

`sql-skill`'s body is 408 lines / 19,894 bytes / **~5,500 tokens** — over the
5,000-token budget — and it has **no `references/` directory**, so the whole
thing is inline. Its `wc -w` is 2,234, so the `≤ 1000` gate would have fired
had anything run it; nothing runs it, and `wc -w` on mixed CJK/latin is not a
token proxy anyway (`sql-skill` is 2,234 "words" but 19,894 bytes).

**Fix**
- The body gate becomes a **token estimate** (CJK 1/char, latin 1/3.5 chars),
  with a hard 5,000-token ceiling on the body and a soft 2,000-token warning
  that fires when the body has no `references/` routing table.
- `validate_skill_body` gains: *"body > 2,000 tok and no read-conditions table
  → warning"*.

### F-4 · no phase of the pipeline measures token cost

Phase 0 classifies a root cause. Phase 4 judges content quality. Phase 5
writes files. **Not one of them knows how many tokens the skill will cost to
load.** A skill can be structurally perfect and still cost 6,000 tokens per
trigger, and skill-forge would happily write `verdict: accept`.

**Fix (cheapest, highest value)**: `audit-report.md` gains a **Cost** section
with the three measured tiers against their budgets, and the Phase 0 marker
prints the index-tier cost. A number in the report is what makes the problem
visible; a rule without a number is a rule nobody applies.

### F-5 · the benchmark has no progressive-loading tasks

The article defines three eval types; skill-forge's Phase 2 generates one
(task quality). There is no "did the agent read only what it needed" signal, so
a skill with everything inline scores exactly as well as a skill with a clean
progressive structure. **Progressive disclosure is currently free — which means
it is currently worth nothing.**

**Fix**: bootstrap generates a slice of tasks that are **unanswerable unless a
specific `references/` file is read**. A skill that inlines its references
passes; a skill that follows the routing table also passes. The differentiator
is **cost**: the inlined skill pays the full body on every trigger, the
progressive one pays only the file it opened.

### F-6..F-9 · the process-level gaps

| # | Gap | Fix |
|---|---|---|
| F-6 | No "is this worth a skill at all" gate | Add the article's rule: **5% edge case → reference, not a skill** |
| F-7 | No description-change protocol | Add: change **1-2 words** at a time, baseline first, evals after each step |
| F-8 | `config.json` and multi-level nesting absent from the file tree (§ 3) | Add both; the 1,945-tax-sections case is exactly `sql-skill`'s 12-frameworks-inlined shape |
| F-9 | Portfolio stacking cost never mentioned | § 12 token budget gains: *"a thread may load 3-5 skills; index costs stack across the whole portfolio"* |

---

## 4. What to implement, in order

**Tier 1 — the automatable half of the rubric (rows 1, 3, 4, 5, 7).** These
are the checks that actually govern token cost, and they are exactly the rows
skill-forge leaves unenforced today.

| # | Change | File |
|---|---|---|
| 1 | `validate_skill_frontmatter`: measure index-tier tokens; warn > 120; warn if `description` contains a `Triggers:` clause; warn if `when_to_use` duplicates `triggers` | `scripts/_lib/frontmatter.py` |
| 2 | `validate_skill_body`: token-estimate the body; warn > 5,000; warn > 2,000 with no read-conditions table | `scripts/_lib/frontmatter.py` |
| 3 | `audit-report.md`: a **Cost** section — index / load / files tiers, measured vs budget | `scripts/run.py` |
| 4 | Phase 0 marker prints the index-tier cost | `scripts/run.py` |

**Tier 2 — the principles rewrite (rows 3, 5, 6, 13, 14).**

| # | Change | File |
|---|---|---|
| 5 | § 1.1 — description carries 1-2 examples, never a phrase list | `docs/PRINCIPLES.md` |
| 6 | § 2.8-2.10 — move to `references/`, body states the read condition | `docs/PRINCIPLES.md` |
| 7 | New § 2.11 — progressive loading table (`Read <file> if <condition>`) | `docs/PRINCIPLES.md` |
| 8 | New § 13 — "5% edge case → reference" creation gate | `docs/PRINCIPLES.md` |
| 9 | § 3 file tree — add `config.json`, multi-level nesting guidance | `docs/PRINCIPLES.md` |
| 10 | § 12 — portfolio stacking note | `docs/PRINCIPLES.md` |

**Tier 3 — the process gaps (rows 9-12).** Needs a design decision, not code:
progressive-loading benchmark tasks, the description-change protocol,
cross-family evals.

---

## 5. The uncomfortable conclusion

skill-forge's 2026-10-15 audit applied the Perplexity article to skill-forge
and found the *cosmetic* violations: a redundant sentence, a missing
references/ directory, a duplicated trigger list. It fixed those.

It did not apply the article to **what skill-forge tells other skills to be** —
and that is where the token cost actually comes from. The article's two
load-bearing numbers are **~100 tokens of index** and **~5,000 tokens of
body**. skill-forge enforces neither, prescribes a body layout that pushes
toward the second, and its own frontmatter blows the first by 78%.

**The measure that matters is not "did this skill follow the principles?" but
"how many tokens does invoking it cost, per layer?"** That number should be
the first thing the audit prints and the last thing the report shows.

---

## 6. Open questions for the reviewer

1. **Should the body ceiling be enforced or reported?** The article's ~5,000
   tokens is a guideline ("ideally"). skill-forge's contract is "audit, don't
   block" (RULING-1: absent rubric ≠ failure). Recommend: **report, never
   refuse** — consistent with the rest of the validator, and a hard ceiling on
   body size would block legitimate heavy skills.
2. **Should the index tier get a hard ceiling?** Index cost is paid by every
   user of every session, so it is the more expensive of the two to ignore —
   but it is also trivially fixable by the author, so a warning may be enough.
3. **Do the two out-of-band skills (`evidence-skill`, `sql-skill`) get
   re-optimized, or only the meta-skill?** Re-optimizing them is a separate
   piece of work with its own risk (they are live, in-use skills).

---

## Appendix — the measurements

```
evidence-skill  index 146 tok (budget 100)  |  load 2,431 tok  |  files: references/ 5 files / 13,683 tok
sql-skill       index 221 tok (budget 100)  |  load 5,500 tok  |  files: NO references/ directory
skill-forge     index 178 tok (budget 100)  |  load ~1,100 tok |  files: docs/ + references/
portfolio       63 user-scope skills installed -> ~6,300-11,300 index tokens per session
```

Reproduction: the estimates above come from a single script over
`~/.claude/skills/<name>/SKILL.md` (CJK 1 tok/char, latin 1 tok/3.5 chars).
The `sql-skill` load-tier figure is the one that matters most: it is over the
article's body budget and it has nowhere to push the overflow to.
