import json

import pytest

import bm_config


def test_save_json_atomic_round_trip(tmp_path):
    path = tmp_path / "config.json"
    value = {"name": "測試", "groups": [1, 2, 3]}
    bm_config.save_json_atomic(str(path), value)
    assert json.loads(path.read_text(encoding="utf-8")) == value
    assert list(tmp_path.glob(".bm-config-*.tmp")) == []


def test_save_json_atomic_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "config.json"

    bm_config.save_json_atomic(str(path), {"ok": True})

    assert path.is_file()
    assert bm_config.load_json(str(path)) == {"ok": True}


def test_save_json_atomic_replaces_existing_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"old": true}\n', encoding="utf-8")

    bm_config.save_json_atomic(str(path), {"new": True})

    assert bm_config.load_json(str(path)) == {"new": True}
    assert list(tmp_path.glob(".bm-config-*.tmp")) == []


def test_load_json_returns_default_for_missing_file(tmp_path):
    default = {"groups": []}
    assert bm_config.load_json(str(tmp_path / "missing.json"), default) == default


def test_load_json_returns_default_for_invalid_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text('{not valid json', encoding="utf-8")

    sentinel = {"fallback": True}
    assert bm_config.load_json(str(path), sentinel) is sentinel


def test_save_json_atomic_does_not_replace_when_serialization_fails(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"keep": true}\n', encoding="utf-8")

    with pytest.raises(TypeError):
        bm_config.save_json_atomic(str(path), {"bad": object()})

    assert bm_config.load_json(str(path)) == {"keep": True}
    assert list(tmp_path.glob(".bm-config-*.tmp")) == []
