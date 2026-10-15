"""Fallback wrapper: forward skill creation to skill-creator's init_skill.py.

Invoked by scripts/router.py only when gbrain is unavailable AND scope == "create".
Exits non-zero and prints a loud diagnostic if the bundled script cannot be found —
never silently swallows the failure (T6 brief, Global Constraints).
"""
import subprocess
import sys
from pathlib import Path

_INIT_SKILL = (
    Path(__file__).resolve().parent.parent.parent / "skill-creator" / "scripts" / "init_skill.py"
)


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: _legacy_init_skill.py <skill-name>", file=sys.stderr)
        return 2
    if not _INIT_SKILL.exists():
        print(f"[ERROR] skill-creator init_skill.py not found at {_INIT_SKILL}", file=sys.stderr)
        return 2
    cmd = [sys.executable, str(_INIT_SKILL), argv[0], "--path", str(Path.cwd())]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    sys.stdout.write(r.stdout.decode(errors="replace"))
    sys.stderr.write(r.stderr.decode(errors="replace"))
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
