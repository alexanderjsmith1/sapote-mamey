"""The print_calls ratchet counted only the bare-Name call, leaving a one-line bypass.

`tools/_console.py::emit` and `mamey/console.py::emit` are pass-through emitters: they forward
*args/**kwargs to `builtins.print` unchanged. `check_print_calls` counts them, which is right — a
centralised seam removes no emission site. But it counted them only where the call is a bare Name.
Written the other way round, the identical emission was invisible:

    from _console import emit
    emit("x")             # counted
    import _console
    _console.emit("x")    # NOT counted, same bytes on stdout

Measured on sealed v9.7.417: a probe adding three bare and three attribute-form calls — six
identical runtime emissions — moved the metric from 1323 to **1326**, not 1329. At a ceiling with
zero headroom and a waiver signed at the exact observed count, that is the difference between paying
a regression down and routing around the gate in one line, with the gate still reporting green.

Also measured at .417: **zero** shipped call sites use the attribute form, so closing the hole moves
the count by nothing. This is hardening an unexploited gap, not paying down a discovered one.

Claim-safety: code-hygiene metric only. No scan, scorer or emitted scientific value is read.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_HEALTH = ROOT / "tools" / "repo_health.py"


def _load():
    """repo_health defines dataclasses at module level, so it must be in sys.modules first."""
    spec = importlib.util.spec_from_file_location("_probe_repo_health", REPO_HEALTH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    return mod


def _count(tmp_path, source, name="probe.py"):
    mamey = tmp_path / "mamey"
    mamey.mkdir(exist_ok=True)
    p = mamey / name
    p.write_text(source, encoding="utf-8")
    return _load().check_print_calls([p], tmp_path)


def _total(result) -> int:
    return int(result.detail.split(None, 1)[0])


BARE = "from _console import emit\n\n\ndef f():\n    emit('a')\n    emit('b')\n    emit('c')\n"
ATTR = "import _console\nfrom _console import emit  # noqa: F401\n\n\ndef f():\n" \
       "    _console.emit('a')\n    _console.emit('b')\n    _console.emit('c')\n"


def test_the_bare_form_is_counted(tmp_path):
    assert _total(_count(tmp_path, BARE)) == 3


def test_the_attribute_form_is_counted_too(tmp_path):
    """Same three emissions, written through the module object."""
    assert _total(_count(tmp_path, ATTR)) == 3


BOTH = ("import _console\n"
        "from _console import emit\n"
        "\n\n"
        "def f():\n"
        "    emit('a')\n"
        "    emit('b')\n"
        "    emit('c')\n"
        "    _console.emit('d')\n"
        "    _console.emit('e')\n"
        "    _console.emit('f')\n")


def test_both_forms_together_count_every_emission(tmp_path):
    """Six emissions, identical on stdout; the metric must see six.

    Concatenating the two fixtures instead of writing one coherent module is how this test first
    failed on the PATCHED tree: the joined source never imported `_console`, so the attribute calls
    were correctly uncounted and the assertion measured a fixture defect, not the code.
    """
    assert _total(_count(tmp_path, BOTH)) == 6


@pytest.mark.parametrize("source,why", [
    ("import logging\nlog = logging.getLogger(__name__)\n\n\ndef f():\n    log.print('x')\n",
     "a logger's own print is a different function and never was library debt"),
    ("class C:\n    def emit(self, x):\n        pass\n\n    def f(self):\n        self.emit('x')\n",
     "a method named emit on an unrelated class is not the console seam"),
    ("import builtins\n\n\ndef emit(*a, **k):\n    builtins.print(*a, **k)\n",
     "the emitter definition itself — counting this would double-count every call site"),
    ("import _console\n\n\ndef f():\n    other.emit('x')\n",
     "an object the file never imported as the console module"),
])
def test_unrelated_attribute_calls_stay_uncounted(tmp_path, source, why):
    assert _total(_count(tmp_path, source)) == 0, why


def test_an_aliased_import_is_followed(tmp_path):
    src = "import _console as c\nfrom _console import emit  # noqa: F401\n\n\ndef f():\n    c.emit('x')\n"
    assert _total(_count(tmp_path, src)) == 1


def test_the_alias_helper_only_trusts_real_imports(tmp_path):
    mod = _load()
    aliases = mod._console_aliases(ast.parse("import _console as c\n"))
    assert aliases == frozenset({"c"})
    assert mod._console_aliases(ast.parse("console = object()\n")) == frozenset()
