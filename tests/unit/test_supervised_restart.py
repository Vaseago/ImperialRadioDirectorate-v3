"""Unit tests for `web.supervised_restart` — the self-restart gate +
mechanism. `trigger_self_restart`'s grace-period sleep is monkeypatched
away so this suite stays fast — the real 1.0s value itself isn't the
behavior under test, the "sleep then signal" ordering is."""

from __future__ import annotations

import asyncio

from web import supervised_restart


def test_supervised_restart_ok_is_a_bool():
    # Read once at import from SUPERVISED_RESTART_OK — this just locks the
    # type/contract, not the real env's current value (irrelevant here).
    assert isinstance(supervised_restart.SUPERVISED_RESTART_OK, bool)


def test_trigger_self_restart_calls_the_injected_restart_fn(monkeypatch):
    monkeypatch.setattr(supervised_restart.asyncio, "sleep", lambda *_a, **_k: _immediate())
    calls = []
    asyncio.run(supervised_restart.trigger_self_restart(restart_fn=lambda: calls.append(1)))
    assert calls == [1]


def test_trigger_self_restart_sleeps_before_signaling(monkeypatch):
    order = []
    monkeypatch.setattr(supervised_restart.asyncio, "sleep", lambda *_a, **_k: _record_sleep(order))
    asyncio.run(supervised_restart.trigger_self_restart(restart_fn=lambda: order.append("restart")))
    assert order == ["sleep", "restart"]


def test_trigger_self_restart_defaults_to_a_real_os_kill(monkeypatch):
    """Never actually sends a real SIGTERM in a test — confirms the
    DEFAULT wiring is `_real_restart` (patched here to a spy) rather than
    a silent no-op, without ever calling the real `os.kill`."""
    monkeypatch.setattr(supervised_restart.asyncio, "sleep", lambda *_a, **_k: _immediate())
    calls = []
    monkeypatch.setattr(supervised_restart, "_real_restart", lambda: calls.append("real"))
    asyncio.run(supervised_restart.trigger_self_restart())
    assert calls == ["real"]


async def _immediate():
    return None


async def _record_sleep(order):
    order.append("sleep")
