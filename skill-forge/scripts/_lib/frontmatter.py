"""YAML frontmatter loader. Pure helper, no phase-script deps.

Only the FIRST `---` after line 1 is the closing fence; later `---` lines
are body content (commonly horizontal rules), not duplicates.
"""
from pathlib import Path
from typing import Any
import yaml

class FrontmatterError(Exception):
    """Raised when frontmatter is missing, malformed, or absent."""

def load(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError(f"{path}: missing opening '---' fence on line 1")
    close_at: int | None = None
    for i, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            close_at = i
            break
    if close_at is None:
        raise FrontmatterError(f"{path}: missing closing '---' fence")
    raw = "\n".join(lines[1:close_at-1])
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as e:
        raise FrontmatterError(f"{path}: YAML parse error: {e}") from e
    if not isinstance(data, dict):
        raise FrontmatterError(f"{path}: frontmatter must be a mapping, got {type(data).__name__}")
    return data
