"""Unit tests for `storage.json_store.JsonStore` — the atomic typed-JSON
envelope every IRD v3 persisted document is wrapped in."""

from __future__ import annotations

import json

import pytest

from primitives.errors import DomainRuleViolation
from storage import CorruptStoreError, JsonStore, SchemaVersionError


def test_write_then_read_roundtrips(tmp_path):
    store = JsonStore(path=tmp_path / "doc.json", schema_version=1)
    store.write({"a": 1, "b": [1, 2, 3]})
    assert store.read() == {"a": 1, "b": [1, 2, 3]}


def test_write_wraps_in_schema_version_envelope(tmp_path):
    path = tmp_path / "doc.json"
    JsonStore(path=path, schema_version=3).write({"x": True})
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == {"schema_version": 3, "data": {"x": True}}


def test_write_creates_parent_directories(tmp_path):
    path = tmp_path / "a" / "b" / "c" / "doc.json"
    JsonStore(path=path, schema_version=1).write({"ok": True})
    assert path.is_file()


def test_write_rejects_non_dict_payload(tmp_path):
    store = JsonStore(path=tmp_path / "doc.json", schema_version=1)
    with pytest.raises(DomainRuleViolation):
        store.write(["not", "a", "dict"])  # type: ignore[arg-type]


def test_write_leaves_no_tmp_file_behind(tmp_path):
    store = JsonStore(path=tmp_path / "doc.json", schema_version=1)
    store.write({"a": 1})
    leftovers = [p for p in tmp_path.iterdir() if p.name != "doc.json"]
    assert leftovers == []


def test_read_missing_file_raises_file_not_found(tmp_path):
    store = JsonStore(path=tmp_path / "missing.json", schema_version=1)
    with pytest.raises(FileNotFoundError):
        store.read()


def test_read_invalid_json_raises_corrupt(tmp_path):
    path = tmp_path / "doc.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(CorruptStoreError):
        JsonStore(path=path, schema_version=1).read()


def test_read_missing_envelope_keys_raises_corrupt(tmp_path):
    path = tmp_path / "doc.json"
    path.write_text(json.dumps({"just": "data"}), encoding="utf-8")
    with pytest.raises(CorruptStoreError):
        JsonStore(path=path, schema_version=1).read()


def test_read_non_dict_data_raises_corrupt(tmp_path):
    path = tmp_path / "doc.json"
    path.write_text(json.dumps({"schema_version": 1, "data": [1, 2]}), encoding="utf-8")
    with pytest.raises(CorruptStoreError):
        JsonStore(path=path, schema_version=1).read()


def test_read_wrong_schema_version_raises(tmp_path):
    path = tmp_path / "doc.json"
    JsonStore(path=path, schema_version=1).write({"a": 1})
    with pytest.raises(SchemaVersionError):
        JsonStore(path=path, schema_version=2).read()


def test_read_or_returns_default_deep_copy_when_missing(tmp_path):
    store = JsonStore(path=tmp_path / "missing.json", schema_version=1)
    default = {"nested": {"a": 1}}
    result = store.read_or(default)
    assert result == default
    result["nested"]["a"] = 999
    assert default["nested"]["a"] == 1  # untouched — a real deep copy


def test_read_or_still_raises_on_a_present_but_corrupt_file(tmp_path):
    path = tmp_path / "doc.json"
    path.write_text("not json", encoding="utf-8")
    store = JsonStore(path=path, schema_version=1)
    with pytest.raises(CorruptStoreError):
        store.read_or({"default": True})


def test_exists(tmp_path):
    store = JsonStore(path=tmp_path / "doc.json", schema_version=1)
    assert store.exists() is False
    store.write({"a": 1})
    assert store.exists() is True


def test_schema_version_must_be_positive_int(tmp_path):
    with pytest.raises(DomainRuleViolation):
        JsonStore(path=tmp_path / "doc.json", schema_version=0)
    with pytest.raises(DomainRuleViolation):
        JsonStore(path=tmp_path / "doc.json", schema_version=True)  # type: ignore[arg-type]
