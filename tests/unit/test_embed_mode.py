"""Embed mode (the page shown inside the ICD desktop app) - static guards.

The contract is ICD's docs/EMBED_CONTRACT.md. These fail if the page loses a
piece of it: the boot flag, the chrome-hiding stylesheet, `window.icdEmbed`'s
members, or a `data-icd-panel` sticker. There is no JS runtime in this test
environment, so behaviour (with and without the flag) is verified live in the
browser pane; these guard the structure that makes it possible, and the "a
normal visit is unchanged" half of the contract.

IRD's frontend is plain (classic scripts, no router, no theme), so it meets the
contract by its own means - see js/icdEmbed.js.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from web.app import create_app

_STATIC = Path(__file__).resolve().parents[2] / "src" / "web" / "static"
_PANEL_KINDS = {"page", "card", "table", "modal", "button"}
_TAG = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)\b([^<>]*?)>")


def _read(rel: str) -> str:
    return (_STATIC / rel).read_text(encoding="utf-8")


def _expected_kind(tag: str, attrs: str) -> str | None:
    """The sticker kind a tag must carry, or None when it needs none."""
    cls = re.search(r'class="([^"]*)"', attrs)
    tokens = cls.group(1).split() if cls else []
    if tag == "table":
        return "table"
    if "modal" in tokens:
        return "modal"
    if any(t == "card" or (t.endswith("-card") and "__" not in t) for t in tokens):
        return "card"
    return None


def _sticker_problems(source: str) -> list[str]:
    """Every tag that needs a panel sticker but lacks the right one, and every sticker value outside the vocabulary."""
    problems = []
    for m in _TAG.finditer(source):
        tag, attrs = m.group(1), m.group(2)
        found = re.search(r'data-icd-panel="([^"]*)"', attrs)
        if found and found.group(1) not in _PANEL_KINDS:
            problems.append(f"unknown kind {found.group(1)!r} in <{tag}{attrs}>")
        want = _expected_kind(tag, attrs)
        if want and (not found or found.group(1) != want):
            problems.append(f"<{tag}{attrs}> needs data-icd-panel=\"{want}\"")
    return problems


def test_boot_script_sets_the_embed_flag_before_anything_else_loads():
    html = _read("index.html")
    assert 'new URLSearchParams(window.location.search).get("embed")' in html
    assert 'EMBED_KEY = "icd.embed"' in html
    assert 'document.documentElement.dataset.embed = "1"' in html
    assert 'document.documentElement.dataset.theme = "icd"' in html
    # ?embed=1 remembers, ?embed=0 forgets, neither falls back to the memory
    assert 'sessionStorage.setItem(EMBED_KEY, "1")' in html
    assert "sessionStorage.removeItem(EMBED_KEY)" in html
    assert 'sessionStorage.getItem(EMBED_KEY) === "1"' in html
    # the decision is inline in <head>, ahead of every stylesheet and script
    assert html.index("dataset.embed") < html.index('href="css/embed.css"') < html.index("<body>")
    assert html.index("dataset.embed") < html.index('src="js/')


def test_every_embed_css_rule_is_gated_on_the_flag_and_uses_no_literal_values():
    css = _read("css/embed.css")
    body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    selectors = [s.strip() for block in re.findall(r"([^{}]+)\{", body) for s in block.split(",")]
    assert selectors
    assert all(s.startswith(':root[data-embed="1"]') for s in selectors), selectors
    for chrome in ("#app-header", "#app-nav"):
        assert f':root[data-embed="1"] {chrome}' in body
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", body)


def test_the_chrome_the_stylesheet_hides_exists_in_the_page():
    html = _read("index.html")
    assert '<header id="app-header">' in html and '<nav id="app-nav">' in html


def test_the_update_panel_is_shown_only_on_the_settings_view_in_embed_mode():
    css = _read("css/embed.css")
    assert '[data-icd-view="settings"]' in css and "#app-update-panel" in css
    # it only ever HIDES (never sets display:block), so the panel's own `hidden` stays in charge
    assert "display: block" not in css


def test_app_installs_the_embed_api_with_a_music_stories_and_settings_view():
    app = _read("js/app.js")
    assert "installIcdEmbed({" in app
    marked = re.findall(r'(\w+): \{ label: "[^"]+", kind: "settings"', app)
    assert marked == ["settings"]
    for view in ("music", "stories", "settings"):
        assert re.search(rf"\b{view}: \{{ label:", app), view
    assert _read("index.html").index('src="js/icdEmbed.js"') < _read("index.html").index('src="js/app.js"')


def test_opening_settings_or_the_tuned_channel_never_touches_the_player():
    """Radio must keep playing while ICD flips between its views."""
    app = _read("js/app.js")
    for fn in ("openSettingsView", "openChannelView"):
        body = app[app.index(f"function {fn}("):]
        body = body[: body.index("\n  }\n")]
        assert "pause()" not in body and "player" not in body, fn


def test_icd_embed_exposes_exactly_the_contract_members():
    src = _read("js/icdEmbed.js")
    api = src[src.index("Object.freeze({"):]
    api = api[: api.index("});")]
    assert "version: EMBED_CONTRACT_VERSION" in api
    for member in ("getNav", "navigate", "getStatus", "applyTheme"):
        assert re.search(rf"\b{member}\b", api), member
    assert "EMBED_CONTRACT_VERSION = 1;" in src
    assert "if (!isEmbedded()) return null;" in src
    status = src[src.index("function statusSnapshot"):]
    status = status[: status.index("\n}\n")]
    for field in ("title", "connection", "updateAvailable", "restartPending", "detail"):
        assert re.search(rf"\b{field}\b", status), field
    # the nav entry shape: {id, label, route, kind}
    nav = src[src.index("function navFromViews"):]
    nav = nav[: nav.index("\n}\n")]
    for field in ("id", "label", "route", "kind"):
        assert re.search(rf"\b{field}\b", nav), field


def test_connection_and_update_state_that_getstatus_reports_exist():
    assert 'const ConnectionState = { status: "connecting" };' in _read("js/api.js")
    for status in ('"connected"', '"disconnected"'):
        assert status in _read("js/api.js")
    update = _read("js/appUpdate.js")
    assert "const UpdateState = { updateAvailable: false, restartPending: false" in update
    assert "UpdateState.restartPending = true" in update


def test_theme_tokens_are_restricted_to_the_shared_token_families():
    src = _read("js/icdEmbed.js")
    assert "(color|space|radius|font)" in src
    assert "url\\(" in src  # no url() in a token value


def test_main_container_is_the_page_panel():
    assert '<main id="app-main" data-icd-panel="page">' in _read("index.html")


def test_every_card_table_and_modal_carries_its_panel_sticker():
    sources = {"index.html": _read("index.html")}
    sources.update({p.name: p.read_text(encoding="utf-8") for p in (_STATIC / "js").rglob("*.js")})
    problems = [f"{name}: {p}" for name, src in sources.items() for p in _sticker_problems(src)]
    assert not problems, problems


def test_sticker_check_catches_missing_and_unknown_kinds():
    assert _sticker_problems('<table class="x">')
    assert _sticker_problems('<div class="modal big">')
    assert _sticker_problems('<section class="group-card">')
    assert _sticker_problems('<section data-icd-panel="card" class="a-card"><b data-icd-panel="frame">')
    assert _sticker_problems('<div class="card">')
    assert not _sticker_problems('<div class="character-card__name">')
    assert not _sticker_problems('<section data-icd-panel="card" class="group-card">')


def test_the_embed_assets_are_served(make_config):
    client = TestClient(create_app(make_config()))
    assert client.get("/css/embed.css").status_code == 200
    assert client.get("/js/icdEmbed.js").status_code == 200
    assert client.get("/js/embedButtons.js").status_code == 200
    html = client.get("/").text
    assert 'href="css/embed.css"' in html and 'src="js/icdEmbed.js"' in html and 'src="js/embedButtons.js"' in html


def test_buttons_are_stamped_only_in_embed_mode_and_never_by_hand():
    """Embed mode stamps `data-icd-panel="button"` on every button (embedButtons.js) so ICD can tighten the spacing
    (contract section 4). It must do nothing without the flag, so a normal visit is unchanged."""
    script = _read("js/embedButtons.js")
    assert 'if (document.documentElement.dataset.embed !== "1") return;' in script  # the single gate
    assert 'el.dataset.icdPanel = "button"' in script and "MutationObserver" in script
    assert "audio" not in script.lower().replace("never touches the audio element", "")  # Radio's player is left alone
    html = _read("index.html")
    assert html.index('src="js/embedButtons.js"') > html.index('src="js/icdEmbed.js"')
    for path in sorted((_STATIC / "js").glob("*.js")) + [_STATIC / "index.html"]:
        if path.name != "embedButtons.js":  # nothing else may write the sticker (it would then exist in a normal visit)
            text = path.read_text(encoding="utf-8")
            assert 'icdPanel = "button"' not in text and 'data-icd-panel="button"' not in text
