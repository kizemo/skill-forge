# Handoff: skill-forge post-audit optimization

**Date:** 2026-10-15
**From session:** `b30a6b89-26f5-428f-a594-83028dc836cf` (running since v2 cycle start, now >2h)
**To session:** fresh
**Trigger:** user asked to optimize skill-forge based on the Perplexity audit. The 7 gaps require focused code + doc work that a fresh session can do efficiently.

---

## 1. Project state at handoff

| Field | Value |
|---|---|
| **Repository** | `F:\soft\00selfmade\skill-optimizer` (Windows) |
| **Branch** | `main` |
| **Local HEAD** | `03e5575 docs(skill-forge): audit vs Perplexity skill-writing principles` |
| **Remote HEAD** | `bb0f7ce` (push of `03e5575` FAILED — TLS error from local proxy; needs retry from a fresh session) |
| **Tag** | `v0.2.0-rc1` (preserved; do not move) |
| **Tests** | 76 / 76 pass (58 from v0.2.0 + 18 new for `validate_skill_frontmatter`) |
| **Latest un-pushed commits** | just `03e5575` (the audit report). All 13 prior commits are already on `origin/main = bb0f7ce`. |

**Verify on session start:** `cd F:/soft/00selfmade/skill-optimizer && git log --oneline -3 && git log --oneline origin/main..HEAD && git status --short`. Expect: `03e5575` at HEAD, one commit ahead of `origin/main`, working tree clean except for the 4 pre-existing untracked handoff/prompt files at repo root.

---

## 2. Project background (read in this order)

| Read | Why | Path |
|---|---|---|
| 1 | The pre-audit handoff (v1+v2 cycle, 8 tasks, deployment, principles work) | `F:\soft\00selfmade\skill-optimizer\handoff-2026-10-15-skill-forge-v2.md` |
| 2 | The audit report (the source of truth for the 7 gaps to close) | `F:\soft\00selfmade\skill-optimizer\skill-forge\docs\AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md` |
| 3 | The skill-forge principles (current contract for what skill-forge enforces) | `F:\soft\00selfmade\skill-optimizer\skill-forge\docs\PRINCIPLES.md` |
| 4 | The skill-forge entry point (what cc-haha calls) | `F:\soft\00selfmade\skill-optimizer\skill-forge\SKILL.md` |
| 5 | The deployment contract (junction layout) | `F:\soft\00soft\00selfmade-skill-optimizer\skill-forge\docs\DEPLOYMENT.md` |

**No need to re-read:** `docs/foundry.md` (~670 lines, heavy reference), `tests/test_*.py` (read only the ones you touch), `docs/v2-progress.md` (out-of-session, in gitignored `.superpowers/sdd/`).

---

## 3. The task: close the 7 gaps from the audit

The audit identified two axes of compliance. Both must be addressed.

### Axis 1 — `skill-forge` as a skill (be audited well)

### Axis 2 — `skill-forge` as a tool (`validate_skill_frontmatter` must enforce well)

### The 7 gaps (priority-ordered)

| # | Priority | Effort | Risk | What | Where (file + line) |
|---|---|---|---|---|---|
| **1** | HIGH | 30 min | zero | Add 3 checks to `validate_skill_frontmatter`: (a) `description` starts with "Use when" or "Load when"; (b) `description` ≤ 50 words (separate from the existing 1024-char cap); (c) `dir.name == fm["name"]` (skill dir name matches frontmatter name). All return warnings, never raise. | `skill-forge/scripts/_lib/frontmatter.py` (the function already exists); `tests/test_frontmatter.py` (add ~3 tests) |
| **2** | HIGH | 30 min | zero | Add 2 more body checks: (a) presence of a gotcha-style section (`## .*[Gg]otcha|## .*[Pp]itfall|## .*[Ff]ail|## .*[Rr]ationaliz`); (b) optional: warn if `references/` or `assets/` is missing for non-trivial skills. The body check needs to access the SKILL.md body, so the function should take a `Path` (or both `dict` and `body`). Refactor signature accordingly. | `skill-forge/scripts/_lib/frontmatter.py` (add `validate_skill_body(path, fm)`); `tests/test_frontmatter.py` |
| **3** | HIGH | 1 h | zero | Trim `SKILL.md` per Pascal test: 846 → ~700 words. Targets: (a) "It does not edit skills directly" sentence (obvious from the position statement); (b) "Default behavior: bare `python -m scripts.run`..." line (model knows how to run a script); (c) the navigation-aid block before `## v2 specifics` (model doesn't need "see SKILL_REFERENCE.md" hint at this point); (d) tighten the v2 specifics "Skip optional deps gracefully" sub-bullet. Do NOT remove the Iron Law (Perplexity's Pascal test exempts Iron Laws). | `skill-forge/SKILL.md` |
| **4** | MED | 30 min | zero | Add 3 new sections to `PRINCIPLES.md`: § "Gotcha flywheel" (the maintenance process from the article), § "Action at a distance" (changing one skill's description can break another), § "Token budget" (the 100/5000/unlimited tiers). Each section can be ~50-100 words. | `skill-forge/docs/PRINCIPLES.md` |
| **5** | MED | 30 min | zero | Add `references/` directory to `skill-forge/` containing: (a) `references/hero-queries.md` — 5-10 example user queries the skill should match; (b) `references/token-budget.md` — the 100/5000/unlimited tier breakdown. Move from PRINCIPLES.md or write fresh. | new files: `skill-forge/references/hero-queries.md`, `skill-forge/references/token-budget.md` |
| **6** | MED | 1 h | zero | Split `docs/foundry.md` (~6,500 tokens, over the 5,000 cap) into: (a) `docs/foundry-overview.md` (~3,000 tokens, the "load on first trigger" page); (b) `docs/foundry-details.md` (the rest). Update SKILL.md and PRINCIPLES.md to point to overview. Keep the old `foundry.md` as a redirect/pointer for a release to avoid breaking existing links. | `skill-forge/docs/foundry.md` → split |
| **7** | LOW | 1 h | low | Add a "Suggested gotchas" section to the `audit-report.md` template. When the audit returns a non-trivial verdict (non-`other`, non-`missing`), suggest 1-2 gotchas the author should add to their target skill's Red Flags / Anti-Patterns sections. This is the "gotcha flywheel input" — without it, the flywheel has no fuel. Update `scripts/run.py::_materialize` and add a test in `tests/test_run.py`. | `skill-forge/scripts/run.py` (the materialize step) |

**Total estimated effort:** 4-5 hours of focused work. Each gap is one commit. Expected commit count: 7.

---

## 4. How to work (conventions)

### TDD for code changes (gaps 1, 2, 7)

For each validator / materialize change:
1. Write a RED test in the corresponding `tests/test_*.py` file
2. Run `python -m pytest -q tests/test_*.py::test_name` and confirm RED
3. Implement the change in the production file
4. Run the same test, confirm GREEN
5. Run the full suite `python -m pytest -q`, confirm 76+ tests still pass
6. Commit with Conventional Commits prefix: `feat(skill-forge): ...` or `fix(skill-forge): ...`

### Doc changes (gaps 3, 4, 5, 6)

For doc changes:
1. Read the target file
2. Apply the edit
3. Verify the result (e.g. for Pascal test: re-read and mentally apply "agent fails without this?")
4. Commit with `docs(skill-forge): ...` prefix

### Commit granularity

- One commit per gap. If a gap naturally splits into 2-3 commits (e.g. test then impl then docs), that's also fine.
- Never amend. If a commit is wrong, add a new commit on top.
- Subject lines are `<type>(<scope>): <subject>` with imperative mood, ≤ 72 chars, no trailing period.

### Don't modify

- `v1/progress.md` (gitignored, in v1's SDD workspace) — out of scope, immutable
- `v2/progress.md` (gitignored, in v2's SDD workspace) — out of scope, immutable
- Bundled v0 at `C:\Users\Duanyi\.claude\plugins\marketplaces\gbrain\plugin\skills\skill-optimizer\` — read-only by v2 design
- The `v0.2.0-rc1` tag — don't move it. Add a new commit on top; let user re-tag if needed.

---

## 5. Test infrastructure

### How to run tests

```bash
cd F:/soft/00selfmade/skill-optimizer/skill-forge
python -m pytest -q    # primary; 76 tests
pytest -q              # equivalent (RULING-4, requires [tool.pytest.ini_options] pythonpath = ["."])
```

Both should report the same count. Bare `pytest -q` requires the `pythonpath = ["."]` line in `pyproject.toml` (RULING-4) — already in place, don't change.

### Conventions for new tests

- Tests live in `tests/test_<module>.py` matching the source file naming
- Use `tmp_path` for filesystem fixtures
- Use `monkeypatch.setattr` for module-level mocking
- For `validate_skill_frontmatter` tests, pass a dict directly (not a Path) — the function takes parsed frontmatter
- For `validate_skill_body` tests (new), pass a Path

### Verify after each commit

```bash
cd F:/soft/00selfmade/skill-optimizer/skill-forge
python -m pytest -q   # must show ≥ 76 passed
```

If a test fails, fix the test or the production code. Do NOT skip tests.

---

## 6. Push workflow

The current session's last push failed with a TLS error. The local commit `03e5575` is in place; just `git push origin main` from the new session. Verify with:

```bash
cd F:/soft\00selfmade/skill-optimizer
git status --short   # expect: clean
git push origin main # expect: 03e5575..HEAD main -> main (or already-up-to-date)
git ls-remote origin | head -3   # expect: HEAD == <local HEAD>
```

After every commit in this session, push. The local network may be intermittent; if push fails with TLS, retry once or twice before giving up.

---

## 7. The 2 junctions (deployment-specific)

The skill is deployed at TWO paths on this host, both as PowerShell junctions:

| Path | Purpose |
|---|---|
| `C:\Users\Duanyi\.claude\skills\skill-forge\` | User-scope. Visible in cc-haha settings panel. |
| `C:\Users\Duanyi\.claude\plugins\marketplaces\gbrain\plugin\skills\skill-forge\` | Marketplace-link. Required for `@skill-forge` invocation in cc-haha. |

Both point to `F:\soft\00selfmade\skill-optimizer\skill-forge\` via `mklink /J`. After any commit, both junctions see the change automatically (no need to re-deploy).

To verify: `powershell -NoProfile -Command "(Get-Item 'C:\Users\Duanyi\.claude\skills\skill-forge').Attributes"` should return `Directory, ReparsePoint`.

---

## 8. Pitfalls

- **v0 skill-optimizer** is at the marketplace path. Its `name:` in frontmatter is `skill-optimizer` (NOT `skill-forge`). Don't confuse it with the new skill.
- **CLAUDE.md "Drinkx" path typo** — the global CLAUDE.md says `E:\Users\Drinkx\.claude\...` but the actual path is `C:\Users\Duanyi\.claude\...`. Use the real path.
- **Token budget on foundry.md** — Perplexity's article warns that bodies > 5,000 tokens "degrade other Skills". Our `foundry.md` is ~6,500 tokens, which is why gap 6 matters.
- **The Iron Law is exempt from Pascal** — don't remove "Violating the letter of these rules is violating the spirit of these rules." Perplexity's example table has its own Iron Law; convention is that Iron Laws are rules, not tutorials.
- **No `import` of test fixtures from other tests** — each test file is independent. Copy fixtures inline.
- **Don't touch the `v0.2.0-rc1` tag** — it's a release tag. Add new commits on top; let the user re-tag.
- **The audit's high-priority gaps are AUTOMATABLE** — gaps 1, 2, 3, 7 are code/test changes; gaps 4, 5, 6 are doc changes. All have well-defined acceptance.

---

## 9. End-state success criteria

When the new session is done, verify:

| Check | Command | Expected |
|---|---|---|
| All 7 gaps closed | `git log --oneline 03e5575..HEAD` | 7 commits (or more if natural splits) |
| Tests pass | `python -m pytest -q` (in `skill-forge/`) | ≥ 76 passed (likely 80-82 with new validator tests) |
| `validate_skill_frontmatter` has new checks | `grep -c "warns on\|warning" tests/test_frontmatter.py` | increased count |
| SKILL.md trimmed | `wc -w skill-forge/SKILL.md` | < 800 (target: ~700) |
| `references/` directory exists | `ls skill-forge/references/` | `hero-queries.md` and `token-budget.md` |
| `docs/foundry-overview.md` exists | `ls skill-forge/docs/` | both `foundry-overview.md` and `foundry-details.md` |
| All committed and pushed | `git log --oneline origin/main..HEAD` | empty (everything pushed) |
| Junctions reflect changes | `head -3 ~/.claude/skills/skill-forge/SKILL.md` | new version |

---

## 10. Out of scope

- Adding a new skill via `gbrain:skill-creator` — not part of this audit's mandate
- Changing the 6-phase pipeline semantics — the v0.2.0 design is locked
- Adding CI/CD (no GitHub Actions) — out of scope for this task
- Adding a `LICENSE` file — user mentioned this is a non-blocking follow-up in a previous turn; not part of the audit
- Optimizing further than the 7 gaps — additional principles from the Perplexity article (e.g. MECE, no-command-sequences) are semantic and cannot be automated; document as manual review steps in PRINCIPLES.md if you want

---

## 11. End of handoff

The new session should: read the 5 docs in § 2, then start with gap 1 (highest ROI, lowest risk). Use TDD for the validator changes. Commit and push after each gap. Stop when all 7 are closed and pushed.

If you hit a wall (e.g. the 50-word cap conflicts with an existing well-formed skill that has a longer description, or the dir-name check breaks a test that uses tmp_path), surface it as a Concern in the per-task report rather than silently deviating. The reviewer will rule.
