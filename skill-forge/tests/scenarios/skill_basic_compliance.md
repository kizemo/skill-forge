## Pressure scenario for skill-forge SKILL.md

**Setup:** Fresh `claude -p` session with NO inherited context. Only the
skill-forge/SKILL.md contents are injected (description + body).

**Task prompt:** "The skill `weekly-digest` keeps producing shallow
summaries. Improve it."

**Expectation when skill is present:**
- Agent loads skill-forge, knows Phase 0 audit comes first.
- Agent does NOT immediately start editing `weekly-digest`'s SKILL.md.
- Agent asks clarifying question (Phase 1 scope: create vs improve vs
  audit vs retire) before running anything.

**Expectation when skill is absent (RED baseline):**
- Agent opens `weekly-digest/SKILL.md`, edits sentence 3 to add "be
  more thorough", saves, declares done.
