# skill-forge

> A six-phase meta-skill for auditing, creating, improving, and retiring other skills — built on the [Perplexity skill-writing principles](#-good-skill-standards) and dogfooding every one of them.

<div align="right">

[🇺🇸 English](#en) · [🇨🇳 中文](#zh)

</div>

---

<a id="en"></a>

## 🇺🇸 English

### ⚡ The 5-minute version

**What this is.** A CLI that **writes, audits, judges, and safely lands** Agent
Skills. The write lane generates a skill that is *already inside the token
budget*; the improve lane turns "this skill isn't working" into a measured,
verifiable change.

**The 8 standards a good skill meets** — the rubric skill-forge scores
against, and half of it is checked in code:

| # | Standard | In one line | Who checks it |
|---|---|---|---|
| 1 | Description is a routing trigger | `Use when…` / `Load when…`, ≤ 50 words, **no trigger list inside the description** | validator |
| 2 | A skill is a folder, not a file | Lean `SKILL.md` hub + `scripts/` `references/` `assets/` spokes, loaded on demand | validator |
| 3 | Gotchas are the highest-value content | ≥ 1 `## Gotchas` / `## Common Rationalizations` / `## Red Flags` section | validator |
| 4 | Pascal test, every sentence | "Without this instruction, would the agent fail?" If no → delete it | human |
| 5 | Token budget 100 / 5,000 / ∞ | **index** ~100 tok (every session, every user) · **load** ~5,000 tok (every trigger) · **files** unlimited | measured |
| 6 | Action at a distance | Changing one skill's description can break a neighbour's recall | process |
| 7 | Write evals first | 5-10 hero queries: positive + negative + neighbour-confusion | the author writes them |
| 8 | Dir name == frontmatter `name` | `my-skill/SKILL.md` must declare `name: my-skill` | validator |

**The 5 practices that keep it good** — the process, not the shape:

| # | Practice | In one line |
|---|---|---|
| P1 | Gotcha flywheel | agent failed → append a gotcha · wrong skill loaded → tighten the description |
| P2 | Eval-driven iteration | benchmark → optimize → judge → materialize; every run is a measurable delta |
| P3 | Safe-by-default landing | never overwrite `SKILL.md`; write `best.md` / `proposed.md` and let a human merge |
| P4 | Concurrent-edit safety | a SHA baseline catches "you edited it between audit and materialize" |
| P5 | Distinct exit codes | `0` accept · `2` refuse · `3` race — CI can branch on each |

**Which one do you actually want?**

| If you want… | Use |
|---|---|
| a prompt that tells an agent how to write a good skill | Anthropic's `skill-creator` |
| a tool that *makes* good skills, and proves what they cost | `skill-forge --scope create` |
| to know **why** a skill underperforms | `skill-forge --scope audit-only` |
| to iterate a skill with a real before/after | `skill-forge --scope improve` |
| a dashboard of eval results | Anthropic's `skill-creator` (it ships an HTML viewer) |

→ **Full detail:** [the standards, the practices, and how skill-forge holds
itself to them](docs/SKILL-DESIGN-GUIDE.md)

### What it is

`skill-forge` is a CLI that **writes, audits, judges, and safely lands** Agent Skills.

**The write lane** — `--scope create --spec <file.json>` generates a skill that is
*already inside the token budget*, with its read-conditions table and gotchas in
place. The rubric is applied at generation time, not reported afterwards.

**The improve lane** — a six-phase pipeline that turns "this skill isn't working"
into a measured, verifiable change:

1. **Audit** — classifies the failure as `prompt` / `routing` / `contract` / `missing` / `other` (RULING-6 order); prints the measured index/load token cost.
2. **Scope** — user picks `create` / `improve` / `audit-only` / `retire`.
3. **Bootstrap** — generates a 15-row benchmark template (or `--held-out N`, refuses `N<5`).
4. **Forward** — calls `gbrain skillopt` with the benchmark, an explicit split, and an explicit spend cap, inside an isolated `GBRAIN_HOME`; degrades gracefully on failure.
5. **Verify** — deterministic trace + LLM rubric + optional spot-check, judged against a **real baseline** (the pre-run snapshot); absent rubric ≠ failure (RULING-1).
6. **Materialize** — writes `audit-report.md` (always, with a `## Cost` section and a `## Change` diff) + `best.md` (non-bundled accept) or `proposed.md` (bundled accept); never overwrites the target `SKILL.md`. Emits **Suggested gotchas** when the verdict is non-trivial.

The body still gets written by a human or by an agent — but skill-forge now owns
the whole loop: it can **author** a skill that starts inside the budget, and it
can **measure** what any skill costs to load.

### Why a pipeline at all

A skill usually fails for one of three reasons: the description doesn't trigger, the body is too thin, or the body references code that doesn't exist. The first is `routing`, the second is `prompt`, the third is `contract`. Without a classifier, you fix all three and hope. With `skill-forge`'s six phases you fix only the one the audit named.

The judge phase (Phase 4) is what makes the difference: an identical candidate passes (deterministic + skip-rubric + skip-spot = `accept`), so a no-op rewrite is provably safe. A candidate with `TODO` markers refuses, so you can't ship "I'll finish this later" by accident. A candidate whose `description` is a YAML list refuses instead of raising, so a partial-formatted frontmatter is caught at the gate.

The materialize phase (Phase 5) is the safety story: a bundled skill (one registered in `~/.gbrain/install.json`) is **refused** from being written. The candidate lands in `proposed.md` next to it; the bundled `SKILL.md` is untouched. The race check against `.skill-forge-baseline.json` catches the case where you edited `SKILL.md` between audit and materialize — exit code `3` on a bundled install, `[WARN]` on a non-bundled.

### 🆚 vs Anthropic's `skill-creator`

The honest comparison, because Anthropic ships an official skill-creator and
this project has to earn its keep against it.

| Dimension | Anthropic `skill-creator` | `skill-forge` |
|---|---|---|
| **Shape** | A prompt + scripts + an `agents/` subagent directory — the agent reads it and follows it | A standalone CLI with a 6-phase pipeline plus a write lane |
| **Write lane** | An interview + research flow, a writing guide, and a full **description-optimization loop** (`improve_description.py`: generate trigger eval queries → review → run the loop → apply) | ✅ **Built-in author** (`--scope create --spec`): generates SKILL.md + `references/` + `assets/` + `scripts/`, **with the token rubric and the progressive-disclosure structure applied at generation time**. The interview and the description loop are still the agent's job — skill-forge is the generator, not the interviewer |
| **Token cost measurement** | `total_tokens` recorded per run; `benchmark.json` reports `pass_rate`, `time`, and `tokens` | ✅ **Same, and more**: a three-tier axis (index / load / files) measured by `scripts/_lib/token_cost.py`, printed in the Phase 0 marker and written to the report's `## Cost` section |
| **Before / after** | Snapshots the pre-change skill and points the baseline run at the copy | ✅ **Same**: `scripts/_lib/snapshot.py` snapshots the before state in Phase 0, judges the candidate against it, and writes a `## Change` diff (`+4 / -0` lines) to the report |
| **Body budget** | "< 500 lines ideal"; "> 300 lines → add a table of contents" | ✅ **Token-based**: ~5,000-token load tier (measured, not word-counted), ~100-token index tier; the body ceiling is *reported*, never enforced |
| **Eval set** | Hero queries: 5-10, positives + negatives, neighbouring-confusion pool | ✅ **The author writes one for every skill** (`references/hero-queries.md`), with the positives **derived from `triggers:`** so the machine-readable short-circuit and the human rubric cannot drift |
| **Root-cause diagnosis** | Per-assertion grader feedback + an analyzer agent — it tells you *which assertion failed*, not *which class of defect* it is | ✅ **`audit()` returns `prompt` / `routing` / `contract` / `missing` / `other`** with a confidence score and a **typed** `recommend_scope` (`create` / `improve` / `audit-only` / `retire`) — a class, not just a failing check |
| **Eval presentation** | ✅ A full eval viewer (`eval-viewer/`) — per-assertion grades, qualitative outputs, and a benchmark view | ❌ Plain-text `audit-report.md` — parseable and diffable, but not a dashboard |
| **Blind comparison** | ✅ A/B the old and new skill without knowing which is which | ❌ The `## Change` diff shows the delta; it does not hide which side is which |
| **Bundling repeated work** | ✅ Reads the transcripts and notices when every run re-invented the same helper, then bundles it into `scripts/` | ❌ The author will put a script in `scripts/` if the spec says so, but it does not mine transcripts for it |
| **Safety invariants** | Manual `cp -r` before editing | ✅ **Enforced in code**: a bundled install is refused from forwarding and only ever gets `proposed.md`; the SHA race check refuses with exit `3`; **`SKILL.md` is never overwritten by any path** |
| **Exit codes** | n/a (a prompt) | `0` accept · `2` refuse · `3` race — three distinct failure modes, CI-routable |
| **Agent orchestration** | ✅ Same-turn parallel subagents (with-skill + baseline) | ❌ A CLI does not spawn agents — **and it should not**: that is the caller's job |
| **Runs headless / in CI** | Needs a harness that can spawn subagents | ✅ It IS a CLI — `python -m scripts.run` in CI, exit code and report as the contract |
| **Judge provenance** | Model provenance matters; `--models-strict` can abort | ✅ The judge model is named explicitly (`--rubric-model`) and echoed in the Phase 4 marker, so the judge is auditable and can be a *different* model from the author |

### 💪 Where skill-forge wins outright

**1. It applies the rubric at the moment of authoring.** Anthropic's
skill-creator teaches the agent to write well; skill-forge *generates* a skill
that is already inside the budget, with a read-conditions table, a gotcha
section, and a `references/hero-queries.md` — and then measures its own output
(`index=97tok load=304tok`). A skill that comes out of the author passes
skill-forge's own validator with **zero warnings**.

**2. It knows *why* a skill fails, not just that it does.** `audit()` names the
root cause and a typed scope. Batch-governing forty skills without a classifier
means reading forty skills by hand.

**3. It cannot destroy anything.** A bundled marketplace install is refused
from forwarding; the target `SKILL.md` is never overwritten by any code path;
a concurrent edit between audit and materialize is detected and refused with a
distinct exit code. Anthropic's skill-creator edits in place and relies on you
having made a copy.

**4. It measures the thing users actually pay.** The index tier is the cost
every session pays whether or not the skill is ever invoked, and it stacks
across the whole installed portfolio. skill-forge puts that number in the
first line of the output.

**5. It is a CLI, not a prompt.** It runs headless, in CI, in a cron job, from
a different host. It exits with a code a pipeline can branch on.

### 🟡 The real gaps

**1. Agent orchestration.** Anthropic's harness runs the with-skill and
baseline subagents in the same turn, grades each assertion with a grader
agent, and ships an HTML eval viewer. skill-forge is a CLI and does not spawn
agents. That is a deliberate boundary — a CLI that spawned agents would be tied
to one harness — but it means the parallel A/B and the dashboard are the
caller's job.

**2. The authoring conversation.** Anthropic's skill-creator *interviews* you
(interview → research → write → report → iterate) and optimizes the
description against generated trigger queries. skill-forge's author takes a
finished spec. It generates a compliant skill; it does not interview you into
one.

**What skill-forge does instead:** it is the *audit and safety* layer, and it
is a CLI. Use it where you need a machine-checkable verdict, a token cost, a
before/after diff, and the guarantee that nothing was overwritten. Use
Anthropic's skill-creator where you need a conversation and a dashboard.

### The 30-second version

> Anthropic's `skill-creator` is **a recipe for writing a skill**.
> `skill-forge` is **a pipeline for owning a skill's whole life** — author it
> inside the budget, measure what it costs, diagnose why it fails, judge it
> against a real baseline, and land it without being able to break anything.
>
> Use `skill-creator` if you want a prompt that tells an agent how to write a
> good skill. Use `skill-forge` if you want a tool that *makes* good skills and
> proves it.

### Install

```bash
git clone https://github.com/kizemo/skill-forge
cd skill-forge/skill-forge
pip install -e .
```

`pip install -e .` puts the `skill-forge` console script on `PATH` (entry point declared in `pyproject.toml`). The same code also runs as `python -m scripts.run` from inside `skill-forge/`.

### Quick start

```bash
# WRITE a new skill, already inside the token budget.
python -m scripts.run --skill C:/Temp/e2e-target/my-new-skill \
    --scope create --spec C:/Temp/e2e-target/my-new-skill.json

# OR improve an existing one. Copy a target skill into a scratch dir FIRST
# (do not run against a marketplace install until you have read the
# bundled-skill safety section).
cp -r ~/.claude/plugins/marketplaces/gbrain/plugin/skills/my-skill C:/Temp/e2e-target/

# Audit-only — classifies the failure, writes audit-report.md, does not
# modify SKILL.md. Default exit 0 on accept, 2 on refuse.
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope audit-only

# Improve — full pipeline. Writes best.md (your skill) or proposed.md
# (bundled) with the candidate content, leaving SKILL.md untouched.
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope improve

# Held-out task count: refuse if N<5 (gbrain hard-refuses <5 internally).
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope improve --held-out 5
```

### Bundled vs. non-bundled skills

`skill-forge` distinguishes a *bundled* skill (one whose directory resolves to a path listed in `~/.gbrain/install.json`) from a *non-bundled* skill (a local working copy). The bundled check fails open — if `install.json` is missing, every skill is treated as non-bundled.

| Scenario | What `is_bundled()` returns | What `materialize` writes | Exit on accept |
|---|---|---|---|
| Working copy under `C:/Temp/e2e-target/my-skill` | `False` | `best.md` (candidate) + `audit-report.md` | `0` |
| Real bundled install at `~/.claude/.../skill-optimizer/` with `install.json` listing it | `True` | `proposed.md` (candidate) + `audit-report.md`; bundled `SKILL.md` untouched | `0` |
| Bundled install with no `install.json` on this host | `False` (fail-open) | `best.md` + `audit-report.md` | `0` |

The bundled check is **defence-in-depth**, not a lock. The real safety property is that you copy the skill to a scratch dir before iterating. `is_bundled()` exists so that if you forget, the bundled `SKILL.md` is not silently overwritten.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Accept — `audit-report.md` (always) + `best.md` (non-bundled) or `proposed.md` (bundled) written; baseline updated |
| `2` | Refuse — `audit-report.md` written with `verdict: refuse`; no candidate written; no baseline update. Triggered by: deterministic failure (e.g. `TODO` in body), `--held-out N<5`, or `--scope create` with no `gbrain` (forwards to `init_skill.py`, which returns its own non-zero) |
| `3` | Race — a bundled skill's `SKILL.md` SHA drifted between audit and materialize; refusing protects the bundled install. Distinct from refuse so CI can route them differently |

### Repository layout

```
skill-forge/
├── SKILL.md                  # 797 words (under the 1000-word gate). Iron Law + 6 phases + Common Rationalizations.
├── README.md                 # this file
├── references/               # heavy docs loaded on demand
│   ├── hero-queries.md       # 10 positive + 5 negative + 4 neighbor-confusion queries
│   └── token-budget.md       # 100/5000/unlimited tier checklist
├── docs/
│   ├── PRINCIPLES.md         # the rules skill-forge enforces (§ 1-12)
│   ├── foundry-overview.md   # load on first trigger (~1700 tokens: install / CLI / Phase 5 / failure catalog)
│   ├── foundry-details.md    # load only when troubleshooting (~5200 tokens: phases / gbrain / judges / safety)
│   ├── foundry.md            # redirect (kept one release for backwards-compatible links)
|   ├── SKILL-DESIGN-GUIDE.md   # the 8 standards + 5 practices in full (EN + 中文)
│   ├── SKILL_DESIGN_RUBRIC.md  # the 14-row scoring sheet: what is automatable, what is process
│   ├── AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md  # the audit that produced the 7 gaps
│   ├── SKILL_REFERENCE.md    # load-on-demand heavy reference (Output Format / Anti-Patterns / When it fails / Tools Used)
│   └── DEPLOYMENT.md         # local Claude-skills deployment backup
├── scripts/                  # executable code
│   ├── audit.py              # Phase 0: root-cause classifier
│   ├── author.py             # the WRITE lane: generates a skill inside the budget
│   ├── bootstrap_benchmark.py # Phase 2: 15-row JSONL generator
│   ├── judge_triple.py       # Phase 4: deterministic + LLM rubric + spot-check
│   ├── router.py             # Phase 3: gbrain soft-bind + bundled-skill short-circuit
│   ├── run.py                # 6-phase CLI + materialize + the create lane
│   ├── _legacy_init_skill.py # create-scope shim (skill-creator)
│   └── _lib/                 # pure helpers
│       ├── frontmatter.py    # loader + frontmatter/body validators
│       ├── token_cost.py     # the three-tier token cost axis
│       ├── snapshot.py       # the real baseline (before/after)
│       ├── llm_channel.py    # the pluggable judge channel (script / HTTP)
│       ├── baseline_log.py   # SHA race check
│       ├── bundle.py         # bundled-install detection
│       └── sha.py
└── tests/                    # 98 tests, split per phase
```

### The two vendored reference copies

This repository keeps **two** snapshots of Anthropic's official
`skill-creator`, and they are not redundant:

| Directory | What it is | Why it is here |
|---|---|---|
| `../skill-creator/` | The **Oct 2026** snapshot (7 files): `SKILL.md` + `scripts/init_skill.py` and friends | `scripts/_legacy_init_skill.py` forwards the legacy create scope to `skill-creator/scripts/init_skill.py`. Upstream **removed `init_skill.py`** in the current version (the scaffolding moved to `agents/`), so overwriting this copy would break the shim. |
| `../skill-creator-upstream/` | The **current** upstream (18 files): `SKILL.md` + `agents/{analyzer,comparator,grader}.md` + `scripts/{run_eval,run_loop,improve_description,aggregate_benchmark,generate_report}.py` + `eval-viewer/` + `references/schemas.md` | The reference the comparison in this README is written against. Upstream evolved a long way: an interview flow, a full eval harness with an HTML viewer, blind comparison, and a description-optimization loop. |

Refresh the upstream copy with:

```bash
cd /c/Temp && gh api repos/anthropics/skills/tarball/main > repo.tar.gz
tar -xzf repo.tar.gz --wildcards "*/skills/skill-creator/*"
cp -r anthropics-skills-*/skills/skill-creator <repo>/skill-creator-upstream
```

**Do not** overwrite `../skill-creator/` with the current upstream: the
`init_skill.py` the shim depends on is gone there.

### Rulings that shape this package

`skill-forge` has 10 cross-task rules, each pinned to a commit:

- **RULING-3** — `frontmatter.load()` and `body_of()` use the same closer (`_find_closer`); the fence rule lives in one place (`3020f`).
- **RULING-4** — `[tool.pytest.ini_options] pythonpath = ["."]` in `pyproject.toml`, so bare `pytest -q` works from `skill-forge/` without `python -m pytest` (`5a7c2dd`).
- **RULING-6** — `audit()` precedence is `missing → other(frontmatter) → routing → contract → prompt → other` (`9155b4e`). The `routing` check fires first because the description is the user-facing entry point; without it the deeper branches would shadow each other.
- **RULING-6 corollary** — any `audit()` fixture targeting `contract` or `prompt` must start `description` with `Use when`; the routing gate is a silent precondition for reaching the deeper branches (`4e3c1b4`).
- **RULING-7** — `bootstrap()` cycles the template bucket to reach `n_tasks`; default 15 rows, sentinel `# BOOTSTRAP_PENDING_REVIEW` (`fd86978`).
- **RULING-8 part 1** — rubric-skipped is invisible in `verdict.llm_score`; branch on `llm_call is None` at the call site, never on the verdict (`4fc95e2`).
- **RULING-8 part 2 (v2-T2)** — `baseline` is consumed by the rubric prompt (`f"score candidate=… baseline=…"`); the LLM call can perform a candidate-vs-baseline comparison (`3020cb2`).
- **RULING-9 v2** — the router invokes the shim with `sys.executable` (not bare `python`); the shim reads the skill dir from `SKILL_DIR` env (cwd-agnostic); the shim refuses with `[FATAL] …` if both `SKILL_DIR` and `argv` are missing (`072db5e`).
- **RULING-9 v2 corollary** — the env-merge order in `router.py:34` is `{**os.environ, "SKILL_DIR": ...}`; the router's value outranks any ambient `SKILL_DIR` so a stale parent env cannot reintroduce v1's wrong-directory bug class (`5b2ab23`).
- **RULING-10** — the dead `"env"` `RootCause` member and its `TEMPLATES` bucket are dropped; strict narrowing of the v1 contract (`b31ec91`).

Full ledger: `docs/foundry-details.md` § 0 (ruling index). The foundry is the heavy reference; this README is the 5-minute tour.

### Development

```bash
cd skill-forge
pip install -e .[dev]      # or: pip install pytest pyyaml
pytest -q                  # bare invocation, RULING-4
python -m pytest -q        # equivalent
```

Test counts: **98** (76 from v0.2.0 + 18 from `validate_skill_frontmatter` / `validate_skill_body` and 4 from `_suggested_gotchas`). The `tests/` directory is split per phase (`test_frontmatter.py`, `test_audit.py`, `test_judge_triple.py`, `test_bootstrap_benchmark.py`, `test_router.py`, `test_run.py`, `test_bundle.py`, `test_sha.py`).

### License

The project is shipped without a license file; under default copyright, all rights are reserved by the author. Add a `LICENSE` file (e.g. MIT, Apache-2.0) to grant downstream rights.

---

<a id="zh"></a>

## 🇨🇳 中文

### ⚡ 5 分钟版

**这是什么。** 一个 **写、审、判、安全落地** Agent Skill 的 CLI。写作通道生成的 skill
**一出生就在 token 预算内**;改进通道把「这个 skill 不工作」变成可测量、可验证的改动。

**好 skill 要满足的 8 条标准** —— skill-forge 的评分标尺,其中一半是代码自动检查的:

| # | 标准 | 一句话 | 谁来查 |
|---|---|---|---|
| 1 | 描述是路由触发器 | `Use when…` / `Load when…`,≤ 50 词,**description 里不放 trigger 清单** | validator |
| 2 | skill 是文件夹不是单文件 | 精简的 `SKILL.md` 当 hub + `scripts/` `references/` `assets/` 当按需加载的 spoke | validator |
| 3 | Gotcha 是最高价值内容 | 至少有一个 `## Gotchas` / `## Common Rationalizations` / `## Red Flags` 小节 | validator |
| 4 | Pascal 测试,逐句过 | 「没这句 agent 会不会失败?」不会 → 删 | 人 |
| 5 | Token 预算 100 / 5,000 / ∞ | **index** ~100 tok(每会话、每用户)· **load** ~5,000 tok(每次触发)· **files** 无限 | 实测 |
| 6 | Action at a distance | 改一个 skill 的 description 会破坏邻居的召回 | 流程 |
| 7 | 先写 evals | 5-10 条 hero query:正面 + 负面 + 邻居混淆 | author 自动写 |
| 8 | 目录名 == frontmatter `name` | `my-skill/SKILL.md` 必须声明 `name: my-skill` | validator |

**让它持续变好的 5 条实践** —— 是过程,不是形状:

| # | 实践 | 一句话 |
|---|---|---|
| P1 | Gotcha 飞轮 | agent 失败 → 追加 gotcha · 加载错 skill → 收紧 description |
| P2 | 评测驱动迭代 | benchmark → 优化 → 判分 → 物化;每次运行都是可测量的 delta |
| P3 | 默认安全的落地 | 永不覆盖 `SKILL.md`;写 `best.md` / `proposed.md`,让人来合 |
| P4 | 并发编辑安全 | SHA 基线抓得住「你在 audit 和 materialize 之间改了它」 |
| P5 | 不同的退出码 | `0` 接受 · `2` 拒绝 · `3` 竞态 —— CI 可分别分支 |

**你到底想要哪个?**

| 你想要… | 用 |
|---|---|
| 一份告诉 agent 怎么写好 skill 的提示词 | Anthropic 的 `skill-creator` |
| 一个**制造**好 skill、并证明它成本多少的工具 | `skill-forge --scope create` |
| 知道 skill 为什么表现不好 | `skill-forge --scope audit-only` |
| 带真实前后对照地迭代一个 skill | `skill-forge --scope improve` |
| 评测结果的仪表盘 | Anthropic 的 `skill-creator`(它有 HTML viewer) |

→ **完整版:** [标准、实践,以及 skill-forge 如何要求自己](docs/SKILL-DESIGN-GUIDE.md)

### 这是什么

`skill-forge` 是一个 **写、审、判、安全落地** Agent Skill 的 CLI。

**写作通道** —— `--scope create --spec <file.json>` 生成的 skill **一出生就在 token 预算内**,
读取条件表和 gotchas 都已就位。标尺是在**生成时**施加的,不是事后才报告超标。

**改进通道** —— 一条六阶段流水线,把「这个 skill 不工作」变成可测量、可验证的改动:

1. **审计(Audit)** — 把失败原因分类为 `prompt` / `routing` / `contract` / `missing` / `other`(遵循 RULING-6 顺序);并打印实测的 index/load token 成本。
2. **范围(Scope)** — 用户选 `create` / `improve` / `audit-only` / `retire`。
3. **基准生成(Bootstrap)** — 生成 15 行 benchmark 模板(可用 `--held-out N` 覆盖,`N<5` 拒绝)。
4. **转发(Forward)** — 调用 `gbrain skillopt`,带上 benchmark、显式 split、显式预算上限,跑在隔离的 `GBRAIN_HOME` 里;失败时优雅降级。
5. **验证(Verify)** — 确定性检查 + LLM 评分 + 可选人工 spot-check,对照**真基线**(运行前的快照)判定;评分器缺省 ≠ 失败(RULING-1)。
6. **物化(Materialize)** — 始终写 `audit-report.md`(含 `## Cost` 段和 `## Change` diff);接受时非 bundled 写 `best.md`、bundled 写 `proposed.md`;**绝不覆盖**目标 `SKILL.md`。

正文仍然由人或 agent 写 —— 但整个闭环现在归 skill-forge 管:它能**创作**一个一出生就合预算的 skill,
也能**测量**任何 skill 的加载成本。

### 为什么要一条流水线

一个 skill 失败通常是这三种之一:描述不触发(是 `routing`)、正文太薄(是 `prompt`)、正文引用的代码不存在(是 `contract`)。没有分类器,你只能三种都改然后碰运气。有 `skill-forge` 的六阶段,你只改审计指出的那一种。

第四阶段(Verify)的判分是真正的差异:同一个候选通过(确定性 + 跳过评分 + 跳过 spot = `accept`),所以"无意义重写"是被证明无害的;带 `TODO` 的候选直接拒绝,所以"我等下再补完"不能蒙混过关;`description` 是 YAML 列表时,`isinstance(desc, str)` 守卫会拒绝而不是抛 `AttributeError`,所以半成品 frontmatter 在闸口就被截住。

第五阶段(Materialize)是安全故事的本体:一个 bundled skill(出现在 `~/.gbrain/install.json` 里的)被**拒绝**写入。候选落到同目录的 `proposed.md`;bundled 的 `SKILL.md` 始终不动。`.skill-forge-baseline.json` 记录上一次成功运行时的 SHA,下一次运行比对 —— 如果 audit 和 materialize 之间你手改了 `SKILL.md`,bundled 路径直接 `exit 3` 拒绝,非 bundled 路径走 `[WARN]` 放行。

### 🆚 对比 Anthropic 的 `skill-creator`

诚实的对比 —— Anthropic 有官方 skill-creator,这个项目得凭真本事站住。

| 维度 | Anthropic `skill-creator` | `skill-forge` |
|---|---|---|
| **形态** | 提示词 + 脚本 + `agents/` 子 agent 目录 —— agent 读了照着做 | 独立 CLI:6 阶段流水线 + 写作通道 |
| **写作通道** | 访谈 + 调研流程、一份写作指南,以及完整的 **description 优化循环**(`improve_description.py`:生成触发 eval query → 复核 → 跑循环 → 应用) | ✅ **自带 author**(`--scope create --spec`):生成 SKILL.md + `references/` + `assets/` + `scripts/`,**在生成时就施加 token 标尺与渐进式披露结构**。访谈和 description 循环仍然是 agent 的活 —— skill-forge 是生成器,不是访谈者 |
| **token 成本度量** | 每次运行记录 `total_tokens`;`benchmark.json` 输出 `pass_rate` / `time` / `tokens` | ✅ **一样,而且更多**:三层(index / load / files)由 `scripts/_lib/token_cost.py` 实测,打在 Phase 0 marker 上,写进报告的 `## Cost` 段 |
| **前后对照** | 快照改动前的 skill,让 baseline run 指向副本 | ✅ **一样**:`scripts/_lib/snapshot.py` 在 Phase 0 快照 before 态,拿候选跟它判分,报告给 `## Change` diff(`+4 / -0` 行) |
| **正文预算** | 「< 500 lines ideal」;「> 300 lines 要加目录」 | ✅ **按 token 计**:load 层 ~5,000 token(实测,不是数字数)、index 层 ~100 token;正文上限**只报不拦** |
| **评测集** | hero query:5-10 条,含正例/负例/邻居混淆池 | ✅ **author 给每个 skill 都写一份**(`references/hero-queries.md`),正面 query **由 `triggers:` 派生**,机器可读短路列表与人读的标尺不会漂移 |
| **根因诊断** | 逐条断言的 grader 反馈 + 一个 analyzer agent —— 它告诉你*哪条断言挂了*,不告诉你*这是哪一类缺陷* | ✅ **`audit()` 返回 `prompt` / `routing` / `contract` / `missing` / `other`**,带置信度 + **类型化** `recommend_scope`(`create` / `improve` / `audit-only` / `retire`) —— 是一类缺陷,不只是某条检查没过 |
| **评测呈现** | ✅ 完整的 eval viewer(`eval-viewer/`)—— 逐条断言评分、质性输出、benchmark 视图 | ❌ 纯文本 `audit-report.md` —— 可解析、可 diff,但不是仪表盘 |
| **盲测对比** | ✅ 不告诉 agent 哪份是新哪份是旧,直接 A/B | ❌ `## Change` diff 展示差异,但不隐藏哪边是哪边 |
| **把重复劳动打包** | ✅ 读运行记录,发现每次都重新造同一个 helper,就打包进 `scripts/` | ❌ spec 里写了,author 就会放进 `scripts/`;但它不会去挖运行记录 |
| **安全不变量** | 手工 `cp -r` 备份后再改 | ✅ **代码强制**:bundled install 拒绝转发、只出 `proposed.md`;SHA 竞态检查以 exit `3` 拒绝;**任何路径都不覆盖 `SKILL.md`** |
| **退出码** | n/a(它是一段提示词) | `0` 接受 · `2` 拒绝 · `3` 竞态 —— 三种失败模式分开,CI 可分支 |
| **agent 编排** | ✅ 同 turn 并行跑 with-skill / baseline 两个 subagent | ❌ CLI 不 spawn agent —— **而且它不该**:那是调用方的活 |
| **headless / CI 运行** | 需要能 spawn subagent 的 harness | ✅ 它本来就是 CLI —— CI 里 `python -m scripts.run`,退出码和报告就是契约 |
| **判官来源** | 模型来源重要;`--models-strict` 可能中止 | ✅ 判官模型显式指定(`--rubric-model`)并在 Phase 4 marker 回显,可审计,且**可以和作者不是同一个模型** |

### 💪 skill-forge 明确胜出的地方

**1. 它在「写」的当下就施加标尺。** Anthropic 的 skill-creator 教 agent 怎么写好;
skill-forge **生成**一个一出生就合预算的 skill —— 带读取条件表、带 gotcha 小节、带
`references/hero-queries.md`,然后测量自己的产出(`index=97tok load=304tok`)。
从 author 出来的 skill 通过 skill-forge 自家 validator 时**零警告**。

**2. 它知道 skill 为什么坏,而不只是知道它坏了。** `audit()` 给出根因和类型化的 scope。
没有分类器,批量治理 40 个 skill 就意味着手读 40 个。

**3. 它破坏不了任何东西。** bundled marketplace install 拒绝转发;目标 `SKILL.md`
任何代码路径都不覆盖;audit 与 materialize 之间被人手改过会被检测并以独立退出码拒绝。
Anthropic 的 skill-creator 是就地编辑,靠你自己记得先备份。

**4. 它量的是用户真正付的钱。** index 层是**每个会话都付**的成本 —— 无论 skill 是否被触发 ——
而且在整份已安装技能清单上累加。skill-forge 把这个数字放在输出的第一行。

**5. 它是 CLI,不是提示词。** 能 headless 跑、能进 CI、能进定时任务、能在别的机器上跑,
并且以流水线可分支的退出码结束。

### 🟡 真实的差距

**1. agent 编排。** Anthropic 的 harness 在同一个 turn 里并发跑 with-skill 和 baseline 两个
subagent,用 grader agent 逐条判断言,还提供一个 HTML eval viewer。skill-forge 是 CLI,
不 spawn agent。这是有意的边界 —— 一个会 spawn agent 的 CLI 就被绑死在某个 harness 上了 ——
但代价是并行 A/B 和仪表盘得由调用方来做。

**2. 创作过程是对话。** Anthropic 的 skill-creator 会**访谈**你(访谈 → 调研 → 写 → 报告 →
迭代),并针对生成的触发 query 优化 description。skill-forge 的 author 接受一份成型的 spec。
它生成一个合规的 skill;它不通过访谈把你引导到那一步。

**skill-forge 的替代定位:** 它是**审计与安全层**,而且是个 CLI。当你要的是可机器判定的结论、
token 成本、前后 diff,以及"什么都没被覆盖"的保证时用 skill-forge。当你要的是一次对话和一块
仪表盘时,用 Anthropic 的 skill-creator。

### 30 秒版总结

> Anthropic 的 `skill-creator` 是**一份教你怎么写 skill 的配方**。
> `skill-forge` 是**一条掌管 skill 全生命周期的流水线** —— 在预算内创作它、测量它的加载成本、
> 诊断它为什么坏、对照真基线判分,并且在落地时无法破坏任何东西。
>
> 想要一份「告诉 agent 怎么写好 skill」的提示词 → 用 `skill-creator`。
> 想要一个**制造**好 skill 并且**证明**它的工具 → 用 `skill-forge`。

### 安装

```bash
git clone https://github.com/kizemo/skill-forge
cd skill-forge/skill-forge
pip install -e .
```

`pip install -e .` 把 `skill-forge` 控制台脚本放到 `PATH`(入口在 `pyproject.toml` 声明)。同一份代码也可以在 `skill-forge/` 目录下用 `python -m scripts.run` 运行。

### 快速开始

```bash
# 写一个新 skill —— 一出生就在 token 预算内。
python -m scripts.run --skill C:/Temp/e2e-target/my-new-skill \
    --scope create --spec C:/Temp/e2e-target/my-new-skill.json

# 或者改进一个已有的。第一步:把目标 skill 复制到 scratch 目录(在读懂
# bundled-skill 安全章节之前,不要直接对 marketplace install 跑)。
cp -r ~/.claude/plugins/marketplaces/gbrain/plugin/skills/my-skill C:/Temp/e2e-target/

# 只审计 — 分类失败原因,写 audit-report.md,不动 SKILL.md。
# 默认接受时 exit 0,拒绝时 exit 2。
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope audit-only

# Improve — 全流水线。写 best.md(你自己的 skill)或 proposed.md(bundled),
# SKILL.md 不动。
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope improve

# held-out 任务数:N<5 拒绝(gbrain 内部硬性拒绝 <5)。
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope improve --held-out 5
```

### Bundled vs. 非 Bundled Skill

`skill-forge` 区分 **bundled** skill(目录解析到 `~/.gbrain/install.json` 列出的路径)和**非 bundled** skill(本地工作副本)。bundled 检测 fail-open —— `install.json` 缺失时,所有 skill 都按非 bundled 处理。

| 场景 | `is_bundled()` 返回 | materialize 写什么 | 接受时退出码 |
|---|---|---|---|
| `C:/Temp/e2e-target/my-skill` 下的工作副本 | `False` | `best.md`(候选) + `audit-report.md` | `0` |
| 真实 bundled install 在 `~/.claude/.../skill-optimizer/`,`install.json` 列出 | `True` | `proposed.md`(候选) + `audit-report.md`;bundled `SKILL.md` 不动 | `0` |
| Bundled install,但本机无 `install.json` | `False`(fail-open) | `best.md` + `audit-report.md` | `0` |

bundled 检测是**纵深防御**,不是锁。真正的安全属性是:**你在迭代之前把 skill 复制到 scratch 目录**。`is_bundled()` 的存在是为了:就算你忘了,bundled `SKILL.md` 也不会被悄悄覆盖。

### 退出码

| 码 | 含义 |
|---|---|
| `0` | 接受 — `audit-report.md`(总是写) + `best.md`(非 bundled)或 `proposed.md`(bundled) 已写;baseline 已更新 |
| `2` | 拒绝 — `audit-report.md` 写 `verdict: refuse`;不写候选;不更新 baseline。触发场景:确定性失败(比如正文有 `TODO`)、`--held-out N<5`、或 `--scope create` 且无 `gbrain`(转发到 `init_skill.py`,它返回自己的非零) |
| `3` | 竞态 — bundled skill 的 `SKILL.md` SHA 在 audit 和 materialize 之间被改过;拒绝以保护 bundled install。和"拒绝"区分开,方便 CI 走不同分支 |

### 仓库布局

```
skill-forge/
├── SKILL.md                  # 797 词(在 1000 词闸门之下)。Iron Law + 6 阶段 + Common Rationalizations。
├── README.md                 # 本文件
├── references/               # 按需加载的重量级文档
│   ├── hero-queries.md       # 10 正面 + 5 负面 + 4 邻居混淆 查询
│   └── token-budget.md       # 100/5000/无限 层级 checklist
├── docs/
│   ├── PRINCIPLES.md         # skill-forge 强制执行的规则(§ 1-12)
│   ├── foundry-overview.md   # 首次触发时加载(~1700 tokens:安装/CLI/Phase 5/失败目录)
│   ├── foundry-details.md    # 仅在排错时加载(~5200 tokens:阶段细节/gbrain/判分器/安全)
│   ├── foundry.md            # 跳转页(保留一个 release 周期以兼容老链接)
|   ├── SKILL-DESIGN-GUIDE.md   # 8 条标准 + 5 条实践完整版(EN + 中文)
│   ├── SKILL_DESIGN_RUBRIC.md  # 14 行评分表:哪些可自动化,哪些是流程
│   ├── AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md  # 产生 7 个 gap 的审计
│   ├── SKILL_REFERENCE.md    # 按需加载的重量级参考(Output Format / Anti-Patterns / When it fails / Tools Used)
│   └── DEPLOYMENT.md         # 本地 Claude-skills 部署备查
├── scripts/                  # 可执行代码
│   ├── audit.py              # Phase 0:根因分类器
│   ├── author.py             # 写作通道:生成一个一出生就合预算的 skill
│   ├── bootstrap_benchmark.py # Phase 2:15 行 JSONL 生成器
│   ├── judge_triple.py       # Phase 4:确定性 + LLM 评分 + spot-check
│   ├── router.py             # Phase 3:gbrain 软绑定 + bundled-skill 短路
│   ├── run.py                # 6 阶段 CLI + materialize + create 通道
│   ├── _legacy_init_skill.py # create 范围 shim(skill-creator)
│   └── _lib/                 # 纯辅助
│       ├── frontmatter.py    # 加载器 + frontmatter/body 校验器
│       ├── token_cost.py     # 三层 token 成本轴
│       ├── snapshot.py       # 真基线(before/after)
│       ├── llm_channel.py    # 可插拔判官通道(script / HTTP)
│       ├── baseline_log.py   # SHA 竞态检查
│       ├── bundle.py         # bundled-install 检测
│       └── sha.py
└── tests/                    # 98 个测试,按阶段分文件
```

### 两个 vendored 参考副本

本仓库保存着 Anthropic 官方 `skill-creator` 的**两个**快照,它们不重复:

| 目录 | 是什么 | 为什么留着 |
|---|---|---|
| `../skill-creator/` | **2026-10** 的快照(7 个文件):`SKILL.md` + `scripts/init_skill.py` 等 | `scripts/_legacy_init_skill.py` 把 legacy create 范围转发到 `skill-creator/scripts/init_skill.py`。上游在当前版本**删掉了 `init_skill.py`**(脚手架改成了 `agents/` 驱动),所以就地覆盖会打断这个 shim。 |
| `../skill-creator-upstream/` | **当前**上游(18 个文件):`SKILL.md` + `agents/{analyzer,comparator,grader}.md` + `scripts/{run_eval,run_loop,improve_description,aggregate_benchmark,generate_report}.py` + `eval-viewer/` + `references/schemas.md` | 本 README 里的对比表就是对着它写的。上游已经走了很远:访谈流程、带 HTML viewer 的完整 eval harness、盲测对比、description 优化循环。 |

刷新上游副本:

```bash
cd /c/Temp && gh api repos/anthropics/skills/tarball/main > repo.tar.gz
tar -xzf repo.tar.gz --wildcards "*/skills/skill-creator/*"
cp -r anthropics-skills-*/skills/skill-creator <repo>/skill-creator-upstream
```

**不要**用当前上游覆盖 `../skill-creator/`:shim 依赖的 `init_skill.py` 在那边已经没有了。

### 塑造这个项目的 10 条规则

`skill-forge` 跨任务有 10 条规则,每条都钉在一次 commit 上:

- **RULING-3** — `frontmatter.load()` 和 `body_of()` 用同一个 closer(`_find_closer`);栅栏规则只在一处(`3020f`)。
- **RULING-4** — `pyproject.toml` 里的 `[tool.pytest.ini_options] pythonpath = ["."]`,让 `skill-forge/` 下裸跑 `pytest -q` 也能工作,不用 `python -m pytest`(`5a7c2dd`)。
- **RULING-6** — `audit()` 优先级是 `missing → other(frontmatter) → routing → contract → prompt → other`(`9155b4e`)。`routing` 排在最前,因为描述是面向用户的入口;不排前的话,后面的分支会互相遮挡。
- **RULING-6 corollary** — 任何针对 `contract` 或 `prompt` 分支的 `audit()` fixture 必须以 `Use when` 开头;`routing` 闸门是触达更深分支的隐式前置条件(`4e3c1b4`)。
- **RULING-7** — `bootstrap()` 循环模板桶以凑齐 `n_tasks`;默认 15 行,带哨兵 `# BOOTSTRAP_PENDING_REVIEW`(`fd86978`)。
- **RULING-8 part 1** — rubric-skipped 在 `verdict.llm_score` 里不可见;在调用现场用 `llm_call is None` 判断,不要从 verdict 推断(`4fc95e2`)。
- **RULING-8 part 2 (v2-T2)** — `baseline` 被 rubric prompt 消费(`f"score candidate=… baseline=…"`);真实 LLM 调用可以做候选 vs baseline 对比(`3020cb2`)。
- **RULING-9 v2** — 路由器用 `sys.executable`(不是裸 `python`)调 shim;shim 从 `SKILL_DIR` 环境变量读 skill 目录(与 cwd 无关);两者都缺时,shim 输 `[FATAL] …` 然后退出 2(`072db5e`)。
- **RULING-9 v2 corollary** — `router.py:34` 的 env 合并顺序是 `{**os.environ, "SKILL_DIR": ...}`;路由器的值盖过任何环境里的 `SKILL_DIR`,防止陈旧父环境让 v1 的"错目录"bug 类重新出现(`5b2ab23`)。
- **RULING-10** — 死值 `"env"` `RootCause` 成员及其 `TEMPLATES` 桶被删;v1 契约的严格缩窄(`b31ec91`)。

完整台账:见 `docs/foundry-details.md` § 0(规则索引)。foundry 是大而全的参考;这份 README 是 5 分钟导览。

### 开发

```bash
cd skill-forge
pip install -e .[dev]      # 或:pip install pytest pyyaml
pytest -q                  # 裸调用,RULING-4
python -m pytest -q        # 等价
```

测试数:**98**(76 来自 v0.2.0 + 18 来自 `validate_skill_frontmatter` / `validate_skill_body` + 4 来自 `_suggested_gotchas`)。`tests/` 目录按阶段分文件(`test_frontmatter.py`、`test_audit.py`、`test_judge_triple.py`、`test_bootstrap_benchmark.py`、`test_router.py`、`test_run.py`、`test_bundle.py`、`test_sha.py`)。

### 许可证

项目未带 `LICENSE` 文件;按默认版权,所有权利归作者所有。添加 `LICENSE`(例如 MIT、Apache-2.0)即可向下游授予权限。