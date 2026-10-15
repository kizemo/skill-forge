import pytest
from pathlib import Path
from scripts._lib.frontmatter import (
    load, FrontmatterError, body_of,
    validate_skill_frontmatter, validate_skill_body,
)


def test_load_and_body_of_select_the_same_closer_on_inline_dashes(tmp_path):
    """Post-v2 hardening (v2-T1 M4): pin the literal text of RULING-3 —
    that load() and body_of() select the *same* closer on the same file.
    A future edit that makes body_of() use a different rule would be
    caught here, not only via the indirect audit reproducer."""
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\n"
        "name: x\n"
        "description: y\n"
        "---\n"
        "# body one\n"
        "\n"
        "---\n"
        "\n"
        "more body (this `---` is body content, not a fence)\n",
        encoding="utf-8",
    )
    fm = load(p)
    assert fm == {"name": "x", "description": "y"}
    body = body_of(p)
    # Frontmatter keys must NOT be in body.
    assert "name: x" not in body
    assert "description: y" not in body
    # Both body segments after the closer must be present.
    assert "body one" in body
    assert "more body" in body
    # The body-level horizontal rule must be present (proves the closer
    # was the FIRST `---` and not the second).
    assert "---" in body


def test_load_parses_valid_frontmatter(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text("---\nname: x\ndescription: y\n---\n# body\n", encoding="utf-8")
    assert load(p) == {"name": "x", "description": "y"}


def test_load_raises_on_missing_fence(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text("name: x\nno fence\n", encoding="utf-8")
    with pytest.raises(FrontmatterError):
        load(p)


def test_load_raises_on_missing_close_fence(tmp_path):
    """Opening fence present, no closing fence → raises.

    Two consecutive `---` lines (close + an immediately-following line)
    are NOT a duplicate-fence error — only the first `---` after line 1
    is interpreted as the closing fence; everything after it is body.
    """
    p = tmp_path / "SKILL.md"
    p.write_text("---\nname: x\ndescription: y\n# body\n", encoding="utf-8")
    with pytest.raises(FrontmatterError):
        load(p)


def test_load_tolerates_body_with_horizontal_rule(tmp_path):
    """Body content may contain `---` horizontal rules; only the FIRST
    fence after line 1 is the closer."""
    p = tmp_path / "SKILL.md"
    p.write_text("---\nname: x\ndescription: y\n---\n# body\n\n---\n\nmore\n", encoding="utf-8")
    assert load(p) == {"name": "x", "description": "y"}


def test_load_handles_description_with_inline_colon_and_apostrophe(tmp_path):
    """Regression for RULING-5: a description containing `: ` (colon+space)
    and an apostrophe must NOT be written as an unquoted plain scalar (PyYAML
    treats `: ` as a mapping start, and apostrophes break naive quoting).
    Authors must use a YAML block scalar (e.g. `>-`) — but the loader itself
    must parse whatever the resulting folded scalar produces.

    This fixture uses the block-scalar form. If a SKILL.md is authored from
    the spec verbatim without the `>-` fix, this test would not catch it;
    the loader-level invariant here is: a correctly-authored multi-line
    description folds to a single string containing every token, including
    the colon and apostrophe."""
    skill_md = (
        "---\n"
        "name: skill-forge\n"
        "description: >-\n"
        "  Use when a skill is not producing the quality you want. "
        "Triggers: \"improve\", \"skill won't trigger\".\n"
        "mutating: true\n"
        "brain_first: exempt\n"
        "---\n"
        "# body\n"
    )
    p = tmp_path / "SKILL.md"
    p.write_text(skill_md, encoding="utf-8")
    data = load(p)
    assert data["name"] == "skill-forge"
    assert data["mutating"] is True
    assert data["brain_first"] == "exempt"
    desc = data["description"]
    assert "Triggers:" in desc
    assert "won't trigger" in desc
    assert "Use when a skill" in desc


def test_body_of_returns_text_after_first_closer(tmp_path):
    """body_of() must use the same fence rule as load() (RULING-3):
    only the FIRST '---' after line 1 closes; later '---' lines are body."""
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\nname: x\ndescription: y\n---\n# body\n\n---\n\nmore body\n",
        encoding="utf-8",
    )
    body = body_of(p)
    assert "# body" in body
    assert "more body" in body
    # And critically: frontmatter content (name: x, description: y) is NOT in body
    assert "name: x" not in body
    assert "description: y" not in body


def test_body_of_refuses_on_missing_closer(tmp_path):
    """body_of() must raise FrontmatterError if there is no closing '---'
    after line 1 — symmetric with load() per RULING-3."""
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\nname: x\ndescription: y\n# body\n", encoding="utf-8",
    )
    with pytest.raises(FrontmatterError):
        body_of(p)


def test_body_of_refuses_on_missing_opener(tmp_path):
    """body_of() must raise FrontmatterError if the file does not start with '---'."""
    p = tmp_path / "SKILL.md"
    p.write_text("name: x\nno fence\n", encoding="utf-8")
    with pytest.raises(FrontmatterError):
        body_of(p)


# ---------------------------------------------------------------------------
# validate_skill_frontmatter — principles 1.1..1.8 (PRINCIPLES.md § 1)
# ---------------------------------------------------------------------------

def test_validate_skill_frontmatter_no_warnings_on_full_conformant_skill():
    """A fully-conformant skill (all 8 frontmatter principles met) returns []."""
    fm = {
        "name": "skill-forge",
        "version": "0.2.0",
        "description": "Use when a skill is not producing the quality you want.",
        "triggers": ["improve this skill", "audit skill quality", "fix skill"],
        "tools": ["search", "list_pages"],
        "mutating": True,
        "brain_first": "exempt",
        "when_to_use": "Use when the user asks: \"improve this skill\".",
    }
    assert validate_skill_frontmatter(fm) == []


def test_validate_skill_frontmatter_no_warnings_on_recommended_minimum():
    """A skill that satisfies the strict-parse principles (1.1, 1.3, 1.5)
    but omits the convention-only fields (1.4 mutating, 1.6 brain_first,
    1.7 when_to_use, 1.8 version) produces warnings on the omitted fields.

    This test pins the contract: validate() is NOT a permission gate.
    A skill that passes principles 1.1/1.3/1.5 (parsing) and 1.4 (mutating)
    is a valid v0.2 skill; the other 4 are documented conventions."""
    fm = {
        "name": "skill-forge",
        "description": "Use when a skill needs auditing.",
        "triggers": ["improve this skill", "audit skill quality", "fix skill"],
        "mutating": True,
    }
    warnings = validate_skill_frontmatter(fm)
    # No warnings about name/description/triggers/mutating.
    assert not any(("`name`" in w and "missing" in w) for w in warnings)
    assert not any("`description`" in w and ("missing" in w or "1024" in w) for w in warnings)
    assert not any("`triggers`" in w for w in warnings)
    assert not any("`mutating`" in w and "missing" in w for w in warnings)
    # But warnings on the convention fields.
    assert any("`brain_first`" in w for w in warnings)
    assert any("`when_to_use`" in w for w in warnings)
    assert any("`version`" in w for w in warnings)


def test_validate_warns_on_missing_name():
    assert any("`name` is missing" in w for w in validate_skill_frontmatter({}))


def test_validate_warns_on_non_kebab_name():
    fm = {"name": "My Skill", "description": "Use when x.", "triggers": ["a", "b", "c"]}
    warnings = validate_skill_frontmatter(fm)
    assert any("kebab-case" in w for w in warnings)


def test_validate_warns_on_missing_description():
    fm = {"name": "skill-x", "triggers": ["a", "b", "c"]}
    warnings = validate_skill_frontmatter(fm)
    assert any("`description` is missing" in w for w in warnings)


def test_validate_warns_on_empty_description():
    fm = {"name": "skill-x", "description": "  ", "triggers": ["a", "b", "c"]}
    assert any("`description` is missing" in w for w in validate_skill_frontmatter(fm))


def test_validate_warns_on_long_description():
    fm = {
        "name": "skill-x",
        "description": "x" * 1100,
        "triggers": ["a", "b", "c"],
    }
    assert any("1024" in w for w in validate_skill_frontmatter(fm))


def test_validate_accepts_description_at_exactly_1024_chars():
    fm = {
        "name": "skill-x",
        "description": "x" * 1024,
        "triggers": ["a", "b", "c"],
    }
    # 1024 is the limit, not over — no warning.
    assert all("1024" not in w for w in validate_skill_frontmatter(fm))


def test_validate_warns_on_missing_triggers():
    fm = {"name": "skill-x", "description": "Use when x."}
    assert any("`triggers`" in w for w in validate_skill_frontmatter(fm))


def test_validate_warns_on_empty_triggers_list():
    fm = {"name": "skill-x", "description": "Use when x.", "triggers": []}
    assert any("`triggers`" in w for w in validate_skill_frontmatter(fm))


def test_validate_warns_on_too_few_triggers():
    fm = {"name": "skill-x", "description": "Use when x.", "triggers": ["only one"]}
    assert any("< 3" in w for w in validate_skill_frontmatter(fm))


def test_validate_warns_on_missing_mutating():
    fm = {"name": "skill-x", "description": "Use when x.", "triggers": ["a", "b", "c"]}
    assert any("`mutating`" in w for w in validate_skill_frontmatter(fm))


def test_validate_warns_on_non_boolean_mutating():
    fm = {"name": "skill-x", "description": "Use when x.", "triggers": ["a", "b", "c"], "mutating": "yes"}
    assert any("`mutating`" in w for w in validate_skill_frontmatter(fm))


def test_validate_warns_on_missing_brain_first():
    fm = {
        "name": "skill-x", "description": "Use when x.", "triggers": ["a", "b", "c"],
        "mutating": True,
    }
    assert any("`brain_first`" in w for w in validate_skill_frontmatter(fm))


def test_validate_warns_on_missing_when_to_use():
    fm = {
        "name": "skill-x", "description": "Use when x.", "triggers": ["a", "b", "c"],
        "mutating": True, "brain_first": "exempt",
    }
    assert any("`when_to_use`" in w for w in validate_skill_frontmatter(fm))


def test_validate_warns_on_missing_version():
    fm = {
        "name": "skill-x", "description": "Use when x.", "triggers": ["a", "b", "c"],
        "mutating": True, "brain_first": "exempt", "when_to_use": "Use when x.",
    }
    assert any("`version`" in w for w in validate_skill_frontmatter(fm))


def test_validate_warns_on_non_semver_version():
    fm = {
        "name": "skill-x", "description": "Use when x.", "triggers": ["a", "b", "c"],
        "mutating": True, "brain_first": "exempt", "when_to_use": "Use when x.",
        "version": "v1",
    }
    assert any("semver" in w for w in validate_skill_frontmatter(fm))


# ---------------------------------------------------------------------------
# validate_skill_frontmatter — gap 1 (2026-10-15 Perplexity audit):
#   (a) description starts with "Use when" or "Load when"
#   (b) description ≤ 50 words (separate from the 1024-char cap)
#   (c) skill_dir.name matches fm["name"]
# All three return warnings; the function never raises.
# ---------------------------------------------------------------------------

def test_validate_warns_on_description_without_use_when_prefix():
    """Per Perplexity: a description should be a routing phrase, not a self-
    intro. The accepted prefixes are 'Use when …' (skill-forge's convention)
    or 'Load when …' (Perplexity's literal). Anything else → warning."""
    fm = {
        "name": "skill-x",
        "description": "Improve this skill by auditing its body.",  # no prefix
        "triggers": ["a", "b", "c"],
    }
    warnings = validate_skill_frontmatter(fm)
    assert any("`description`" in w and ("Use when" in w or "Load when" in w)
               for w in warnings), warnings


def test_validate_warns_on_load_when_prefix_too():
    """The literal 'Load when …' prefix (Perplexity's phrasing) is also valid."""
    fm = {
        "name": "skill-x",
        "description": "Load when the user asks to improve a skill.",
        "triggers": ["a", "b", "c"],
    }
    assert not any("`description`" in w and ("Use when" in w or "Load when" in w)
                   for w in validate_skill_frontmatter(fm))


def test_validate_warns_on_description_over_50_words():
    """Per Perplexity: keep description ≤ 50 words. 51 words → warning,
    even if the 1024-char cap would have accepted it (51 short words is
    well under 1024 chars; the two caps are independent)."""
    fm = {
        "name": "skill-x",
        "description": "Use when " + ("word " * 51),  # 52 words total, well under 1024 chars
        "triggers": ["a", "b", "c"],
    }
    warnings = validate_skill_frontmatter(fm)
    assert any("`description`" in w and "50" in w and "words" in w
               for w in warnings), warnings


def test_validate_accepts_description_at_exactly_50_words():
    """50 words is the cap, not over — no word-count warning. (We still
    count the leading 'Use when' as 2 words, so this fixture has 50.)"""
    words = "Use when " + " ".join(f"w{i}" for i in range(48))  # 2 + 48 = 50
    assert len(words.split()) == 50
    fm = {
        "name": "skill-x",
        "description": words,
        "triggers": ["a", "b", "c"],
    }
    warnings = validate_skill_frontmatter(fm)
    assert not any("50 words" in w for w in warnings), warnings


def test_validate_warns_when_dir_name_mismatches_frontmatter_name(tmp_path):
    """Per Perplexity: skill dir name == frontmatter name. When the caller
    passes skill_dir (optional kwarg) and dir.name != fm["name"], warn."""
    fm = {
        "name": "actual-skill-name",
        "description": "Use when x.",
        "triggers": ["a", "b", "c"],
    }
    # tmp_path is a different name.
    skill_dir = tmp_path / "different-name"
    skill_dir.mkdir()
    warnings = validate_skill_frontmatter(fm, skill_dir=skill_dir)
    assert any("dir" in w and "actual-skill-name" in w and "different-name" in w
               for w in warnings), warnings


def test_validate_skips_dir_check_when_skill_dir_omitted():
    """Default (no skill_dir): the dir-name check is silently skipped so
    existing callers that only pass a dict keep working unchanged."""
    fm = {
        "name": "anything",
        "description": "Use when x.",
        "triggers": ["a", "b", "c"],
    }
    warnings = validate_skill_frontmatter(fm)
    assert not any("dir" in w for w in warnings), warnings


def test_validate_no_dir_warning_when_dir_name_matches(tmp_path):
    """When the caller passes skill_dir and dir.name == fm["name"]: no
    dir-mismatch warning. (The dir-name match is a soft convention; no
    warning is emitted on success.)"""
    fm = {
        "name": "matching-name",
        "description": "Use when x.",
        "triggers": ["a", "b", "c"],
    }
    skill_dir = tmp_path / "matching-name"
    skill_dir.mkdir()
    warnings = validate_skill_frontmatter(fm, skill_dir=skill_dir)
    assert not any("dir" in w for w in warnings), warnings


# ---------------------------------------------------------------------------
# validate_skill_body — gap 2 (2026-10-15 Perplexity audit):
#   (a) presence of a gotcha-style section in the body
#   (b) warn when references/ or assets/ is missing for non-trivial bodies
# Both checks read the body via body_of() and never raise.
# ---------------------------------------------------------------------------

def test_validate_body_warns_when_no_gotcha_section(tmp_path):
    """A body with no gotcha-style section (## Common Rationalizations /
    ## Red Flags / ## Anti-Patterns / ## Pitfalls / ## Failure modes / etc.)
    emits a warning. Perplexity: gotchas are the highest-value content."""
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\nname: x\n---\n# body\n\nSome plain content with no gotchas.\n",
        encoding="utf-8",
    )
    warnings = validate_skill_body(p, {"name": "x"})
    assert any("gotcha" in w.lower() for w in warnings), warnings


def test_validate_body_accepts_common_rationalizations_section(tmp_path):
    """'## Common Rationalizations' is one of the accepted gotcha-section
    patterns (matches the 'rationaliz' branch of the regex)."""
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\nname: x\n---\n# body\n\n## Common Rationalizations\n\n| a | b |\n",
        encoding="utf-8",
    )
    warnings = validate_skill_body(p, {"name": "x"})
    assert not any("gotcha" in w.lower() for w in warnings), warnings


def test_validate_body_accepts_red_flags_section(tmp_path):
    """'## Red Flags' is another accepted pattern (matches the convention)."""
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\nname: x\n---\n# body\n\n## Red Flags\n\n- one\n",
        encoding="utf-8",
    )
    warnings = validate_skill_body(p, {"name": "x"})
    assert not any("gotcha" in w.lower() for w in warnings), warnings


def test_validate_body_warns_when_long_body_lacks_references_dir(tmp_path):
    """A body over 150 lines without a references/ or assets/ directory in
    the parent skill_dir emits a warning. Perplexity: heavy content should
    live in references/, not inline in SKILL.md."""
    long_body = "\n".join(f"line {i}" for i in range(200))
    p = tmp_path / "SKILL.md"
    p.write_text(
        f"---\nname: x\n---\n# body\n\n{long_body}\n",
        encoding="utf-8",
    )
    warnings = validate_skill_body(p, {"name": "x"})
    assert any("references" in w.lower() or "assets" in w.lower()
               for w in warnings), warnings


def test_validate_body_no_warning_when_references_dir_present(tmp_path):
    """A long body WITH a references/ directory: no overflow warning."""
    long_body = "\n".join(f"line {i}" for i in range(200))
    p = tmp_path / "SKILL.md"
    p.write_text(
        f"---\nname: x\n---\n# body\n\n{long_body}\n",
        encoding="utf-8",
    )
    (tmp_path / "references").mkdir()
    warnings = validate_skill_body(p, {"name": "x"})
    assert not any("references" in w.lower() or "assets" in w.lower()
                   for w in warnings), warnings


def test_validate_body_no_warning_when_assets_dir_present(tmp_path):
    """Long body WITH an assets/ directory: no overflow warning (assets/
    is an accepted alternative to references/)."""
    long_body = "\n".join(f"line {i}" for i in range(200))
    p = tmp_path / "SKILL.md"
    p.write_text(
        f"---\nname: x\n---\n# body\n\n{long_body}\n",
        encoding="utf-8",
    )
    (tmp_path / "assets").mkdir()
    warnings = validate_skill_body(p, {"name": "x"})
    assert not any("references" in w.lower() or "assets" in w.lower()
                   for w in warnings), warnings


def test_validate_body_skips_overflow_check_for_short_body(tmp_path):
    """Short bodies (<= 150 lines) skip the overflow check: not every
    small skill needs a references/ directory."""
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\nname: x\n---\n# body\n\nshort content\n",
        encoding="utf-8",
    )
    warnings = validate_skill_body(p, {"name": "x"})
    assert not any("references" in w.lower() or "assets" in w.lower()
                   for w in warnings), warnings


def test_validate_body_never_raises_on_missing_fence(tmp_path):
    """A malformed SKILL.md (no closing fence) must not raise — the body
    check degrades to a single warning, matching the frontmatter validator's
    'never raises' contract."""
    p = tmp_path / "SKILL.md"
    p.write_text("---\nname: x\nno closer\n", encoding="utf-8")
    warnings = validate_skill_body(p, {"name": "x"})
    assert isinstance(warnings, list)
    assert len(warnings) >= 1


def test_validate_never_raises_on_garbage():
    """A frontmatter-shaped object that's not a dict (or contains non-string
    values) must not raise — it must return a warnings list. The contract
    is 'suboptimal, not broken' (PRINCIPLES.md § 1)."""
    for fm in [None, "not a dict", 42, [], {"name": 123, "description": 456}]:
        warnings = validate_skill_frontmatter(fm)  # type: ignore[arg-type]
        assert isinstance(warnings, list)
        assert len(warnings) > 0  # every garbage input is a violation
