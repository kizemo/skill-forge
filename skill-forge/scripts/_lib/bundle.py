"""Classify whether a skill is bundled (installed via the gbrain plugin
marketplace) vs. a local developer's skill. The bundled install under
the gbrain marketplace's ``plugin/skills/<name>/`` tree is treated as
read-only from skill-forge's perspective: we may propose changes
(proposed.md) but must never write SKILL.md directly.

Fail-open: if ``~/.gbrain/install.json`` is missing, unreadable, malformed,
or unparseable, return False (not bundled). Fail-closed would block every
v2 run on a host without a gbrain install. See v2 progress.md Default
Decision #2.

This module is pure: no subprocess, no network, no global mutation. It
only reads the filesystem, and it NEVER raises — callers need no
try/except around ``is_bundled()``.
"""
import json
from pathlib import Path
from typing import Any

GBRAIN_HOME = Path.home() / ".gbrain"
INSTALL_JSON = GBRAIN_HOME / "install.json"


def _candidate_paths(payload: Any) -> list[Path]:
    """Extract skill paths from a parsed install.json payload, tolerating
    two on-disk shapes:
      (a) ``{"<skill-name>": "<path>", ...}``                — name→path dict
      (b) ``{"skills": [{"name": ..., "path": ...}, ...]}``  — list of entries

    Returns resolved absolute Paths. Anything we can't parse is silently
    dropped — fail-open is the contract.
    """
    out: list[Path] = []
    if isinstance(payload, dict):
        # shape (a): name→path
        for v in payload.values():
            if isinstance(v, str):
                out.extend(_resolved(v))
        # shape (b): skills list
        skills = payload.get("skills")
        if isinstance(skills, list):
            for entry in skills:
                if isinstance(entry, dict):
                    p_str = entry.get("path")
                    if isinstance(p_str, str):
                        out.extend(_resolved(p_str))
    return out


def _resolved(raw: str) -> list[Path]:
    """Resolve one candidate path string; drop it if it is relative or
    unresolvable. Never raises."""
    try:
        p = Path(raw)
        if not p.is_absolute():
            return []
        return [p.resolve()]
    except (OSError, ValueError, RuntimeError):
        return []


def is_bundled(skill_dir: Path) -> bool:
    """Return True iff skill_dir's resolved path appears in
    ~/.gbrain/install.json. Fail-open on any error: return False."""
    try:
        if not INSTALL_JSON.exists():
            return False
        text = INSTALL_JSON.read_text(encoding="utf-8")
        payload = json.loads(text)
    except (OSError, ValueError, RuntimeError):
        return False
    try:
        target = skill_dir.resolve()
    except (OSError, ValueError, RuntimeError):
        return False
    return any(candidate == target for candidate in _candidate_paths(payload))
