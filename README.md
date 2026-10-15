# skill-forge

> A six-phase meta-skill for auditing, creating, improving, and retiring other skills — with a deterministic + LLM-rubric judge, bundled-skill safety, and a SHA-baseline race check that refuses to overwrite a marketplace install.

<div align="right">

[🇺🇸 **English**](#-english) · [🇨🇳 **中文**](#-中文)

</div>

---

<a id="-english"></a>

## 🇺🇸 English

### What is skill-forge?

`skill-forge` is a CLI pipeline that turns *"this skill isn't working"* into a measurable, auditable, safe-to-fail loop. It does not write skills itself — it audits the failure, judges the candidate with a deterministic + LLM-rubric gate, and writes the new content to a non-source file (`best.md` for local skills, `proposed.md` for bundled marketplace installs) so the user can diff and merge by hand.

The author still writes the body. `skill-forge` is the pipeline *around* the author: 6 phases (audit → scope → bootstrap → forward → verify → materialize) that fail loudly and never overwrite a marketplace install.

### Why a pipeline at all?

A skill usually fails for one of three reasons — and the fix differs:

| Failure | Branch | What the fix looks like |
|---|---|---|
| Description doesn't trigger | `routing` | Rewrite the `description` and `triggers` blocks |
| Body is too thin | `prompt` | Add a verification checklist, an Anti-Patterns section, or an explicit `When to use` example |
| Body references code that doesn't exist | `contract` | Drop the dead reference or implement it |

Without a classifier you fix all three and hope. With `skill-forge`'s Phase 0 you fix only the one the audit named.

The Phase 4 judge is what makes the difference: an identical candidate passes (deterministic + skip rubric + skip spot = `accept`), so a no-op rewrite is provably safe. A candidate with `TODO` markers refuses. A candidate whose `description` is a YAML list refuses instead of raising. The materialize phase (5) writes the candidate to `best.md` or `proposed.md` and pins a SHA baseline; the next run detects drift and refuses to clobber a marketplace install.

### Why not just use `skill-creator` (or `skill-writer`)?

`skill-creator` and `skill-writer` answer *"what should this skill say?"*. `skill-forge` answers *"is the skill I'm about to change actually a change, and am I about to break a marketplace install?"*. The two are complementary, not substitutable.

| Dimension | `skill-creator` (gbrain marketplace) | `skill-creator` (`init_skill.py` scaffold) | `skill-writer` (typical) | `skill-forge` v0.2 |
|---|---|---|---|---|
| **Output** | A 95-line LLM-authoring recipe the LLM follows by hand | A 378-line Python scaffold that creates a directory + templated `SKILL.md` | A one-shot rewrite / scaffold (varies) | A 6-phase CLI pipeline with audit, judge, race check, and materialize |
| **Frontmatter validation** | Template instructions; the LLM is told to use YAML block-scalar | None — template is plain `description: [TODO: …]` | None / minimal | `frontmatter.load()` enforces the first-`---`-after-line-1 fence rule (RULING-3); refuses unquoted `:` or `'` literals (RULING-5) |
| **Failure classifier** | None | None | None | `audit()` returns one of `prompt` / `routing` / `contract` / `missing` / `other` with a confidence score and a typed `recommend_scope` |
| **Triple-judge gate** | None | None | None | Deterministic + LLM rubric + spot-check; absent rubric ≠ failure (RULING-1); `baseline` is consumed in the rubric prompt so a real LLM call can compare candidate vs. baseline |
| **Bundled-skill safety** | None — the LLM just writes whatever was asked | None — `init_skill.py` writes a new directory under the requested path, refuses only if the directory already exists | None | `is_bundled(skill_dir)` reads `~/.gbrain/install.json` and refuses to forward a marketplace install; candidate lands in `proposed.md`, the bundled `SKILL.md` is never overwritten |
| **Concurrent-edit safety** | None | None | None | `.skill-forge-baseline.json` records the `SKILL.md` SHA from the last run; the next run compares and refuses a bundled drift with exit `3` (or `[WARN]`-and-proceed for a non-bundled drift) |
| **CI-readable exit codes** | n/a (recipe) | `0` / `1` | n/a | `0` accept · `2` refuse · `3` race — distinct codes for distinct failure modes |
| **Audit trail** | None | None | None | `audit-report.md` (always) + `.skill-forge-baseline.json` (on accept); plain text and parseable JSON |
| **MECE check** | Yes (manual, by the LLM) | n/a | n/a | n/a — `skill-forge` operates on one skill at a time; MECE is a *creation-time* concern that `skill-creator` already handles |
| **LLM rubric dependency** | None (recipe-only) | None (scaffold-only) | Often (one-shot rewrite) | Optional — `llm_call=None` skips the rubric entirely; the deterministic + spot gates run without an LLM |
| **Operating envelope** | 95 lines of markdown; works in any LLM session | 378-line Python script; needs Python 3.11+ | Varies | Python 3.11+; optional `gbrain` CLI on `PATH`; optional `~/.gbrain/install.json` (fail-open if missing) |

**The 30-second version**: pick `skill-creator` or `skill-writer` when you're *writing a new skill once* and shipping it. Pick `skill-forge` when you're *iterating on an existing skill* and want a gated, auditable, CI-routable, marketplace-safe pipeline.

### Quick start (90 seconds)

```bash
# Read the package README first.
cat skill-forge/README.md

# Then install:
cd skill-forge
pip install -e .
pytest -q                       # 58 passed

# Smoke run:
python -m scripts.run --skill . --scope audit-only
```

For a real run, copy a target skill to a scratch dir first:

```bash
cp -r ~/.claude/plugins/marketplaces/gbrain/plugin/skills/my-skill C:/Temp/e2e-target/
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope improve
```

### Where the docs live

| Doc | Path | What it is |
|---|---|---|
| **Package README** | [`skill-forge/README.md`](skill-forge/README.md) | Bilingual install / quick start / exit codes / rulings (the deep operational doc) |
| **Heavy reference** | [`skill-forge/docs/foundry.md`](skill-forge/docs/foundry.md) | ~670-line deep dive: phase semantics, the file-state model, RULING-1..10 ledger, failure catalog, change-log, every detail this README skips |
| **Local deployment** | [`skill-forge/docs/DEPLOYMENT.md`](skill-forge/docs/DEPLOYMENT.md) | The PowerShell junction + `pip install -e .` recipe that puts skill-forge at `~/.claude/skills/skill-forge/` for cc-haha / Claude Code discovery |
| **SKILL.md (entry)** | [`skill-forge/SKILL.md`](skill-forge/SKILL.md) | The gbrain-conformance frontmatter that the LLM reads when invoking the skill |
| **SKILL reference** | [`skill-forge/docs/SKILL_REFERENCE.md`](skill-forge/docs/SKILL_REFERENCE.md) | Heavy reference split off from SKILL.md: Output Format, Anti-Patterns, When it fails, Tools Used (loaded on demand, not on every invocation) |
| **Skill-writing principles** | [`skill-forge/docs/PRINCIPLES.md`](skill-forge/docs/PRINCIPLES.md) | The 8 frontmatter principles + body principles + safety principles that `skill-forge` itself follows and enforces. `validate_skill_frontmatter()` in code catches violations and surfaces them as evidence in `audit-report.md` |
| **Spec** | [`analysis-2026-10-14.md`](analysis-2026-10-14.md) | The v0 spec that started the project |

### Skill-writing principles (self-imposed)

`skill-forge` follows — and now *enforces* in code — the 8 frontmatter principles documented in [`skill-forge/docs/PRINCIPLES.md`](skill-forge/docs/PRINCIPLES.md):

1. **Concise description** (recommended ≤ 1024 chars; one sentence + concrete triggers)
2. **YAML block scalar** (`>-` or `|`) when the description contains `:` or `'`
3. **Explicit `triggers:` list** (≥ 3 concrete user phrases)
4. **`mutating:` boolean** declared
5. **`name:` is lowercase kebab-case**
6. **`brain_first:` declared** (gbrain convention)
7. **`when_to_use:`** one-line summary
8. **`version:`** semver (MAJOR.MINOR.PATCH)

A target skill that fails any of these gets a warning in `audit-report.md` (evidence list). Warnings are **non-fatal** — `skill-forge` does not refuse a skill on principle violations; the materialize still runs and the author reviews the warnings. The 6-phase pipeline is the safety property, the principles are the maintainability property.

Progressive disclosure: the frontmatter is always loaded; the lean body is loaded on demand; the heavy reference (`docs/SKILL_REFERENCE.md`) is loaded only when troubleshooting.

### State

| | |
|---|---|
| Latest commit | `d019eb9` (on `main`) |
| Tag | `v0.2.0-rc1` |
| Tests | 76 (all green; 58 from v0.2.0 + 18 new for `validate_skill_frontmatter()`) |
| License | None — default copyright. Add a `LICENSE` to grant downstream rights. |

---

<a id="-中文"></a>

<details>
<summary><strong>🇨🇳 中文 — 点击展开</strong></summary>

# skill-forge

> 一个六阶段的元技能,用于审计、创建、改进、退休其他 skill — 带确定性 + LLM 评分闸门、bundled-skill 安全保护、SHA 竞态检测(在 race 情况下拒绝覆盖 marketplace install)。

### 什么是 skill-forge?

`skill-forge` 是一条 CLI 流水线,把"这个 skill 不工作"翻译成可测量、可审计、失败安全的循环。它不直接写 skill — 它审计失败原因,用确定性 + LLM-评分闸门评判候选内容,然后把新内容写到**非源文件**(`best.md` 给本地 skill,`proposed.md` 给 bundled marketplace install),让用户 diff 后手动合并。

作者还是写正文。`skill-forge` 是套在作者周围的流水线:6 个阶段(audit → scope → bootstrap → forward → verify → materialize),大声失败,绝不覆盖 marketplace install。

### 为什么要流水线?

一个 skill 通常因为三种原因之一失败 — 修法各不相同:

| 失败 | 分支 | 修法 |
|---|---|---|
| 描述不触发 | `routing` | 重写 `description` 和 `triggers` 块 |
| 正文太薄 | `prompt` | 加 verification checklist、Anti-Patterns 段、显式 `When to use` 示例 |
| 正文引用的代码不存在 | `contract` | 删掉死引用,或把代码补上 |

没有分类器你只能三种都改然后碰运气。`skill-forge` 的 Phase 0 只让你改审计指出的那一种。

Phase 4 闸门是关键差异:同一个候选通过(确定性 + 跳过评分 + 跳过 spot = `accept`),所以"无意义重写"是被证明无害的;带 `TODO` 的候选直接拒绝;`description` 是 YAML 列表时,`isinstance(desc, str)` 守卫会拒绝而不是抛 `AttributeError`。Phase 5 物化把候选写到 `best.md` / `proposed.md`,并钉一份 SHA baseline;下次运行检测到漂移就拒绝覆盖 marketplace install。

### 为什么不直接用 `skill-creator`(或 `skill-writer`)?

`skill-creator` 和 `skill-writer` 回答的是"这个 skill 应该说什么"。`skill-forge` 回答的是"我打算改的这个 skill 真的算改动吗?我会不会顺手把 marketplace install 搞坏"。两者互补,不是替代。

| 维度 | `skill-creator`(gbrain marketplace) | `skill-creator`(`init_skill.py` 脚手架) | `skill-writer`(典型) | `skill-forge` v0.2 |
|---|---|---|---|---|
| **输出** | 95 行的 LLM 写作配方 | 378 行的 Python 脚手架,创建目录 + 模板化 `SKILL.md` | 一次性改写 / 脚手架(各家不一) | 6 阶段 CLI 流水线,带审计、判分、竞态检测、物化 |
| **Frontmatter 校验** | 模板说明;告诉 LLM 用 YAML block-scalar | 无 — 模板是 `description: [TODO: …]` | 无 / 极弱 | `frontmatter.load()` 强制执行首条 `---` 之后的栅栏规则(RULING-3);未引号的 `:` 或 `'` 直接拒(RULING-5) |
| **失败分类器** | 无 | 无 | 无 | `audit()` 返回 `prompt` / `routing` / `contract` / `missing` / `other` 之一,带置信度和**类型化**的 `recommend_scope` |
| **三路判分闸门** | 无 | 无 | 无 | 确定性 + LLM 评分 + spot-check;评分器缺省 ≠ 失败(RULING-1);`baseline` 进 rubric prompt,真实 LLM 可以做候选 vs baseline 对比 |
| **Bundled-skill 安全** | 无 — LLM 就直接写 | 无 — `init_skill.py` 在请求路径下写新目录,只在目录已存在时拒绝 | 无 | `is_bundled(skill_dir)` 读 `~/.gbrain/install.json`,marketplace install 拒绝转发;候选落 `proposed.md`,bundled `SKILL.md` 不动 |
| **并发编辑安全** | 无 | 无 | 无 | `.skill-forge-baseline.json` 记录上一次 `SKILL.md` 的 SHA;下次运行比对,bundled 漂移 → `exit 3`,非 bundled 漂移 → `[WARN]` 放行 |
| **CI 可读退出码** | n/a(配方) | `0` / `1` | n/a | `0` 接受 · `2` 拒绝 · `3` 竞态 — 不同失败模式用不同码 |
| **审计轨迹** | 无 | 无 | 无 | `audit-report.md`(总是写) + `.skill-forge-baseline.json`(接受时写);纯文本 + 可解析 JSON |
| **MECE 检查** | 有(手工,LLM 自己做) | n/a | n/a | n/a — `skill-forge` 一次只处理一个 skill;MECE 是创建期问题,`skill-creator` 已覆盖 |
| **LLM 评分依赖** | 无(纯配方) | 无(纯脚手架) | 经常(一次性改写) | 可选 — `llm_call=None` 直接跳过评分;确定性 + spot 闸门无需 LLM 即可运行 |
| **运行依赖** | 任意 LLM 会话 | Python 3.11+ | 不一 | Python 3.11+;`PATH` 上可选 `gbrain` CLI;可选 `~/.gbrain/install.json`(缺失则 fail-open) |

**30 秒版总结**:你要**写一个新 skill 一次发出去**时用 `skill-creator` 或 `skill-writer`。你要**在一个已有 skill 上迭代**,要一个带闸门、带审计、CI 可路由、marketplace 安全的流水线时,用 `skill-forge`。

### 快速开始(90 秒)

```bash
# 先读包内 README。
cat skill-forge/README.md

# 然后安装:
cd skill-forge
pip install -e .
pytest -q                  # 58 通过

# smoke run:
python -m scripts.run --skill . --scope audit-only
```

要跑真实目标,先把目标 skill 复制到 scratch 目录:

```bash
cp -r ~/.claude/plugins/marketplaces/gbrain/plugin/skills/my-skill C:/Temp/e2e-target/
python -m scripts.run --skill C:/Temp/e2e-target/my-skill --scope improve
```

### 文档位置

| 文档 | 路径 | 内容 |
|---|---|---|
| **包 README** | [`skill-forge/README.md`](skill-forge/README.md) | 双语安装 / 快速开始 / 退出码 / 规则(深度操作文档) |
| **大而全的参考** | [`skill-forge/docs/foundry.md`](skill-forge/docs/foundry.md) | ~670 行深潜:阶段语义、文件状态模型、RULING-1..10 台账、失败目录、变更日志、本 README 跳过的所有细节 |
| **本地部署** | [`skill-forge/docs/DEPLOYMENT.md`](skill-forge/docs/DEPLOYMENT.md) | PowerShell junction + `pip install -e .` 配方,把 skill-forge 放到 `~/.claude/skills/skill-forge/` 给 cc-haha / Claude Code 发现 |
| **SKILL.md(入口)** | [`skill-forge/SKILL.md`](skill-forge/SKILL.md) | LLM 调用 skill 时读的 gbrain-conformance frontmatter |
| **SKILL reference** | [`skill-forge/docs/SKILL_REFERENCE.md`](skill-forge/docs/SKILL_REFERENCE.md) | 从 SKILL.md 拆出的重参考:Output Format / Anti-Patterns / When it fails / Tools Used(按需加载,非每次调用都读) |
| **skill 撰写原则** | [`skill-forge/docs/PRINCIPLES.md`](skill-forge/docs/PRINCIPLES.md) | `skill-forge` 自己遵循并在代码中**强制**的 8 条 frontmatter 原则 + body 原则 + 安全原则。`validate_skill_frontmatter()` 把违反写到 `audit-report.md` 的 evidence 列表 |
| **规格** | [`analysis-2026-10-14.md`](analysis-2026-10-14.md) | 启动本项目的 v0 规格 |

### skill 撰写原则(自我约束)

`skill-forge` 遵循 — 并且现在在代码中**强制** — [`skill-forge/docs/PRINCIPLES.md`](skill-forge/docs/PRINCIPLES.md) 里文档化的 8 条 frontmatter 原则:

1. **描述简洁**(推荐 ≤ 1024 字;一句话 + 具体 triggers)
2. **YAML block scalar**(`>-` 或 `|`)— 描述含 `:` 或 `'` 时
3. **显式 `triggers:` 列表**(≥ 3 条具体用户短语)
4. **`mutating:` 布尔**必须声明
5. **`name:` 小写 kebab-case**
6. **`brain_first:` 声明**(gbrain 约定)
7. **`when_to_use:`** 一句话总结
8. **`version:`** semver(MAJOR.MINOR.PATCH)

违反任一原则的目标 skill,审计时会在 `audit-report.md` evidence 列表里出 warning。Warning 是**非致命的** — skill-forge 不会因为原则违反拒绝一个 skill;物化照跑,作者读 warning 自己改。6 阶段流水线是**安全**属性,原则是**可维护性**属性。

渐进式披露:frontmatter 永远加载;精简 body 按需加载;重参考(`docs/SKILL_REFERENCE.md`)只在排查时才读。

### 当前状态

| | |
|---|---|
| 最新 commit | `d019eb9`(在 `main`) |
| Tag | `v0.2.0-rc1` |
| 测试 | 76(全绿;v0.2.0 的 58 + `validate_skill_frontmatter()` 的 18 个新测试) |
| 许可证 | 无 — 默认保留所有权利。加一个 `LICENSE` 文件即可向下游授权。 |

</details>
