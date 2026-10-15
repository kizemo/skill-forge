import pytest
from pathlib import Path
from scripts._lib.frontmatter import load, FrontmatterError, body_of


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
