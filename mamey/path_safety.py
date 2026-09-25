"""Shared output-containment guard for tools that name a file from a caller-supplied label.

v9.7.438. Several post-seal tools build an output path as ``Path(outdir) / f"{label}.gbk"`` with
no validation of ``label``. A label carrying ``..`` or a separator resolves outside ``outdir`` and
silently overwrites whatever is there -- reproduced on v9.7.437 against
``tools/fetch_mibig_reference.py``, where ``--acc BGC0000001:../project_data/precious`` replaced an
existing reference GBK and still reported a normal write. ``--outdir`` is the whole safety contract
of these tools, so a path that leaves it must fail closed rather than succeed quietly.

The bundle already contains several ad-hoc containment checks (``mamey/document_factory._contained``,
``mamey/lab_quest.contained_path``, and inline ``is_relative_to`` guards in
``cohort_enzyme_neighborhoods.py``, ``scan_channel_alias.py``, ``tool_database_reader.py``). Each is
bound to its own module's error type or project-root semantics. This module is the general form for
tools that have none, following the same shape as ``mamey.csv_safety``: importable from ``tools/``,
no dependencies beyond the standard library.

Scope: this validates a NAME. It is not an archive-extraction guard (see ``mamey.ziputil``) and it
makes no claim about the file's contents.
"""
from __future__ import annotations

import re
from pathlib import Path

__all__ = ["UnsafeOutputLabel", "OutputInsideBundle", "safe_label", "contained_output_path",
           "running_bundle_root", "assert_output_outside_bundle"]

# Conservative on purpose: MIBiG accessions, compound names and operator labels all fit.
# Anything outside it is far more likely to be a typo or a traversal than an intended filename.
_LABEL_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._+-]*\Z")
_MAX_LABEL = 100


class UnsafeOutputLabel(ValueError):
    """Raised when a caller-supplied label cannot be used as a filename inside an output root."""


def safe_label(label: str, *, field: str = "label") -> str:
    """Return ``label`` unchanged, or raise ``UnsafeOutputLabel`` with a typed reason.

    Rejects: empty/blank, separators (``/`` and ``\\`` on every platform, not just this one),
    NUL and other control characters, leading dots (``.``, ``..``, and dotfiles), anything outside
    the grammar, and anything over 100 characters.
    """
    text = "" if label is None else str(label)
    if not text.strip():
        raise UnsafeOutputLabel(f"OUTPUT_LABEL_EMPTY: {field}")
    if len(text) > _MAX_LABEL:
        raise UnsafeOutputLabel(f"OUTPUT_LABEL_TOO_LONG: {field}={len(text)} chars (max {_MAX_LABEL})")
    if "/" in text or "\\" in text:
        raise UnsafeOutputLabel(f"OUTPUT_LABEL_HAS_SEPARATOR: {field}={text!r}")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in text):
        raise UnsafeOutputLabel(f"OUTPUT_LABEL_HAS_CONTROL_CHAR: {field}={text!r}")
    if text.startswith("."):
        raise UnsafeOutputLabel(f"OUTPUT_LABEL_LEADING_DOT: {field}={text!r}")
    if not _LABEL_RE.match(text):
        raise UnsafeOutputLabel(
            f"OUTPUT_LABEL_GRAMMAR: {field}={text!r} (allowed: letters, digits, . _ + -)")
    return text


def contained_output_path(outdir: str | Path, label: str, suffix: str = "",
                          *, field: str = "label") -> Path:
    """Resolve ``outdir/<label><suffix>`` and prove it is a direct child of ``outdir``.

    The grammar check above already blocks every traversal this project has seen; the resolved
    comparison is the belt-and-braces half, and it also catches an ``outdir`` whose own components
    are symlinked somewhere unexpected relative to the name we hand back.
    """
    name = safe_label(label, field=field) + suffix
    root = Path(outdir).resolve()
    target = (root / name).resolve()
    if target.parent != root:
        raise UnsafeOutputLabel(f"OUTPUT_PATH_ESCAPES_OUTDIR: {field}={label!r} -> {target}")
    return target


class OutputInsideBundle(ValueError):
    """Raised when an output ROOT resolves inside the sealed code bundle the tool runs from."""


def running_bundle_root(module_file: str | Path) -> Path | None:
    """Return the code bundle a tool FILE lives in (its ancestor carrying ``BUILD_STAMP.txt``), or None.

    Anchored to the file, never to the current directory, so a stray bundle-shaped copy elsewhere --
    e.g. a polluted workspace root that also carries a ``BUILD_STAMP.txt`` -- does not cause false
    positives. Pass ``__file__`` from the calling tool.
    """
    p = Path(module_file).resolve()
    for anc in p.parents:
        if (anc / "BUILD_STAMP.txt").is_file():
            return anc
    return None


def assert_output_outside_bundle(path: str | Path, module_file: str | Path,
                                 *, kind: str = "output") -> Path:
    """Return ``path``, or raise ``OutputInsideBundle`` if it resolves inside the tool's own bundle.

    Write-side complement of ``contained_output_path``: that stops a label escaping an outdir; this
    stops the outdir ITSELF landing inside the sealed code tree. ``workspace_root()`` falls back to
    the current directory and the standing rule is to run tools FROM the bundle root, so a
    ROOT-relative default (``f"{ROOT}/strain_data/..."``) resolves into the bundle and litters it
    (observed: a 12.7 MB placement refpkg, and MIBiG neighbourhood trees, written into the sealed
    directory). If the tool is not running from a recognizable bundle, nothing is protected and
    ``path`` is returned unchanged.
    """
    bundle = running_bundle_root(module_file)
    if bundle is None:
        return Path(path)
    out = Path(path).resolve()
    if out == bundle or bundle in out.parents:
        raise OutputInsideBundle(
            f"OUTPUT_INSIDE_BUNDLE: refusing to write {kind} inside the code bundle ({bundle}). "
            f"Set SAPOTE_WORKSPACE_ROOT to your workspace root, or pass an explicit path outside the "
            f"bundle. Resolved: {out}")
    return Path(path)
