"""v9.7.268 — the CLI parser must build when biopython is absent.

Regression guard for the class that shipped since v9.7.233: `build_parser()` eagerly imported
`raw_antismash_triage`, which hard-imports `from Bio import SeqIO`. That made biopython a hard
requirement for EVERY command — `mamey doctor`, `mamey --help`, `mamey list-bgcs`, all of it —
even though biopython is documented optional (docs/PREREQUISITES.md §0) and the extraction path shims
it via `_gbk_shim`. No test exercised the parser build with biopython absent, so it went unnoticed
in every container that happened to have biopython installed.

These tests simulate biopython being absent by blocking `Bio` at import time, then assert:
  1. build_parser() still succeeds and registers `triage-raw`;
  2. invoking the triage-raw handler without biopython raises a clear SystemExit, not a raw
     ModuleNotFoundError traceback.
"""
import builtins
import importlib
import sys

import pytest


class _BlockBio:
    """Context manager: make `import Bio[...]` raise ModuleNotFoundError."""

    def __enter__(self):
        # drop any already-imported Bio + the triage module that caches the import
        self._saved = {k: v for k, v in sys.modules.items()
                       if k == "Bio" or k.startswith("Bio.")
                       or k.endswith("raw_antismash_triage")}
        for k in list(self._saved):
            del sys.modules[k]
        self._real_import = builtins.__import__

        def _guarded(name, *a, **k):
            if name == "Bio" or name.startswith("Bio."):
                raise ModuleNotFoundError(f"No module named 'Bio'", name="Bio")
            return self._real_import(name, *a, **k)

        builtins.__import__ = _guarded
        return self

    def __exit__(self, *exc):
        builtins.__import__ = self._real_import
        sys.modules.update(self._saved)


def test_build_parser_succeeds_without_biopython():
    from mamey import cli
    with _BlockBio():
        parser = cli.build_parser()  # must NOT raise ModuleNotFoundError: No module named 'Bio'
    # triage-raw must still be a registered subcommand
    args = parser.parse_args(["triage-raw", "--input-zip", "x.zip"])
    assert getattr(args, "func", None) is not None


def test_triage_raw_handler_reports_clear_message_without_biopython():
    from mamey import cli
    with _BlockBio():
        parser = cli.build_parser()
        args = parser.parse_args(["triage-raw", "--input-zip", "x.zip"])
        with pytest.raises(SystemExit) as ei:
            args.func(args)
    msg = str(ei.value)
    assert "biopython" in msg.lower()
    assert "triage-raw" in msg
