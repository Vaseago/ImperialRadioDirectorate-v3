"""The Iron Gate — structural build-constraint audit for IRD v3.

Enforces the invariants an ordinary unit test cannot:

1. no SQL / ORM engine anywhere in ``src/`` at all — unlike the other v3
   apps, IRD v3 has no SDE to read, so there is no sqlite3 exception here;
2. every ``@dataclass`` in ``src/primitives/`` and ``src/schema/`` is
   ``frozen=True, slots=True``;
3. module imports follow the layer DAG
   ``config < primitives < schema < {storage, adapters} < solvers <
   services < web`` (no ``resolvers`` layer — IRD v3 has no dogma-graph
   concept, matching ILD v3's own narrower DAG);
4. **Manager Isolation Law**: no `web/routers/` module may import a real
   persisted-document ``*Store`` class directly — persistence goes through
   a ``*Manager`` pulled off `app.state`. Empty allowlist for now (no
   Store/Manager pair exists yet); add one here the moment a real one
   lands, same hand-matched shape the sibling apps use.
5. **Lint-clean**: ``ruff check`` over the whole ``src/`` tree must pass
   with zero violations under this repo's own ``[tool.ruff]`` config.

Runs as part of the normal ``pytest`` sweep — a violation fails the build.
Checks 1-4 parse source with ``ast`` and never import the modules; check 5
shells out to the real ``ruff`` binary.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _py_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _imported_modules(tree: ast.AST) -> set[str]:
    """Every absolute dotted module name imported by this tree. Relative
    imports (``from . import x``) stay inside their own package and cannot
    cross a layer boundary upward, so they are ignored."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module)
    return names


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# ===================================================================== #
# 0. the harness is actually pointed at the real source tree
# ===================================================================== #


def test_iron_gate_is_scanning_the_real_src_tree():
    files = _py_files(SRC)
    assert files, f"no .py files found under {SRC} — harness misconfigured"
    assert any(p.name == "config.py" and p.parent == SRC for p in files)


# ===================================================================== #
# 1. no SQL / ORM engine at all — IRD v3 has no SDE, no exception needed
# ===================================================================== #

_BANNED_SQL = {
    "sqlalchemy",
    "alembic",
    "sqlmodel",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "pymysql",
    "MySQLdb",
    "peewee",
    "tortoise",
    "pony",
    "databases",
    "aiosqlite",
    "sqlite3",
}


def test_no_sql_or_orm_engine_in_src():
    offenders: list[str] = []
    for path in _py_files(SRC):
        for module in _imported_modules(_parse(path)):
            top = module.split(".")[0]
            if top in _BANNED_SQL:
                offenders.append(f"{path.relative_to(SRC)}: imports {module}")
    assert not offenders, "SQL/ORM engine in src/:\n  " + "\n  ".join(offenders)


# ===================================================================== #
# 2. primitive / schema dataclasses are frozen + slotted
# ===================================================================== #


def _is_dataclass_decorator(deco: ast.expr) -> bool:
    target = deco.func if isinstance(deco, ast.Call) else deco
    if isinstance(target, ast.Name):
        return target.id == "dataclass"
    if isinstance(target, ast.Attribute):
        return target.attr == "dataclass"
    return False


def _keyword_is_true(deco: ast.expr, name: str) -> bool:
    if not isinstance(deco, ast.Call):
        return False
    for kw in deco.keywords:
        if kw.arg == name:
            return isinstance(kw.value, ast.Constant) and kw.value.value is True
    return False


def _check_dataclasses_frozen_slotted(root: Path) -> list[str]:
    bad: list[str] = []
    for path in _py_files(root):
        for node in ast.walk(_parse(path)):
            if not isinstance(node, ast.ClassDef):
                continue
            decos = [d for d in node.decorator_list if _is_dataclass_decorator(d)]
            if not decos:
                continue  # plain classes are intentional (e.g. a Protocol)
            deco = decos[0]
            missing = [flag for flag in ("frozen", "slots") if not _keyword_is_true(deco, flag)]
            if missing:
                rel = path.relative_to(SRC)
                bad.append(f"{rel}::{node.name} missing {', '.join(missing)}=True")
    return bad


def test_primitive_dataclasses_are_frozen_and_slotted():
    bad = _check_dataclasses_frozen_slotted(SRC / "primitives")
    assert not bad, "primitive @dataclass not frozen+slotted:\n  " + "\n  ".join(bad)


def test_schema_dataclasses_are_frozen_and_slotted():
    """Persisted-document types (`schema/`) must be immutable — a mutable
    on-disk model is how state corruption creeps in."""
    bad = _check_dataclasses_frozen_slotted(SRC / "schema")
    assert not bad, "schema @dataclass not frozen+slotted:\n  " + "\n  ".join(bad)


# ===================================================================== #
# 3. layer import DAG
# ===================================================================== #

_LAYER_ALLOW: dict[str, set[str]] = {
    "config": {"config"},
    "primitives": {"config", "primitives"},
    "schema": {"config", "primitives", "schema"},
    "storage": {"config", "primitives", "schema", "storage"},
    "adapters": {"config", "primitives", "schema", "adapters"},
    "solvers": {"config", "primitives", "schema", "solvers"},
    "services": {"config", "primitives", "schema", "storage", "adapters", "solvers", "services"},
    "web": {"config", "primitives", "schema", "storage", "adapters", "solvers", "services", "web"},
}
_LAYERS = set(_LAYER_ALLOW)


def _layer_of(rel: Path) -> str:
    """Top-level package for a src-relative path; a top-level module like
    ``config.py`` is its own stem."""
    first = rel.parts[0]
    return first[:-3] if first.endswith(".py") else first


def test_layer_imports_follow_the_dag():
    violations: list[str] = []
    for path in _py_files(SRC):
        rel = path.relative_to(SRC)
        layer = _layer_of(rel)
        allowed = _LAYER_ALLOW.get(layer)
        if allowed is None:
            continue
        for module in _imported_modules(_parse(path)):
            top = module.split(".")[0]
            if top in _LAYERS and top not in allowed:
                violations.append(f"{rel} (layer '{layer}') imports '{module}'")
    assert not violations, "cross-layer import violations:\n  " + "\n  ".join(violations)


# ===================================================================== #
# 4. Manager Isolation Law — routers never touch a *Store directly
# ===================================================================== #

_ROUTERS_DIR = SRC / "web" / "routers"

# Real persisted-document Store classes, each behind exactly one owning
# Manager — the ONLY things a router may never import directly. Never
# widen this into a generic name-suffix check (see the sibling apps' own
# history of a false positive on an in-memory, non-persisted Store there).
_FORBIDDEN_STORE_IMPORTS: dict[str, str] = {
    "PlaybackResumeStateStore": "services.resume_state_store.ResumeCheckpointManager",
}


def test_routers_never_import_a_store_directly():
    violations: list[str] = []
    for path in _py_files(_ROUTERS_DIR):
        tree = _parse(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            for alias in node.names:
                if alias.name in _FORBIDDEN_STORE_IMPORTS:
                    manager = _FORBIDDEN_STORE_IMPORTS[alias.name]
                    violations.append(
                        f"{path.relative_to(SRC)}: imports {alias.name} directly — use {manager} instead"
                    )
    assert not violations, "Manager Isolation Law violated:\n  " + "\n  ".join(violations)


# ===================================================================== #
# 5. lint-clean — ruff, baked into the Iron Gate itself
# ===================================================================== #


def test_ruff_check_is_clean():
    """`ruff check` over the whole `src/` AND `tests/` trees, under this repo's own
    `[tool.ruff]` config, must pass with zero violations — same "no
    warnings, no soft overrides" standard every other Iron Gate check
    holds. Shells out to the real `ruff` (installed as a `dev` extra,
    `pyproject.toml`) rather than re-implementing lint rules here."""
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", str(SRC), str(REPO_ROOT / "tests")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    message = "ruff check failed — fix the violation, don't relax this test:\n"
    assert result.returncode == 0, message + result.stdout + result.stderr
