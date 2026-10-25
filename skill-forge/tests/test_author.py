"""P1: the WRITE lane — skill-forge authors skills, not just audits them.

Until now skill-forge could only audit / improve / retire an existing
skill. Authoring was delegated to Anthropic's skill-creator, which means
the two most important properties of this package — the token rubric
and the progressive-disclosure structure — were only ever applied AFTER
the skill was written, by a human.

The author lane moves the rubric to the FRONT: a skill generated here
comes out already inside the budgets, with the read-conditions table
in place and the heavy detail split into references/.

The contract:
  - SKILL.md is generated LEAN (body under the load-tier budget)
  - the index tier is under budget (description carries 1-2 examples,
    never a phrase list; `triggers:` is the only phrase list)
  - heavy content goes to references/, and the body states WHEN to read
    each file ("Read x.md if <condition>")
  - at least one gotcha section, always
  - the generated result is measured and reported, like every other
    skill-forge output
"""
import json
import pytest
from scripts.author import AuthorSpec, author_skill, load_spec


# --- the spec ---------------------------------------------------------------

def test_spec_roundtrips_through_json(tmp_path):
    spec = AuthorSpec(
        name="my-skill",
        description="Use when the user asks about widget calibration.",
        triggers=["calibrate widget", "widget is off"],
        intent="Calibrate widgets so they measure right.",
        gotchas=["Never trust the vendor's default scale."],
    )
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec.to_dict(), ensure_ascii=False), encoding="utf-8")
    back = load_spec(p)
    assert back.name == "my-skill"
    assert back.triggers == spec.triggers
    assert back.gotchas == spec.gotchas


def test_load_spec_rejects_a_name_that_is_not_kebab_case(tmp_path):
    p = tmp_path / "spec.json"
    p.write_text(json.dumps({"name": "My Skill"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_spec(p)


def test_load_spec_rejects_a_description_without_the_routing_prefix(tmp_path):
    """The description is the routing trigger. A spec whose description
    does not start with Use when/Load when would produce a skill that
    does not route — refuse it at the door."""
    p = tmp_path / "spec.json"
    p.write_text(json.dumps({
        "name": "my-skill",
        "description": "A skill for widgets.",
    }), encoding="utf-8")
    with pytest.raises(ValueError):
        load_spec(p)


# --- the author -------------------------------------------------------------

def _spec(**kw):
    base = dict(
        name="my-skill",
        description="Use when the user asks about widget calibration.",
        triggers=["calibrate widget", "widget reads wrong"],
        intent="Calibrate widgets so they measure right.",
        gotchas=["Never trust the vendor's default scale."],
    )
    base.update(kw)
    return AuthorSpec(**base)


def test_author_creates_the_skill_with_a_skill_md(tmp_path):
    out = tmp_path / "my-skill"
    result = author_skill(_spec(), out)
    assert (out / "SKILL.md").is_file()
    assert result.skill_md_path == out / "SKILL.md"


def test_authored_skill_md_has_a_lean_index_tier(tmp_path):
    """The index tier must be under budget — the description carries
    1-2 examples, never the whole trigger list."""
    from scripts._lib.token_cost import measure_skill
    out = tmp_path / "my-skill"
    author_skill(_spec(), out)
    cost = measure_skill(out)
    assert not cost.index_over_budget, cost.index_tokens


def test_authored_skill_md_has_a_lean_load_tier(tmp_path):
    from scripts._lib.token_cost import measure_skill
    out = tmp_path / "my-skill"
    author_skill(_spec(), out)
    cost = measure_skill(out)
    assert not cost.load_over_budget, cost.load_tokens


def test_authored_skill_md_contains_the_routing_prefix(tmp_path):
    out = tmp_path / "my-skill"
    author_skill(_spec(), out)
    text = (out / "SKILL.md").read_text(encoding="utf-8")
    assert "Use when" in text


def test_authored_skill_md_carries_the_trigger_list_once(tmp_path):
    """The trigger phrases belong in `triggers:` and NOWHERE ELSE. The
    duplication was the cause of the index-tier blowup."""
    out = tmp_path / "my-skill"
    author_skill(_spec(), out)
    text = (out / "SKILL.md").read_text(encoding="utf-8")
    fm = text.split("---")[1]
    desc = fm.split("description:")[1].split("triggers:")[0]
    assert "calibrate widget" not in desc, desc


def test_authored_skill_md_always_has_a_gotcha_section(tmp_path):
    out = tmp_path / "my-skill"
    author_skill(_spec(), out)
    text = (out / "SKILL.md").read_text(encoding="utf-8")
    assert "## Gotchas" in text or "## Common Rationalizations" in text


def test_authored_skill_md_states_where_to_read_each_reference(tmp_path):
    """The read-condition table is the mechanism that makes progressive
    disclosure work: without it, the agent does not know what is not
    already in context."""
    out = tmp_path / "my-skill"
    author_skill(
        _spec(references=[{"path": "references/calibration.md",
                           "when": "the widget scale is wrong",
                           "content": "# Calibration\n\ndetails\n"}]),
        out,
    )
    text = (out / "SKILL.md").read_text(encoding="utf-8")
    assert "references/calibration.md" in text
    assert "the widget scale is wrong" in text


def test_authored_reference_files_are_written(tmp_path):
    out = tmp_path / "my-skill"
    author_skill(
        _spec(references=[{"path": "references/calibration.md",
                           "when": "the widget scale is wrong",
                           "content": "# Calibration\n\ndetails\n"}]),
        out,
    )
    assert (out / "references" / "calibration.md").is_file()


def test_author_reports_the_measured_cost(tmp_path):
    """The author's own output is measured and reported — the same
    contract every audited skill gets."""
    out = tmp_path / "my-skill"
    result = author_skill(_spec(), out)
    assert result.cost is not None
    assert result.cost.index_tokens > 0
    assert result.cost.load_tokens > 0


def test_author_result_reports_the_warnings(tmp_path):
    """A spec that would blow a budget is reported, not silently
    accepted (RULING-1's spirit: absent information is not failure, but
    a known problem must be visible)."""
    out = tmp_path / "my-skill"
    result = author_skill(
        _spec(description="Use when " + "触发场景" * 60), out
    )
    assert result.warnings, "an over-budget spec must produce a warning"


def test_author_refuses_to_overwrite_an_existing_skill(tmp_path):
    out = tmp_path / "my-skill"
    out.mkdir()
    (out / "SKILL.md").write_text("EXISTING\n", encoding="utf-8")
    with pytest.raises(ValueError):
        author_skill(_spec(), out)


def test_author_creates_assets_when_specified(tmp_path):
    out = tmp_path / "my-skill"
    author_skill(
        _spec(assets=[{"path": "assets/report.md", "content": "# Report\n"}]),
        out,
    )
    assert (out / "assets" / "report.md").is_file()


def test_author_creates_scripts_when_specified(tmp_path):
    out = tmp_path / "my-skill"
    author_skill(
        _spec(scripts=[{"path": "scripts/check.py", "content": "print('ok')\n"}]),
        out,
    )
    assert (out / "scripts" / "check.py").is_file()


def test_authored_skill_passes_skill_forge_own_validator(tmp_path):
    """The strongest possible check: a skill skill-forge authored must
    pass skill-forge's own validator with no warnings.

    The author emits the GENERAL skill contract (name, description,
    triggers) plus the gbrain-convention fields, so the result is
    loadable by any host — not just by skill-forge.
    """
    from scripts._lib.frontmatter import load, validate_skill_frontmatter, validate_skill_body
    out = tmp_path / "my-skill"
    author_skill(
        _spec(
            triggers=["calibrate widget", "widget reads wrong", "widget scale"],
            extra_frontmatter={
                "version": "0.1.0",
                "mutating": False,
                "brain_first": "exempt",
                "when_to_use": "Use when the user asks about widget calibration.",
            },
        ),
        out,
    )
    sm = out / "SKILL.md"
    fm = load(sm)
    assert validate_skill_frontmatter(fm, skill_dir=out) == []
    assert validate_skill_body(sm, fm) == []


def test_authored_skill_emits_the_general_contract(tmp_path):
    """A generated skill must be loadable by ANY host, not only by
    skill-forge — so it carries the gbrain-convention fields too."""
    out = tmp_path / "my-skill"
    author_skill(
        _spec(extra_frontmatter={
            "version": "0.1.0",
            "mutating": False,
            "brain_first": "exempt",
            "when_to_use": "Use when the user asks about widget calibration.",
        }),
        out,
    )
    text = (out / "SKILL.md").read_text(encoding="utf-8")
    for field_name in ("name:", "description:", "triggers:", "version:",
                       "mutating:", "brain_first:", "when_to_use:"):
        assert field_name in text, f"{field_name} missing from the generated skill"


def test_authored_skill_defaults_the_convention_fields(tmp_path):
    """When the spec does not supply them, the author fills in sensible
    defaults so the result is complete on its own."""
    out = tmp_path / "my-skill"
    author_skill(
        _spec(triggers=["a", "b", "c"]), out,
    )
    text = (out / "SKILL.md").read_text(encoding="utf-8")
    assert "version:" in text
    assert "mutating:" in text
    assert "brain_first:" in text
    assert "when_to_use:" in text


def test_cli_create_lane_generates_a_skill(tmp_path, capsys):
    """The WRITE lane is reachable from the CLI: --scope create --spec."""
    from scripts.run import main
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({
        "name": "cli-made",
        "description": "Use when the user asks about cli-made things.",
        "triggers": ["cli made", "make cli", "cli thing"],
        "intent": "Do cli-made things.",
        "gotchas": ["Never skip the cli-made setup step."],
    }), encoding="utf-8")
    out = tmp_path / "cli-made"
    rc = main(["--skill", str(out), "--scope", "create", "--spec", str(spec)])
    assert rc == 0
    assert (out / "SKILL.md").is_file()
    captured = capsys.readouterr().out
    assert "author" in captured
    assert "index=" in captured


def test_cli_create_lane_refuses_a_bad_spec(tmp_path, capsys):
    """A spec that would produce an unroutable skill is refused at the
    door, with a message — not silently authored."""
    from scripts.run import main
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({
        "name": "Bad Name",
        "description": "A skill without a routing prefix.",
    }), encoding="utf-8")
    out = tmp_path / "bad"
    rc = main(["--skill", str(out), "--scope", "create", "--spec", str(spec)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "error" in err.lower()
    assert not (out / "SKILL.md").exists()
