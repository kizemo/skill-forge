# 移交:`evidence-skill` 的 token 效率问题与方案

**日期:** 2026-10-25(第二版,用 skill-forge 新增的 cost 轴实测复核)
**给:** evidence-skill 所属项目 · **来源:** skill-forge 的 token 效率审计
**依据:** Perplexity《Designing, Refining, and Maintaining Agent Skills》+ Anthropic 官方 `skill-creator` 的篇幅约定

---

## 1. 结论先说

**`evidence-skill` 的渐进式披露结构是对的 —— 这是它比 `sql-skill` 好得多的地方。问题只剩两个:index 层超预算,和正文里两段重复的索引表。**

用 skill-forge 自己的 cost 轴实测:

| 层级 | 实测 | 预算 | 判定 |
|---|---|---|---|
| **Index**(每会话都付) | **217 tok** | ~100 | ✗ 超 117 |
| **Load**(触发时) | 2,445 tok | ~5,000 | ✓ 合格,余量充足 |
| **Files**(按需读) | 13,769 tok(5 个文件) | 无限 | ✓ **结构正确** |

**触发一次的上下文 ≈ 2,662 tok。**

skill-forge validator 对它只报 **1 条**警告(index 层)。其余 8 条规范它都过了。

---

## 2. 问题一:index 层 217 tok,超预算 117

现在的 frontmatter:

```yaml
description: >-
  Use when configuring, debugging, or designing Evidence BI Core 2026 pages on
  bi.jury.xin — charts, tables, filters, Chinese-schema SQL, nginx, themes, MCP,
  upgrades, and report-page UI contracts.
  Triggers: "evidence", "bi.jury.xin", "sales-bi", "Evidence 报表", "combo_chart",
  "legend", "page_size", "Evidence 部署", "FastMCP evidence".
triggers:
  - "evidence"
  - "bi.jury.xin"
  - "sales-bi"
  - "Evidence 报表 / 页面 / 组件 / 部署"
  - "combo_chart / legend / page_size / 瀑布图"
  - "Evidence 升级 / MCP / FastMCP"
mutating: true
brain_first: exempt
when_to_use: "Use when the user asks about Evidence BI Core 2026 pages, charts, tables, SQL, deployment, or upgrade."
version: 0.3.0
```

**三个地方各写了一遍同一批短语:**
- description 内嵌 9 条(`Triggers:` 子句)
- `triggers:` 6 条
- `when_to_use:` 又把"charts, tables, SQL, deployment, upgrade"重述一遍

**为什么这值得改:** index 层是**每个会话、每个用户**都付的钱,不随是否触发而变。你本机 63 个 skill,这一项乘以 63 —— 按当前写法,仅这一项就在每会话收约 13,700 tokens。

**Perplexity 的规则:** index 层 ~100 tokens/skill,description 里 **"2-3 examples usually cover 80/20"**,而且 description 要回答"何时加载"而非"它是干什么的"。
**Anthropic 官方 skill-creator 更直接:** "**Metadata** (name + description) - Always in context (~100 words)" —— **两个字段**。

**方案:**

```yaml
description: >-
  Use when configuring, debugging, or designing Evidence BI Core 2026 pages on
  bi.jury.xin — charts, tables, filters, Chinese-schema SQL, nginx, themes, MCP,
  upgrades, and report-page UI contracts.
triggers:
  - "evidence"
  - "bi.jury.xin"
  - "sales-bi"
  - "Evidence 报表 / 页面 / 组件 / 部署"
  - "combo_chart / legend / page_size / 瀑布图"
  - "Evidence 升级 / MCP / FastMCP"
mutating: true
brain_first: exempt
when_to_use: "Evidence BI Core 2026 pages on bi.jury.xin."
version: 0.3.0
```

三处改动:
1. **删掉 description 里的 `Triggers:` 子句**(9 条短语全部只在 `triggers:` 里)
2. **`when_to_use:` 压成一句 8 词的市场行摘要**,不再重述 trigger 短语
3. description 保留**能力范围**(configuring / debugging / designing + 领域词)—— 它要帮 resolver 判"该不该加载",这部分不能删

**预计 index → ~120 tok**(降 45%)。

> 对照 `sql-skill`:它连 `triggers:` 都没有,19 条短语全塞在 description 里,index 231 tok。**你有 `triggers:` 字段,只是没把 description 清干净** —— 这是最容易的一步。

---

## 3. 问题二:正文里 52 行是导航,不是决策信息

正文 156 行里,这两块是**索引/速查**,而它们的职责已经有专门文件承担:

| 章节 | 行数 | 已经有的对应物 |
|---|---|---|
| `## Quick Decision Table` | 26 | `references/cheatsheet.md`(203 行,含 14 张决策表) |
| `## Chapter Index` | 26 | `references/topic-index.md`(140 行,80+ 主题 → 章映射) |

**而且 `## References(按需加载)` 这张表已经写得很好了:**

```
| 文件 | 何时读 |
|---|---|
| `references/cheatsheet.md` | 14 决策表 + 12 阶段 actionable,决策快查 |
| `references/patterns.md` | 8 大模式 + 反模式表,复用现成方案 |
| `references/glossary.md` | 术语不熟 |
| `references/frameworks.md` | 需要解释"为什么" |
| `references/topic-index.md` | 80+ 主题 → 章映射,grep 不到时 |
```

**这张"文件 | 何时读"表就是 Perplexity 要求的 read-conditions 表** —— 它是全文最值钱的一块,**保留**。

**方案:**

1. **`Quick Decision Table`(26 行)→ 删。** 内容与 `references/cheatsheet.md` 重复;真要速查时,`References` 表已经指了路。若确有正文才有的部分(比如"最常见 3 个决策 → 读哪个文件"),压到 5 行以内。
2. **`Chapter Index`(26 行)→ 压到 5-8 行。** 只留"哪章解决什么问题"的一句话映射;详细摘要移进 `references/topic-index.md`。
3. **`Output Format`(9 行)/ `When it fails`(8 行)→ 移进 `references/`。** 按 Perplexity 的文件分工,SKILL.md 只留"必须立刻在上下文里的决策信息";输出格式和失败模式是**特定场景才需要**的。
4. **保留在正文**:`## When to use / NOT`(6)、`## Scope & Limits`(7)、`## Anti-Patterns(踩坑飞轮)`(15)、`## Verification`(8)、`## 沉淀回写 SOP`(13)。后三个是 Perplexity 说的"最高价值的 gotcha",触发时确实需要。

**预计正文 → ~100 行 / ~1,500 tok。**

---

## 4. 改完之后

| | 现在 | 改后 |
|---|---|---|
| index | 217 tok | **~120 tok** |
| load | 2,445 tok | **~1,500 tok** |
| files | 13,769 tok | 13,769 tok(不变) |
| **每次触发合计** | **2,662 tok** | **~1,620 tok** |
| 降幅 | — | **-39%** |

Anthropic 官方对照:body "< 500 lines" —— 改后约 100 行,达标。

---

## 5. 一个可选的小优化:长参考文件加目录

Anthropic 官方约定:"For large reference files (**>300 lines**), include a **table of contents**"。

| 文件 | 行数 | 是否需要目录 |
|---|---|---|
| `references/cheatsheet.md` | 203 | 可选 |
| `references/patterns.md` | 294 | 接近,建议加 |
| `references/glossary.md` | 161 | 否 |

`patterns.md` 加一个 8-10 行目录。成本很低,而且它是**按需读**的,不影响 index/load 层。

---

## 6. 验收标准

| 检查 | 目标 | 怎么验 |
|---|---|---|
| description 词数 | ≤ 50 词 | 现在 40 词(去掉 `Triggers:` 子句后) |
| description 内无 `Triggers:` 子句 | ✓ | 肉眼 |
| `when_to_use` 不重述 trigger 短语 | ✓ | 肉眼 |
| index 层 token | ≤ ~120 tok | `skill-forge --skill <dir> --scope audit-only`,看 `## Cost` 段的 index 行 |
| 正文字数 | ≤ ~1,500 tok | 同上,看 load 行 |
| `references/` 5 个文件 | 不变 | `ls references/` |
| `## References(按需加载)` 表 | **保留** | 肉眼 |
| 触发一次的实际上下文 | ≤ ~1,620 tok | 当前 2,662 |

**回归检查:** 改 description 时按 Perplexity 的协议**一次只改 1-2 个词、每步跑一次 eval**。加任何新 skill 后重跑邻居的 eval —— "Adding a new Skill can break other pre-existing Skills"。

**复审工具已就绪:** 改完直接跑
```bash
python -m scripts.run --skill <你的 skill 目录> --scope audit-only
```
报告里的 `## Cost` 段会直接给出 index / load / files 三层的实测值与预算对比,不需要人算。

---

## 7. 附:完整 token 测量口径

CJK ≈ 1 token/char,latin ≈ 1 token/3.5 chars。**index 层 = 整个 frontmatter**(每个字段都会被注入,不只 description)。测量实现:`skill-forge/scripts/_lib/token_cost.py`。
