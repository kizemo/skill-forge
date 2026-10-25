"""P0: the token cost axis — measure what a skill costs to load.

Perplexity's three tiers, each with its own budget and its own pain:

| Tier | Content | Budget | When paid |
|---|---|---|---|
| Index | `name` + `description` (+ the other always-loaded metadata) | ~100 tok | EVERY session, EVERY user |
| Load  | the `SKILL.md` body | ~5,000 tok | on every trigger |
| Files | `scripts/`, `references/`, `assets/` | unlimited | only when the agent reads one |

The index tier is the expensive one to ignore: it is paid by every user of
every session whether or not the skill is ever invoked, and it stacks across
the whole installed portfolio. The load tier is paid on every trigger. The
files tier has no budget — it is the escape valve for a body that is too big,
and a skill with no `references/` has nowhere to put the overflow.

Token estimation: CJK ≈ 1 token/char, latin ≈ 1 token/3.5 chars. This is an
estimate, not a tokenizer, and it is used for BUDGET COMPARISON, not for
billing. A real tokenizer would be more accurate but would add a dependency
and a per-call cost to every measurement.

**Reporting, not blocking.** The user ruled (2026-10-25): the 5,000-token
body ceiling is REPORTED, never enforced; the index tier is a WARNING. This
matches skill-forge's existing contract (RULING-1: absent rubric ≠ failure,
"audit, judge, materialize" — a skill that fails a principle is suboptimal,
not broken).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "TokenCost",
    "estimate_tokens",
    "measure_text_tiers",
    "measure_skill",
    "INDEX_BUDGET",
    "LOAD_BUDGET",
    "CJK",
]

# Perplexity's numbers, verbatim from the guide.
INDEX_BUDGET = 100
LOAD_BUDGET = 5_000

# The characters that cost roughly one token each. Built from Unicode
# code-point ranges rather than a hand-written table: a literal table
# silently misses whole scripts (the first draft of this file had
# Hangul and Katakana but no Simplified Chinese, because the table was
# copied by hand).
def _build_cjk() -> frozenset[str]:
    ranges = (
        (0x1100, 0x11FF),   # Hangul Jamo
        (0x2E80, 0x2EFF),   # CJK Radicals Supplement
        (0x3000, 0x303F),   # CJK Symbols and Punctuation
        (0x3040, 0x30FF),   # Hiragana + Katakana
        (0x3130, 0x318F),   # Hangul Compatibility Jamo
        (0x31F0, 0x31FF),   # Katakana Phonetic Extensions
        (0x3400, 0x4DBF),   # CJK Unified Ideographs Extension A
        (0x4E00, 0x9FFF),   # CJK Unified Ideographs
        (0xA960, 0xA97F),   # Hangul Jamo Extended-A
        (0xAC00, 0xD7AF),   # Hangul Syllables
        (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
        (0xFF00, 0xFFEF),   # Halfwidth and Fullwidth Forms
        (0x20000, 0x2A6DF), # CJK Ext B
        (0x2A700, 0x2EBEF), # CJK Ext C-F
        (0x2F800, 0x2FA1F), # CJK Compatibility Supplement
    )
    out: set[str] = set()
    for lo, hi in ranges:
        out.update(chr(c) for c in range(lo, hi + 1))
    return frozenset(out)


CJK = _build_cjk()

# The tiers that carry a budget. Latin text is ~1 token per 3.5 chars;
# CJK is ~1 token per char. This is an ESTIMATE used for budget
# comparison, not a billable count.
_LATIN_PER_TOKEN = 3.5

# The always-loaded metadata fields. `description` is the big one, but
# the sibling fields are injected too, so the index tier counts them all.
_INDEX_FIELDS = (
    "name", "description", "triggers", "tools", "mutating",
    "brain_first", "when_to_use", "version",
)


def estimate_tokens(text: str) -> int:
    """Estimate the token count of `text`.

    CJK characters cost ~1 token each; everything else costs ~1 token per
    3.5 characters. An estimate, deliberately: a real tokenizer adds a
    dependency and a per-call cost to every measurement, and this is used
    for BUDGET COMPARISON against Perplexity's ~100 / ~5,000 thresholds.
    """
    if not text:
        return 0
    cjk = sum(1 for c in text if c in CJK)
    other = len(text) - cjk
    return int(cjk + other / _LATIN_PER_TOKEN)


@dataclass
class TokenCost:
    """The three-tier cost of one skill, measured."""

    index_tokens: int = 0
    load_tokens: int = 0
    files_tokens: int = 0
    index_budget: int = INDEX_BUDGET
    load_budget: int = LOAD_BUDGET
    # Per-file breakdown of the Files tier, for the report.
    files_breakdown: dict[str, int] | None = None

    @property
    def index_over_budget(self) -> bool:
        return self.index_tokens > self.index_budget

    @property
    def load_over_budget(self) -> bool:
        return self.load_tokens > self.load_budget

    @property
    def files_over_budget(self) -> bool:
        # The Files tier has no budget — it is the escape valve.
        return False

    @property
    def total_tokens(self) -> int:
        return self.index_tokens + self.load_tokens + self.files_tokens

    def as_report_rows(self) -> list[tuple[str, int, int, str]]:
        """(tier, used, budget, status) rows for the audit report."""
        return [
            ("index", self.index_tokens, self.index_budget,
             "OVER" if self.index_over_budget else "ok"),
            ("load", self.load_tokens, self.load_budget,
             "OVER" if self.load_over_budget else "ok"),
            ("files", self.files_tokens, 0, "ok"),
        ]


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_text, body_text). Frontmatter is empty when the
    file has no fence. Never raises."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "", text
    for i, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return "\n".join(lines[1:i - 1]), "\n".join(lines[i:])
    # No closer: treat everything as body (a malformed skill still costs
    # the same to load).
    return "", text


def measure_text_tiers(text: str) -> dict[str, Any]:
    """Split `text` into its index and load tiers and measure each.

    The index tier is the FRONTMATTER — every field in it is injected into
    the session's context whether or not the skill is ever invoked. The
    load tier is the body.
    """
    fm, body = _split_frontmatter(text)
    return {
        "index": estimate_tokens(fm),
        "load": estimate_tokens(body),
        "index_text": fm,
        "load_text": body,
    }


def _measure_dir(path: Path, skip: set[Path]) -> dict[str, int]:
    """Token count of every file under `path`, keyed by relative path."""
    out: dict[str, int] = {}
    if not path.is_dir():
        return out
    for f in sorted(path.rglob("*")):
        if not f.is_file() or f in skip:
            continue
        if any(part in ("__pycache__", ".git") for part in f.parts):
            continue
        try:
            out[str(f.relative_to(path))] = estimate_tokens(
                f.read_text(encoding="utf-8", errors="replace")
            )
        except OSError:
            continue
    return out


def measure_skill(skill_dir: Path) -> TokenCost:
    """Measure the three-tier token cost of a skill directory.

    Never raises: a missing or malformed skill yields zeros and the
    flags all False, so an audit of a broken skill still completes.
    """
    cost = TokenCost()
    sm = skill_dir / "SKILL.md"
    if not sm.is_file():
        return cost
    try:
        text = sm.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return cost
    tiers = measure_text_tiers(text)
    cost.index_tokens = tiers["index"]
    cost.load_tokens = tiers["load"]
    breakdown: dict[str, int] = {}
    for sub in ("references", "assets", "scripts"):
        d = skill_dir / sub
        if d.is_dir():
            for rel, n in _measure_dir(d, {sm}).items():
                breakdown[f"{sub}/{rel}"] = n
    cost.files_breakdown = breakdown
    cost.files_tokens = sum(breakdown.values())
    return cost
