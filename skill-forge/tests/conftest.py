from pathlib import Path
import pytest

@pytest.fixture
def tmp_skill_tree(tmp_path: Path) -> Path:
    """Create a minimal skill folder with a valid SKILL.md and return its root."""
    skill = tmp_path / "demo-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Use when testing fixtures.\n---\n# Demo\n",
        encoding="utf-8",
    )
    return skill
