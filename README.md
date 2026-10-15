# skill-forge

> A six-phase meta-skill for auditing, creating, improving, and retiring other skills — with a deterministic + LLM-rubric judge, bundled-skill safety, and a SHA-baseline race check that refuses to overwrite a marketplace install.

## Where the docs live

This repo is a workspace. The actual skill-forge package is in the **`skill-forge/`** subdirectory; the full README, heavy reference, and deployment notes are there.

| Document | Path | What it is |
|---|---|---|
| **Main README** | [`skill-forge/README.md`](skill-forge/README.md) | Bilingual (English + 中文) overview, install, quick start, vs. skill-creator / skill-writer comparison, 6 phases, exit codes, rulings |
| **Heavy reference** | [`skill-forge/docs/foundry.md`](skill-forge/docs/foundry.md) | The ~670-line deep dive: phase semantics, the file-state model, RULING-1..10 ledger, failure catalog, change-log, every detail the README skips |
| **Local deployment** | [`skill-forge/docs/DEPLOYMENT.md`](skill-forge/docs/DEPLOYMENT.md) | The PowerShell junction + `pip install -e .` recipe that puts skill-forge at `~/.claude/skills/skill-forge/` so cc-haha (and any Claude variant) can call it; also a SKILL.md snapshot for re-deployment |
| **SKILL.md (entry)** | [`skill-forge/SKILL.md`](skill-forge/SKILL.md) | The gbrain-conformance frontmatter that the LLM reads when invoking the skill; describes the 6-phase process + v2 specifics |
| **Spec** | [`analysis-2026-10-14.md`](analysis-2026-10-14.md) | The v0 spec that started the project (skill-forge v0, user-confirmed 2026-10-14) |
| **v1 plan** | [`docs/superpowers/plans/2026-10-14-skill-forge.md`](docs/superpowers/plans/2026-10-14-skill-forge.md) | The 8-task v1 implementation plan that produced the v1 SHIP commit (`5a7c2dd`) |

## What's in the package

```
skill-forge/                   # the v0.2.0-rc1 package
├── SKILL.md                   # entry: 6 phases + v2 specifics + verification
├── README.md                  # main doc (bilingual)
├── pyproject.toml             # deps: pyyaml>=6.0, pytest>=8.0
├── scripts/                   # the 6 phases
│   ├── audit.py               # 0  : root-cause classifier
│   ├── run.py                 # 1+2+3+4+5 : scope, bootstrap, forward, verify, materialize
│   ├── bootstrap_benchmark.py # 2  : n_tasks rows
│   ├── router.py              # 3  : gbrain / shim forwarder
│   ├── judge_triple.py        # 4  : deterministic + LLM rubric + spot
│   └── _lib/                  # shared helpers (frontmatter, sha, bundle, baseline_log)
├── tests/                     # 58 tests
├── docs/
│   ├── foundry.md             # heavy reference (~670 lines)
│   └── DEPLOYMENT.md          # local Claude-skills deployment backup
└── README.md                  # (the bilingual doc GitHub shows when you open the directory)
```

## Quick start (90 seconds)

```bash
# Read the package README first.
cat skill-forge/README.md

# Then install:
cd skill-forge
pip install -e .
pytest -q   # 58 passed

# Smoke run:
python -m scripts.run --skill . --scope audit-only
```

## State at this push

| | |
|---|---|
| Latest commit | `9aa2f5b` (on `main`) |
| Tag | `v0.2.0-rc1` (annotated, peels to `d765930`) |
| Test count | 58 |
| v1 final | `5a7c2dd` (was local-only until the v0.2.0-rc1 push) |
| v2 commits since v1 | 16 (12 v2 tasks + 4 post-v2 hardening + 1 SKILL.md update) |
| Backlog at `v0.2.0-rc1` | none — all 8 v2 tasks closed; the 24 parked Minors from final review are documented in `skill-forge/docs/foundry.md` § 9 and are non-blocking cosmetic items |

## Other top-level files

| File | What it is |
|---|---|
| `analysis-2026-10-14.md` | The v0 spec that defined what skill-forge should do |
| `skill-creator/` | A local working copy of the `skill-creator` skill (the gbrain-marketplace tool that skill-forge forwards to in Phase 3 when `gbrain` is absent and `--scope create` is requested). Read-only reference; not under active development here |
| `skill-creator.skill` | The marketplace-installer form of the same `skill-creator` skill (used by the v1 router's `_legacy_init_skill.py` shim to find the upstream script). Not a skill-forge output |
| `docs/superpowers/plans/2026-10-14-skill-forge.md` | The 8-task v1 plan (historical, complete) |
| `.gitignore` | excludes `__pycache__/`, `*.egg-info/`, `.venv/`, `.skill-forge-baseline.json`, `.skill-forge-baseline.*.tmp` |

## License

Shipped without a `LICENSE` file. Under default copyright, all rights are reserved by the author. Add a `LICENSE` (MIT, Apache-2.0, etc.) to grant downstream rights; the v2 `docs/foundry.md` § 0 has a one-line note.
