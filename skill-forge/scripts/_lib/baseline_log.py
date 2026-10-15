"""Read/write the per-skill SHA baseline at .skill-forge-baseline.json.

The baseline records the SHA of SKILL.md at the end of the last successful
skill-forge run. The next run compares the current SHA to the recorded one;
a mismatch signals a race (the user edited SKILL.md between runs) and the
materialize phase is gated on this check.

Never raise: any IO error, JSON error, or path error is treated as 'no
baseline present', which means 'first run for this skill' from the caller's
perspective.
"""
from __future__ import annotations
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BASENAME = ".skill-forge-baseline.json"


def _read_payload(skill_dir: Path) -> dict | None:
    """Return the parsed baseline payload, or None if absent/malformed.

    Never raises — mirrors ``bundle.py``'s widened ``(OSError, ValueError,
    RuntimeError)`` guard recommended by the v2-T4 review.
    """
    p = skill_dir / BASENAME
    try:
        if not p.exists():
            return None
        text = p.read_text(encoding="utf-8")
        payload = json.loads(text)
    except (OSError, ValueError, RuntimeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def read_baseline(skill_dir: Path) -> str | None:
    """Return the recorded SHA, or None if missing/malformed. Never raises."""
    payload = _read_payload(skill_dir)
    if payload is None:
        return None
    sha = payload.get("sha")
    if not isinstance(sha, str) or not sha:
        return None
    return sha


def write_baseline(skill_dir: Path, sha: str) -> None:
    """Atomically write the new baseline. Never raises."""
    payload = {
        "sha": sha,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    target = skill_dir / BASENAME
    try:
        # Atomic write via a temp file in the same dir + os.replace, so a
        # crashed write never leaves a half-written baseline. os.replace is
        # atomic on POSIX and on Windows (MoveFileEx with REPLACE_EXISTING),
        # but it can transiently fail with PermissionError on Windows if the
        # target is open elsewhere — hence the guard below.
        fd, tmp = tempfile.mkstemp(
            prefix=".skill-forge-baseline.", suffix=".tmp", dir=str(skill_dir),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            os.replace(tmp, target)
        except Exception:
            # Clean up the temp file on any failure.
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except (OSError, ValueError, RuntimeError):
        return  # Never raise from the materialize path.


def race(skill_dir: Path, current_sha: str) -> bool:
    """Return True iff a recorded baseline exists AND its sha differs
    from ``current_sha``. Never raises."""
    prior = read_baseline(skill_dir)
    return prior is not None and prior != current_sha
