"""Fallback wrapper: forward skill creation to skill-creator's init_skill.py.

Invoked by scripts/router.py only when gbrain is unavailable AND scope == "create".
Exits non-zero and prints a loud diagnostic if the bundled script cannot be found —
never silently swallows the failure (T6 brief, Global Constraints).
"""
import os
import subprocess
import sys
from pathlib import Path

_INIT_SKILL = (
    Path(__file__).resolve().parent.parent.parent / "skill-creator" / "scripts" / "init_skill.py"
)


def main(argv: list[str]) -> int:
    # v2-T3 (RULING-9 v2 + T8 review M-2): the skill dir now comes from
    # SKILL_DIR env var (preferred, cwd-agnostic) or argv[0] (back-compat).
    # v1 used `Path.cwd()` for the --path value, which broke E2E in
    # tmp_path because the caller's cwd was the test dir, not the skill
    # dir. Now we always pass the resolved skill dir.
    skill_dir_str = os.environ.get("SKILL_DIR") or (argv[0] if argv else "")
    if not skill_dir_str:
        print(
            "[FATAL] skill_dir not provided: set SKILL_DIR env var or pass "
            "skill_dir as first argv",
            file=sys.stderr,
        )
        return 2
    skill_dir = Path(skill_dir_str).resolve()
    if not _INIT_SKILL.exists():
        print(f"[ERROR] skill-creator init_skill.py not found at {_INIT_SKILL}", file=sys.stderr)
        return 2
    cmd = [sys.executable, str(_INIT_SKILL), skill_dir.name, "--path", str(skill_dir)]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    sys.stdout.write(r.stdout.decode(errors="replace"))
    sys.stderr.write(r.stderr.decode(errors="replace"))
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
