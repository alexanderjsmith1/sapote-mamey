"""blastp_gate.py — BLASTp-completeness HARD gate (.344).

Why this exists: BLASTp ingestion is a MANDATORY workflow step (step 3, before Mode B and the
compiled report), but nothing in the engine could tell that ingestable BLASTp was sitting on
disk un-folded-in. So an operator could walk straight past it and the report/cards would render
with an empty (or thin) BLASTp evidence channel — silently. This module detects
"available-but-not-ingested" BLASTp per strain/BGC/channel and lets the callers (compile-report,
emit-modeb-template) HARD-BLOCK until it is either ingested or explicitly waived with a logged
reason.

Contract (chosen 2026-07-31): scan known trove locations for <strain>/<BGC>/<per-gene>.csv across
channels {nr, clustered_nr, swissprot, ebi}; compare against what is in the package blastp store
(<pkg>/blastp_online/<BGC>_online_blastp.csv, `channel` column); if any channel is
available-but-not-ingested -> the caller errors (exit 3) with the exact ingest command, OR proceeds
only with a --blastp-waiver "<reason>" recorded to manifest + report provenance.

Report-only / non-scoring: this NEVER touches AB/AF/tiers/scans. It gates deliverable emission.
"""
from __future__ import annotations
import csv
import fnmatch
import glob
import json
import os
from datetime import date
from pathlib import Path

# channel -> (folder-name substrings that identify a trove root, per-gene file globs inside <BGC>/)
CHANNEL_TROVE = {
    "nr":           (("_nr_rid", "nr_rid", "/nr/", "ncbi_nr"),
                     ("*_top_hit_per_gene.csv", "*_nr_top_hit_per_gene.csv")),
    "clustered_nr": (("clustered nr", "clustered_nr", "clusterednr", "cluster_nr"),
                     ("*_top10_clustered.csv", "*clustered*per_gene*.csv", "*_top_hit_per_gene.csv")),
    "swissprot":    (("swissprot", "swiss_prot", "swiss-prot"),
                     ("*_top10_local.csv", "*_swissprot*.csv", "*local*per_gene*.csv")),
    "ebi":          (("(ebi)", "_ebi", "ebi_", "/ebi"),
                     ("*_ebi*.csv", "*ebi_top_hit_per_gene.csv", "*per_gene*.csv")),
}


def _norm(s: str) -> str:
    return s.lower().replace("\\", "/")


# GENERIC project-root markers — NOT user- or dataset-specific. Any Claude Code / git project
# will have one of these at its root. Users can also set MAMEY_BLASTP_SCAN_ROOT explicitly.
_PROJECT_MARKERS = (".claude", ".git", ".mamey_project", "CLAUDE.md")


class BlastpDiscoveryError(RuntimeError):
    """A configured BLASTp evidence root could not be traversed completely."""


def find_workspace_root(package: str | Path, max_up: int = 12) -> Path:
    """Resolve the folder to scan for BLASTp troves, for ANY user's layout (no hardcoded folder
    names). Precedence:
      1. $MAMEY_BLASTP_SCAN_ROOT (explicit override).
      2. nearest ancestor of the package containing a generic project marker (.claude/.git/…), below the home/root boundary.
      3. the current working directory (where the operator ran mamey).
      4. the package containing directory, without climbing unrelated ancestors.
    """
    env = os.environ.get("MAMEY_BLASTP_SCAN_ROOT")
    if env:
        if not Path(env).is_dir():
            raise BlastpDiscoveryError("BLASTP_DISCOVERY_HOLD: configured scan root is not a directory")
        return Path(env).resolve()
    p = Path(package).resolve()
    home = Path.home().resolve()
    for _ in range(max_up):
        # Account configuration is not an analysis-project boundary. Explicit
        # MAMEY_BLASTP_SCAN_ROOT still permits an intentionally selected home root.
        if p == home or p.parent == p:
            break
        try:
            if any((p / m).exists() for m in _PROJECT_MARKERS):
                return p
        except OSError:
            pass
        if p.parent == p:
            break
        p = p.parent
    cwd = Path.cwd().resolve()
    # prefer cwd only if the package lives under it (so we scan the operator's project)
    try:
        Path(package).resolve().relative_to(cwd)
        if cwd != home and cwd.parent != cwd:
            return cwd
    except ValueError:
        pass
    # Unmarked standalone packages have no authority to scan unrelated ancestors.
    # Wider discovery requires an explicit scan root or a recognized project marker.
    return Path(package).resolve().parent


def discover_trove_roots(package: str | Path, extra_roots=None, roots_base: str | Path | None = None) -> dict:
    """Return {channel: [trove_root Path, ...]}. Anchor at the workspace root and match its
    children AND grandchildren (depth <=2) against each channel's folder substrings — the workspace
    troves are irregularly nested (e.g. 'Blastp RESULTS/_NR_RID'). `extra_roots` (list of
    (channel, path)) are added verbatim. Directory-name scan only; fast."""
    found: dict[str, list[Path]] = {c: [] for c in CHANNEL_TROVE}
    base = Path(roots_base) if roots_base else find_workspace_root(package)
    seen: set[str] = set()

    def _scan(d: Path):
        try:
            for child in d.iterdir():
                if not child.is_dir():
                    continue
                key = str(child)
                if key in seen:
                    continue
                seen.add(key)
                nd = _norm(child.name)
                for ch, (folder_subs, _globs) in CHANNEL_TROVE.items():
                    if any(sub in nd for sub in folder_subs):
                        found[ch].append(child)
                yield child
        except OSError as exc:
            raise BlastpDiscoveryError(
                f"BLASTP_DISCOVERY_HOLD: cannot traverse evidence directory {d.name!r} "
                f"({type(exc).__name__})"
            ) from exc

    # depth 1
    level1 = list(_scan(base))
    # depth 2 (grandchildren) — needed for nested troves like 'Blastp RESULTS/_NR_RID'
    for d in level1:
        list(_scan(d))
    for ch, root in (extra_roots or []):
        if ch in found:
            found[ch].append(Path(root))
    return found


def _strain_dirs_in(root: Path, strain: str) -> list:
    """Find <strain> directories inside a trove root, tolerating an intermediate level
    (e.g. '_NR_RID/results/<strain>/'). Also accepts a root that is already strain-scoped."""
    dirs: list[Path] = []
    root = Path(root)
    # direct
    if (root / strain).is_dir():
        dirs.append(root / strain)
    # one level down (the 'results' case)
    try:
        children = list(root.iterdir())
        for child in children:
            if child.is_dir() and (child / strain).is_dir():
                dirs.append(child / strain)
        # root already inside the strain (contains BGC dirs)
        if any(p.is_dir() and p.name.upper().startswith("BGC") for p in children):
            dirs.append(root)
    except OSError as exc:
        raise BlastpDiscoveryError(
            f"BLASTP_DISCOVERY_HOLD: cannot traverse configured trove root {root.name!r} "
            f"({type(exc).__name__})"
        ) from exc
    # de-dup
    seen: set[str] = set(); uniq = []
    for d in dirs:
        k = str(d.resolve())
        if k not in seen:
            seen.add(k); uniq.append(d)
    return uniq


def available(strain: str, trove_roots: dict) -> dict:
    """{channel: {bgc: path}} for per-gene BLASTp files present under a trove root's
    <strain>/<BGC>/ (tolerating an intermediate dir), keyed by channel."""
    out: dict[str, dict[str, str]] = {}
    for ch, roots in trove_roots.items():
        globs = CHANNEL_TROVE[ch][1]
        for root in roots:
            for sdir in _strain_dirs_in(Path(root), strain):
                for bgc_dir in sorted(p for p in sdir.iterdir() if p.is_dir()
                                      and p.name.upper().startswith("BGC")):
                    if bgc_dir.name in out.get(ch, {}):
                        continue
                    try:
                        candidates = sorted(bgc_dir.iterdir())
                    except OSError as exc:
                        raise BlastpDiscoveryError(
                            f"BLASTP_DISCOVERY_HOLD: cannot traverse candidate BGC directory "
                            f"{bgc_dir.name!r} ({type(exc).__name__})"
                        ) from exc
                    for g in globs:
                        # v9.7.345 fix: only count files with a real data row. A header-only /
                        # empty trove file means NO BLASTp for that BGC — nothing to ingest, so it
                        # must NOT block the gate forever. (Regression: this fix was lost before .344.)
                        hits = [h for h in candidates if fnmatch.fnmatch(h.name, g)
                                and _has_data_row(h)]
                        if hits:
                            out.setdefault(ch, {})[bgc_dir.name] = str(hits[0])
                            break
    return out


def _has_data_row(path) -> bool:
    """True if a CSV has at least one non-empty line beyond the header."""
    try:
        with Path(path).open(encoding="utf-8") as fh:
            if not fh.readline():
                return False
            for line in fh:
                if line.strip():
                    return True
        return False
    except OSError as exc:
        raise BlastpDiscoveryError(
            f"BLASTP_DISCOVERY_HOLD: cannot read candidate evidence file "
            f"{Path(path).name!r} ({type(exc).__name__})"
        ) from exc


def ingested(package: str | Path) -> dict:
    """{bgc: set(channel)} of what has been ingested into the package.

    AUTHORITATIVE source is the ingest LEDGER (<pkg>/blastp_online/_ingest_ledger.json), which
    records every (channel, bgc) folded in regardless of channel-precedence. This matters because
    the merged store keeps only the highest-precedence row per gene, so a lower channel can
    contribute 0 surviving rows yet still have been ingested — reading surviving rows alone would
    make the gate over-block forever. Falls back to surviving-row inference only when no ledger
    exists (older packages)."""
    out: dict[str, set] = {}
    # 1. authoritative: the ledger
    ledger = read_ingest_ledger(package)
    for channel, bgcs in ledger.items():
        for bgc, receipt in bgcs.items():
            # Five-part guarded ledgers mark zero-admission/all-quarantined sources incomplete.
            # Older ledgers have no explicit status and retain their legacy fallback behavior;
            # they must be audited/re-ingested before the next release claims completeness.
            if isinstance(receipt, dict) and "evidence_complete" in receipt:
                if not receipt.get("evidence_complete") or int(receipt.get("admitted_rows", 0)) <= 0:
                    continue
            out.setdefault(bgc, set()).add(channel)
    # 2. fallback / augment: surviving rows (covers the native 'online' channel + pre-ledger pkgs)
    store = Path(package) / "blastp_online"
    try:
        store_entries = list(store.iterdir())
    except (FileNotFoundError, NotADirectoryError):
        store_entries = []
    except OSError as exc:
        raise BlastpDiscoveryError(
            f"BLASTP_DISCOVERY_HOLD: cannot traverse stored overlay directory "
            f"({type(exc).__name__})"
        ) from exc
    for f in (p for p in store_entries
              if p.is_file() and p.name.endswith("_online_blastp.csv")):
            bgc = f.name.split("_")[0]
            chans = out.setdefault(bgc, set())
            try:
                for r in csv.DictReader(f.open(newline="")):
                    c = (r.get("channel") or "").strip()
                    chans.add(c if c else "online")
            except (OSError, csv.Error) as exc:
                raise BlastpDiscoveryError(
                    f"BLASTP_DISCOVERY_HOLD: cannot read stored overlay {f.name!r} "
                    f"({type(exc).__name__})"
                ) from exc
    return out


def read_ingest_ledger(package: str | Path) -> dict:
    """Read the package's BLASTp ingest ledger ({channel: {bgc: {...}}}). Empty if none."""
    try:
        from .blastp_ingest import read_ingest_ledger as _r
    except ImportError:
        import json
        led = Path(package) / "blastp_online" / "_ingest_ledger.json"
        try:
            return json.loads(led.read_text(encoding="utf-8")) if led.exists() else {}
        except (OSError, json.JSONDecodeError) as exc:
            raise BlastpDiscoveryError(
                f"BLASTP_INGEST_LEDGER_HOLD: cannot read ingest ledger {led.name!r} "
                f"({type(exc).__name__})"
            ) from exc
    return _r(package)


def missing_ingestions(package: str | Path, strain: str, trove_roots: dict | None = None,
                       extra_roots=None) -> list:
    """List of (channel, bgc, trove_path) that are available on disk but NOT in the package store."""
    roots = trove_roots if trove_roots is not None else discover_trove_roots(package, extra_roots)
    avail = available(strain, roots)
    have = ingested(package)
    # v9.7.371 fix: available()'s bgc keys come from the trove directory's own on-disk casing
    # (e.g. an operator folder named 'bgc003/'), while have (ingested()) is keyed by the
    # package/ledger's own convention (uppercase 'BGC003'). A case mismatch made this comparison
    # silently miss an already-ingested BGC, hard-blocking the gate on evidence that IS ingested.
    # Compare case-insensitively without changing either side's own stored casing (avail's paths
    # and have's set contents are used elsewhere and are left untouched).
    have_upper = {b.upper(): chans for b, chans in have.items()}
    missing = []
    for ch, bgcs in sorted(avail.items()):
        for bgc, path in sorted(bgcs.items()):
            if ch not in have_upper.get(bgc.upper(), set()):
                missing.append((ch, bgc, path))
    return missing


def _trove_root_for(missing: list, channel: str) -> str:
    for ch, _bgc, path in missing:
        if ch == channel:
            # trove root = two levels up from <root>/<strain>/<BGC>/<file>
            return str(Path(path).parent.parent.parent)
    return "<trove_root>"


def format_block_message(strain: str, package: str | Path, missing: list) -> str:
    by_ch: dict[str, list] = {}
    for ch, bgc, _p in missing:
        by_ch.setdefault(ch, []).append(bgc)
    lines = [
        f"BLASTP GATE — BLOCKED for {strain}: {len(missing)} BGC-channel pair(s) have BLASTp on "
        f"disk that is NOT ingested into the package store.",
        "BLASTp ingestion is a MANDATORY step before Mode B / the compiled report. Ingest it, or "
        "re-run with --blastp-waiver \"<reason>\".",
        "",
    ]
    for ch in ("nr", "clustered_nr", "swissprot", "ebi"):
        if ch not in by_ch:
            continue
        bgcs = by_ch[ch]
        root = _trove_root_for(missing, ch)
        lines.append(f"  channel {ch}: {len(bgcs)} BGC(s) not ingested "
                     f"({', '.join(bgcs[:8])}{' …' if len(bgcs) > 8 else ''})")
        lines.append(f"    fix: python -m mamey ingest-blastp-trove "
                     f"--trove \"{root}\" --package \"{package}\" --channel {ch} --strain {strain}")
    return "\n".join(lines)


def record_waiver(package: str | Path, strain: str, reason: str, missing: list) -> bool:
    """Stamp the waiver into manifest.json provenance so a report/card that shipped BLASTp-incomplete
    says so, permanently and machine-readably. Returns True iff the write actually landed on disk —
    the caller MUST check this before telling anyone the waiver was recorded (v9.7.374 fix: this used
    to swallow (OSError, json.JSONDecodeError) with a bare `pass` and the caller never checked, so a
    write failure — read-only manifest, disk full, or a manifest.json already corrupted — silently
    dropped the waiver while `gate()` still reported ok=True/waived=True with a message claiming
    "Recorded to manifest provenance", leaving a BLASTp-incomplete deliverable with NO audit trail of
    why)."""
    man = Path(package) / "manifest.json"
    entry = {
        "strain": strain, "reason": reason, "date": date.today().isoformat(),
        "waived_pairs": [{"channel": c, "bgc": b} for c, b, _ in missing],
        "n_waived": len(missing),
    }
    try:
        try:
            raw = man.read_text(encoding="utf-8")
        except FileNotFoundError:
            raw = "{}"
        data = json.loads(raw)
        data.setdefault("blastp_waivers", []).append(entry)
        tmp = man.with_name(man.name + ".blastp-waiver.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(man)
        return True
    except (OSError, json.JSONDecodeError):
        return False


def gate(package: str | Path, strain: str, waiver: str | None = None, extra_roots=None,
         trove_roots: dict | None = None) -> dict:
    """The hard gate. Returns a dict:
      {ok: bool, blocked: bool, missing: [...], message: str, waived: bool}
    ok=True means the caller may proceed (nothing missing, or a waiver was given). ok=False means
    the caller MUST refuse (print `message`, exit 3)."""
    missing = missing_ingestions(package, strain, trove_roots=trove_roots, extra_roots=extra_roots)
    if not missing:
        return {"ok": True, "blocked": False, "missing": [], "message": "", "waived": False}
    if waiver:
        recorded = record_waiver(package, strain, waiver, missing)
        if not recorded:
            # v9.7.374 fix: do not report a successful waiver when the manifest write failed — that
            # would let a BLASTp-incomplete deliverable ship with no provenance trail of why. Fail
            # closed instead, same as an un-waived block, but with a distinct message so the operator
            # fixes the manifest (permissions/corruption) rather than re-typing the waiver reason.
            msg = (f"BLASTP GATE — WAIVER NOT RECORDED for {strain}: could not write the waiver to "
                   f"manifest.json in {package} (unwritable or corrupt manifest). Refusing to proceed "
                   f"with an unrecorded waiver — fix the manifest and retry with --blastp-waiver "
                   f"\"{waiver}\", or resolve the {len(missing)} un-ingested pair(s) directly.")
            return {"ok": False, "blocked": True, "missing": missing, "message": msg, "waived": False}
        msg = (f"BLASTP GATE — WAIVED for {strain} ({len(missing)} un-ingested pair(s)): {waiver}. "
               f"Recorded to manifest provenance; deliverables are BLASTP-INCOMPLETE by attestation.")
        return {"ok": True, "blocked": False, "missing": missing, "message": msg, "waived": True}
    return {"ok": False, "blocked": True, "missing": missing,
            "message": format_block_message(strain, package, missing), "waived": False}
