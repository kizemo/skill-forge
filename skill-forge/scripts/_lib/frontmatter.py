"""YAML frontmatter loader. Pure helper, no phase-script deps.

Only the FIRST `---` after line 1 is the closing fence; later `---` lines
are body content (commonly horizontal rules), not duplicates.
"""
import re
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


# ---------------------------------------------------------------------------
# Skill frontmatter validation (principles 1.1 - 1.8 in docs/PRINCIPLES.md)
# ---------------------------------------------------------------------------
#
# A skill that fails these principles is suboptimal, not broken. The
# materialize step still runs; the warnings are surfaced as evidence in
# audit-report.md so the author can review. There is no "fail to install"
# path — that would block the v0.2 contract (RULING-1: absent rubric ≠
# failure; the same principle applies to principle-validation warnings).

_NAME_KEBAB = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DESCRIPTION_MAX = 1024  # character budget for frontmatter description


def validate_skill_frontmatter(fm: Any) -> list[str]:
    """Return a list of human-readable warnings about frontmatter fields
    that violate skill-writing principles. Empty list = no problems found.

    Principles enforced (see docs/PRINCIPLES.md § 1):
      1.1 — description: present, ≤ 1024 chars, leading-text-1-sentence
      1.3 — triggers: non-empty list with ≥ 3 concrete phrases
      1.4 — mutating: explicit boolean
      1.5 — name: lowercase kebab-case
      1.6 — brain_first: declared (exempt or required; the marketplace
            convention; "absent" emits a warning)
      1.7 — when_to_use: declared (one-line summary)
      1.8 — version: semver

    The function never raises. Missing fields produce a warning, not an
    error, because skill-forge's contract is "audit, judge, materialize"
    — failing the principles degrades the audit, it does not block the run.
    Garbage inputs (None, non-dict, etc.) are treated as "no frontmatter
    at all" and produce a single warning.
    """
    warnings: list[str] = []

    if not isinstance(fm, dict):
        warnings.append(f"frontmatter: expected a mapping, got {type(fm).__name__}")
        return warnings

    # 1.5 name: lowercase kebab-case
    name = fm.get("name")
    if not isinstance(name, str) or not name:
        warnings.append("frontmatter: `name` is missing (skill cannot be referenced by the resolver)")
    elif not _NAME_KEBAB.match(name):
        warnings.append(f"frontmatter: `name` is {name!r}, expected lowercase kebab-case (e.g. 'my-skill')")

    # 1.1 description: present, ≤ 1024 chars
    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        warnings.append("frontmatter: `description` is missing or empty (skill will not be matched by description-based resolver)")
    elif len(desc) > _DESCRIPTION_MAX:
        warnings.append(f"frontmatter: `description` is {len(desc)} chars, recommended ≤ {_DESCRIPTION_MAX}")

    # 1.3 triggers: non-empty list with ≥ 3 entries
    triggers = fm.get("triggers")
    if not isinstance(triggers, list) or not triggers:
        warnings.append("frontmatter: `triggers` is missing or empty (skill will be matched only by description-similarity)")
    elif len([t for t in triggers if isinstance(t, str) and t.strip()]) < 3:
        warnings.append("frontmatter: `triggers` has < 3 concrete phrases (resolver match quality degrades)")

    # 1.4 mutating: explicit boolean
    if "mutating" not in fm:
        warnings.append("frontmatter: `mutating` is missing (default false; skill may be confirmed unnecessarily before invocation)")
    elif not isinstance(fm["mutating"], bool):
        warnings.append(f"frontmatter: `mutating` is {fm['mutating']!r}, expected true or false")

    # 1.6 brain_first: declared (exempt or required)
    if "brain_first" not in fm:
        warnings.append("frontmatter: `brain_first` is missing (declare 'exempt' or 'required' per gbrain convention)")

    # 1.7 when_to_use: declared
    if "when_to_use" not in fm:
        warnings.append("frontmatter: `when_to_use` is missing (one-line summary recommended for marketplace listings)")

    # 1.8 version: semver
    version = fm.get("version")
    if not isinstance(version, str) or not version:
        warnings.append("frontmatter: `version` is missing (semver MAJOR.MINOR.PATCH recommended)")
    elif not re.match(r"^\d+\.\d+\.\d+", version):
        warnings.append(f"frontmatter: `version` is {version!r}, expected semver MAJOR.MINOR.PATCH")

    return warnings
