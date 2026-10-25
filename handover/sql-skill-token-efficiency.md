# 移交:`sql-skill` 的 token 效率问题与方案

**日期:** 2026-10-25 · **给:** sql-skill 所属项目 · **来源:** skill-forge 的 token 效率审计
**依据:** Perplexity《Designing, Refining, and Maintaining Agent Skills》+ Anthropic 官方 `skill-creator` 的篇幅约定

---

## 1. 结论先说

**`sql-skill` 已经做对了最难的那一步 —— 它有 `chapters/`(10 章)+ `supporting/` 的渐进式披露结构。问题是 SKILL.md 把 chapters 的摘要又抄了一遍,加上 description 塞了 19 个短语。**

| 层级 | 实测 | 预算 | 判定 |
|---|---|---|---|
| **Index**(每会话都付) | description **221 tok** | ~100 | ✗ **超 2.2×** |
| **Load**(触发时) | 正文 **5,500 tok** | ~5,000 | ✗ **超 500** |
| **Files**(按需读) | `chapters/` 10 章 + `supporting/` | 无限 | ✓ **结构正确** |

**每次触发 ≈ 5,721 tok。** 相对 `evidence-skill` 的 2,577 tok,贵一倍多。

---

## 2. 问题一:description 里塞了 19 个 trigger 短语

现在的 frontmatter(**只有 name + description,没有独立的 `triggers:`**):

```yaml
description: "通用 SQL 编写专业度 Skill — PostgreSQL 视角。Use when writing enterprise
PostgreSQL queries, debugging slow queries, deciding between index types (B-Tree / GIN /
BRIN / Hash), reading EXPLAIN ANALYZE plans, using JSONB / array / GIN indexes, querying
via postgres_fdw cross-DB, handling Chinese schema columns (双引号 / 假名 / date SUBSTR),
or evaluating query plan operators (Seq Scan / Index Scan / Hash Join / Sort). Triggers:
'sql skill', 'PG performance', 'index decision', 'EXPLAIN ANALYZE', 'jsonb_path_ops',
'GIN index', 'BRIN time-series', 'taobao.mart_X', 'postgres_fdw', 'pg_stat_statements',
'jsonb @>', 'Chinese column', 'shop_name 假名', 'SUBSTR date', 'array unnest', 'pgbouncer
session', 'OFFSET keyset', 'pg 索引', 'explain 解读'."
```

**101 词 / 221 tok。** Perplexity 的规则是 **≤ 50 词**,且"**2-3 examples usually cover 80/20**"。这里有 19 个。

**更关键的是:正文里已经有 `## Chapter Index` 把 10 章列出来了。** 19 个短语里的一大半(`taobao.mart_X`、`shop_name 假名`、`SUBSTR date`、`array unnest`、`pgbouncer session`)是**业务特定**的词,不是通用 SQL 意图 —— 它们把 index 层变成了一个业务词表。

**方案:**

```yaml
---
name: sql-skill
description: >-
  Use when writing or debugging enterprise PostgreSQL queries — index selection
  (B-Tree / GIN / BRIN), reading EXPLAIN ANALYZE plans, JSONB and array
  columns, cross-DB via postgres_fdw, and Chinese-schema column quirks.
triggers:
  - "sql skill"
  - "PG performance"
  - "index decision"
  - "EXPLAIN ANALYZE"
  - "GIN index"
  - "BRIN time-series"
  - "jsonb @>"
  - "postgres_fdw"
  - "OFFSET keyset"
  - "explain 解读"
---
```

- description 降到 **~35 词 / ~85 tok**
- `triggers:` 成为唯一的短语清单(通用意图为主)
- 业务特定词(`taobao.mart_X`、`shop_name 假名`)**移出 index 层**,改放进 `chapters/` 的检索路径和 `supporting/`(它们是"要查什么内容"的线索,不是"何时加载这个 skill"的线索)
- 预计 index 层 **221 → ~120 tok**

> 收益不止这一项:本机 63 个 skill 的 index 层总和,每个都在收这份税。

---

## 3. 问题二:12 大框架内联在正文,与 chapters 重复

正文 412 行里,最重的一块是 `## Core Frameworks & Mental Models(12 大)`:

```
### 1.  SQL 执行顺序 — FROM → WHERE → …          6 行
### 2.  NULL 三值逻辑 — `NULL = NULL` 是 NULL    7 行
### 3.  索引选择 — B-Tree 默认 / GIN 多值 …       8 行
### 4.  WHERE 索引失效 — 函数 / 隐式 cast …       7 行
### 5.  JOIN 算法 — Nested Loop / Hash Join …     6 行
### 6.  ORDER BY / GROUP BY 索引                  6 行
### 7.  分页 Top-N vs keyset                     7 行
### 8.  EXPLAIN ANALYZE 是唯一真相                7 行
### 9.  JSONB vs JSON                            7 行
### 10. array 列决策                             7 行
### 11. postgres_fdw 跨 DB                       7 行
### 12. 慢 query 排查 SOP                         9 行
```

**≈ 85 行 / ~1,700 tok。**

**但这 12 条,chapters 里已经全都写过一遍:**

| 内联框架 | 已有章节 |
|---|---|
| 1 SQL 执行顺序 · 2 NULL 三值逻辑 | [ch01 SQL 语法铁律](chapters/ch01-grammar.md)(8 子句执行顺序 / 别名作用域 / NULL 三值逻辑 / 风格铁律) |
| 3 索引选择 · 4 WHERE 索引失效 · 6 排序分组索引 · 7 分页 Top-N | [ch08 索引与性能](chapters/ch08-indexes-perf.md)(索引结构 / WHERE 索引 / JOIN 算法 / 排序分组 / 分页窗口 / EXPLAIN ANALYZE) |
| 5 JOIN 算法 | ch02(ch02-joins.md,JOIN 7 种 + 性能差异) |
| 9 JSONB vs JSON · 10 array 列决策 · 11 postgres_fdw | [ch07 PostgreSQL 特有](ch07-pg-specific.md)(JSONB / array / GIN / FDW 2-segment / 中文 schema 雷区) |
| 8 EXPLAIN ANALYZE | ch08 |
| 12 慢 query 排查 SOP | ch08 / ch09 |

**Perplexity 的判据直接适用:**"Every sentence has to earn its place." —— 这 12 段是 chapters 的**摘要副本**,而 `chapters/` 已经是 runtime 层(按需读)。摘要在 load 层重复一遍,就是白付一次钱。

**方案(选 A 或 B):**

**方案 A(推荐):12 大框架整体移出正文,换成一张路由表**

```markdown
## Core Frameworks 速查(按需读)

| 框架 | 读哪一章 |
|---|---|
| SQL 执行顺序 · NULL 三值逻辑 · 风格铁律 | [ch01](chapters/ch01-grammar.md) |
| JOIN 7 种 + 性能差异 | [ch02](chapters/ch02-joins.md) |
| JSONB / array / GIN / FDW 2-segment / 中文 schema 雷区 | [ch07](chapters/ch07-pg-specific.md) |
| 索引结构 · WHERE 索引失效 · JOIN 算法 · 排序分组 · 分页窗口 · EXPLAIN ANALYZE | [ch08](chapters/ch08-indexes-perf.md) |
| 7 类 25+ 反模式 | [ch09](chapters/ch09-antipatterns.md) |
```

正文保留 12 行表格,删掉 85 行摘要。**省 ~1,550 tok。**

**方案 B(保守):框架留在正文,但每条压到 2 行(只留结论 + 指针)**

```markdown
### 3. 索引选择 — B-Tree 默认 / GIN 多值 / BRIN 时序 / Hash 几乎不用
→ 详见 [ch08](chapters/ch08-indexes-perf.md)
```

12 条 × 2 行 = 24 行,**省 ~1,100 tok**,且"最常被问的 12 件事"仍然直接可见。**如果你担心纯表格会丢掉"agent 该想到去查索引"这个信号,选 B。**

---

## 4. 问题三:Layer 0 的 Obsidian 检索说明 ~23 行

`### Layer 0: 直接 Read + Grep 检索 Obsidian SQL vault(NEW · v2.1)`(23 行)+ `Layer 0+`(5 行)+ `其他入口`(10 行)= **38 行**,描述的是**怎么用这个 skill**(去哪个 vault 路径、怎么 grep)。

**方案:** 这类"使用说明"里,真正必须常驻的只有"**去哪找**"一行;具体 grep 命令与 vault 路径细节属于**按需细节**。

- 正文保留:一行"知识源在 `E:/obsidian/SQL/`,章节映射见 `supporting/`;先用 Grep 定位主题,再 Read 对应 chapter"
- 23 行 → 1 行,**省 ~450 tok**
- 详细检索策略(路径、命令、fallback 顺序)→ `supporting/retrieval.md`,由 Layer 0 小节指向它

---

## 5. 问题四:`Chapter Index` 15 行(可选)

`## Chapter Index(10 章)` 那张表列了每章的"关键内容 + 状态 ✅"。15 行里,状态列(`✅ Phase 2 完成`)**是开发过程信息,不是给 agent 的检索信息**。

**方案:** 删掉"状态"列,只留 `# | 主题 | 关键内容`;`#` 列本身可以只留章号(链接已经给了路径)。压到 8 行。**省 ~200 tok。**

---

## 6. 改完之后

| | 现在 | 方案 A | 方案 B |
|---|---|---|---|
| index | 221 tok | ~120 tok | ~120 tok |
| load | 5,500 tok | ~3,300 tok | ~3,750 tok |
| **每次触发合计** | **5,721** | **~3,420** | **~3,870** |
| 降幅 | — | **-40%** | **-32%** |

方案 A + Layer 0 压缩 + Chapter Index 压缩三项都做,正文约 5,500 → ~3,000 tok,仍在 5,000 预算内且留有余量。

**Anthropic 官方对照:** "**SKILL.md body** - In context whenever skill triggers (**<500 lines** ideal)" —— 改后约 240 行,达标。

---

## 7. 验收标准

| 检查 | 目标 |
|---|---|
| description 词数 | ≤ 50 词 |
| index 层 token | ≤ ~120 tok |
| 正文字数 | ≤ ~3,300 tok / ≤ 250 行 |
| `chapters/` + `supporting/` | **不变**(这是你已经做对的部分) |
| 12 大框架 | 要么在正文只留路由表,要么每条 ≤ 2 行 + 指针 |
| 触发一次的上下文 | ≤ ~3,500 tok(当前 5,721) |

**回归检查:** 改 description 时**一次只改 1-2 个词、每步跑一次 eval**。sql-skill 与 evidence-skill 有重叠意图(都在 PostgreSQL 侧),改任一方的 description 前,**先重跑对方的 eval** —— Perplexity 明写:"Adding a new Skill can break other pre-existing Skills." 建议补一个邻居混淆 eval:`"evidence 报表加了个新过滤维度"` 应命中 evidence-skill 而不是 sql-skill。

---

## 8. 附:完整 token 测量口径

CJK ≈ 1 token/char,latin ≈ 1 token/3.5 chars。测量脚本在 skill-forge 审计里,口径一致。
