"""P0: the token cost axis.

Perplexity's three tiers, each with a budget:
  Index  (name + description)   ~100 tokens  — paid by EVERY session, EVERY user
  Load   (the SKILL.md body)    ~5,000 tokens — paid on every trigger
  Files  (scripts/references/assets)  unlimited — paid only when read

A skill that violates these is not "less good"; it taxes every session
that has it installed. skill-forge's judge scored content only, so a
5,500-token body could pass every gate. This module measures the cost
so the report can show it.
"""
import pytest
from scripts._lib.token_cost import (
    TokenCost,
    estimate_tokens,
    measure_skill,
    measure_text_tiers,
)


# --- estimate_tokens -------------------------------------------------------

def test_estimate_tokens_counts_cjk_at_one_per_char():
    # 7 CJK characters -> 7 tokens.
    assert estimate_tokens("中文字符四个字") == 7


def test_estimate_tokens_counts_latin_at_about_one_per_3_5_chars():
    # 35 latin chars -> ~10 tokens
    assert estimate_tokens("a" * 35) == pytest.approx(10, abs=1)


def test_estimate_tokens_handles_mixed_cjk_and_latin():
    text = "Use when 触发 skill 触发"  # latin + CJK
    n = estimate_tokens(text)
    # 4 CJK chars cost 4; the latin run costs ~len/3.5
    assert n >= 4
    assert n < len(text)


def test_estimate_tokens_of_empty_string_is_zero():
    assert estimate_tokens("") == 0


# --- measure_text_tiers ----------------------------------------------------

def test_measure_text_tiers_splits_frontmatter_from_body():
    text = (
        "---\n"
        "name: x\n"
        "description: Use when A.\n"
        "---\n"
        "# body here\n"
    )
    tiers = measure_text_tiers(text)
    assert tiers["index"] > 0
    assert tiers["load"] > 0
    # The body tier must NOT contain the frontmatter.
    assert "name: x" not in tiers["load_text"]


def test_measure_text_tiers_of_a_body_only_string_puts_it_all_in_load():
    tiers = measure_text_tiers("just a body, no frontmatter\n")
    assert tiers["index"] == 0
    assert tiers["load"] > 0


# --- measure_skill ---------------------------------------------------------

def _write_skill(root, name="x", desc="Use when A.", body="# body\n", extra=None):
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {desc}\n---\n{body}", encoding="utf-8"
    )
    for rel, content in (extra or {}).items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return d


def test_measure_skill_reports_all_three_tiers(tmp_path):
    d = _write_skill(tmp_path, extra={"references/a.md": "x" * 3500})
    cost = measure_skill(d)
    assert isinstance(cost, TokenCost)
    assert cost.index_tokens > 0
    assert cost.load_tokens > 0
    assert cost.files_tokens > 0


def test_measure_skill_counts_only_the_tiers_budget_files(tmp_path):
    """references/ + assets/ + scripts/ are the Files tier. A skill with
    none of them has files_tokens == 0."""
    d = _write_skill(tmp_path)
    cost = measure_skill(d)
    assert cost.files_tokens == 0


def test_measure_skill_reports_budget_flags(tmp_path):
    """A skill with a fat description and a huge body must be flagged on
    the index and load tiers, and NOT on files (files has no budget).

    The description is padded with CJK so the token estimate is real: a
    latin padding of the same word count costs ~3.5x less per token.
    """
    d = _write_skill(
        tmp_path,
        desc="Use when " + "触发场景" * 40,     # 160 CJK chars -> ~160 tokens
        body="y" * 30_000,                     # > 5,000 tokens
    )
    cost = measure_skill(d)
    assert cost.index_over_budget is True
    assert cost.load_over_budget is True
    assert cost.files_over_budget is False


def test_measure_skill_flags_a_lean_skill_as_within_budget(tmp_path):
    d = _write_skill(tmp_path, desc="Use when A.", body="# small body\n")
    cost = measure_skill(d)
    assert cost.index_over_budget is False
    assert cost.load_over_budget is False


def test_measure_skill_of_a_missing_skill_is_zero_and_safe(tmp_path):
    cost = measure_skill(tmp_path / "nope")
    assert cost.index_tokens == 0
    assert cost.load_tokens == 0
    assert cost.index_over_budget is False


def test_measure_skill_counts_assets_and_scripts_as_files(tmp_path):
    d = _write_skill(
        tmp_path,
        extra={"assets/t.md": "a" * 1000, "scripts/s.py": "b" * 1000},
    )
    cost = measure_skill(d)
    assert cost.files_tokens >= 550  # ~2000 latin chars -> ~570 tokens


def test_measure_skill_of_a_broken_skill_does_not_raise(tmp_path):
    """A SKILL.md with no closing fence must not crash the measurement —
    the audit must survive a malformed skill (same contract as the
    frontmatter validator)."""
    d = tmp_path / "broken"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: x\nno closer\n", encoding="utf-8")
    cost = measure_skill(d)
    assert cost.load_tokens > 0  # the text still counts
