"""Atomic, typed JSON persistence — the only storage mechanism in v3.

Every persisted document is wrapped in an envelope::

    {"schema_version": <int>, "data": {...}}

Writes are crash-safe: the payload is written to a temp file in the *same*
directory, flushed and ``fsync``'d, then ``os.replace``'d over the target
(atomic on POSIX and Windows). A partially-written file can never be observed
at the real path. No SQLAlchemy, no ORM, no SQL engine at all — IRD v3 has
no SDE to read, so unlike the other v3 apps there's no sqlite3 exception
anywhere in this app.

`StorageError` and its subclasses are raised when the *file* is at fault
(missing envelope, bad JSON, wrong schema version). `DomainRuleViolation` is
raised when the *caller* is at fault (a non-`dict` payload, a `schema_version`
that is not an int >= 1) — the same fatal-circuit-breaker contract as the rest
of v3.

Hand-matched from ISD v3's own `storage/json_store.py` (itself hand-matched
from IID v3's) — generic cross-app infrastructure, not domain logic, same
footing as a sibling app's own `adapters/esi/auth.py` exception.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from primitives.errors import DomainRuleViolation

__all__ = ["JsonStore", "StorageError", "SchemaVersionError", "CorruptStoreError"]


class StorageError(Exception):
    """Base class for storage faults that are about the file, not the caller."""


class SchemaVersionError(StorageError):
    """The stored document's ``schema_version`` is not the one requested."""

    def __init__(self, path: Path, found: int, expected: int) -> None:
        super().__init__(f"{path}: schema_version {found}, expected {expected}")
        self.path = path
        self.found = found
        self.expected = expected


class CorruptStoreError(StorageError):
    """The file is not valid JSON, or not a well-formed v3 envelope."""


def _require_schema_version(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DomainRuleViolation(
            f"schema_version must be an int >= 1, got {value!r}",
            rule="json_store.schema_version",
        )
    return value


@dataclass(frozen=True, slots=True)
class JsonStore:
    """A typed JSON document at `path`, expected on schema `schema_version`."""

    path: Path
    schema_version: int

    def __post_init__(self) -> None:
        _require_schema_version(self.schema_version)
        if not isinstance(self.path, Path):
            object.__setattr__(self, "path", Path(self.path))

    # -- write ------------------------------------------------------------- #

    def write(self, data: dict[str, Any]) -> None:
        """Atomically write `data` under this store's schema version.

        Creates parent directories as needed. Raises `DomainRuleViolation` if
        `data` is not a ``dict``.
        """
        if not isinstance(data, dict):
            raise DomainRuleViolation(
                f"JsonStore.write expects a dict, got {type(data).__name__}",
                rule="json_store.write",
            )
        envelope = {"schema_version": self.schema_version, "data": data}
        body = json.dumps(envelope, indent=2, sort_keys=True, ensure_ascii=False)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    # -- read -------------------------------------------------------------- #

    def read(self) -> dict[str, Any]:
        """Return the document's ``data`` object.

        Raises `FileNotFoundError` if the file does not exist, `CorruptStoreError`
        for invalid JSON or a malformed envelope, and `SchemaVersionError` if
        the stored ``schema_version`` differs from this store's.
        """
        raw = self.path.read_text(encoding="utf-8")  # FileNotFoundError propagates
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CorruptStoreError(f"{self.path}: invalid JSON: {exc}") from exc

        if not isinstance(doc, dict) or "schema_version" not in doc or "data" not in doc:
            raise CorruptStoreError(f"{self.path}: not a v3 envelope (need 'schema_version' and 'data' keys)")

        found = doc["schema_version"]
        if isinstance(found, bool) or not isinstance(found, int):
            raise CorruptStoreError(f"{self.path}: schema_version is not an int ({found!r})")
        if found != self.schema_version:
            raise SchemaVersionError(self.path, found, self.schema_version)

        data = doc["data"]
        if not isinstance(data, dict):
            raise CorruptStoreError(f"{self.path}: 'data' is not an object ({type(data).__name__})")
        return data

    def read_or(self, default: dict[str, Any]) -> dict[str, Any]:
        """Like `read`, but return a deep copy of `default` if the file does
        not exist yet.

        A file that *exists* but is corrupt or on the wrong schema still
        raises — a present-but-bad file is never silently replaced with
        defaults.
        """
        try:
            return self.read()
        except FileNotFoundError:
            return copy.deepcopy(default)

    def exists(self) -> bool:
        return self.path.is_file()
