"""Regression guard for the sapote_judgment_receipt.py Py3.12 regex crash.

Bug: count_modeb_cards() used an inline `(?m)` global flag mid-pattern (after the `|`), which raises
`re.error: global flags not at the start of the expression` on Python 3.11+. Unfixed across v9.7.6/7/8.

Standalone: python3 tests/test_judgment_receipt_regex.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import importlib.util

_TOOL = Path(__file__).resolve().parent.parent / "tools" / "sapote_judgment_receipt.py"
_spec = importlib.util.spec_from_file_location("sapote_judgment_receipt", _TOOL)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def test_count_modeb_cards_does_not_crash(tmp_path=None):
    """The core regression: the function must run without re.error on Python 3.11+."""
    import tempfile, os
    d = tempfile.mkdtemp()
    p = os.path.join(d, "compilation.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("# BGC 1 — first card\nbody text\n## BGC 2 — second\n### BGC[3 truncated\nnot a card\n")
    n = _mod.count_modeb_cards([p])   # must not raise re.error
    assert n == 3, f"expected 3 BGC card headers, got {n}"


def test_regex_has_no_midpattern_global_flag():
    """Source-level guard: no `(?m)` may appear after the start of the pattern in the tool."""
    src = _TOOL.read_text(encoding="utf-8")
    # the fixed form uses flags=re.M; there must be no second inline (?m) (i.e. one after a `|`)
    assert "|(?m)" not in src, "illegal mid-pattern (?m) global flag still present"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")
