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
import hashlib
import json
import os
import sys
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
        except OSError as exc:
            sys.stderr.write(
                f"blastp_gate: cannot inspect project markers under {p} "
                f"({type(exc).__name__}: {exc}); continuing toward the package root\n"
            )
        if p.parent == p:
            break
        p = p.parent
    cwd = Path.cwd().resolve()
    # prefer cwd only if the package lives under it (so we scan the operator's project)
    package_resolved = Path(package).resolve()
    if package_resolved == cwd or cwd in package_resolved.parents:
        if cwd != home and cwd.parent != cwd:
            return cwd
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


def _source_sha256(path: str | Path) -> str:
    """Hash a discovered trove source so a re-key receipt can be bound to its exact bytes."""
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise BlastpDiscoveryError(
            f"BLASTP_DISCOVERY_HOLD: cannot hash candidate evidence file "
            f"{Path(path).name!r} ({type(exc).__name__})"
        ) from exc
    return digest.hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


def _referenced_rekey_source_index(package: str | Path) -> tuple[dict, list]:
    """Index current-ledger re-key receipts by ``(channel, source BGC, source SHA-256)``.

    Receipts are considered only when the current ingest ledger references them.  This avoids
    reviving superseded immutable receipts that remain in the package.  Missing, legacy, or
    non-re-key receipts simply leave the source on the established folder-alias path.
    """
    ledger = read_ingest_ledger(package)
    receipt_names: set[str] = set()
    for bgcs in ledger.values():
        if not isinstance(bgcs, dict):
            continue
        for record in bgcs.values():
            if isinstance(record, dict):
                name = str(record.get("receipt") or "").strip()
                if name and Path(name).name == name:
                    receipt_names.add(name)

    index: dict[tuple[str, str, str], list[dict]] = {}
    receipt_summaries: list[dict] = []
    receipt_dir = Path(package) / "blastp_ingest_receipts"
    for name in sorted(receipt_names):
        path = receipt_dir / name
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            # No receipt authority is asserted when its bytes are unavailable or invalid.
            # The caller therefore retains the existing folder-name expectation and blocks
            # stale aliases rather than silently treating them as re-keyed.
            continue
        if not isinstance(receipt, dict):
            continue
        if receipt.get("schema") != "mamey_blastp_locus_rekey_ingest_v2":
            continue
        rekey = receipt.get("locus_rekey")
        if not isinstance(rekey, dict) or rekey.get("enabled") is not True:
            raise BlastpDiscoveryError(
                f"BLASTP_REKEY_RECEIPT_HOLD: malformed current re-key receipt {name!r}"
            )
        channel = str(receipt.get("channel") or "").strip()
        admitted = rekey.get("admitted_current_bgcs")
        sources = receipt.get("sources")
        hold_reason_counts = receipt.get("quarantined_by_reason")
        admitted_total = receipt.get("admitted_total")
        quarantined_total = receipt.get("quarantined_total")
        if (channel not in CHANNEL_TROVE or not isinstance(admitted, dict)
                or not isinstance(sources, list) or not isinstance(hold_reason_counts, dict)
                or not isinstance(admitted_total, int) or isinstance(admitted_total, bool)
                or not isinstance(quarantined_total, int) or isinstance(quarantined_total, bool)
                or admitted_total < 0 or quarantined_total < 0
                or any(not isinstance(count, int) or isinstance(count, bool) or count < 0
                       for count in admitted.values())
                or any(not isinstance(count, int) or isinstance(count, bool) or count < 0
                       for count in hold_reason_counts.values())):
            raise BlastpDiscoveryError(
                f"BLASTP_REKEY_RECEIPT_HOLD: malformed current re-key receipt {name!r}"
            )
        admitted_bgcs = {
            str(bgc).strip() for bgc, count in admitted.items()
            if str(bgc).strip() and isinstance(count, int) and not isinstance(count, bool) and count > 0
        }
        hold_reasons = {
            str(reason): int(count) for reason, count in
            hold_reason_counts.items()
            if isinstance(count, int) and not isinstance(count, bool) and count > 0
        }
        receipt_summaries.append({
            "receipt": name,
            "channel": channel,
            "admitted_total": admitted_total,
            "quarantined_total": quarantined_total,
            "hold_reasons": hold_reasons,
        })
        held_by_source: dict[tuple[str, str], dict] = {}
        quarantine_name = str(receipt.get("quarantine_file") or "").strip()
        quarantine_sha = str(receipt.get("quarantine_sha256") or "").strip().lower()
        if (not quarantine_name or Path(quarantine_name).name != quarantine_name
                or not _is_sha256(quarantine_sha)):
            raise BlastpDiscoveryError(
                f"BLASTP_REKEY_RECEIPT_HOLD: malformed quarantine binding in {name!r}"
            )
        quarantine_path = Path(package) / "blastp_quarantine" / quarantine_name
        if _source_sha256(quarantine_path) != quarantine_sha:
            raise BlastpDiscoveryError(
                f"BLASTP_REKEY_RECEIPT_HOLD: quarantine hash disagrees with {name!r}"
            )
        try:
            with quarantine_path.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    source_file = str(row.get("source_file") or "")
                    source_sha = str(row.get("source_file_sha256") or "").lower()
                    resolved = str(row.get("resolved_bgc") or "").strip()
                    held = held_by_source.setdefault(
                        (source_file, source_sha), {"current_bgcs": set(), "hold_reasons": {}}
                    )
                    if resolved and ";" not in resolved:
                        held["current_bgcs"].add(resolved)
                    reason = str(row.get("reason") or "").strip()
                    if reason:
                        held["hold_reasons"][reason] = held["hold_reasons"].get(reason, 0) + 1
        except (OSError, csv.Error) as exc:
            raise BlastpDiscoveryError(
                f"BLASTP_REKEY_RECEIPT_HOLD: cannot read quarantine for {name!r} "
                f"({type(exc).__name__})"
            ) from exc
        for source in sources:
            if not isinstance(source, dict):
                raise BlastpDiscoveryError(
                    f"BLASTP_REKEY_RECEIPT_HOLD: malformed source row in {name!r}"
                )
            source_bgc = str(source.get("bgc") or "").strip()
            source_sha = str(source.get("sha256") or "").strip().lower()
            source_file = str(source.get("file") or "")
            destinations = source.get("destination_bgcs", [])
            if (not source_bgc or not source_file or not _is_sha256(source_sha)
                    or not isinstance(destinations, list)
                    or any(not isinstance(bgc, str) or not bgc.strip() for bgc in destinations)):
                # Existing-overlay provenance rows predate destination_bgcs and cannot match a
                # discovered trove source safely.  Other malformed rows are likewise ignored,
                # preserving the established blocking behavior for that source.
                continue
            admitted_destinations = sorted({bgc.strip() for bgc in destinations})
            if not set(admitted_destinations).issubset(admitted_bgcs):
                raise BlastpDiscoveryError(
                    f"BLASTP_REKEY_RECEIPT_HOLD: source destinations disagree with admitted "
                    f"current BGCs in {name!r}"
                )
            key = (channel, source_bgc.upper(), source_sha)
            held = held_by_source.get((source_file, source_sha), {})
            index.setdefault(key, []).append({
                "receipt": name,
                "admitted_current_bgcs": admitted_destinations,
                "held_current_bgcs": sorted(held.get("current_bgcs", set())),
                "source_hold_reasons": dict(sorted(held.get("hold_reasons", {}).items())),
            })
    return index, receipt_summaries


def availability_expectations(package: str | Path, strain: str,
                              trove_roots: dict) -> tuple[dict, list, list]:
    """Return current-BGC output expectations plus source-folder reconciliation.

    Strict and unmatched sources remain keyed by their folder alias.  A source whose exact bytes
    are named by a current-ledger re-key receipt is keyed by the receipt's admitted current
    destinations.  A fully quarantined re-key source contributes no admitted output expectation;
    its typed holds remain explicit in ``source_reconciliation``.
    """
    discovered = available(strain, trove_roots)
    rekey_index, receipt_summaries = _referenced_rekey_source_index(package)
    expected: dict[str, dict[str, str]] = {}
    reconciliation: list[dict] = []
    for channel, bgcs in sorted(discovered.items()):
        for source_bgc, path in sorted(bgcs.items()):
            source_sha = _source_sha256(path)
            matches = rekey_index.get((channel, source_bgc.upper(), source_sha), [])
            if not matches:
                expected.setdefault(channel, {})[source_bgc] = path
                reconciliation.append({
                    "channel": channel,
                    "source_bgc": source_bgc,
                    "source_path": path,
                    "source_sha256": source_sha,
                    "state": "FOLDER_ALIAS_EXPECTATION",
                    "current_bgcs": [source_bgc],
                    "receipt": "",
                })
                continue
            resolution_sets = {
                (tuple(match["admitted_current_bgcs"]), tuple(match["held_current_bgcs"]))
                for match in matches
            }
            if len(resolution_sets) != 1:
                raise BlastpDiscoveryError(
                    "BLASTP_REKEY_RECEIPT_HOLD: current receipts disagree on destinations for "
                    f"channel {channel!r}, source BGC {source_bgc!r}, SHA-256 {source_sha}"
                )
            admitted_current_bgcs, held_current_bgcs = map(list, next(iter(resolution_sets)))
            current_bgcs = sorted(set(admitted_current_bgcs) | set(held_current_bgcs))
            for current_bgc in admitted_current_bgcs:
                expected.setdefault(channel, {}).setdefault(current_bgc, path)
            if admitted_current_bgcs:
                state = "REKEYED_SOURCE_WITH_ADMITTED_DESTINATIONS"
            elif held_current_bgcs:
                state = "REKEYED_SOURCE_WITH_TYPED_HOLDS_ONLY"
            else:
                state = "REKEYED_SOURCE_WITH_NO_ADMITTED_DESTINATION"
            reconciliation.append({
                "channel": channel,
                "source_bgc": source_bgc,
                "source_path": path,
                "source_sha256": source_sha,
                "state": state,
                "current_bgcs": current_bgcs,
                "admitted_current_bgcs": admitted_current_bgcs,
                "held_current_bgcs": held_current_bgcs,
                "source_hold_reasons": matches[-1]["source_hold_reasons"],
                "receipt": ";".join(sorted({match["receipt"] for match in matches})),
            })
    used_receipts = {
        name for row in reconciliation for name in str(row.get("receipt") or "").split(";") if name
    }
    return expected, reconciliation, [
        summary for summary in receipt_summaries if summary["receipt"] in used_receipts
    ]


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


def _missing_and_reconciliation(package: str | Path, strain: str,
                                trove_roots: dict | None = None,
                                extra_roots=None) -> tuple[list, list, list]:
    """List of (channel, bgc, trove_path) that are available on disk but NOT in the package store."""
    roots = trove_roots if trove_roots is not None else discover_trove_roots(package, extra_roots)
    avail, reconciliation, receipt_summaries = availability_expectations(package, strain, roots)
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
    return missing, reconciliation, receipt_summaries


def missing_ingestions(package: str | Path, strain: str, trove_roots: dict | None = None,
                       extra_roots=None) -> list:
    """Current-BGC output expectations that are available on disk but not ingested."""
    missing, _reconciliation, _receipt_summaries = _missing_and_reconciliation(
        package, strain, trove_roots=trove_roots, extra_roots=extra_roots,
    )
    return missing


def _trove_root_for(missing: list, channel: str) -> str:
    for ch, _bgc, path in missing:
        if ch == channel:
            # trove root = two levels up from <root>/<strain>/<BGC>/<file>
            return str(Path(path).parent.parent.parent)
    return "<trove_root>"


def format_rekey_reconciliation(reconciliation: list[dict]) -> str:
    """Render compact source-folder alias to current-destination alias reconciliation."""
    by_channel: dict[str, list[str]] = {}
    for row in reconciliation:
        if not str(row.get("state", "")).startswith("REKEYED_SOURCE_"):
            continue
        source = str(row.get("source_bgc") or "")
        current = [str(bgc) for bgc in row.get("current_bgcs", [])]
        if current == [source]:
            continue
        held = {str(bgc) for bgc in row.get("held_current_bgcs", [])}
        admitted = {str(bgc) for bgc in row.get("admitted_current_bgcs", [])}
        destination = ",".join(
            f"{bgc} [TYPED_HOLD_ONLY]" if bgc in held and bgc not in admitted else bgc
            for bgc in current
        ) if current else "NO_ADMITTED_DESTINATION"
        by_channel.setdefault(str(row.get("channel") or "unknown"), []).append(
            f"{source} -> {destination}"
        )
    return "\n".join(
        f"BLASTP RE-KEY RECONCILIATION — channel {channel} "
        f"(source folder alias -> current destination alias): {'; '.join(mappings)}"
        for channel, mappings in sorted(by_channel.items())
    )


def format_block_message(strain: str, package: str | Path, missing: list,
                         rekey_channels: set[str] | None = None) -> str:
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
        rekey_arg = " --rekey-by-locus" if ch in (rekey_channels or set()) else ""
        lines.append(f"    fix: python -m mamey ingest-blastp-trove "
                     f"--trove \"{root}\" --package \"{package}\" --channel {ch} --strain {strain}"
                     f"{rekey_arg}")
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
    missing, reconciliation, receipt_summaries = _missing_and_reconciliation(
        package, strain, trove_roots=trove_roots, extra_roots=extra_roots,
    )
    rekey_channels = {
        row["channel"] for row in reconciliation
        if row["state"] == "REKEYED_SOURCE_WITH_ADMITTED_DESTINATIONS"
    }
    reconciliation_message = format_rekey_reconciliation(reconciliation)
    if not missing:
        return {"ok": True, "blocked": False, "missing": [],
                "message": reconciliation_message, "waived": False,
                "source_reconciliation": reconciliation,
                "rekey_receipt_summaries": receipt_summaries}
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
            return {"ok": False, "blocked": True, "missing": missing, "message": msg, "waived": False,
                    "source_reconciliation": reconciliation,
                    "rekey_receipt_summaries": receipt_summaries}
        msg = (f"BLASTP GATE — WAIVED for {strain} ({len(missing)} un-ingested pair(s)): {waiver}. "
               f"Recorded to manifest provenance; deliverables are BLASTP-INCOMPLETE by attestation.")
        if reconciliation_message:
            msg += "\n" + reconciliation_message
        return {"ok": True, "blocked": False, "missing": missing, "message": msg, "waived": True,
                "source_reconciliation": reconciliation,
                "rekey_receipt_summaries": receipt_summaries}
    block_message = format_block_message(strain, package, missing, rekey_channels)
    if reconciliation_message:
        block_message += "\n\n" + reconciliation_message
    return {"ok": False, "blocked": True, "missing": missing,
            "message": block_message,
            "waived": False, "source_reconciliation": reconciliation,
            "rekey_receipt_summaries": receipt_summaries}
