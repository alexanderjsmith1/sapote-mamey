"""v9.7.410 hostile audit — deliverable text embedded as JSON inside the widget's <script> block
must not be able to alter HTML tokenization. Only `</` was escaped before; `<!--<script` (the
"double-escaped script data" trick) survived and would swallow the rest of the page."""
from __future__ import annotations

import json

from mamey.widget_deliverable import _json_script


def test_every_angle_bracket_is_escaped_and_round_trips():
    payload = {
        "product": "</script><script>alert(1)</script>",
        "note": "<!--<script>",
        "plain": "a < b <= c",
        "unicode": "α-β ⟨x⟩",
    }
    s = _json_script(payload)
    assert "<" not in s, s
    assert json.loads(s) == payload  # < is a legal JSON escape; the value is unchanged
