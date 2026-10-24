"""P0-2: the pluggable LLM channel that backs the Phase 4 rubric judge.

The rubric judge must be able to talk to a real model, and that model
should be a DIFFERENT source from whoever authored the candidate — a
judge that shares the author's blind spots is not a review, it is an
echo. The channel therefore always names the model explicitly, and
run.py echoes that name in the Phase 4 marker, so the operator can see
which model judged which candidate.

Degradation contract (RULING-1): an ABSENT judge is skipped, never a
failure. This module keeps two kinds of absence distinct:

- **no judge configured / no script on this host** → `make_llm_call`
  returns `None` → the caller passes `llm_call=None` → the rubric is
  SKIPPED (RULING-1's original case).
- **a judge that IS configured but errors** (network, auth, an
  unparseable answer) → `RubricError`. The error is never silently
  converted into a score of 0.0, because 0.0 means "the judge said no"
  — a different claim from "the judge could not answer". The caller
  decides, and it must make the failure visible.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Callable

__all__ = [
    "RubricError",
    "make_llm_call",
    "parse_score",
    "discover_rubric_script",
    "default_launcher",
]


class RubricError(RuntimeError):
    """Raised when the judge channel is configured but could not deliver a
    score. Distinct from "no judge configured" (which is a skip)."""


# A bare number, optionally signed, not glued to word characters. The
# lookarounds keep "0.2.0" and "3-item" from being mis-read.
_SCORE_RE = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")


def parse_score(text: str) -> float:
    """Extract a 0..1 score from the judge's answer.

    Accepts a bare number, a labelled number ("SCORE: 0.72"), or a
    number inside prose. The LAST such number wins: a judge that
    reasons out loud tends to state its verdict last, and the verdict is
    what we asked for.

    Raises RubricError when no number can be found — an answer we cannot
    read is an error, not a zero.
    """
    matches = _SCORE_RE.findall(text or "")
    if not matches:
        raise RubricError(
            f"no score found in judge answer: {(text or '').strip()[:200]!r}"
        )
    value = float(matches[-1])
    return max(0.0, min(1.0, value))


def default_launcher() -> list[str]:
    """The Python launcher used to run the judge script.

    Windows: `py -3` (a bare `python` may not exist on a default
    install). Elsewhere: `python3`.
    """
    if os.name == "nt":
        return ["py", "-3"]
    return ["python3"]


def discover_rubric_script() -> Path | None:
    """Find the llm-call script on this host, or None.

    The script is a plain .py file shipped with the llm-call skill; the
    skill's own SKILL.md documents the invocation contract.
    """
    candidates = [
        Path.home() / ".minimax" / ".builtin-skills" / "llm-call" / "scripts" / "llm_call.py",
        Path.home() / ".claude" / "skills" / "llm-call" / "scripts" / "llm_call.py",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _as_text(value: str | bytes | None) -> str:
    """Normalize a subprocess stream to str.

    `text=True` normally yields str, but a caller may swap in a runner
    that yields bytes; the channel must not explode on that.
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def make_llm_call(*, model: str | None, script: Path | None,
                  timeout: int = 180,
                  launcher: list[str] | None = None,
                  extra_args: list[str] | None = None) -> Callable[[str], float] | None:
    """Build the rubric's llm_call, or None when no judge is configured.

    Returns a callable with the judge's signature
    `llm_call(prompt: str) -> float` (score in 0..1), or None when
    `model` is unset or `script` is missing — the RULING-1 "no judge"
    case, which the caller turns into a skipped rubric.

    The returned callable raises RubricError when the channel is
    configured but fails (non-zero exit, timeout, unreadable answer).
    """
    if not model:
        return None
    if script is None or not Path(script).is_file():
        return None
    cmd_prefix = [*(launcher if launcher is not None else default_launcher()),
                  str(script)]
    args_prefix = [*(extra_args or []), "--model", model]

    def llm_call(prompt: str) -> float:
        cmd = [*cmd_prefix, *args_prefix, "--prompt", prompt]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=timeout, text=True)
        except subprocess.TimeoutExpired as e:
            raise RubricError(f"judge timed out after {timeout}s") from e
        except (OSError, subprocess.SubprocessError) as e:
            raise RubricError(f"judge channel failed: {e}") from e
        stdout = _as_text(getattr(r, "stdout", ""))
        stderr = _as_text(getattr(r, "stderr", ""))
        if getattr(r, "returncode", 0) != 0:
            detail = (stderr or stdout).strip()[:300]
            raise RubricError(f"judge exited {r.returncode}: {detail}")
        return parse_score(stdout)

    return llm_call
