# Hero queries for skill-forge

**Purpose:** Perplexity's eval-first principle — a skill should have a
written registry of the queries the agent should match on before the skill
is finalized. This file is the source of truth for the eval set.
Re-run after any change to `description` or `triggers`.

The positive queries below are derived from the `triggers:` list in
`SKILL.md` — the machine-readable short-circuit and this human-readable
rubric are the same list, so they cannot drift.

---

## Positive queries (this skill SHOULD match)

| # | Query | Why this matches |
|---|---|---|
| 1 | "improve this skill" | matches the `triggers:` entry |
| 2 | "skill won't trigger" | matches the `triggers:` entry |
| 3 | "audit skill quality" | matches the `triggers:` entry |
| 4 | "make a skill benchmark" | matches the `triggers:` entry |
| 5 | "retire old skill" | matches the `triggers:` entry |

## Negative queries (this skill should NOT match)

| # | Query | Why this skill is wrong |
|---|---|---|
| 1 | "create a brand-new skill from scratch" | that's `gbrain:skill-creator` — the creator lane; skill-forge owns the improve / retire lane |
| 2 | "write me a skill for video editing" | creator lane, not optimization lane |
| 3 | "what does my-skill do?" | that's `read`, not an optimization |
| 4 | "fix the bug in my-skill (it's an exception)" | the agent's normal bugfix loop, not skill-level |
| 5 | "improve my code" | code-quality lane, not skill-quality |

## Neighbor-confusion queries (could match but is NOT this skill's lane)

| # | Query | Closer skill / why |
|---|---|---|
| 1 | "make this prompt better" | prompt-engineering lane — no SKILL.md involved |
| 2 | "the agent is loading too many skills, getting confused" | resolver / routing lane, not a single-skill audit |
| 3 | "evaluate this skill" | ambiguous: a one-shot review could be `simplify`; improving an underperformer is skill-forge |
| 4 | "this skill triggers too often" | `description`-tightening lane — `audit()` surfaces it, but the fix is local |

---

## Maintenance

When the resolver short-circuits wrong (a positive query does not fire
this skill) or fires wrongly (a negative query fires it), add the query to
the right table and adjust `description` / `triggers` in `SKILL.md`.

**Change 1-2 words at a time**, establish a baseline first, and re-run the
evals after each step — never rewrite the description wholesale. Adding a
skill can break pre-existing skills, so re-run the neighbours' evals too.

## Cross-references

- `SKILL.md` — the `triggers:` list is the machine-readable short-circuit;
  this file is the human-readable eval rubric.
- `PRINCIPLES.md` § 11 — action at a distance: changing `description` can
  break neighbours; re-run these evals when the change set changes.
