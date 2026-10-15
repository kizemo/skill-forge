# Hero queries for skill-forge

**Purpose:** Perplexity's eval-first principle — a skill should have a
written registry of "queries the agent should match on" before the skill
is finalized. This file is the source of truth for `skill-forge`'s
hero-query set. Re-run after any change to `description` or `triggers`.

The set below is grouped by intent. Negative and confusion cases are
included so the resolver can rule skill-forge out cleanly.

---

## Positive queries (skill-forge SHOULD match)

| # | Query | Why this matches |
|---|---|---|
| 1 | "this skill isn't producing the quality I want — can you improve it?" | core optimization use case |
| 2 | "audit skill quality for `<skill-name>`" | matches `audit skill quality` trigger |
| 3 | "skill won't trigger when the user asks X" | matches `skill won't trigger` trigger |
| 4 | "fix skill underperformance for my new skill" | matches `fix skill underperformance` trigger |
| 5 | "build a benchmark for `<skill-name>` so I can measure its quality" | matches `make a skill benchmark` trigger |
| 6 | "this skill is deprecated — retire it cleanly" | matches `retire old skill` trigger |
| 7 | "skill produces shallow output even with the right description" | matches `skill produces shallow output` trigger |
| 8 | "the agent keeps doing the wrong thing for `<skill-name>` — diagnose" | implicit quality failure → audit |
| 9 | "I want to optimize a skill against a held-out test set" | matches the SkillOpt-driven flow |
| 10 | "is my skill's SKILL.md following the gbrain / Perplexity playbook?" | cross-reference audit |

## Negative queries (skill-forge should NOT match)

| # | Query | Why skill-forge is wrong |
|---|---|---|
| 1 | "create a brand-new skill from scratch" | that's `gbrain:skill-creator`, not skill-forge |
| 2 | "what does `<skill-name>` do?" | that's `read`, not an optimization |
| 3 | "write me a skill for video editing" | creator lane, not optimization lane |
| 4 | "fix the bug in `<skill>` (it's an exception)" | that's the agent's normal bugfix loop, not skill-level |
| 5 | "improve my code" | code-quality lane, not skill-quality |

## Neighbor-confusion queries (could match but is NOT skill-forge's lane)

| # | Query | Closer skill / why |
|---|---|---|
| 1 | "make this prompt better" | prompt-engineering lane (no SKILL.md involvement) |
| 2 | "the agent is loading too many skills, getting confused" | resolver / routing lane, not a single-skill audit |
| 3 | "evaluate this skill" | ambiguous: if it's a one-shot review, could be `simplify`; if it's improving an underperformer, skill-forge |
| 4 | "this skill triggers too often" | `description`-tightening lane; skill-forge's `audit()` will surface it but the fix is local |

---

## Maintenance

When the resolver short-circuits wrong (positive query does not fire
skill-forge) or fires wrongly (negative query fires skill-forge), add
the query to the right table and adjust `description` / `triggers` in
`SKILL.md`. The `validate_skill_frontmatter()` warning on
"`description` should start with 'Use when' or 'Load when'" is a
reminder that routing starts at the description prefix; queries below
are the eval rubric.

## Cross-references

- `SKILL.md` — the frontmatter `triggers:` list is the machine-readable
  short-circuit; this file is the human-readable eval rubric.
- `PRINCIPLES.md` § 11 — action at a distance: changing `description`
  can break neighbors; re-run these evals when the change set changes.
- `gbrain:skill-creator` — owns the *create* lane; skill-forge owns the
  *improve / retire* lane.