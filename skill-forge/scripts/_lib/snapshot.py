"""P0: the before/after snapshot — a REAL baseline for the rubric.

Before this module, run.py did:

    candidate = skill_dir / "SKILL.md"
    baseline  = candidate      # PLACEHOLDER

Phase 4's rubric therefore compared the candidate against itself. There
was no before/after: "pass_rate improved" was unmeasurable, and the
materialize step's best.md had nothing to diff against.

Anthropic's skill-creator takes the snapshot approach: copy the
pre-change version, point the baseline run at the copy, and run
with-skill and baseline side by side. This module is the same idea,
minus the parallel subagents (those are the caller's job).

The snapshot lives inside the skill dir as a dotfile, is gitignored, and
is refreshed at the START of a run — before the forward phase can touch
the skill. A second call in the same run does NOT overwrite it, because
the "before" state is what the whole comparison is anchored to.
"""
from __future__ import annotations

import difflib
from pathlib import Path

__all__ = [
    "SNAPSHOT_NAME",
    "snapshot_skill",
    "read_snapshot",
    "clear_snapshot",
    "diff_bodies",
]

SNAPSHOT_NAME = ".skill-forge-snapshot-SKILL.md"


def snapshot_skill(skill_dir: Path) -> Path | None:
    """Capture SKILL.md as the BEFORE state. Returns the snapshot path.

    Never overwrites an existing snapshot: the before state must stay
    anchored to the start of the run. Returns the existing path when one
    is already present, and None when there is no SKILL.md to snapshot.
    """
    src = skill_dir / "SKILL.md"
    snap = skill_dir / SNAPSHOT_NAME
    if snap.exists():
        return snap
    if not src.is_file():
        return None
    try:
        snap.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        return None
    return snap


def read_snapshot(skill_dir: Path) -> Path | None:
    """Return the snapshot path if it exists, else None."""
    snap = skill_dir / SNAPSHOT_NAME
    return snap if snap.is_file() else None


def clear_snapshot(skill_dir: Path) -> None:
    """Remove the snapshot (called at the end of a run). Never raises."""
    snap = skill_dir / SNAPSHOT_NAME
    try:
        if snap.exists():
            snap.unlink()
    except OSError:
        pass


def diff_bodies(before: str, after: str) -> dict:
    """Line-level delta between two texts.

    Returns {"added": int, "removed": int, "changed": bool, "lines": [...]}
    where "lines" holds the unified-diff body (for the report).
    """
    b = (before or "").splitlines()
    a = (after or "").splitlines()
    added = removed = 0
    detail: list[str] = []
    for line in difflib.unified_diff(b, a, lineterm="", n=0):
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
            detail.append(line)
        elif line.startswith("-"):
            removed += 1
            detail.append(line)
    return {
        "added": added,
        "removed": removed,
        "changed": added > 0 or removed > 0,
        "lines": detail[:60],
    }
