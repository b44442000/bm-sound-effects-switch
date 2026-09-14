import json

import bm_config


def test_save_json_atomic_round_trip(tmp_path):
    path = tmp_path / "config.json"
    value = {"name": "測試", "groups": [1, 2, 3]}
    bm_config.save_json_atomic(str(path), value)
    assert json.loads(path.read_text(encoding="utf-8")) == value


def test_load_json_returns_default_for_missing_file(tmp_path):
    default = {"groups": []}
    assert bm_config.load_json(str(tmp_path / "missing.json"), default) == default
