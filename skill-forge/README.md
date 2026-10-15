# skill-forge

> A six-phase meta-skill for auditing, creating, improving, and retiring other skills — with a deterministic + LLM-rubric judge, bundled-skill safety, a SHA-baseline race check, and a validator that enforces the [Perplexity skill-writing principles](#-good-skill-standards) on every skill it touches.

<div align="right">

[🇺🇸 English](#en) · [🇨🇳 中文](#zh)

</div>

---

<a id="en"></a>

## 🇺🇸 English

### What it is

`skill-forge` is a CLI tool that turns "this skill isn't working" into a reproducible pipeline:

1. **Audit** — classifies the failure as `prompt` / `routing` / `contract` / `missing` / `other` (RULING-6 order).
2. **Scope** — user picks `create` / `improve` / `audit-only` / `retire`.
3. **Bootstrap** — generates a 15-row benchmark template (or `--held-out N`, refuses `N<5`).
4. **Forward** — calls `gbrain skillopt` or `skill-creator/init_skill.py`; degrades gracefully on failure.
5. **Verify** — deterministic trace + LLM rubric + optional spot-check; absent rubric ≠ failure (RULING-1).
6. **Materialize** — writes `audit-report.md` (always) + `best.md` (non-bundled accept) or `proposed.md` (bundled accept); never overwrites the target `SKILL.md`.

It is the *pipeline around* skill authoring, not the authoring itself. The author still writes the body; skill-forge audits, judges, races, and materializes.

### ✨ Good skill standards

These are the eight principles distilled from the 2026-10-15 Perplexity
audit (`docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md`) and codified in
`docs/PRINCIPLES.md`. They are the rubric a good skill is judged against.
`validate_skill_frontmatter()` and `validate_skill_body()` automate checks
**1, 2, 3, and 8**; checks **4, 5, 6, and 7** are process / architectural
and require human review.

| # | Standard | What it means | Enforced by |
|---|---|---|---|
| **1** | **Description is a routing trigger, not a self-intro** | Starts with `Use when…` or `Load when…`, ≤ 50 words, targets user intent not workflow. Trigger phrases must NOT be duplicated between `description`, `triggers:`, and `when_to_use:`. | `validate_skill_frontmatter` (prefix check + 50-word cap) |
| **2** | **Skill is a folder, not a file** | Hub-and-spoke: `SKILL.md` (lean hub, ~150 lines) + `scripts/` `references/` `assets/` (spokes, loaded on demand). Heavy content belongs in `references/`, not the body. | `validate_skill_body` (warns when body > 150 lines without `references/` or `assets/`) |
| **3** | **Gotchas are the highest-value content** | Body must contain a gotcha-style section: `## Common Rationalizations`, `## Red Flags`, `## Anti-Patterns`, `## Pitfalls`, or `## When it fails`. Gotchas turn observed failures into reusable rules. | `validate_skill_body` (regex against `##` headers) |
| **4** | **Pascal test per sentence** | "Without this instruction, would the agent fail?" If no, the sentence is deleteable. Iron Laws are exempt. | Manual review (process) |
| **5** | **Token budget: 100 / 5,000 / unlimited** | **Index** (`name` + `description`, every session, ~100 tokens/skill); **Load** (full body, on trigger, ~5,000 tokens); **Runtime** (files in `scripts/`/`references/`/`assets/`, on demand, unlimited). | Manual review + `wc -w SKILL.md ≤ 1000` |
| **6** | **Action at a distance** | Changing one skill's description can break another's recall — every description shifts the embedding space. Keep descriptions short and unique; re-run hero queries on neighboring skills when you change one. | MECE / cross-skill registry (architectural) |
| **7** | **Write evals first (hero queries)** | A good skill ships with a `references/hero-queries.md`: 5-10 positive queries (should match), 3-5 negative (should NOT), 3-4 neighbor-confusion (could match, isn't). Eval before ship. | `references/hero-queries.md` per skill (process) |
| **8** | **Skill dir name == frontmatter `name`** | The directory IS the skill. `my-skill/SKILL.md` must declare `name: my-skill`. Mismatches break marketplace lookup. | `validate_skill_frontmatter(skill_dir=...)` (dir-name match check) |

These eight are the **what**. The **how** (the 6-phase pipeline, the
judge, the materialize, the race check) is the rest of this README.

### Why a pipeline at all

A skill usually fails for one of three reasons: the description doesn't trigger, the body is too thin, or the body references code that doesn't exist. The first is `routing`, the second is `prompt`, the third is `contract`. Without a classifier, you fix all three and hope. With `skill-forge`'s six phases you fix only the one the audit named.

The judge phase (Phase 4) is what makes the difference: an identical candidate passes (deterministic + skip-rubric + skip-spot = `accept`), so a no-op rewrite is provably safe. A candidate with `TODO` markers refuses, so you can't ship "I'll finish this later" by accident. A candidate whose `description` is a YAML list refuses instead of raising, so a partial-formatted frontmatter is caught at the gate.

The materialize phase (Phase 5) is the safety story: a bundled skill (one registered in `~/.gbrain/install.json`) is **refused** from being written. The candidate lands in `proposed.md` next to it; the bundled `SKILL.md` is untouched. The race check against `.skill-forge-baseline.json` catches the case where you edited `SKILL.md` between audit and materialize — exit code `3` on a bundled install, `[WARN]` on a non-bundled.

The audit-report.md now also emits a **Suggested gotchas** section when the verdict is non-trivial (`prompt` / `routing` / `contract`). This is the input side of the gotcha flywheel: 1-2 curated, root-cause-specific suggestions the author can copy into the target skill's Red Flags / Anti-Patterns. Without this, the flywheel has no fuel and gotchas stay frozen at v0.2.0.

### Why not just use `skill-creator` (or `skill-writer`)

This is the comparison the README exists to make. The honest answer is that `skill-creator` and `skill-writer` solve a different (smaller) problem: they take a prompt and write a `SKILL.md` once. `skill-forge` assumes the author is iterating on an existing skill and wants a gated, auditable, safe-to-fail loop. The two are complementary, not substitutable.

| Dimension | `skill-creator` (gbrain) | `skill-creator` (init_skill.py scaffold) | `skill-writer` (typical) | `skill-forge` v0.2 |
|---|---|---|---|---|
| **Output** | A 95-line authoring recipe the LLM follows by hand | A 378-line Python scaffold that creates a directory + templated `SKILL.md` | A one-shot rewrite / scaffold (varies) | A 6-phase CLI pipeline with an audit, a judge, a race check, and a materialize step |
| **Frontmatter validation** | Template instructions; the LLM is told to follow YAML block-scalar form | None — template is plain `description: [TODO: …]` | None / minimal | `frontmatter.load()` enforces first-`---`-after-line-1 fence rule (RULING-3); refuses unquoted `:` or `'` literals (RULING-5); checks `description` prefix / 50-word cap / dir-name match |
| **Body validation** | None | None | None | `validate_skill_body()` checks for gotcha-style section + references/`assets/` presence for non-trivial bodies |
| **Failure classifier** | None | None | None | `audit.py` returns one of `prompt` / `routing` / `contract` / `missing` / `other` with a confidence score and a `recommend_scope`; the recommend-scope is *typed*, not a string match |
| **Triple-judge gate** | None | None | None | Deterministic + LLM rubric + spot-check; absent rubric ≠ failure (RULING-1); `baseline` is consumed in the rubric prompt (v2-T2) so a real LLM call can compare candidate vs. baseline |
| **Bundled-skill safety** | None — the LLM just writes whatever was asked | None — `init_skill.py` writes a new directory under the requested path, refuses only if the directory already exists | None | `is_bundled(skill_dir)` reads `~/.gbrain/install.json` and refuses to forward a marketplace install; candidate lands in `proposed.md` next to the bundled `SKILL.md`, which is never overwritten |
| **Concurrent-edit safety** | None | None | None | `.skill-forge-baseline.json` records the SHA of `SKILL.md` from the last run; the next run compares and (a) refuses a bundled drift with exit `3`, (b) warns and proceeds for a non-bundled drift |
| **CI-readable exit codes** | n/a (recipe) | `0` or `1` (Python script) | n/a | `0` accept · `2` refuse · `3` race (Default Decision #3); distinct codes for distinct failure modes |
| **Audit trail** | None | None | None | `audit-report.md` (always) with `root_cause`, `verdict`, and **Suggested gotchas** section; `.skill-forge-baseline.json` (on accept) with `sha` and `ts`; readable in plain text and parseable as JSON |
| **MECE check** | Yes (manual, by the LLM) | n/a | n/a | n/a — `skill-forge` operates on one skill at a time; MECE is a *creation-time* concern that `skill-creator` already handles |
| **LLM rubric dependency** | None (recipe-only) | None (scaffold-only) | Often (one-shot rewrite) | Optional — `llm_call=None` skips the rubric entirely (RULING-1); the deterministic + spot gates run without an LLM |
| **Operating envelope** | 95 lines of markdown; works in any LLM session | 378-line Python script; needs Python 3.11+ | Varies | Python 3.11+; optional `gbrain` CLI on `PATH`; optional `~/.gbrain/install.json` (fail-open if missing) |

**The 30-second version**: `skill-creator` and `skill-writer` answer *"what should this skill say?"*; `skill-forge` answers *"is the skill I'm about to change actually a change, and am I about to break a marketplace install?"* If your workflow is "write a new skill once, ship it, move on," `skill-creator` is enough. If your workflow is "iterate on a skill until it scores well across a held-out set, and do so without corrupting a marketplace install," `skill-forge` is the right tool.

### Install

```bash
git clone https://github.com/kizemo/skill-forge
cd skill-forge/skill-forge
pip install -e .
```

`pip install -e .` puts the `skill-forge` console script on `PATH` (entry point declared in `pyproject.toml`). The same code also runs as `python -m scripts.run` from inside `skill-forge/`.

### Quick start

```bash
# Copy a target skill into a scratch dir FIRST (do not run against a
# marketplace install until you have read the bundled-skill safety section).
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
├── SKILL.md                  # 797 words (under the 1000-word gate). Iron Law + 6 phases + common rationalizations.
├── README.md                 # this file
├── references/               # heavy docs loaded on demand
│   ├── hero-queries.md       # 10 positive + 5 negative + 4 neighbor-confusion queries
│   └── token-budget.md       # 100/5000/unlimited tier checklist
├── docs/
│   ├── PRINCIPLES.md         # the rules skill-forge enforces (1-12)
│   ├── foundry-overview.md   # load on first trigger (~1700 tokens: install / CLI / Phase 5 / failure catalog)
│   ├── foundry-details.md    # load only when troubleshooting (~5200 tokens: phases / gbrain / judges / safety)
│   ├── foundry.md            # redirect (kept one release for backwards-compatible links)
│   ├── AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md  # the audit that produced the 7 gaps
│   ├── SKILL_REFERENCE.md    # load-on-demand heavy reference (Output Format / Anti-Patterns / When it fails / Tools Used)
│   └── DEPLOYMENT.md         # local Claude-skills deployment backup
├── scripts/                  # executable code
│   ├── audit.py              # Phase 0: root-cause classifier
│   ├── bootstrap_benchmark.py # Phase 2: 15-row JSONL generator
│   ├── judge_triple.py       # Phase 4: deterministic + LLM rubric + spot-check
│   ├── router.py             # Phase 3: gbrain soft-bind + bundled-skill short-circuit
│   ├── run.py                # Phase 6-phase CLI + materialize
│   ├── _legacy_init_skill.py # create-scope shim (skill-creator)
│   └── _lib/                 # pure helpers (frontmatter, sha, baseline_log, bundle)
└── tests/                    # 98 tests, split per phase
```

### Rulings that shape this package

`skill-forge` has 10+ cross-task rules, each pinned to a commit:

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

Test counts: **98** (76 from v0.2.0 + 18 from `validate_skill_frontmatter` /
`validate_skill_body` and 4 from `_suggested_gotchas`). The `tests/`
directory is split per phase (`test_frontmatter.py`, `test_audit.py`,
`test_judge_triple.py`, `test_bootstrap_benchmark.py`, `test_router.py`,
`test_run.py`, `test_bundle.py`, `test_sha.py`).

### License

The project is shipped without a license file; under default copyright, all rights are reserved by the author. Add a `LICENSE` file (e.g. MIT, Apache-2.0) to grant downstream rights.

---

<a id="zh"></a>

## 🇨🇳 中文

### 这是什么

`skill-forge` 是一个 CLI 工具,把"这个 skill 不工作"翻译成一条可复现的流水线:

1. **审计(Audit)** — 把失败原因分类为 `prompt` / `routing` / `contract` / `missing` / `other`(遵循 RULING-6 顺序)。
2. **范围(Scope)** — 用户选 `create` / `improve` / `audit-only` / `retire`。
3. **基准生成(Bootstrap)** — 生成 15 行 benchmark 模板(可用 `--held-out N` 覆盖,`N<5` 拒绝)。
4. **转发(Forward)** — 调用 `gbrain skillopt` 或 `skill-creator/init_skill.py`;失败时优雅降级。
5. **验证(Verify)** — 确定性检查 + LLM 评分 + 可选人工 spot-check;评分器缺省 ≠ 失败(RULING-1)。
6. **物化(Materialize)** — 始终写 `audit-report.md`;接受时非 bundled 写 `best.md`、bundled 写 `proposed.md`;**绝不覆盖**目标 `SKILL.md`。

它是"skill 创作"的*流水线层*,不是创作本身。作者仍然写正文;skill-forge 做的是审计、判分、竞态检测、安全落地。

### ✨ 好 skill 的 8 条标准

这 8 条标准是 2026-10-15 Perplexity 审计(`docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md`)后整理,并已写进 `docs/PRINCIPLES.md`。
它们是判断一个 skill 是否合格的总分细则。`validate_skill_frontmatter()` 和 `validate_skill_body()` 把第 **1、2、3、8** 条自动化成检查;第 **4、5、6、7** 条是流程/架构层面的,需要人 review。

| # | 标准 | 含义 | 由谁强制 |
|---|---|---|---|
| **1** | **描述是路由触发器,不是自我介绍** | 以 `Use when…` 或 `Load when…` 开头,≤ 50 词,目标用户意图而非工作流。触发短语**不要**在 `description`、`triggers:`、`when_to_use:` 三处重复。 | `validate_skill_frontmatter`(前缀检查 + 50 词封顶) |
| **2** | **Skill 是文件夹,不是单文件** | Hub-and-spoke:`SKILL.md`(精简 hub,~150 行)+ `scripts/` `references/` `assets/`(按需加载的 spoke)。重内容放 `references/`,不放正文。 | `validate_skill_body`(正文 > 150 行但无 `references/` 或 `assets/` 时报警) |
| **3** | **Gotcha 是最高价值内容** | 正文必须有 gotcha 风格小节:`## Common Rationalizations`、`## Red Flags`、`## Anti-Patterns`、`## Pitfalls`、`## When it fails` 之一。Gotcha 把"观察到的失败"转成可复用的规则。 | `validate_skill_body`(对 `##` 标题做正则检查) |
| **4** | **每句过 Pascal 测试** | "没有这句,agent 会不会失败?"不会,就删。Iron Law 豁免。 | 人工 review(流程) |
| **5** | **Token 预算:100 / 5,000 / 无限** | **Index**(`name` + `description`,每会话,~100 tokens/skill);**Load**(完整正文,触发时,~5,000 tokens);**Runtime**(`scripts/`/`references/`/`assets/`,按需,无限)。 | 人工 review + `wc -w SKILL.md ≤ 1000` |
| **6** | **Action at a distance(远端作用)** | 改一个 skill 的 description 会破坏另一个 skill 的召回 —— 每个 description 都会动嵌入空间。保持描述短且唯一;改一个时,给相邻 skill 重跑 hero queries。 | MECE / 跨 skill 注册表(架构) |
| **7** | **先写 evals(hero queries)** | 一个合格的 skill 出厂要带 `references/hero-queries.md`:5-10 个正面查询(应匹配)、3-5 个负面(不应匹配)、3-4 个邻居混淆(可匹配但不是它)。先 eval 再 ship。 | 每个 skill 自己的 `references/hero-queries.md`(流程) |
| **8** | **目录名 == frontmatter `name`** | 目录就是 skill。`my-skill/SKILL.md` 必须声明 `name: my-skill`。不匹配会破坏 marketplace 查找。 | `validate_skill_frontmatter(skill_dir=...)`(目录名匹配检查) |

这 8 条是**道**。其下**术**(6 阶段流水线、判分器、物化、竞态检测)是 README 剩余部分。

### 为什么要一条流水线

一个 skill 失败通常是这三种之一:描述不触发(是 `routing`)、正文太薄(是 `prompt`)、正文引用的代码不存在(是 `contract`)。没有分类器,你只能三种都改然后碰运气。有 `skill-forge` 的六阶段,你只改审计指出的那一种。

第四阶段(Verify)的判分是真正的差异:同一个候选通过(确定性 + 跳过评分 + 跳过 spot = `accept`),所以"无意义重写"是被证明无害的;带 `TODO` 的候选直接拒绝,所以"我等下再补完"不能蒙混过关;`description` 是 YAML 列表时,`isinstance(desc, str)` 守卫会拒绝而不是抛 `AttributeError`,所以半成品 frontmatter 在闸口就被截住。

第五阶段(Materialize)是安全故事的本体:一个 bundled skill(出现在 `~/.gbrain/install.json` 里的)被**拒绝**写入。候选落到同目录的 `proposed.md`;bundled 的 `SKILL.md` 始终不动。`.skill-forge-baseline.json` 记录上一次成功运行时的 SHA,下一次运行比对 —— 如果 audit 和 materialize 之间你手改了 `SKILL.md`,bundled 路径直接 `exit 3` 拒绝,非 bundled 路径走 `[WARN]` 放行。

`audit-report.md` 现在也会在 verdict 非平凡时(对应 `prompt` / `routing` / `contract`)输出 **Suggested gotchas** 章节。这是 gotcha 飞轮的输入端:1-2 条针对该 root cause 的、精心写好的建议,作者可以原样贴进目标 skill 的 Red Flags / Anti-Patterns。没有这个,飞轮没燃料,gotcha 就永远冻在 v0.2.0。

### 为什么不直接用 `skill-creator`(或 `skill-writer`)

README 存在的全部意义就是把这点说清楚。老实说,`skill-creator` 和 `skill-writer` 解决的是一个更小的问题:它们接一个 prompt、一次性写一个 `SKILL.md`。`skill-forge` 假设的是:**作者在迭代一个已有 skill,要一个带闸门、带审计、失败安全的循环**。两者是互补的、不是互相替代。

| 维度 | `skill-creator`(gbrain) | `skill-creator`(`init_skill.py` 脚手架) | `skill-writer`(典型) | `skill-forge` v0.2 |
|---|---|---|---|---|
| **输出** | 一份 95 行的 LLM 写作配方 | 一个 378 行的 Python 脚手架,创建目录 + 模板化 `SKILL.md` | 一次性改写/脚手架(各家不一) | 一条 6 阶段 CLI 流水线,带审计、判分、竞态检测、物化步骤 |
| **Frontmatter 校验** | 模板说明;告诉 LLM 用 YAML block-scalar | 无 — 模板就是 `description: [TODO: …]` | 无 / 极弱 | `frontmatter.load()` 强制执行首条 `---` 之后的栅栏规则(RULING-3);未引号的 `:` 或 `'` 直接拒(RULING-5);并检查前缀 / 50 词 / 目录名匹配 |
| **正文校验** | 无 | 无 | 无 | `validate_skill_body()` 检查 gotcha 小节 + 大正文下 `references/`/`assets/` 存在性 |
| **失败分类器** | 无 | 无 | 无 | `audit.py` 返回 `prompt` / `routing` / `contract` / `missing` / `other` 之一,带置信度和 `recommend_scope`;scope 是**类型化的**,不是字符串匹配 |
| **三路判分闸门** | 无 | 无 | 无 | 确定性 + LLM 评分 + spot-check;评分器缺省 ≠ 失败(RULING-1);`baseline` 进 rubric prompt(v2-T2),真实 LLM 可以做候选 vs baseline 对比 |
| **Bundled-skill 安全** | 无 — LLM 就直接写 | 无 — `init_skill.py` 在请求路径下写新目录,只在目录已存在时拒绝 | 无 | `is_bundled(skill_dir)` 读 `~/.gbrain/install.json`,marketplace install 拒绝转发;候选落 `proposed.md`,bundled `SKILL.md` 不动 |
| **并发编辑安全** | 无 | 无 | 无 | `.skill-forge-baseline.json` 记录上一次 `SKILL.md` 的 SHA;下次运行比对,bundled 漂移 → `exit 3`,非 bundled 漂移 → `[WARN]` 放行 |
| **CI 可读退出码** | n/a(配方) | `0` 或 `1`(Python 脚本) | n/a | `0` 接受 · `2` 拒绝 · `3` 竞态(Default Decision #3);不同失败模式用不同码 |
| **审计轨迹** | 无 | 无 | 无 | `audit-report.md`(总是写,带 `root_cause`、`verdict` 和 **Suggested gotchas** 章节);`.skill-forge-baseline.json`(接受时写,带 `sha` 和 `ts`);纯文本 + 可解析 JSON |
| **MECE 检查** | 有(手工,LLM 自己做) | n/a | n/a | n/a — `skill-forge` 一次只处理一个 skill;MECE 是创建期问题,`skill-creator` 已覆盖 |
| **LLM 评分依赖** | 无(纯配方) | 无(纯脚手架) | 经常(一次性改写) | 可选 — `llm_call=None` 直接跳过评分(RULING-1);确定性 + spot 闸门无需 LLM 即可运行 |
| **运行依赖** | 任意 LLM 会话 | Python 3.11+ | 不一 | Python 3.11+;`PATH` 上可选 `gbrain` CLI;可选 `~/.gbrain/install.json`(缺失则 fail-open) |

**30 秒版总结**:`skill-creator` 和 `skill-writer` 回答的是*"这个 skill 应该说什么"*;`skill-forge` 回答的是*"我打算改的这个 skill 真的算改动吗?我会不会顺手把一个 marketplace install 搞坏?"*。如果你的工作流是"写一个新 skill 一次,发出去,继续下一个",`skill-creator` 就够了。如果你的工作流是"在一个 skill 上迭代,直到它在 holdout 集上分数好看,而且过程中不能搞坏 marketplace install",`skill-forge` 才是对的工具。

### 安装

```bash
git clone https://github.com/kizemo/skill-forge
cd skill-forge/skill-forge
pip install -e .
```

`pip install -e .` 把 `skill-forge` 控制台脚本放到 `PATH`(入口在 `pyproject.toml` 声明)。同一份代码也可以在 `skill-forge/` 目录下用 `python -m scripts.run` 运行。

### 快速开始

```bash
# 第一步:把目标 skill 复制到 scratch 目录(在读懂 bundled-skill 安全章节之前,
# 不要直接对 marketplace install 跑)。
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
│   ├── PRINCIPLES.md         # skill-forge 强制执行的规则(1-12)
│   ├── foundry-overview.md   # 首次触发时加载(~1700 tokens:安装/CLI/Phase 5/失败目录)
│   ├── foundry-details.md    # 仅在排错时加载(~5200 tokens:阶段细节/gbrain/判分器/安全)
│   ├── foundry.md            # 跳转页(保留一个 release 周期以兼容老链接)
│   ├── AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md  # 产生 7 个 gap 的审计
│   ├── SKILL_REFERENCE.md    # 按需加载的重量级参考(Output Format / Anti-Patterns / When it fails / Tools Used)
│   └── DEPLOYMENT.md         # 本地 Claude-skills 部署备查
├── scripts/                  # 可执行代码
│   ├── audit.py              # Phase 0:根因分类器
│   ├── bootstrap_benchmark.py # Phase 2:15 行 JSONL 生成器
│   ├── judge_triple.py       # Phase 4:确定性 + LLM 评分 + spot-check
│   ├── router.py             # Phase 3:gbrain 软绑定 + bundled-skill 短路
│   ├── run.py                # Phase 6 阶段 CLI + materialize
│   ├── _legacy_init_skill.py # create 范围 shim(skill-creator)
│   └── _lib/                 # 纯辅助(frontmatter、sha、baseline_log、bundle)
└── tests/                    # 98 个测试,按阶段分文件
```

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