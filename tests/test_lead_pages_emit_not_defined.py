"""mamey/lead_pages.py: `mamey lead-pages <package>` crashed on EVERY invocation with
`NameError: name 'emit' is not defined`.

Found by running the real pipeline (BC2-408): `mamey lead-pages` against this cycle's own real
AS-705 sealed package. The per-BGC dossier pages were written correctly (`build()` never touches
`emit`), but the command's own unconditional wrap-up summary line
(`emit(f"lead-pages: {len(emitted)} page(s) -> {outdir}" ...)`) always raised, so the command never
returned cleanly even once real deliverable content had been produced.

Root cause: the `try: from .console import emit / except ImportError: from mamey.console import
emit` block (added, per its own v9.7.407 comment, to fix exactly this class of import gap) was
pasted INSIDE `_load_lit()`'s docstring as inert prose, not as real executing module-level code --
so `emit` was never actually imported anywhere in this module, despite the fix-shaped text visibly
sitting in the file.

This crash is NOT caught by this module's own existing test suite
(tests/test_lead_pages_wave_b.py's `test_default_scope_emits_only_lead_pages` and
`test_lead_page_carries_enrichment_and_reference_context`, the two tests that actually call
`lead_pages_command()`) because both are gated `@needs_pkg` behind `_find_sealed_package()`, which
only looks at hardcoded paths (`/tmp/sealship`, `./seal338c`, `./seal338b`) -- absent in this
environment (and most others), so both tests silently skip rather than fail. A real regression guard
existed on paper and provided zero protection in practice -- "a test can stop testing" (this
project's own house term for a vanished injection seam reading as green but vacuous). This new test
deliberately avoids any hardcoded/environment-dependent package path.
"""
from __future__ import annotations

import csv
import tempfile
from pathlib import Path
from types import SimpleNamespace

from mamey import lead_pages


def _minimal_package(tmp_path):
    """The crash is unconditional -- it fires even with ZERO BGCs, so no real triage/lead data is
    needed at all: just a *_2_inventory.csv for find_pkg_dir()/strain_of() to locate the package
    root. rows() already degrades gracefully to [] for any other CSV that's absent."""
    pkg = tmp_path / "package"
    pkg.mkdir()
    with open(pkg / "SID100_2_inventory.csv", "w", newline="") as f:
        csv.writer(f).writerow(["BGC_ID"])
    return str(pkg)


def test_lead_pages_command_does_not_raise_nameerror_on_emit(tmp_path):
    pkg = _minimal_package(tmp_path)
    out = tempfile.mkdtemp(prefix="lead_pages_test_")
    rc = lead_pages.lead_pages_command(
        SimpleNamespace(package=pkg, out=out, bgc="ALL", all_tiers=False)
    )
    assert rc == 0


def test_emit_is_a_real_module_level_name_not_docstring_text():
    """Direct assertion on the root cause: `emit` must be an actual attribute of the module, not
    text sitting inside another function's docstring."""
    assert hasattr(lead_pages, "emit"), (
        "lead_pages.emit is not defined at module scope -- the emit import is dead (embedded in a "
        "docstring), not executing code"
    )
    assert callable(lead_pages.emit)
