from __future__ import annotations
import warnings as _warnings
from contextlib import suppress as _suppress

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit
import hashlib, json, os, tempfile, zipfile
from pathlib import Path
from .recovery_status import infer_package_status, write_package_status_receipt
from .claim_safety_gate import run_claim_safety_gate, write_claim_safety_receipt

# v9.7.160: post-seal figure directories are rendered AFTER the checksum seal (the seal-first
# design, cli.py header note): smoke_figures/, gold_figures/, and locus_maps/ are re-emitted
# by the figure phase and by `render-figures`, and matplotlib produces byte-different PNGs on
# every render even for identical plots. Including them in checksums_sha256.txt caused a
# deterministic checksum FAIL on any re-run into an existing package dir (the seal captured
# pre-render hashes invalidated 0.5s later). Their analytical content lives in the companion
# fig_*_data.csv / *_locus_map_data.csv files, which are NOT excluded and stay integrity-checked.
# packaging.py (both writers) and validate.py.verify_checksums share this exclusion.
_POST_SEAL_FIGURE_DIRS = ("smoke_figures/", "gold_figures/", "locus_maps/")


class PackageContainmentError(RuntimeError):
    """The package tree contains an entry that cannot be sealed safely."""


class ManifestRecoveryRequired(RuntimeError):
    """An existing manifest cannot be safely read and must not be replaced."""


def _load_existing_manifest(manifest_path: Path) -> dict:
    """Load an existing manifest only when it is a readable JSON object.

    Resealing must preserve the run snapshot that owns the package's scientific
    metadata.  A malformed, unreadable, or schema-incompatible root value is a
    recovery condition, not an empty base manifest.
    """
    try:
        base = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestRecoveryRequired(
            "existing manifest is unreadable; refusing to replace it during reseal"
        ) from exc
    if not isinstance(base, dict):
        raise ManifestRecoveryRequired(
            "existing manifest must be a JSON object; refusing to replace it during reseal"
        )
    return base


def _package_files_fail_closed(root: str | Path) -> list[Path]:
    """Return regular package files, refusing symlinks before any content is read.

    ``Path.is_file()`` follows symlinks.  Using it as the only admission check lets a
    package-local link hash and archive bytes from anywhere on the host filesystem.
    Sealed packages are standalone artifacts, so every entry must be a physical file
    beneath the package tree; links are never a portable package member.
    """
    import os  # local: module-level `os` is only imported on the direct-script fallback path.

    root = Path(root)
    # The supplied root is part of the trust boundary too.  ``os.walk`` follows
    # a symlink passed as its top argument even when followlinks=False, so a
    # symlinked package root would otherwise admit and hash its external target.
    if root.is_symlink():
        raise PackageContainmentError("package root symlink is prohibited")

    # RGLOB-SEAL-COVERAGE (v9.7.409): this is the seal's single enumeration chokepoint --
    # its output feeds both the checksum writer and validate.py's SEAL-03 untracked scan.
    # ``Path.rglob`` swallows a per-directory OSError, so an unreadable/unlistable subtree
    # would silently vanish: its files would be neither hash-pinned nor flagged as untracked.
    # Walk with an ``onerror`` that re-raises so an unreadable subtree fails the seal closed
    # instead of under-returning. ``followlinks=False`` matches the prior no-descend behavior;
    # the symlink check below still rejects the link entry itself.
    def _onerror(exc: OSError) -> None:
        raise exc

    entries: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, onerror=_onerror, followlinks=False):
        base = Path(dirpath)
        entries.extend(base / name for name in dirnames)
        entries.extend(base / name for name in filenames)

    files: list[Path] = []
    for path in sorted(entries):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise PackageContainmentError(
                f"package symlink is prohibited: {rel}"
            )
        if path.is_file():
            files.append(path)
        elif not path.is_dir():
            # FIFOs, sockets and device nodes are neither portable package
            # members nor safe objects for later readers.  Silently omitting
            # them would let the seal report complete coverage of an
            # incompletely enumerated package tree.
            raise PackageContainmentError(
                f"non-regular package entry: {rel}"
            )
    return files


# SEAL-02b (v9.7.338 follow-up): the single source of truth for files that are REWRITTEN or
# APPENDED after write_manifest() computes checksums, so they cannot be hash-pinned. The manifest
# writer excludes them from checksums_sha256.txt and the validator must exempt the identical set,
# or the two disagree (a file is either an untracked-present error or a stale-hash mismatch
# depending on which side is stricter). Historically this set was copy-pasted into five places
# across packaging.py + validate.py and had already drifted (two copies lacked repro_fingerprint).
MUTABLE_RECEIPT_NAMES = frozenset({
    "run_phase_receipts.jsonl",
    "package_status.json",
    "claim_safety_status.json",
    "repro_fingerprint.json",
    "gate_validation.json",  # rewritten by _phase_package_seal's SEAL-02 post-seal re-validation
    # v9.7.371 fix: seal_package.py::write_receipts()'s five output files were never added here.
    # cli.py's seal_package_command defaults `out_dir = args.out or args.package_dir` -- so the
    # documented default invocation (`mamey seal-package <package_dir>`, no --out) writes these
    # straight into the already-sealed package_dir, and validate.py's SEAL-03 reciprocal scan
    # then reports every one of them as "untracked file present but absent from
    # checksums_sha256.txt" -- the seal_package QC layer breaks the very seal it exists to
    # validate, on its own default invocation path.
    # v9.7.412 (hostile audit of .411, round 5, R1): mamey/figure_save.py:19 APPENDS
    # figure_receipts.jsonl into the package on every governed figure write — after the seal, by
    # design — but it was never registered here, so validate's SEAL-03 reciprocal scan reported it
    # as "untracked file present but absent from checksums_sha256.txt". Reproduced end-to-end on a
    # fresh gold run of the shipped smoke fixture: `mamey validate <package>` returned status=FAIL
    # (rc 1) on a package the engine had just sealed MAMEY_COMPLETE, and the file ships inside the
    # Complete_Package zip. Same class as the seal_package receipts registered just below.
    "figure_receipts.jsonl",
    "seal_status.json",
    "seal_findings.csv",
    "DEBUG_RECEIPT.md",
    "figure_reference_validation.csv",
    "deliverable_status_table.csv",
    # v9.7.374 fix (AUDIT): cli.py::_render_brief_nonblocking()'s failure/timeout path
    # (called post-seal at cli.py:2196, "rendering strain brief (post-seal; supplementary)",
    # AFTER _phase_package_seal() has already written checksums_sha256.txt at cli.py:2187) does
    # two things on a subprocess timeout/error: (1) directly appends a "[WARN] strain brief
    # skipped" line to issue_log.md on disk (cli.py ~412-414) -- an EXISTING core file already
    # hash-pinned in checksums_sha256.txt, so the append breaks its checksum line -- and (2)
    # writes a brand-new BRIEF_SKIPPED_TIMEOUT.md or BRIEF_SKIPPED_ERROR.md marker file
    # (cli.py ~401-409) that was never part of the checksum set. Both are exactly the
    # "REWRITTEN or APPENDED after write_manifest() computes checksums" class this set exists
    # for (same class as run_phase_receipts.jsonl above) -- live-reproduced on a real, single,
    # non-concurrent `run --mode gold` (AS-XXX): a brief-render subprocess timeout left
    # `mamey_run.py validate` reporting checksum_integrity FAIL ("line N: checksum mismatch for
    # issue_log.md" + "untracked file present ... BRIEF_SKIPPED_TIMEOUT.md") on an otherwise
    # cleanly-sealed MAMEY_COMPLETE package, immediately after the run finished.
    "issue_log.md",
    "issue_log.tsv",
    "issue_log.jsonl",
    "BRIEF_SKIPPED_TIMEOUT.md",
    "BRIEF_SKIPPED_ERROR.md",
    # v9.7.409 (CLAUDE post_seal_checksums lane): written at the END of the run and regenerated on every
    # reseal -> must not enter checksums_sha256.txt and is exempt from the SEAL-03 reciprocal scan.
    "post_seal_checksums.txt",
})
# v9.7.409 A10: `<strain>_timing_breakdown.{json,csv}` embed wall-clock/RSS (timing.py) and are
# written BEFORE the seal, so they entered checksums_sha256.txt and made it differ run-to-run with
# no science inside. Strain-prefixed -> matched by suffix like the judgment register. This tuple
# was defined but never consumed; the writer loop and validate.py now both route through it.
MUTABLE_RECEIPT_SUFFIXES = ("_judgment_register.json", "_timing_breakdown.json", "_timing_breakdown.csv")


def is_checksum_excluded(rel_path: str) -> bool:
    """True if a package-relative path is a post-seal figure artifact excluded from checksums.
    Excludes the rendered image files (.png/.svg) under the figure dirs; the fig_*_data.csv
    companions stay IN the checksum set (they carry the numbers, and don't get re-rendered)."""
    rel = rel_path.replace("\\", "/")
    if rel.startswith(_POST_SEAL_FIGURE_DIRS):
        return rel.endswith((".png", ".svg"))
    # Post-seal supplementary presentation PDFs: the matplotlib pdf backend embeds a build
    # timestamp -> nondeterministic bytes, and these are rendered AFTER checksums_sha256.txt is
    # written (same seal-first race documented above for figures). They live at the package
    # ROOT, not under a _POST_SEAL_FIGURE_DIRS prefix, so the branch above misses them and they
    # cause a spurious checksum_integrity FAIL. Their content is supplementary — "the
    # reproducible scientific artifact does not depend on them" (cli.py / FIGURES_SUPPLEMENTARY.md).
    name = rel.rsplit("/", 1)[-1]
    if name.endswith("_strain_brief.pdf") or name == "package_PRINT_FIGURE_PACK.pdf":
        return True
    return False


# v9.7.409 (CLAUDE post_seal_checksums lane) — post-seal integrity coverage.
#
# The seal is a point-in-time snapshot: _phase_package_seal writes checksums_sha256.txt FIRST,
# then ~160 files are written by post-seal phases (mode_b, blastp_online, domain_level, guide,
# figures/figures_rendered/smoke_figures, locus_maps + the root figure-data companions) into
# subtrees that verify_checksums treats as reciprocal-EXEMPT — so their content is never
# hash-pinned. The DEEP_AUDIT found this leaves injection (N1), swap and delete (N2) of fabricated
# scientific data/deliverables invisible to `validate` (checksum_integrity stays PASS).
#
# write_post_seal_checksums() (below, called at the very END of a run) folds exactly those
# currently-exempt DATA/deliverable files into a tracked post_seal_checksums.txt; verify_checksums
# ENFORCES it when present (a missing manifest = the old, backward-compatible behaviour).
#
# The coverage set is deliberately CONSERVATIVE: it must not pin files that are legitimately
# rewritten/regenerated after the run, or the integrity check would fire on a normal reseal.
# Excluded from coverage (kept exempt by design, so they can still change):
#   * every MUTABLE_RECEIPT_NAMES entry (manifest/package_status/gate_validation/claim_safety_status/
#     repro_fingerprint/issue_log/run_phase_receipts/... and post_seal_checksums.txt itself);
#   * the per-strain *_judgment_register.json (rewritten by `ingest-receipts`);
#   * the regenerated report suffixes *_compiled_report.md / *_SAPOTE_WORKFLOW_LEDGER.md and the
#     *_cnbu.json narrative-buffer files;
#   * locus_maps/, figures/, figures_rendered/, smoke_figures/ image re-renders under locus_maps/
#     (only the *_data.csv numbers + *.json receipts under locus_maps/ are covered — matplotlib
#     re-renders PNGs/SVGs non-deterministically; the plotted NUMBERS are what carry the claim).
# Everything else under the covered subtrees, plus root figure images and root *_fig_*_data.csv,
# IS covered.
_POST_SEAL_COVERED_SUBTREES = (
    "mode_b/",
    "blastp_online/",
    "domain_level/",
    "guide/",
    "figures/",
    "figures_rendered/",
    "smoke_figures/",
    # v9.7.409 r2 (CLAUDE_409_seal_integrity_r2; DEEP_AUDIT2 R2-3/R2-4): the round-1 covered
    # allowlist was a hand-maintained SUBSET of the core reciprocal-exempt subtree list and had
    # drifted out of sync with it, so the REAL Mode B judgment-card home (judgment/) and ~9 other
    # core-exempt subtrees accepted arbitrary INJECTED files with checksum_integrity=PASS (A3, C1-C4).
    # Bring every exempt subtree that accepts governed post-seal deliverables under coverage. The
    # non-deterministic re-renders inside them (.png/.svg/.pdf) are still left uncovered by
    # is_post_seal_covered() below — only the claim-bearing text/data (.md/.csv/.json) is pinned.
    "judgment/",            # R2-3: the §1-§30 Mode B judgment cards — highest scientific impact.
    "gold_figures/",
    "cohort_figures/",
    "mamey_native_figures/",
    "ASSEMBLY_LINES/",
    "P450_TAILORING/",
    "COMPOUND_FAMILIES/",
    "mode_b_templates/",
    "blastp_quarantine/",
    "blastp_ingest_receipts/",
)

# v9.7.409 r2 (CLAUDE_409_seal_integrity_r2; DEEP_AUDIT2 R2-5): the ONLY files that legitimately
# live INSIDE a covered subtree and are still rewritten post-seal. The report/buffer suffixes
# (_compiled_report.md, _SAPOTE_WORKFLOW_LEDGER.md, _cnbu.json) and the mutable-receipt NAMES
# (package_status.json, …) are all written at the package ROOT (verified: cli.py:2481, compile_
# report.py:1108 write _compiled_report.md to package_dir; render_brief.py:581 writes _cnbu.json at
# the stem root; judgment_store.py:72 writes _judgment_register.json at pkg root) — NONE of them
# is ever authored inside a covered data subtree. So inside a covered subtree the basename-based
# regenerated/mutable exemptions must NOT apply (that is exactly the R2-5 trick: naming an injected
# file EVIL_cnbu.json / EVIL_compiled_report.md / package_status.json to dodge coverage). This set
# is empty by design — there is no legitimately-mutable file inside the covered subtrees today.
_POST_SEAL_SUBTREE_MUTABLE_EXEMPT_SUFFIXES: tuple[str, ...] = ()


def _is_post_seal_regenerated(name: str) -> bool:
    """True for a basename that is legitimately rewritten/regenerated post-run, so it must stay
    OUT of post_seal_checksums.txt (mirrors the report-suffix / mutable-receipt exemptions that
    _checksum_reciprocal_exempt already honours for the core seal)."""
    if name in MUTABLE_RECEIPT_NAMES:
        return True
    if name in {"manifest.json", "checksums_sha256.txt", "post_seal_checksums.txt"}:
        return True
    if name.endswith(MUTABLE_RECEIPT_SUFFIXES):  # *_judgment_register.json
        return True
    if name.endswith(("_compiled_report.md", "_SAPOTE_WORKFLOW_LEDGER.md")):
        return True
    if name.endswith("_cnbu.json"):
        return True
    return False


def is_post_seal_covered(rel_path: str) -> bool:
    """True if a package-relative path is a post-seal DATA/deliverable file that
    write_post_seal_checksums() should hash-pin (and verify_checksums should enforce).

    Conservative by construction: only currently-exempt post-seal data is covered, and the
    genuinely-mutable receipts / regenerated reports (see _is_post_seal_regenerated) are never
    covered, so a legitimate reseal never trips the enforcement.

    v9.7.409 r2 (CLAUDE_409_seal_integrity_r2; DEEP_AUDIT2 R2-5): the round-1 version evaluated the
    regenerated/mutable exemption on the RAW disk basename BEFORE deciding coverage, so an attacker
    named an injected file EVIL_cnbu.json / EVIL_compiled_report.md / package_status.json inside a
    covered subtree and is_post_seal_covered() returned False — the reciprocal injection scan then
    skipped it (D1/D2/D3 all leaked). The fix pins the exemption to a TRUSTED structure (WHERE a
    file sits), not the untrusted name: the regenerated/mutable basename exemptions apply ONLY at the
    package ROOT, where those files are actually authored. Inside a covered subtree a file is covered
    on its location alone, so a basename trick can no longer dodge coverage. Image coverage is
    unchanged from round-1 (the post-seal manifest snapshots the FINAL rendered images; a later
    render-figures re-render calls refresh_post_seal_checksums to re-bless them)."""
    rel = rel_path.replace("\\", "/")
    name = rel.rsplit("/", 1)[-1]
    if rel.startswith(_POST_SEAL_COVERED_SUBTREES):
        # R2-5 fix: inside a covered subtree, coverage is by LOCATION, not basename. The only
        # things left out are a fixed, path-anchored set of genuinely-mutable in-subtree files
        # (currently none — every regenerated/mutable file lives at the root; see the suffix tuple
        # above). A file whose name merely *looks* regenerated (…_cnbu.json, …_compiled_report.md)
        # is still covered here, because no such file is ever legitimately written into a subtree.
        if name.endswith(_POST_SEAL_SUBTREE_MUTABLE_EXEMPT_SUFFIXES):
            return False
        return True
    # locus_maps/: the *_data.csv numbers and *.json receipts carry the claim; the png/svg are
    # non-deterministic re-renders (see the seal-first note atop this module).
    # v9.7.410 (CLAUDE_410_seal_locus_maps_coverage; SEAL_INTEGRITY_REATTACK A9): round-1 covered
    # ONLY *_data.csv + *.json here, while validate._checksum_reciprocal_exempt exempted the whole
    # locus_maps/ prefix from the SEAL-03 untracked scan. A fabricated locus_maps/*.md, *.txt or
    # *.pdf therefore sat in the gap between the two predicates — neither hash-pinned (SEAL-05) nor
    # flagged as untracked (SEAL-03) — and validated MAMEY_COMPLETE by execution. Cover by LOCATION
    # like every other subtree: everything under locus_maps/ is covered EXCEPT the image re-renders
    # (.png/.svg), which stay the single documented non-deterministic exception (is_checksum_excluded).
    # The reciprocal exemption in validate.py is narrowed to exactly (covered OR image) in lockstep.
    if rel.startswith("locus_maps/"):
        return not name.endswith((".png", ".svg"))
    # Package-ROOT files: the regenerated/mutable basename exemptions apply HERE (this is where
    # those files are authored). Cover root figure images + their *_fig_*_data.csv companions.
    if "/" not in rel:
        if _is_post_seal_regenerated(name):
            return False
        if name.endswith((".png", ".svg")):
            return True
        if "_fig_" in name and name.endswith("_data.csv"):
            return True
    return False


def write_post_seal_checksums(package_dir: str | Path) -> dict:
    """Fold every currently-exempt post-seal DATA/deliverable file into a tracked
    post_seal_checksums.txt (sha256 per file, sorted, `<hex>  <rel>` lines — same shape as
    checksums_sha256.txt). Call this ONCE at the very end of a run, after every post-seal phase
    has written its files. Returns {"path", "n_files", "files": {rel: sha256}}.

    verify_checksums() enforces this manifest when present, so injection into / swap within /
    deletion from a covered subtree flips checksum_integrity to FAIL. Absence of the file =
    the pre-patch behaviour (backward-compatible)."""
    root = Path(package_dir)
    covered: dict[str, str] = {}
    for p in _package_files_fail_closed(root):
        rel = p.relative_to(root).as_posix()
        if is_post_seal_covered(rel):
            covered[rel] = sha256(p)
    lines = [f"{covered[rel]}  {rel}" for rel in sorted(covered)]
    _atomic_write_text(root / "post_seal_checksums.txt", "\n".join(lines) + "\n")  # CORE-P04
    # v9.7.409 r2 (CLAUDE_409_seal_integrity_r2; DEEP_AUDIT2 R2-1/B1/D4): anchor the just-written
    # manifest's OWN sha256 into the core checksums_sha256.txt so a one-line edit to
    # post_seal_checksums.txt (rewriting a covered file's hash to match a swap, or deleting a line
    # to hide a removal) changes its digest and no longer matches the anchor -> verify_post_seal_
    # anchor() FAILs. This raises the bar (a naive one-file edit is now caught); it is NOT
    # cryptographic authenticity — an insider who also rewrites the anchor line in the unsigned,
    # in-package checksums_sha256.txt still defeats it. External signing is required for authenticity.
    anchor_post_seal_checksums(root)
    return {"path": str(root / "post_seal_checksums.txt"), "n_files": len(covered), "files": covered}


def refresh_post_seal_checksums(package_dir: str | Path) -> dict | None:
    """Re-emit post_seal_checksums.txt IFF the package CORE is already sealed
    (checksums_sha256.txt present). Sanctioned post-seal AUTHORING commands (mode-b, guide,
    render-figures, domain-level, blastp ingest, …) call this after writing their covered
    deliverables, so their LEGITIMATE output is folded into the integrity manifest rather than
    being flagged as an injection. An un-sanctioned raw drop into a delivered package (the N1/N2
    threat) never runs this refresh and is caught by verify_checksums.

    Guarded on the core seal so an in-run/pre-seal invocation is a no-op — the authoritative
    manifest is written by the end-of-run seal (cli.run) after the core is sealed. Returns the
    write_post_seal_checksums() dict, or None when the core is not yet sealed."""
    root = Path(package_dir)
    if not (root / "checksums_sha256.txt").exists():
        return None
    return write_post_seal_checksums(root)


# v9.7.409 r2 (CLAUDE_409_seal_integrity_r2; DEEP_AUDIT2 R2-1) — anchor the post-seal integrity
# manifest into the core seal. The core forward pass already SKIPS post_seal_checksums.txt (it is a
# MUTABLE_RECEIPT_NAME), so we do not rely on it; the anchor is a dedicated tagged line that
# verify_post_seal_anchor() re-checks explicitly against the manifest's live bytes.
_POST_SEAL_ANCHOR_TAG = "# post_seal_checksums.txt.sha256"


def anchor_post_seal_checksums(package_dir: str | Path) -> str | None:
    """Fold sha256(post_seal_checksums.txt) into the core checksums_sha256.txt as a tagged anchor
    comment line, replacing any prior anchor. Returns the anchored hex, or None when either the core
    seal or the post-seal manifest is absent (nothing to anchor — backward-compatible no-op).

    The anchor is a COMMENT line (`# post_seal_checksums.txt.sha256 <hex>`): the core forward pass
    (verify_checksums) ignores '#'-prefixed lines, so this never becomes a spurious tracked entry,
    and older validators simply skip it. verify_post_seal_anchor() below reads it back and FAILs on
    a mismatch, so editing post_seal_checksums.txt without ALSO rewriting this line is detected."""
    root = Path(package_dir)
    core = root / "checksums_sha256.txt"
    psc = root / "post_seal_checksums.txt"
    if not core.exists() or not psc.exists():
        return None
    digest = sha256(psc)
    kept = [ln for ln in core.read_text(encoding="utf-8").splitlines()
            if not ln.startswith(_POST_SEAL_ANCHOR_TAG)]
    while kept and kept[-1].strip() == "":
        kept.pop()
    kept.append(f"{_POST_SEAL_ANCHOR_TAG} {digest}")
    _atomic_write_text(core, "\n".join(kept) + "\n")  # CORE-P04
    return digest


def read_post_seal_anchor(package_dir: str | Path) -> str | None:
    """Return the anchored sha256 hex recorded for post_seal_checksums.txt in checksums_sha256.txt,
    or None when no anchor line is present (a pre-r2 package)."""
    core = Path(package_dir) / "checksums_sha256.txt"
    if not core.exists():
        return None
    for ln in core.read_text(encoding="utf-8").splitlines():
        if ln.startswith(_POST_SEAL_ANCHOR_TAG):
            parts = ln.split()
            if len(parts) >= 3:
                return parts[-1].strip()
    return None


def verify_post_seal_anchor(package_dir: str | Path) -> list[str]:
    """SEAL-06 (v9.7.409 r2; DEEP_AUDIT2 R2-1): recompute sha256(post_seal_checksums.txt) and
    compare it to the anchor recorded in checksums_sha256.txt. Returns a list of error strings
    (empty = OK). Backward-compatible: when NO anchor line exists (pre-r2 package) this returns []
    so an older sealed package still validates.

    Closed by this check: B1 (swap a covered file + rewrite its line in post_seal_checksums.txt) and
    D4 (delete a covered file + delete its manifest line) — both change the manifest's bytes, so its
    digest no longer matches the anchor. NOT closed: an insider who ALSO rewrites this anchor line in
    the unsigned in-package checksums_sha256.txt (see the module caveat; needs external signing)."""
    root = Path(package_dir)
    anchor = read_post_seal_anchor(root)
    if anchor is None:
        return []  # pre-r2 package: no anchor to enforce.
    psc = root / "post_seal_checksums.txt"
    if not psc.exists():
        return ["post_seal_checksums.txt is anchored in checksums_sha256.txt but missing on disk "
                "(post-seal integrity manifest deleted)"]
    actual = sha256(psc)
    if actual != anchor:
        return ["post_seal_checksums.txt does not match its anchor in checksums_sha256.txt "
                "(the post-seal integrity manifest was edited after sealing)"]
    return []


def verify_repro_fingerprint_recompute(package_dir: str | Path) -> dict:
    """PROV-FP (v9.7.409 r2; DEEP_AUDIT2 provenance A / R2-6): RECOMPUTE the determinism fingerprint
    from the actual score-bearing files and compare it to the value STORED in repro_fingerprint.json
    and manifest.repro_fingerprint. Returns {"state": PASS|FAIL|NOT_EVALUABLE, "recomputed"?, "detail"?}.

    The seal/validate path previously TRUSTED the stored receipt (never recomputed it), so a
    hand-edited fingerprint of any chosen value passed. Recomputing here FAILs a fingerprint that
    was edited to a value the files do not produce (audit attack A: forge to deadbeef… -> FAIL) and
    a package whose science was altered without regenerating the receipt. NOT closed: an insider who
    edits the science AND regenerates BOTH stored copies to the new recomputed value stays
    self-consistent (audit C2) — detectable only against an EXTERNALLY-published reference hex, which
    an all-in-package scheme cannot provide. NOT_EVALUABLE (no stored fingerprint) keeps partial /
    fixture packages validating."""
    root = Path(package_dir)
    stored: list[tuple[str, str]] = []
    fp_json = root / "repro_fingerprint.json"
    if fp_json.exists():
        try:
            d = json.loads(fp_json.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {"state": "FAIL", "detail": "repro_fingerprint.json is present but unreadable"}
        if isinstance(d, dict) and d.get("fingerprint"):
            stored.append(("repro_fingerprint.json", str(d["fingerprint"])))
    mf = root / "manifest.json"
    if mf.exists():
        try:
            md = json.loads(mf.read_text(encoding="utf-8"))
            if isinstance(md, dict) and md.get("repro_fingerprint"):
                stored.append(("manifest.repro_fingerprint", str(md["repro_fingerprint"])))
        except (OSError, UnicodeError, json.JSONDecodeError) as _swallowed_exc:
            _warnings.warn(f"packaging.py: non-blocking step skipped ({type(_swallowed_exc).__name__}: {_swallowed_exc})", RuntimeWarning, stacklevel=2)  # v9.7.409: was a silent swallow
    if not stored:
        return {"state": "NOT_EVALUABLE", "detail": "no stored determinism fingerprint to compare"}
    try:
        actual = repro_fingerprint(root)["fingerprint"]
    except Exception as exc:
        return {"state": "FAIL", "detail": f"could not recompute determinism fingerprint: {exc}"}
    mism = [(src, val) for (src, val) in stored if val != actual]
    if mism:
        srcs = ", ".join(f"{s}={v[:16]}…" for s, v in mism)
        return {"state": "FAIL", "recomputed": actual,
                "detail": f"recomputed determinism fingerprint {actual[:16]}… != stored ({srcs})"}
    return {"state": "PASS", "recomputed": actual}


def verify_manifest_provenance_binding(package_dir: str | Path, manifest: dict) -> dict:
    """PROV-BIND (v9.7.409 r2; DEEP_AUDIT2 provenance C5/D / R2-6): cross-check the load-bearing
    manifest.json fields against the CHECKSUM-COVERED core tables (the manifest itself is excluded
    from the seal, so its fields are otherwise free-text forgeable). Returns
    {"state": PASS|FAIL|NOT_EVALUABLE, "engine_version_binding": PASS|MISMATCH|NOT_EVALUABLE, "detail"}.

    Bindings:
      (1) bgcs COUNT: manifest.bgcs length must equal the _2_inventory.csv row count (the inventory
          is checksum-covered) — catches a fabricated/removed manifest BGC entry (audit C5: 60->61).
      (2) mode DOWNGRADE: if the covered inventory carries gold-only Depth_floor assignments but the
          manifest declares a non-gold mode, that is a gold->public downgrade (audit C5) which also
          silently disables the gold-completeness gate. FAIL.
      (3) release: advisory only — no checksum-covered anchor for `release` exists today (documented
          in the PATCH_CARD as a remaining gap needing a covered field).
      (4) engine re-derivation: compare manifest.workflow_version/bundle_version against the RUNNING
          engine (mamey.__version__) instead of trusting the stored string (PROV-01). ADVISORY
          (MISMATCH is surfaced, not blocking — validating with a different engine build is legit).

    Fails CLOSED only on a positive cross-table contradiction; absent inputs -> NOT_EVALUABLE, so
    partial / fixture / legit packages keep validating."""
    root = Path(package_dir)
    if not isinstance(manifest, dict) or not manifest:
        return {"state": "NOT_EVALUABLE", "engine_version_binding": "NOT_EVALUABLE",
                "detail": "manifest absent/unreadable (manifest_parse gate covers this)"}
    import csv as _csv
    detail: list[str] = []
    state = "PASS"
    inv_matches = sorted(root.glob("*_2_inventory.csv"))
    inv = inv_matches[0] if inv_matches else None
    inv_rows = 0
    inv_depth_floor = False
    if inv is not None:
        try:
            with open(inv, newline="", encoding="utf-8") as f:
                for row in _csv.DictReader(f):
                    inv_rows += 1
                    if (row.get("Depth_floor") or "").strip():
                        inv_depth_floor = True
        except OSError:
            inv = None
    m_bgcs = manifest.get("bgcs")
    if inv is not None and isinstance(m_bgcs, list) and inv_rows > 0 and len(m_bgcs) != inv_rows:
        state = "FAIL"
        detail.append(f"manifest.bgcs count {len(m_bgcs)} != _2_inventory.csv row count {inv_rows} "
                      f"(checksum-covered inventory disagrees with the manifest BGC list)")
    m_mode = str(manifest.get("mode") or "").lower()
    if inv is not None and inv_depth_floor and m_mode and m_mode not in ("gold", "full"):  # "full" = legacy internal gold alias (RunContext)
        state = "FAIL"
        detail.append(f"manifest.mode={m_mode!r} but the checksum-covered _2_inventory.csv carries "
                      f"gold-only Depth_floor assignments (a gold->non-gold downgrade)")
    try:
        from . import __version__ as _running_engine
    except Exception:
        try:
            from mamey import __version__ as _running_engine  # direct-script fallback
        except Exception:
            _running_engine = None
    m_engine = str(manifest.get("workflow_version") or manifest.get("bundle_version") or "")
    if _running_engine and m_engine:
        engine_binding = "PASS" if str(_running_engine) in m_engine else "MISMATCH"
    else:
        engine_binding = "NOT_EVALUABLE"
    return {"state": state, "engine_version_binding": engine_binding,
            "detail": "; ".join(detail)}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# v9.7.199 REPRO-FINGERPRINT: checksums_sha256.txt cannot be compared across runs/chats —
# it tracks the date-stamped master workbook, timestamped receipts, and (excludes but is
# adjacent to) re-rendered figures, so two identical runs produce different checksum files.
# The determinism fingerprint hashes ONLY the deterministic, score-bearing outputs, so the
# same strain on the same bundle yields the SAME fingerprint in any chat. A mismatch is a
# real divergence to investigate, not run-to-run noise. Whitelist entries are matched by
# filename suffix (the per-strain prefix varies); missing files hash as "MISSING" rather than
# aborting, so the fingerprint is defined even on a partial package.
DETERMINISM_WHITELIST = (
    "_2_inventory.csv",
    "_2b_bgc_crosswalk.csv",
    "_3_scan_states.json",
    "_4_triage_board.csv",
    "_4c_AB_lead_board.csv",
    "_4c_AF_lead_board.csv",
    "_4A_RGGMCI_ranked_pairs.csv",
    "_4B_pks_ks_fragment_scan.csv",  # .359 (phylogenomics-lane P358): deterministic 5-mer/single-linkage KS scan — belongs in the repro fingerprint
)


def repro_fingerprint(package_dir: str | Path) -> dict:
    """Stable, cross-run/cross-chat determinism fingerprint over the score-bearing outputs.

    Returns {"fingerprint": <sha256 hex>, "components": {suffix: <sha256 head16 | "MISSING">},
    "whitelist": [...]}. Line endings are normalized to \\n so a fingerprint computed on a
    Windows-checkout package matches a Linux one. Intended for `mamey fingerprint` compare and
    for the manifest's repro_fingerprint field. This is NOT a substitute for checksums_sha256.txt
    (whole-package integrity); it answers a different question: 'did two runs agree on the science?'
    """
    root = Path(package_dir)
    _package_files_fail_closed(root)
    h = hashlib.sha256()
    components: dict[str, str] = {}
    for suffix in DETERMINISM_WHITELIST:
        matches = sorted(p for p in root.glob(f"*{suffix}") if p.is_file())
        if not matches:
            components[suffix] = "MISSING"
            h.update(suffix.encode())
            h.update(b"\x00MISSING\x00")
            continue
        data = matches[0].read_bytes().replace(b"\r\n", b"\n")
        components[suffix] = hashlib.sha256(data).hexdigest()[:16]
        h.update(suffix.encode())
        h.update(data)
    return {"fingerprint": h.hexdigest(), "components": components,
            "whitelist": list(DETERMINISM_WHITELIST)}


def write_repro_fingerprint(package_dir: str | Path) -> dict:
    """Compute the determinism fingerprint and write repro_fingerprint.json into the package.
    Returns the fingerprint dict. Excluded from checksums_sha256.txt (written post file-capture)."""
    fp = repro_fingerprint(package_dir)
    (Path(package_dir) / "repro_fingerprint.json").write_text(
        json.dumps(fp, indent=2), encoding="utf-8")
    return fp


def fingerprint_command(args) -> int:
    """`mamey fingerprint <package> [--compare <package_or_hex>] [--json]`.

    Emits the determinism fingerprint of a sealed package. With --compare, diffs it against
    another package (path) or a raw fingerprint hex, returning exit 0 on match, 1 on divergence
    (per-component diff printed). This is the cross-chat reproducibility check: same strain +
    same bundle should yield the same fingerprint in any chat.
    """
    fp = repro_fingerprint(args.package)
    if getattr(args, "compare", None):
        other_arg = args.compare
        other_path = Path(other_arg)
        if other_path.exists():
            other = repro_fingerprint(other_path)
        else:
            # treat as a bare fingerprint hex (component-level diff unavailable)
            other = {"fingerprint": other_arg.strip(), "components": {}}
        match = fp["fingerprint"] == other["fingerprint"]
        if getattr(args, "json", False):
            emit(json.dumps({"match": match, "a": fp, "b": other}, indent=2))
        else:
            emit(f"A fingerprint: {fp['fingerprint']}", f"B fingerprint: {other['fingerprint']}", f"MATCH: {match}", sep="\n")
            if not match and other.get("components"):
                for suf in fp["components"]:
                    a, b = fp["components"][suf], other["components"].get(suf, "ABSENT")
                    if a != b:
                        emit(f"  DIFFERS  {suf:28s} {a}  !=  {b}")
        return 0 if match else 1
    if getattr(args, "json", False):
        emit(json.dumps(fp, indent=2))
    else:
        emit(f"repro_fingerprint: {fp['fingerprint']}")
        for suf, h in fp["components"].items():
            emit(f"  {suf:28s} {h}")
    return 0


def write_manifest(package_dir: str | Path) -> dict:
    root = Path(package_dir)

    # v9.7.146 PATCH-PACKAGING-SEAL: these files are mutated AFTER the file list is built
    # (write_package_status_receipt and write_claim_safety_receipt run below).
    # Exclude them from the checksum set so checksums_sha256.txt is always self-consistent.
    # verify_checksums() in validate.py mirrors this exclusion list.
    # v9.7.199: repro_fingerprint.json is written AFTER the file list is captured (below),
    # like the other post-capture receipts, so it is excluded from checksums_sha256.txt.
    MUTABLE_NAMES = set(MUTABLE_RECEIPT_NAMES)

    files = []
    for p in _package_files_fail_closed(root):
        if (p.name not in {"manifest.json", "checksums_sha256.txt"} | MUTABLE_NAMES
                and not p.name.endswith(MUTABLE_RECEIPT_SUFFIXES)):  # v9.7.409 A10
            if is_checksum_excluded(str(p.relative_to(root))):
                continue
            files.append({"path": str(p.relative_to(root)), "sha256": sha256(p), "bytes": p.stat().st_size})

    manifest_path = root / "manifest.json"
    base = _load_existing_manifest(manifest_path) if manifest_path.exists() else {}
    # Preserve the run snapshot written by cli._write_package.  Add package file
    # inventory instead of replacing scientific metadata (mode, bgcs, scans).
    manifest = dict(base)
    # This is a locator *inside* the portable package, never a sender's machine path.
    manifest["package_dir"] = "."
    manifest["package_status"] = infer_package_status(root, manifest=manifest)
    claim_safety = run_claim_safety_gate(root)
    manifest["claim_safety_status"] = claim_safety["claim_safety_status"]
    manifest["files"] = files
    # Mutating receipts written AFTER file-list/hash capture — intentionally excluded above
    write_package_status_receipt(root, manifest=manifest)
    write_claim_safety_receipt(root)
    # v9.7.199: determinism fingerprint over score-bearing outputs (cross-run/cross-chat compare).
    _fp = repro_fingerprint(root)
    manifest["repro_fingerprint"] = _fp["fingerprint"]
    manifest["repro_fingerprint_components"] = _fp["components"]
    _atomic_write_text(manifest_path, json.dumps(manifest, indent=2))
    _atomic_write_text(root / "checksums_sha256.txt", "\n".join(f"{x['sha256']}  {x['path']}" for x in files) + "\n")
    _atomic_write_text(root / "repro_fingerprint.json", json.dumps(_fp, indent=2))
    return manifest


def _unique_tmp(path) -> Path:
    """v9.7.409 (CLAUDE_409 C2/C3/C4): reserve a UNIQUE same-directory temp via mkstemp instead of
    a fixed ``<name>.tmp`` sibling.

    A fixed ``path.name + '.tmp'`` sibling lets two concurrent writers to the SAME target truncate
    or remove each other's in-progress temp; the loser then crashes in os.replace with
    ``FileNotFoundError`` (e.g. ``manifest.json.tmp -> manifest.json``). mkstemp gives every writer
    a private same-filesystem path, so the sibling-rename atomicity is kept while the collision is
    removed. Mirrors ``tools/_wbio._temp_path`` — the established pattern already used elsewhere in
    this codebase precisely to stop concurrent writers clobbering one temp."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    return Path(tmp)


def _discard_tmp(tmp) -> None:
    """Remove a staging temp on a failed write (best-effort)."""
    with _suppress(OSError):  # v9.7.409: best-effort cleanup, intent explicit (was except: pass)
        if tmp is not None and Path(tmp).exists():
            Path(tmp).unlink()


def _atomic_write_text(path: Path, text: str) -> None:
    """CORE-P04: write to a UNIQUE temp sibling then atomically replace, so an interrupted seal never
    leaves a truncated manifest / checksums / fingerprint that fails verification on re-open.
    v9.7.409 (CLAUDE_409 C2/C3/C4): unique mkstemp temp (was fixed ``<name>.tmp``) so two concurrent
    writers to one target no longer clobber each other's temp and crash in os.replace."""
    path = Path(path)
    tmp = _unique_tmp(path)
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        _discard_tmp(tmp)
        raise


import contextlib as _contextlib

@_contextlib.contextmanager
def atomic_open(path, mode="w", encoding="utf-8", newline=None):
    """AUDIT_374: CORE-P04 sibling for streamed writes (csv.writer loops, line-by-line
    reports) where building the whole payload as one string first would be awkward. Yields a
    file handle on a sibling .tmp; atomically replaces the target only on clean exit. If the
    block raises, the .tmp is discarded and the original file is left untouched -- so a package
    write interrupted mid-CSV never leaves a truncated deliverable sitting in package_dir.
    Mirrors _atomic_write_text above (and tools/_wbio.py's identical helper used elsewhere in
    this codebase) for the streamed case that helper does not cover.
    v9.7.409 (CLAUDE_409 C2/C3): unique mkstemp temp (was fixed ``<name>.tmp``) so two concurrent
    streamed writers to one target no longer collide."""
    path = Path(path)
    tmp = _unique_tmp(path)
    f = open(tmp, mode, encoding=encoding, newline=newline)
    try:
        yield f
        f.close()
        os.replace(tmp, path)
    except BaseException:
        try:
            f.close()
        finally:
            _discard_tmp(tmp)
        raise
def _zip_compression():
    """Select ZIP compression from MAMEY_ZIP_COMPRESSION (v9.7.128).

    default / deflated  -> ZIP_DEFLATED (normal public-release behaviour)
    stored / store / none / 0 -> ZIP_STORED (faster, larger ZIPs for capped ChatGPT-safe runs)
    """
    import os
    val = (os.environ.get("MAMEY_ZIP_COMPRESSION") or "").strip().lower()
    if val in ("stored", "store", "none", "0"):
        return zipfile.ZIP_STORED
    return zipfile.ZIP_DEFLATED


def zip_package(package_dir: str | Path, zip_path: str | Path) -> None:
    package_dir, zip_path = Path(package_dir), Path(zip_path)
    package_files = _package_files_fail_closed(package_dir)
    # CORE-P05: build into a temp sibling then atomically replace, so an interrupted zip never
    # destroys a valid prior ZIP before the new one exists (was: unlink-then-write).
    # v9.7.409 (CLAUDE_409 C2/C3): UNIQUE mkstemp temp (was fixed ``<name>.tmp``) so two concurrent
    # zips to one target don't collide/crash.
    _ztmp = _unique_tmp(zip_path)
    try:
        with zipfile.ZipFile(_ztmp, "w", _zip_compression()) as z:
            for p in package_files:
                z.write(p, p.relative_to(package_dir.parent))
        os.replace(_ztmp, zip_path)  # CORE-P05: atomic swap into place
    except BaseException:
        _discard_tmp(_ztmp)
        raise

def write_checksums(package_dir: str | Path) -> None:
    """Write checksums_sha256.txt without regenerating manifest.json.

    v9.7.146: excludes mutable post-seal files, consistent with write_manifest().
    """
    root = Path(package_dir)
    MUTABLE_NAMES = set(MUTABLE_RECEIPT_NAMES)
    lines = []
    for p in _package_files_fail_closed(root):
        if (p.name not in {"manifest.json", "checksums_sha256.txt"} | MUTABLE_NAMES
                and not p.name.endswith(MUTABLE_RECEIPT_SUFFIXES)):  # v9.7.409 A10
            if is_checksum_excluded(str(p.relative_to(root))):
                continue
            lines.append(f"{sha256(p)}  {p.relative_to(root)}")
    _atomic_write_text(root / "checksums_sha256.txt", "\n".join(lines) + "\n")  # CORE-P04
