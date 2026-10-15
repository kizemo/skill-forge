"""v2-T4: bundled-skill classification (is_bundled).

is_bundled() reads ~/.gbrain/install.json and reports whether skill_dir is
part of a gbrain marketplace install. Bundled installs are read-only from
skill-forge's perspective.

Monkeypatch note (v2-T4 fix of the brief's typo): the brief's Step 1 tests
used `monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)`. That is
too late — `scripts._lib.bundle.INSTALL_JSON` is evaluated at module import
time, so overriding Path.home afterwards has no effect on it. These tests
override the module-level constant directly instead.
"""
import json
from pathlib import Path
import pytest
from scripts._lib.bundle import is_bundled


def test_is_bundled_returns_true_when_skill_dir_matches_install_json(tmp_path, monkeypatch):
    """A: the skill's resolved path appears in install.json → bundled."""
    install = tmp_path / "install.json"
    skill = tmp_path / "plugins" / "my-skill"
    skill.mkdir(parents=True)
    install.write_text(
        json.dumps({"my-skill": str(skill.resolve())}),
        encoding="utf-8",
    )
    # INSTALL_JSON is captured at import time; override it directly.
    monkeypatch.setattr("scripts._lib.bundle.INSTALL_JSON", install)
    assert is_bundled(skill) is True


def test_is_bundled_returns_false_for_non_bundled_skill(tmp_path, monkeypatch):
    """B: a decoy with the same basename elsewhere is not bundled."""
    install = tmp_path / "install.json"
    bundled = tmp_path / "plugins" / "my-skill"
    bundled.mkdir(parents=True)
    install.write_text(
        json.dumps({"my-skill": str(bundled.resolve())}),
        encoding="utf-8",
    )
    decoy = tmp_path / "elsewhere" / "my-skill"
    decoy.mkdir(parents=True)
    monkeypatch.setattr("scripts._lib.bundle.INSTALL_JSON", install)
    assert is_bundled(decoy) is False


def test_is_bundled_returns_false_when_install_json_missing(tmp_path, monkeypatch):
    """C: missing install.json fails OPEN (treated as not-bundled).

    Fail-open is v2 Default Decision #2: fail-closed would block every run
    on a host without a gbrain install.
    """
    skill = tmp_path / "x"
    skill.mkdir()
    monkeypatch.setattr("scripts._lib.bundle.INSTALL_JSON", tmp_path / "install.json")
    assert is_bundled(skill) is False


def test_is_bundled_returns_false_when_install_json_malformed(tmp_path, monkeypatch):
    """D: malformed JSON fails OPEN, and is_bundled() does not raise."""
    install = tmp_path / "install.json"
    install.write_text("{ not valid json", encoding="utf-8")
    skill = tmp_path / "x"
    skill.mkdir()
    monkeypatch.setattr("scripts._lib.bundle.INSTALL_JSON", install)
    assert is_bundled(skill) is False
