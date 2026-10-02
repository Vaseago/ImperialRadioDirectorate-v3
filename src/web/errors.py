"""Maps core domain exceptions to typed HTTP responses — registered once
on the app (`register_exception_handlers`), so every router stays a thin
`try`-free call into `services`/`solvers` (no core domain exception ever
reaches the client as a raw, unstructured 500).

Hand-matched from ISD v3's own `web/errors.py` (itself hand-matched from
IID v3's) — generic cross-app infrastructure, not domain logic.

| Exception              | HTTP | Body                                    |
|-------------------------|-----:|------------------------------------------|
| `DomainRuleViolation`   |  400 | `{"detail": str, "rule": str \\| None}` |
| `ValueError`            |  400 | `{"detail": str}`                        |
| `FileNotFoundError`     |  404 | `{"detail": str}`                        |
| `storage.StorageError`  |  500 | `{"detail": str, "kind": "storage_error"}` — a real server-side data fault (corrupt file / wrong schema version), never silently swallowed, but still a controlled, typed shape rather than a bare traceback. |

FastAPI's own `RequestValidationError` handling (422 on a malformed
request body) is untouched — nothing here needs to intercept it.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from primitives.errors import DomainRuleViolation
from storage import StorageError

__all__ = ["register_exception_handlers"]


async def _domain_rule_violation_handler(request: Request, exc: DomainRuleViolation) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc), "rule": exc.rule})


async def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def _not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc) or "not found"})


async def _storage_error_handler(request: Request, exc: StorageError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc), "kind": "storage_error"})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainRuleViolation, _domain_rule_violation_handler)
    app.add_exception_handler(ValueError, _value_error_handler)
    app.add_exception_handler(FileNotFoundError, _not_found_handler)
    app.add_exception_handler(StorageError, _storage_error_handler)
