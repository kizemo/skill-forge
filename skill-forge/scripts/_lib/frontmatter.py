"""YAML frontmatter loader. Pure helper, no phase-script deps."""
from pathlib import Path
from typing import Any
import yaml

class FrontmatterError(Exception):
    """Raised when frontmatter is missing, malformed, or has duplicate fences."""

def load(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError(f"{path}: missing opening '---' fence on line 1")
    closes: list[int] = []
    for i, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            closes.append(i)
    if not closes:
        raise FrontmatterError(f"{path}: missing closing '---' fence")
    if len(closes) > 1:
        raise FrontmatterError(f"{path}: duplicate closing '---' fence (lines {closes})")
    raw = "\n".join(lines[1:closes[0]-1])
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as e:
        raise FrontmatterError(f"{path}: YAML parse error: {e}") from e
    if not isinstance(data, dict):
        raise FrontmatterError(f"{path}: frontmatter must be a mapping, got {type(data).__name__}")
    return data
