import pytest
from pathlib import Path
from scripts._lib.frontmatter import load, FrontmatterError


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
