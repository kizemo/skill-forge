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


def test_load_raises_on_duplicate_fence(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text("---\nname: x\n---\n---\nbody\n", encoding="utf-8")
    with pytest.raises(FrontmatterError):
        load(p)
