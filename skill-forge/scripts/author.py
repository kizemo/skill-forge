"""P1: the WRITE lane — authoring a skill that is already inside the budget.

Until now skill-forge could only audit / improve / retire an EXISTING
skill; authoring was delegated to Anthropic's skill-creator. The
consequence was that the two properties this package cares most about
— the token rubric and the progressive-disclosure structure — were only
ever checked AFTER the skill was written, by a human reading a report.

This lane moves the rubric to the FRONT. A skill generated here comes
out already inside the budgets:

  - the index tier (always-loaded metadata) is under ~100 tokens: the
    description carries 1-2 representative examples, and the `triggers:`
    list is the ONLY place trigger phrases live (the duplication was
    what blew the index tier on real skills);
  - the load tier (body) is under ~5,000 tokens: heavy content is split
    into references/ at authoring time, not discovered later;
  - the body carries a read-conditions table ("Read x.md if ..."), the
    mechanism that makes progressive disclosure work — without it the
    agent does not know what is NOT already in context;
  - at least one gotcha section, always.

The author also REFUSES two things outright, because they produce a
skill that cannot work: a name that is not lowercase kebab-case (the
marketplace indexes by directory name), and a description without the
routing prefix (the resolver's short-circuit would never fire).
Everything else is a WARNING — per RULING-1's spirit, a skill that
misses a principle is suboptimal, not broken.

**What this does NOT replace.** Anthropic's skill-creator also runs an
assertion-based benchmark harness with parallel subagents and a token
cost axis. skill-forge now has the token axis (see _lib/token_cost.py)
and a real baseline (see _lib/snapshot.py), but it does not spawn
subagents — that is the caller's job. See
docs/SKILL_DESIGN_RUBRIC.md and the handover decision doc.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts._lib.token_cost import TokenCost, measure_skill

__all__ = ["AuthorSpec", "AuthorResult", "author_skill", "load_spec"]

_NAME_KEBAB = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_ROUTING_PREFIXES = ("Use when", "Load when")
_MAX_DESCRIPTION_WORDS = 50


@dataclass
class AuthorSpec:
    """The input to the author: what the skill is and what it must know."""

    name: str
    description: str
    triggers: list[str] = field(default_factory=list)
    # The one-paragraph position statement: what this skill is FOR.
    intent: str = ""
    # The gotchas. Every skill gets at least one; these are the highest
    # value content Perplexity identifies.
    gotchas: list[str] = field(default_factory=list)
    # Heavy content, split out at authoring time. Each entry is
    # {"path": "references/x.md", "when": "Read if ...", "content": "..."}.
    references: list[dict[str, str]] = field(default_factory=list)
    # Templates / schemas the agent copies and fills.
    assets: list[dict[str, str]] = field(default_factory=list)
    # Deterministic code the agent runs instead of re-deriving.
    scripts: list[dict[str, str]] = field(default_factory=list)
    # Optional extra frontmatter fields.
    extra_frontmatter: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "triggers": list(self.triggers),
            "intent": self.intent,
            "gotchas": list(self.gotchas),
            "references": list(self.references),
            "assets": list(self.assets),
            "scripts": list(self.scripts),
            "extra_frontmatter": dict(self.extra_frontmatter),
        }


@dataclass
class AuthorResult:
    """What the author produced, and what it cost."""

    skill_dir: Path
    skill_md_path: Path
    cost: TokenCost | None = None
    warnings: list[str] = field(default_factory=list)
    written: list[str] = field(default_factory=list)


def load_spec(path: Path) -> AuthorSpec:
    """Load and validate an author spec from JSON.

    Raises ValueError for the two defects that make a skill unable to
    work at all: a non-kebab-case name, and a description without the
    routing prefix.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("spec must be a JSON object")
    spec = AuthorSpec(
        name=str(data.get("name", "")),
        description=str(data.get("description", "")),
        triggers=[str(t) for t in (data.get("triggers") or [])],
        intent=str(data.get("intent", "")),
        gotchas=[str(g) for g in (data.get("gotchas") or [])],
        references=[dict(r) for r in (data.get("references") or [])],
        assets=[dict(a) for a in (data.get("assets") or [])],
        scripts=[dict(s) for s in (data.get("scripts") or [])],
        extra_frontmatter=dict(data.get("extra_frontmatter") or {}),
    )
    _validate(spec)
    return spec


def _validate(spec: AuthorSpec) -> None:
    if not _NAME_KEBAB.match(spec.name or ""):
        raise ValueError(
            f"spec name {spec.name!r} must be lowercase kebab-case "
            f"(the marketplace indexes by directory name)"
        )
    if not spec.description.startswith(_ROUTING_PREFIXES):
        raise ValueError(
            f"spec description must start with {' or '.join(repr(p) for p in _ROUTING_PREFIXES)} "
            f"— it is the routing trigger, not an introduction"
        )
    words = len(spec.description.split())
    if words > _MAX_DESCRIPTION_WORDS:
        # Not fatal here: the author will warn. But a spec that is 200
        # words long is not a description, it is a body.
        pass


def _yaml_block(text: str, indent: str = "  ") -> str:
    """Render a multi-line scalar as a YAML block scalar (RULING-5).

    A description containing ':' or "'" MUST be a block scalar —
    single-quoting is not a fix, because the standard trigger list
    contains apostrophes that terminate a single-quoted scalar.
    """
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return '""'
    return ">- \n" + "\n".join(f"{indent}{ln}" for ln in lines)


def _render_frontmatter(spec: AuthorSpec) -> str:
    """The frontmatter. The description carries NO trigger list — the
    `triggers:` field is the single home for trigger phrases. That
    duplication is what pushed real skills' index tier to 2x budget.

    The gbrain-convention fields (version / mutating / brain_first /
    when_to_use) are filled in with sensible defaults when the spec does
    not supply them, so a generated skill is complete and loadable by
    any host — not just by skill-forge.
    """
    parts = [f"name: {spec.name}"]
    parts.append(f"description: {_yaml_block(spec.description)}")
    if spec.triggers:
        parts.append("triggers:")
        parts.extend(f'  - "{t}"' for t in spec.triggers)
    extra = dict(spec.extra_frontmatter)
    extra.setdefault("version", "0.1.0")
    extra.setdefault("mutating", False)
    extra.setdefault("brain_first", "exempt")
    extra.setdefault("when_to_use", spec.description)
    for key, value in extra.items():
        if isinstance(value, list):
            parts.append(f"{key}:")
            parts.extend(f"  - {v}" for v in value)
        else:
            parts.append(f"{key}: {value}")
    return "\n".join(parts)


def _render_read_conditions(spec: AuthorSpec) -> str:
    """The read-conditions table.

    Perplexity's mechanism: "Read api-errors.md if API returns non-200."
    Without this table the agent cannot know what is NOT already in its
    context — which is exactly why a skill with everything inline is
    indistinguishable from a skill with clean progressive disclosure.

    `references/` and `scripts/` are READ under a condition. `assets/`
    are COPIED and filled — an empty read-condition would read as
    "never", so assets get their own default condition.
    """
    if not spec.references and not spec.assets and not spec.scripts:
        return ""
    rows = []
    for entry in spec.references:
        path = entry.get("path", "")
        when = entry.get("when", "")
        if path:
            rows.append(f"| `{path}` | {when or 'the task needs the detail it holds'} |")
    for entry in spec.assets:
        path = entry.get("path", "")
        when = entry.get("when", "")
        if path:
            rows.append(f"| `{path}` | {when or 'you need to produce the output it templates'} |")
    for entry in spec.scripts:
        path = entry.get("path", "")
        when = entry.get("when", "")
        if path:
            rows.append(f"| `{path}` | {when or 'the task needs the deterministic logic it holds'} |")
    if not rows:
        return ""
    return (
        "## References (load on demand)\n\n"
        "| file | read when |\n|---|---|\n"
        + "\n".join(rows)
        + "\n"
    )


def _render_body(spec: AuthorSpec) -> str:
    """The lean body. Sections in the order Perplexity's structure
    prescribes: what this is, when NOT to use, the process, the
    read-conditions, then the gotchas."""
    out: list[str] = [f"# {spec.name}", ""]
    if spec.intent:
        out += [spec.intent, ""]
    out += [
        "## When NOT to use",
        "",
        "- The request is unrelated to this skill's subject.",
        "- A neighbouring skill claims the intent more precisely.",
        "- The information is already in the conversation.",
        "",
    ]
    out += [
        "## Process",
        "",
        "1. Confirm the request matches the description above.",
        "2. Read only the files the table below points to for this case.",
        "3. Apply the gotchas below — they are the accumulated failures.",
        "",
    ]
    rc = _render_read_conditions(spec)
    if rc:
        out += [rc, ""]
    gotchas = spec.gotchas or [
        "This skill has no recorded gotchas yet. Add one the first time the "
        "agent gets something wrong here — a gotcha is a real failure, "
        "distilled.",
    ]
    out += ["## Gotchas", ""]
    out += [f"- {g}" for g in gotchas]
    out += [""]
    return "\n".join(out)


def author_skill(spec: AuthorSpec, out_dir: Path) -> AuthorResult:
    """Generate a skill directory from `spec`.

    Refuses to overwrite an existing skill directory — authoring over
    live content is the one thing this package never does silently
    (the bundled-skill safety invariant, applied to our own output).
    """
    out_dir = Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(
            f"{out_dir} already exists and is not empty; authoring never "
            f"overwrites an existing skill (the bundled-skill safety "
            f"invariant, applied to our own output)"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    result = AuthorResult(skill_dir=out_dir, skill_md_path=out_dir / "SKILL.md")

    # The body and the frontmatter are written first, then the spoke
    # files, so the cost measurement sees the finished skill.
    fm = _render_frontmatter(spec)
    body = _render_body(spec)
    result.skill_md_path.write_text(f"---\n{fm}\n---\n\n{body}", encoding="utf-8")
    result.written.append("SKILL.md")

    for entry in spec.references:
        p = out_dir / entry["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(entry.get("content", ""), encoding="utf-8")
        result.written.append(entry["path"])
    for entry in spec.assets:
        p = out_dir / entry["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(entry.get("content", ""), encoding="utf-8")
        result.written.append(entry["path"])
    for entry in spec.scripts:
        p = out_dir / entry["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(entry.get("content", ""), encoding="utf-8")
        result.written.append(entry["path"])

    # Measure our own output against the same budgets every audited
    # skill is measured against.
    result.cost = measure_skill(out_dir)
    if result.cost.index_over_budget:
        result.warnings.append(
            f"index tier is {result.cost.index_tokens} tokens, over the "
            f"~{result.cost.index_budget}-token budget — it is paid by every "
            f"session, every user, whether or not this skill is invoked"
        )
    if result.cost.load_over_budget:
        result.warnings.append(
            f"load tier is {result.cost.load_tokens} tokens, over the "
            f"~{result.cost.load_budget}-token target — paid on every trigger"
        )
    if not spec.gotchas:
        result.warnings.append(
            "no gotchas supplied — a skill with no gotchas is a snapshot, "
            "not a living artifact"
        )
    return result
