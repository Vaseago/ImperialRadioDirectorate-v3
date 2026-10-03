"""CCP's Developer License Agreement (section 7.1,
https://developers.eveonline.com/license-agreement) requires the CCP notice to
be retained wherever the app ships. These guards fail if a README, notices
file or the in-app footer loses it - the most likely way it would vanish is a
well-meaning "tidy up the footer" edit, which nothing else would catch.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_LICENSE_NOTICE = (
    "© 2014 CCP hf. All rights reserved. 'EVE', 'EVE Online', 'CCP', and all related "
    "logos and images are trademarks or registered trademarks of CCP hf."
)
_GENERAL_STATEMENT = (
    "EVE Online and the EVE logo are the registered trademarks of CCP hf."
)
_UNOFFICIAL = "unofficial fan-made tool"


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_readme_and_third_party_notices_carry_both_ccp_statements():
    for rel in ("README.md", "THIRD_PARTY_NOTICES.md"):
        text = _read(rel)
        assert _LICENSE_NOTICE in text, rel
        assert _GENERAL_STATEMENT in text, rel
        assert _UNOFFICIAL in text, rel


def test_third_party_notices_flag_the_gpl_dependency():
    text = _read("THIRD_PARTY_NOTICES.md")
    assert "mutagen" in text
    assert "GPL-2.0-or-later" in text
