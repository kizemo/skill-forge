"""YAML frontmatter loader. Pure helper, no phase-script deps.

Only the FIRST `---` after line 1 is the closing fence; later `---` lines
are body content (commonly horizontal rules), not duplicates.
"""
from pathlib import Path
from typing import Any
import yaml

class FrontmatterError(Exception):
    """Raised when frontmatter is missing, malformed, or absent."""

def _find_closer(lines: list[str], path: Path) -> int:
    """Return the 1-based line index of the FIRST `---` after line 1 (RULING-3).

    Shared by load() and body_of() so the two parsers cannot drift apart: any
    change to the fence rule lands in exactly one place. Raises
    FrontmatterError when line 1 is not a `---` fence or when no closer exists.
    `path` is required so the error message always carries the source-file
    prefix (consumed by `AuditReport.evidence` via the frontmatter-error
    branch). v2-T1 originally accepted `path: Path | None = None`; making it
    required removes a dead branch whose only effect was to silently drop the
    error prefix.
    """
    prefix = f"{path}: "
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError(f"{prefix}missing opening '---' fence on line 1")
    for i, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return i
    raise FrontmatterError(f"{prefix}missing closing '---' fence")

def load(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    close_at = _find_closer(lines, path)
    raw = "\n".join(lines[1:close_at-1])
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as e:
        raise FrontmatterError(f"{path}: YAML parse error: {e}") from e
    if not isinstance(data, dict):
        raise FrontmatterError(f"{path}: frontmatter must be a mapping, got {type(data).__name__}")
    return data

def body_of(path: Path) -> str:
    """Return the body text after the first `---` closer, using the same
    fence rule as load() (RULING-3). Only the FIRST `---` after line 1
    is the closer; later `---` lines are body content.

    Symmetric with load(): raises FrontmatterError on a missing opener or a
    missing closer. There is no YAML-parse error path here — the YAML lives
    in the frontmatter, and the body is plain text.

    The return value keeps the body's own trailing newline; callers that care
    about leading/trailing whitespace do their own .strip().
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    close_at = _find_closer(lines, path)
    return "\n".join(lines[close_at:])
