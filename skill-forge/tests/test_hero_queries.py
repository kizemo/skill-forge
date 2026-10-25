"""The author generates a standard `references/hero-queries.md` for every
skill it writes.

Perplexity's eval-first principle: a skill should ship with a written
registry of the queries it should match on BEFORE it is finalized. The
three kinds:

  positive           the agent SHOULD match this skill
  negative           the agent should NOT match it (another skill's lane)
  neighbor-confusion it COULD match, but a sibling is the better fit

The third kind is the dangerous one — it surfaces at the resolver level,
not the trigger level, and it is what "action at a distance" breaks.

Deriving the positive queries from `triggers:` is the point: the
machine-readable short-circuit list and the human-readable eval rubric
are then the SAME list, so they cannot drift.
"""
import json
import pytest
from scripts.author import AuthorSpec, author_skill


def _spec(**kw):
    base = dict(
        name="my-skill",
        description="Use when the user asks about widget calibration.",
        triggers=["calibrate widget", "widget reads wrong", "widget scale is off"],
        intent="Calibrate widgets so they measure right.",
        gotchas=["Never trust the vendor's default scale."],
        negative_queries=["write me a python script"],
        neighbor_queries=["the widget dashboard is slow"],
    )
    base.update(kw)
    return AuthorSpec(**base)


def test_author_writes_the_hero_queries_file(tmp_path):
    out = tmp_path / "my-skill"
    author_skill(_spec(), out)
    assert (out / "references" / "hero-queries.md").is_file()


def test_hero_queries_contains_the_three_kinds(tmp_path):
    out = tmp_path / "my-skill"
    author_skill(_spec(), out)
    text = (out / "references" / "hero-queries.md").read_text(encoding="utf-8")
    assert "Positive queries" in text
    assert "Negative queries" in text
    assert "Neighbor-confusion queries" in text


def test_positive_queries_are_derived_from_the_triggers(tmp_path):
    """The eval rubric and the machine-readable `triggers:` list must be
    the SAME list — otherwise they drift and the eval measures a routing
    configuration that no longer exists."""
    out = tmp_path / "my-skill"
    author_skill(_spec(), out)
    text = (out / "references" / "hero-queries.md").read_text(encoding="utf-8")
    for t in ("calibrate widget", "widget reads wrong", "widget scale is off"):
        assert t in text, t


def test_negative_and_neighbor_queries_appear(tmp_path):
    out = tmp_path / "my-skill"
    author_skill(_spec(), out)
    text = (out / "references" / "hero-queries.md").read_text(encoding="utf-8")
    assert "write me a python script" in text
    assert "the widget dashboard is slow" in text


def test_hero_queries_names_the_skill(tmp_path):
    out = tmp_path / "my-skill"
    author_skill(_spec(), out)
    text = (out / "references" / "hero-queries.md").read_text(encoding="utf-8")
    assert "my-skill" in text


def test_hero_queries_states_the_maintenance_rule(tmp_path):
    """The maintenance rule is what makes the file a process rather than
    a snapshot: change 1-2 words at a time, re-run the evals."""
    out = tmp_path / "my-skill"
    author_skill(_spec(), out)
    text = (out / "references" / "hero-queries.md").read_text(encoding="utf-8")
    assert "Maintenance" in text
    low = text.lower()
    assert "1-2" in low or "1–2" in low or "two words" in low or "1-2 words" in low


def test_hero_queries_is_referenced_from_the_skill_md(tmp_path):
    """If the body does not point at the eval file, the agent never
    opens it — the same failure as a references/ dir with no read
    conditions."""
    out = tmp_path / "my-skill"
    author_skill(_spec(), out)
    text = (out / "SKILL.md").read_text(encoding="utf-8")
    assert "references/hero-queries.md" in text


def test_author_can_skip_the_hero_queries_file(tmp_path):
    out = tmp_path / "my-skill"
    author_skill(_spec(hero_queries=False), out)
    assert not (out / "references" / "hero-queries.md").exists()


def test_hero_queries_survives_a_spec_with_no_negative_or_neighbor(tmp_path):
    """A skill with no negatives yet still gets the file — the headings
    stay so the author knows what to fill in later."""
    out = tmp_path / "my-skill"
    author_skill(_spec(negative_queries=[], neighbor_queries=[]), out)
    text = (out / "references" / "hero-queries.md").read_text(encoding="utf-8")
    assert "Negative queries" in text
    assert "Neighbor-confusion queries" in text


def test_spec_roundtrip_keeps_the_query_lists(tmp_path):
    spec = _spec()
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec.to_dict(), ensure_ascii=False), encoding="utf-8")
    from scripts.author import load_spec
    back = load_spec(p)
    assert back.negative_queries == spec.negative_queries
    assert back.neighbor_queries == spec.neighbor_queries


def test_hero_queries_keeps_a_per_query_rationale(tmp_path):
    """A query entry may carry its own "why". "another skill's lane"
    tells the reader nothing about WHICH lane, so the next author has
    to re-derive it."""
    out = tmp_path / "my-skill"
    author_skill(
        _spec(negative_queries=[
            {"query": "write me a python script",
             "why": "that's the normal code lane, not the skill lane"},
        ]),
        out,
    )
    text = (out / "references" / "hero-queries.md").read_text(encoding="utf-8")
    assert "write me a python script" in text
    assert "that's the normal code lane" in text


def test_authored_when_to_use_is_one_sentence_not_the_whole_description(tmp_path):
    """when_to_use is the marketplace one-liner. Defaulting it to the
    WHOLE description re-creates the duplication that blew the index
    tier on real skills."""
    from scripts._lib.frontmatter import load
    out = tmp_path / "my-skill"
    author_skill(
        _spec(description="Use when A. Also covers B. And C as well."),
        out,
    )
    fm = load(out / "SKILL.md")
    assert fm["when_to_use"] == "Use when A."
