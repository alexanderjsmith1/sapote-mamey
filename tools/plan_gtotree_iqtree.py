#!/usr/bin/env python3
"""Plan and inspect a bounded GToTree -> IQ-TREE workflow without running it.

This command may inventory, hash, de-duplicate, and source-preservingly stage local
FASTA data.  It never downloads genomes and never invokes GToTree or IQ-TREE for an
analysis.  The only subprocesses it may run are version/help probes.  A new run is
left in ``PLANNED_AWAITING_APPROVAL`` (or a more specific HOLD state).

Direct panel TSV columns (legacy/manual ingress):
    role, query_id, strain_id, label, assembly_path, archive_member,
    accession, reference_rank, selection_basis

``role`` is QUERY, REFERENCE, or OUTGROUP. ``archive_member`` is required when
``assembly_path`` is an antiSMASH ZIP.  References are associated with their focal
query through ``query_id`` and are ranked numerically.  A local assembly may serve
multiple queries but is stored only once by normalized assembly SHA-256.

The canonical ingress is a directory created by ``build_phylo_panel.py``. The
planner revalidates its selected rows, staged FASTAs, exact-content hashes,
single outgroup, reference links, and receipt before creating the immutable run.
"""
from __future__ import annotations

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible stdout/stderr writer (no bare print(); keeps strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()


SCHEMA_VERSION = "sapote-phylo-plan/1.1"
# Accepted GToTree versions are one shared list (tools/_gtotree_versions.py), read by this planner
# and by gtotree_execution_gate.py; the workflow doc states the same list.
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gtotree_versions import (  # noqa: E402
    ACCEPTED_GTOTREE_VERSIONS_TEXT, GTOTREE_BINS, accepted as _gtotree_accepted,
    probe as _probe_gtotree, command as _gtotree_command, resource_contract as _gtotree_resource_contract,
    safe_tip_label, plan_tip_rows, plan_mapping_rows, mapping_input_keys, GOVERNED_LAYOUT, governed_paths,
)
VERIFIED_GTOTREE_VERSION = "1.8.19"   # production version; kept as a name for callers
DEFAULT_PANEL_CAP = 40
HARD_PANEL_CAP = 60
DEFAULT_REFERENCES_PER_QUERY = 3
HARD_REFERENCES_PER_QUERY = 3
DEFAULT_MAX_CONCURRENT_CORES = 4
REQUIRED_GTOTREE_HELP = ("-f <file>", "-H <file>", "-m <file>", "-N ", "-k ",
                         "-n <int>", "-M <int>", "-j ", "-o <str>")
REQUIRED_IQTREE_HELP = ("-s FILE", "-m MODEL", "-B, --ufboot", "--alrt", "-T NUM|AUTO",
                        "--prefix", "--seed")


@dataclass(frozen=True)
class PanelRow:
    role: str
    query_id: str
    strain_id: str
    label: str
    assembly_path: str
    archive_member: str
    accession: str
    reference_rank: int
    selection_basis: str
    source_row: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _fasta_sequences(data: bytes) -> list[str]:
    """Return non-empty normalized sequences; reject non-FASTA/region-only text."""
    text = data.decode("utf-8", errors="strict")
    seqs: list[str] = []
    current: list[str] = []
    saw_header = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            saw_header = True
            if current:
                seqs.append("".join(current).upper())
                current = []
        else:
            if not saw_header:
                raise ValueError("assembly is not FASTA: sequence text precedes first header")
            seq = re.sub(r"\s+", "", line).upper()
            if not re.fullmatch(r"[ACGTURYSWKMBDHVNX.-]+", seq):
                raise ValueError("assembly FASTA contains non-nucleotide symbols")
            current.append(seq.replace("U", "T").replace(".", "-").replace("-", ""))
    if current:
        seqs.append("".join(current).upper())
    seqs = [s for s in seqs if s]
    if not saw_header or not seqs:
        raise ValueError("assembly FASTA has no non-empty records")
    return seqs


def normalized_assembly_sha256(data: bytes) -> str:
    """Hash sequence content independent of FASTA headers and contig order."""
    h = hashlib.sha256()
    for seq in sorted(_fasta_sequences(data)):
        h.update(str(len(seq)).encode("ascii"))
        h.update(b"\n")
        h.update(seq.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def _read_local_assembly(row: PanelRow) -> tuple[bytes, dict]:
    if not row.assembly_path:
        if row.accession:
            raise FileNotFoundError("NETWORK_REFERENCE_NOT_STAGED")
        raise FileNotFoundError("ASSEMBLY_PATH_MISSING")
    source = Path(row.assembly_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"ASSEMBLY_NOT_FOUND: {source}")
    if source.suffix.lower() == ".zip":
        if not row.archive_member:
            raise ValueError(f"archive_member required for ZIP source: {source}")
        with zipfile.ZipFile(source) as archive:
            try:
                info = archive.getinfo(row.archive_member)
            except KeyError as exc:
                raise FileNotFoundError(
                    f"ARCHIVE_MEMBER_NOT_FOUND: {source}::{row.archive_member}"
                ) from exc
            data = archive.read(info)
        meta = {
            "source_type": "zip_member",
            "source_path": str(source),
            "source_sha256": file_sha256(source),
            "archive_member": row.archive_member,
            "archive_member_bytes": len(data),
            "archive_member_sha256": sha256_bytes(data),
        }
    else:
        if row.archive_member:
            raise ValueError("archive_member supplied for a non-ZIP assembly")
        data = source.read_bytes()
        meta = {
            "source_type": "local_fasta",
            "source_path": str(source),
            "source_sha256": sha256_bytes(data),
            "archive_member": "",
            "archive_member_bytes": len(data),
            "archive_member_sha256": sha256_bytes(data),
        }
    seqs = _fasta_sequences(data)
    meta.update({
        "assembly_bytes": len(data),
        "contigs": len(seqs),
        "assembled_nt": sum(map(len, seqs)),
        "normalized_assembly_sha256": normalized_assembly_sha256(data),
    })
    return data, meta


def read_panel(path: Path) -> list[PanelRow]:
    required = {"role", "query_id", "strain_id", "label", "assembly_path"}
    rows: list[PanelRow] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"panel TSV missing columns: {', '.join(sorted(missing))}")
        for line_no, raw in enumerate(reader, 2):
            role = str(raw.get("role") or "").strip().upper()
            if role not in {"QUERY", "REFERENCE", "OUTGROUP"}:
                raise ValueError(f"row {line_no}: role must be QUERY, REFERENCE, or OUTGROUP")
            qid = str(raw.get("query_id") or "").strip()
            if not qid and role != "OUTGROUP":
                raise ValueError(f"row {line_no}: query_id is required")
            if role == "OUTGROUP":
                qid = "__OUTGROUP__"
            rank_raw = str(raw.get("reference_rank") or "").strip()
            rank = int(rank_raw) if rank_raw else (0 if role == "QUERY" else 999999)
            assembly_raw = str(raw.get("assembly_path") or "").strip()
            if assembly_raw and not Path(assembly_raw).expanduser().is_absolute():
                assembly_raw = str((path.parent / Path(assembly_raw).expanduser()).resolve())
            rows.append(PanelRow(
                role=role,
                query_id=qid,
                strain_id=str(raw.get("strain_id") or "").strip(),
                label=str(raw.get("label") or "").strip(),
                assembly_path=assembly_raw,
                archive_member=str(raw.get("archive_member") or "").strip(),
                accession=str(raw.get("accession") or "").strip(),
                reference_rank=rank,
                selection_basis=str(raw.get("selection_basis") or "").strip(),
                source_row=line_no,
            ))
    if not rows or not any(r.role == "QUERY" for r in rows):
        raise ValueError("panel must contain at least one QUERY row")
    return rows


def select_reference_rows(rows: Iterable[PanelRow], per_query: int) -> list[PanelRow]:
    if not 1 <= per_query <= HARD_REFERENCES_PER_QUERY:
        raise ValueError("references-per-query must be 1, 2, or 3")
    queries = [r for r in rows if r.role == "QUERY"]
    refs = [r for r in rows if r.role == "REFERENCE"]
    outgroups = [r for r in rows if r.role == "OUTGROUP"]
    if len(outgroups) != 1:
        raise ValueError("panel must contain exactly one OUTGROUP row")
    selected = list(queries) + outgroups
    for query in queries:
        ranked = sorted(
            (r for r in refs if r.query_id == query.query_id),
            key=lambda r: (r.reference_rank, r.strain_id, r.source_row),
        )
        selected.extend(ranked[:per_query])
    return selected


def read_prepared_panel(directory: Path, references_per_query: int) -> tuple[list[PanelRow], dict]:
    """Validate and read the canonical output of build_phylo_panel.py."""
    directory = directory.expanduser().resolve()
    selected_path = directory / "panel_selected.tsv"
    receipt_path = directory / "panel_receipt.json"
    genomes_path = directory / "genomes"
    if not selected_path.is_file() or not receipt_path.is_file() or not genomes_path.is_dir():
        raise FileNotFoundError(
            "prepared panel requires panel_selected.tsv, panel_receipt.json, and genomes/"
        )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "PANEL_STAGED_NOT_RUN":
        raise ValueError("prepared panel receipt is not PANEL_STAGED_NOT_RUN")
    required = {
        "candidate_id", "role", "decision", "tree_label", "display_label",
        "content_sha256", "related_query_ids", "selection_basis",
    }
    with selected_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                "prepared panel selected TSV missing columns: " + ", ".join(sorted(missing))
            )
        raw_rows = list(reader)
    if int(receipt.get("selected_count", -1)) != len(raw_rows):
        raise ValueError("prepared panel selected_count does not match panel_selected.tsv")
    target = int(receipt.get("target_total_tips", -1))
    if not 3 <= target <= HARD_PANEL_CAP or target != len(raw_rows):
        raise ValueError("prepared panel target must equal selected rows and be within 3..60")

    query_ids = {
        str(row.get("candidate_id") or "").strip()
        for row in raw_rows if str(row.get("role") or "").strip().upper() == "QUERY"
    }
    if not query_ids:
        raise ValueError("prepared panel has no QUERY row")
    outgroup_count = sum(
        str(row.get("role") or "").strip().upper() == "OUTGROUP" for row in raw_rows
    )
    if outgroup_count != 1:
        raise ValueError("prepared panel must contain exactly one OUTGROUP row")

    linked_counts = {query_id: 0 for query_id in query_ids}
    # Type anchors (build_phylo_panel.py): named type strains outside the related cap, re-checked here.
    anchor_counts = {query_id: 0 for query_id in query_ids}
    rows: list[PanelRow] = []
    observed_labels: set[str] = set()
    for line_no, raw in enumerate(raw_rows, 2):
        candidate_id = str(raw.get("candidate_id") or "").strip()
        role = str(raw.get("role") or "").strip().upper()
        if role not in {"QUERY", "REFERENCE", "OUTGROUP"}:
            raise ValueError(f"prepared panel row {line_no}: invalid role {role!r}")
        if str(raw.get("decision") or "").strip() != "SELECTED":
            raise ValueError(f"prepared panel row {line_no}: decision is not SELECTED")
        tree_label = str(raw.get("tree_label") or "").strip()
        if not tree_label or tree_label in observed_labels:
            raise ValueError(f"prepared panel row {line_no}: empty or duplicate tree_label")
        observed_labels.add(tree_label)
        assembly = genomes_path / f"{tree_label}.fna"
        if not assembly.is_file():
            raise FileNotFoundError(f"prepared panel staged FASTA missing: {assembly}")
        observed_hash = normalized_assembly_sha256(assembly.read_bytes())
        expected_hash = str(raw.get("content_sha256") or "").strip()
        if observed_hash != expected_hash:
            raise ValueError(
                f"prepared panel row {line_no}: staged FASTA content hash mismatch"
            )
        related = [
            token.strip() for token in re.split(r"[,;]", str(raw.get("related_query_ids") or ""))
            if token.strip()
        ]
        if role == "REFERENCE":
            unknown = sorted(set(related) - query_ids)
            if not related or unknown:
                raise ValueError(
                    f"prepared panel row {line_no}: reference link missing/unknown: {unknown}"
                )
            if not str(raw.get("selection_basis") or "").strip():
                raise ValueError(f"prepared panel row {line_no}: reference selection_basis missing")
            anchor = str(raw.get("type_anchor") or "").strip() == "yes"
            if anchor and (
                not re.fullmatch(r"nearest_type_strain_[a-z0-9]+", str(raw.get("selection_basis") or "").strip(), re.I)
                or str(raw.get("assembly_fromtype") or "").strip().lower() != "assembly from type material"
            ):
                raise ValueError(
                    f"prepared panel row {line_no}: type anchor needs nearest_type_strain_<method> "
                    "and assembly_fromtype = assembly from type material"
                )
            for query_id in set(related):
                (anchor_counts if anchor else linked_counts)[query_id] += 1
        query_id = candidate_id if role == "QUERY" else (
            ";".join(related) if role == "REFERENCE" else "__OUTGROUP__"
        )
        priority = str(raw.get("priority") or "").strip()
        rows.append(PanelRow(
            role=role,
            query_id=query_id,
            strain_id=candidate_id,
            label=str(raw.get("display_label") or "").strip() or tree_label,
            assembly_path=str(assembly.resolve()),
            archive_member="",
            accession="",
            reference_rank=int(priority) if priority else (0 if role != "REFERENCE" else 999999),
            selection_basis=str(raw.get("selection_basis") or "").strip(),
            source_row=line_no,
        ))
    over = {query_id: count for query_id, count in linked_counts.items()
            if count > references_per_query}
    if over:
        raise ValueError(f"prepared panel exceeds references-per-query cap: {over}")
    anchor_cap = int(receipt.get("max_type_anchors_per_query", 0))
    over = {q: n for q, n in anchor_counts.items() if n > anchor_cap}
    if over:
        raise ValueError(f"prepared panel exceeds type-anchors-per-query cap {anchor_cap}: {over}")
    over = {q: linked_counts[q] + anchor_counts[q] for q in query_ids if linked_counts[q] + anchor_counts[q] > 4}
    if over:
        raise ValueError(f"prepared panel exceeds 4 comparators per query: {over}")
    return rows, {
        "directory": str(directory),
        "panel_selected": {"path": str(selected_path), "sha256": file_sha256(selected_path)},
        "panel_receipt": {"path": str(receipt_path), "sha256": file_sha256(receipt_path)},
        "target_total_tips": target,
        "selected_count": len(rows),
        "role_counts": {role: sum(row.role == role for row in rows)
                        for role in ("QUERY", "REFERENCE", "OUTGROUP")},
    }


def resolve_executable(explicit: str | None, names: tuple[str, ...]) -> str | None:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        return str(p) if p.is_file() and os.access(p, os.X_OK) else None
    for name in names:
        found = shutil.which(name)
        if found:
            return str(Path(found).resolve())
    return None


def resolve_iqtree(explicit: str | None = None) -> str | None:
    return resolve_executable(explicit, ("iqtree3", "iqtree2", "iqtree"))


def _probe(binary: str | None, version_flag: str, help_flag: str,
           required_help: tuple[str, ...]) -> dict:
    if not binary:
        return {"status": "MISSING", "path": None, "version": None,
                "help_contract": "NOT_CHECKED", "missing_help_tokens": list(required_help)}
    try:
        ver = subprocess.run([binary, version_flag], capture_output=True, text=True,
                             timeout=10, check=False)
        hp = subprocess.run([binary, help_flag], capture_output=True, text=True,
                            timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "PROBE_FAILED", "path": binary, "version": None,
                "error": type(exc).__name__, "help_contract": "NOT_CHECKED",
                "missing_help_tokens": list(required_help)}
    version_text = ((ver.stdout or "") + "\n" + (ver.stderr or "")).strip().splitlines()
    help_text = (hp.stdout or "") + "\n" + (hp.stderr or "")
    missing = [token for token in required_help if token not in help_text]
    probe_ok = ver.returncode == 0 and hp.returncode == 0 and bool(version_text)
    return {
        "status": "PRESENT" if probe_ok else "PROBE_FAILED",
        "path": binary,
        "version": version_text[0].strip() if version_text else None,
        "version_exit": ver.returncode,
        "help_exit": hp.returncode,
        "help_contract": ("PROBE_FAILED" if not probe_ok else
                          "PASS" if not missing else "HOLD_HELP_DRIFT"),
        "missing_help_tokens": missing,
    }


def probe_toolchain(gtotree_bin: str | None, iqtree_bin: str | None, verified_runtime=None) -> dict:
    if verified_runtime is not None:
        from _gtotree_runtime import verified_interface
        gtt = verified_interface(verified_runtime, gtotree_bin)
    else:
        gtt = _probe_gtotree(gtotree_bin)
    iq = _probe(iqtree_bin, "--version", "-h", REQUIRED_IQTREE_HELP)
    helpers = {}
    gtt_parent = Path(gtotree_bin).parent if gtotree_bin else None
    for name in gtt.get("required_helpers", []):
        sibling = gtt_parent / name if gtt_parent else None
        resolved = (str(sibling.resolve()) if sibling and sibling.is_file() and os.access(sibling, os.X_OK)
                    else shutil.which(name))
        helpers[name] = {"status": "PRESENT" if resolved else "MISSING", "path": resolved}
    return {"gtotree": gtt, "iqtree": iq, "helpers": helpers}


def _safe_label(value: str, fallback: str) -> str:
    return safe_tip_label(value, fallback)


def _write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def _write_json_new(path: Path, payload: dict) -> None:
    _write_new(path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _write_tsv_new(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _command_text(run_dir: Path, hmm_relpath: Path, gtt_bin: str, iq_bin: str, threads: int = 1,
                  version_text: str = "1.8.19", hold_reason: str | None = None,
                  governed_argv: list[str] | None = None) -> str:
    # GToTree 1.8 contains shell loops that split paths on whitespace. Run from
    # the run directory and give it only controlled, space-free relative paths.
    if hmm_relpath.is_absolute() or any(" " in part for part in hmm_relpath.parts):
        raise ValueError("staged HMM path must be a space-free path relative to the run directory")
    if hold_reason or not _gtotree_accepted(version_text):
        reason = re.sub(r"[^A-Z0-9_]", "_", hold_reason or "HOLD_UNVERIFIED_VERSION")
        return ("#!/usr/bin/env bash\nset -euo pipefail\n"
                f"# {reason}: no executable recipe was generated.\n"
                "# Re-plan against an admitted version and successful native help contract.\n"
                "exit 2\n")
    if str(version_text).strip() in ("2.0.0", "GToTree v2.0.0"):
        if not governed_argv:
            return "#!/usr/bin/env bash\n# HOLD: governed v2 runner bindings missing\nexit 2\n"
        return ("#!/usr/bin/env bash\nset -euo pipefail\n"
                "# Requires RUN_STATE approved=true and an explicit --approved argument.\n"
                + " ".join(shlex.quote(x) for x in governed_argv)
                + ' --gtotree-runtime-probe-dir "${GTOTREE_RUNTIME_PROBE_DIR:?Set a fresh explicit software-probe directory}" "$@"\n')
    gtt = _gtotree_command(gtt_bin, version_text, "input_view/genomes.txt",
                           hmm_relpath.as_posix(), threads, 1, "outputs/gtotree_alignment",
                           mapping_file="input_view/labels.tsv", keep_alignments=True)
    iq = [iq_bin, "-s", "<DISCOVERED_ALIGNMENT_PATH>", "-m", "MFP", "-mset",
          "LG,WAG,JTT,Q.pfam", "-mrate", "G,I,I+G", "-B", "1000", "--alrt", "1000",
          "-T", str(threads), "--seed", "12345", "--prefix", "outputs/iqtree/final"]
    return (
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        "# GENERATED PLAN ONLY. Do not execute until RUN_STATE records APPROVED.\n"
        "# Run GToTree first. Discover and hash its emitted alignment before replacing the placeholder.\n"
        + "export PATH=" + shlex.quote(str(Path(gtt_bin).parent)) + ":\"$PATH\"\n"
        + "cd " + shlex.quote(str(run_dir)) + "\n"
        + " ".join(shlex.quote(x) for x in gtt) + "\n"
        + "# IQ-TREE (only after exact alignment discovery):\n"
        + " ".join(shlex.quote(x) for x in iq) + "\n"
    )


def _hmm_profile_count(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("NAME") and (len(line) == 4 or line[4].isspace()):
                count += 1
    return count


def plan(args: argparse.Namespace) -> int:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_id):
        raise ValueError("run-id must be a single name beginning with a letter or digit; use letters, digits, _, . or -")
    if not 1 <= args.max_concurrent_cores <= DEFAULT_MAX_CONCURRENT_CORES:
        raise ValueError("max-concurrent-cores must be between 1 and 4")
    threads = int(getattr(args, "threads_per_tree", 1) or 1)
    if not 1 <= threads <= args.max_concurrent_cores:
        raise ValueError("threads-per-tree must be between 1 and max-concurrent-cores (at most 4)")
    concurrent_trees = args.max_concurrent_cores // threads   # the combined core ceiling is unchanged
    prepared_meta: dict | None = None
    if getattr(args, "prepared_panel", None):
        rows, prepared_meta = read_prepared_panel(
            Path(args.prepared_panel), args.references_per_query
        )
        selected = list(rows)
        prepared_cap = int(prepared_meta["target_total_tips"])
        if args.panel_cap is not None and args.panel_cap != prepared_cap:
            raise ValueError(
                f"panel-cap {args.panel_cap} conflicts with prepared panel target {prepared_cap}"
            )
        panel_cap = prepared_cap
        source_panel_path = Path(prepared_meta["panel_selected"]["path"])
    else:
        panel_cap = DEFAULT_PANEL_CAP if args.panel_cap is None else args.panel_cap
        source_panel_path = Path(args.panel_tsv).resolve()
        rows = read_panel(source_panel_path)
        selected = select_reference_rows(rows, args.references_per_query)
    if not 3 <= panel_cap <= HARD_PANEL_CAP:
        raise ValueError(f"panel-cap must be between 3 and {HARD_PANEL_CAP}")
    hmm = Path(args.hmm).expanduser().resolve()
    if not hmm.is_file():
        raise FileNotFoundError(f"HMM target set not found: {hmm}")

    workspace = Path(args.workspace).expanduser().resolve()
    run_dir = workspace / "runs" / args.run_id
    if run_dir.exists():
        raise FileExistsError(f"run already exists; resume it instead of overwriting: {run_dir}")

    gtt_bin = resolve_executable(args.gtotree_bin, GTOTREE_BINS)
    iq_bin = resolve_iqtree(args.iqtree_bin)
    from _gtotree_runtime import runtime_from_arguments, resource_pass
    runtime = runtime_from_arguments(args, gtt_bin)
    toolchain = probe_toolchain(gtt_bin, iq_bin, runtime) if runtime else probe_toolchain(gtt_bin, iq_bin)
    raw_gtt_version = str(toolchain["gtotree"].get("version") or "")
    resource_contract = ((_gtotree_resource_contract(raw_gtt_version, threads, 1,
                             verified_runtime=runtime, cpu_budget=args.max_concurrent_cores) if runtime else
                             _gtotree_resource_contract(raw_gtt_version, threads, 1))
                         if _gtotree_accepted(raw_gtt_version) else
                         {"status": "HOLD_UNVERIFIED_VERSION", "hmm_threads": None})

    if runtime:
        concurrent_trees = args.max_concurrent_cores // resource_contract["phase_requested_threads"]
    admitted: list[dict] = []
    excluded: list[dict] = []
    network_rows: list[dict] = []
    admitted_payloads: list[tuple[dict, bytes]] = []
    seen_normalized: dict[str, dict] = {}
    for row in sorted(selected, key=lambda r: (0 if r.role == "QUERY" else 1,
                                                r.query_id, r.reference_rank, r.source_row)):
        try:
            data, meta = _read_local_assembly(row)
        except FileNotFoundError as exc:
            if str(exc) == "NETWORK_REFERENCE_NOT_STAGED":
                network_rows.append({**asdict(row), "reason": "NETWORK_REFERENCE_NOT_STAGED"})
                continue
            raise
        norm = meta["normalized_assembly_sha256"]
        record = {**asdict(row), **meta}
        if norm in seen_normalized:
            kept = seen_normalized[norm]
            excluded.append({**record, "status": "DUPLICATE_EXCLUDED",
                             "reason": "NORMALIZED_ASSEMBLY_SHA256_DUPLICATE",
                             "kept_strain_id": kept["strain_id"],
                             "kept_role": kept["role"]})
            continue
        seen_normalized[norm] = record
        obj_rel = Path("input_objects") / f"{norm}.fna"
        obj = run_dir / obj_rel
        record.update({"status": "ADMITTED", "object_path": str(obj),
                       "object_relpath": obj_rel.as_posix(), "object_sha256": sha256_bytes(data)})
        admitted.append(record)
        admitted_payloads.append((record, data))

    query_norm = {r["normalized_assembly_sha256"] for r in admitted if r["role"] == "QUERY"}
    duplicate_queries = [r for r in excluded if r["role"] == "QUERY"]
    admitted_outgroups = sum(r["role"] == "OUTGROUP" for r in admitted)
    if len(admitted) > panel_cap:
        state = "HOLD_PANEL_CAP"
    elif duplicate_queries:
        state = "HOLD_DUPLICATE_QUERY_REVIEW"
    elif admitted_outgroups != 1:
        state = "HOLD_OUTGROUP_REVIEW"
    elif network_rows:
        state = "HOLD_NETWORK_APPROVAL"
    elif len(query_norm) == 0:
        state = "HOLD_NO_QUERY_ASSEMBLY"
    elif (toolchain["gtotree"]["status"] != "PRESENT" or
          toolchain["iqtree"]["status"] != "PRESENT" or
          any(v["status"] != "PRESENT" for v in toolchain["helpers"].values())):
        state = "HOLD_TOOL_MISSING"
    elif (toolchain["gtotree"]["help_contract"] != "PASS" or
          toolchain["iqtree"]["help_contract"] != "PASS" or
          toolchain["gtotree"]["verified_interface"] != "PASS"):
        state = "HOLD_TOOL_INTERFACE_REVIEW"
    elif not resource_pass(resource_contract):
        state = "HOLD_RESOURCE_PROFILE"
    else:
        state = "PLANNED_AWAITING_APPROVAL"

    labels = [_safe_label(r["label"], r["strain_id"]) for r in admitted]
    if len(labels) != len(set(labels)):
        raise ValueError("desired GToTree labels are not unique after safe-character normalization")

    if runtime and (any(ch.isspace() for ch in str(run_dir)) or
                    any(any(ch.isspace() or ch in "():,;[]'\"" for ch in label) for label in labels)):
        state = "HOLD_NATIVE_PATH_OR_TIP_LABEL"
    run_dir.mkdir(parents=True)
    for rel in ("input_objects", "input_view", "references", "resources", "logs", "outputs", "qa"):
        (run_dir / rel).mkdir()
    for record, data in admitted_payloads:
        _write_new(Path(record["object_path"]), data)

    object_paths = [r["object_relpath"] for r in admitted]
    _write_new(run_dir / "input_view" / "genomes.txt",
               ("\n".join(object_paths) + "\n").encode("utf-8"))
    if runtime:
        _write_new(run_dir / "input_view" / "genomes_absolute.txt",
                   ("\n".join(r["object_path"] for r in admitted) + "\n").encode("utf-8"))
    # v1 maps basenames; v2 accepts the exact path supplied in its input list.
    # A v2 basename retaining .fna is neither that path nor its extension-free ID.
    # An unrecognized version remains a held, legacy-shaped inspection plan.
    mapping_version = raw_gtt_version if _gtotree_accepted(raw_gtt_version) else "1.8.19"
    mapping_keys = mapping_input_keys([r["object_path"] for r in admitted], mapping_version)
    label_lines = [f"{key}\t{label}" for key, label in zip(mapping_keys, labels)]
    _write_new(run_dir / "input_view" / "labels.tsv",
               ("\n".join(label_lines) + "\n").encode("utf-8"))
    _write_tsv_new(run_dir / "references" / "REFERENCE_SELECTION.tsv",
                   ["role", "query_id", "strain_id", "label", "accession", "reference_rank",
                    "selection_basis", "normalized_assembly_sha256", "status", "reason",
                    "kept_strain_id"],
                   ([r for r in admitted if r["role"] == "REFERENCE"] +
                    [r for r in excluded if r["role"] == "REFERENCE"] + network_rows))
    _write_tsv_new(run_dir / "qa" / "DUPLICATES.tsv",
                   ["role", "query_id", "strain_id", "label", "normalized_assembly_sha256",
                    "status", "reason", "kept_strain_id", "kept_role"], excluded)

    hmm_sha = file_sha256(hmm)
    hmm_relpath = Path("resources") / f"{hmm_sha}.hmm"
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": args.run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "immutable": True,
        "execution_authorized": False,
        "network_authorized": False,
        "source_panel": {"path": str(source_panel_path),
                         "sha256": file_sha256(source_panel_path),
                         "prepared_panel": prepared_meta},
        "panel_policy": {
            "proposed_rows": len(rows), "selected_rows_before_dedup": len(selected),
            "admitted_unique_assemblies": len(admitted), "queries_admitted": len(query_norm),
            "references_per_query": args.references_per_query,
            "panel_cap_selected_by_user": panel_cap, "hard_panel_cap": HARD_PANEL_CAP,
            "duplicate_rows_excluded": len(excluded), "network_rows_not_staged": len(network_rows),
        },
        "resource_policy": {
            "gtotree_jobs": 1, "hmm_threads": resource_contract["hmm_threads"],
            "requested_threads_per_tree": threads, "muscle_threads": threads,
            "gtotree_resource_contract": resource_contract,
            "iqtree_threads_per_tree": threads,
            "phase_requested_threads": resource_contract.get("phase_requested_threads", threads),
            "max_concurrent_trees": (concurrent_trees if resource_pass(resource_contract) else 0),
            "accepted_gtotree_versions": list(ACCEPTED_GTOTREE_VERSIONS_TEXT),
            "maximum_concurrent_cores": args.max_concurrent_cores,
        },
        "hmm": {"kind": "PROTEIN_PROFILE_SET_FOR_GTOTREE",
                "path": str(hmm), "sha256": hmm_sha,
                "object_relpath": hmm_relpath.as_posix(),
                "profile_count": _hmm_profile_count(hmm)},
        "toolchain": toolchain,
        "runtime_binding": ({"manifest": str(Path(args.gtotree_runtime_manifest).absolute()),
                             "manifest_sha256": resource_contract["manifest_sha256"],
                             "environment": str(Path(args.gtotree_runtime_environment).absolute()),
                             "editable_source": str(Path(args.gtotree_runtime_source).absolute())}
                            if runtime else None),
        "execution_layout": dict(GOVERNED_LAYOUT) if runtime else None,
        "assemblies": admitted,
        "excluded_duplicates": excluded,
        "network_inputs_pending": network_rows,
        "claim_ceiling": (
            "Tree placement is within the sampled panel; it is not species delimitation, "
            "formal taxonomy, strain identity, or a biological activity claim."
        ),
    }
    _write_json_new(run_dir / "RUN_MANIFEST.json", manifest)
    state_doc = {
        "schema_version": SCHEMA_VERSION,
        "run_id": args.run_id,
        "state": state,
        "approved": False,
        "network_approved": False,
        "last_event": "PLAN_CREATED",
        "updated_utc": manifest["created_utc"],
        "next_action": "Show the preflight to the user; do not run GToTree before explicit approval.",
    }
    _write_json_new(run_dir / "RUN_STATE.json", state_doc)
    _write_new(run_dir / hmm_relpath, hmm.read_bytes())
    governed_argv = None
    if runtime:
        governed_argv = [sys.executable, str(Path(__file__).with_name("run_planned_tree.py")),
            "--plan-dir", str(run_dir), "--genome-list", str(run_dir / "input_view/genomes_absolute.txt"),
            "--mapping-file", str(run_dir / "input_view/labels.tsv"),
            "--workdir", str(run_dir / "outputs/governed_run"),
            "--hmm", str(run_dir / hmm_relpath), "--hmm-sha256", hmm_sha,
            "--gtotree-bin", str(gtt_bin), "--iqtree-bin", str(iq_bin),
            "--threads", str(threads), "--parallel", "1", "--iqtree-threads", str(threads),
            "--query-tips", ",".join(label for r, label in zip(admitted, labels) if r["role"] == "QUERY"),
            "--outgroup", ",".join(label for r, label in zip(admitted, labels) if r["role"] == "OUTGROUP"),
            "--gtotree-runtime-manifest", str(args.gtotree_runtime_manifest),
            "--gtotree-runtime-environment", str(args.gtotree_runtime_environment),
            "--gtotree-runtime-source", str(args.gtotree_runtime_source),
            "--gtotree-cpu-budget", str(args.max_concurrent_cores),
            "--gtotree-rss-limit", str(args.gtotree_rss_limit),
            "--gtotree-min-disk", str(args.gtotree_min_disk),
            "--gtotree-timeout", str(args.gtotree_timeout)]
    _write_new(run_dir / "COMMAND.sh", _command_text(
        run_dir, hmm_relpath, gtt_bin or "GToTree", iq_bin or "iqtree3", threads,
        version_text=str(toolchain["gtotree"].get("version") or ""),
        hold_reason=None if state == "PLANNED_AWAITING_APPROVAL" else state,
        governed_argv=governed_argv
    ).encode("utf-8"))
    event = {"time_utc": manifest["created_utc"], "event": "PLAN_CREATED", "state": state,
             "execution_authorized": False}
    _write_new(run_dir / "EVENTS.jsonl", (json.dumps(event, sort_keys=True) + "\n").encode("utf-8"))
    handoff = f"""# GToTree / IQ-TREE run handoff: {args.run_id}

State: **{state}**. Execution and network access are **not approved**.

Read `RUN_MANIFEST.json`, then `RUN_STATE.json`, then `COMMAND.sh`. The manifest is immutable.
The shared interface profile is {toolchain["gtotree"].get("profile") or "UNRESOLVED"}.
Resource admission: {resource_contract["status"]}; admitted HMM threads:
{resource_contract["hmm_threads"] if resource_contract["hmm_threads"] is not None else "NOT_BOUND"}.
MUSCLE is requested with `-M {threads}`; IQ-TREE uses `-T {threads}`. GToTree uses
`-j 1 -N -k`, with `-n {threads}` only for 1.8.19. Scheduled concurrent trees:
{manifest["resource_policy"]["max_concurrent_trees"]}; declared total core budget:
{args.max_concurrent_cores}. A held plan has a refusal stub, not an executable recipe.
Accepted version families: {", ".join(ACCEPTED_GTOTREE_VERSIONS_TEXT)}. CLI compatibility
alone does not bind a native v2 HMM CPU profile; `-M` does not control HMM searches.

    Panel: {len(admitted)} unique local assemblies admitted / cap {panel_cap};
{len(excluded)} normalized-sequence duplicate row(s) excluded; {len(network_rows)} network input(s)
remain unstaged. References are capped at {args.references_per_query} per query before global
assembly-hash de-duplication.

After an approved GToTree process exits zero, run this planner's `discover` subcommand to locate and
hash the observed alignment. Replace `<DISCOVERED_ALIGNMENT_PATH>` only with the path named by that
receipt. Do not assume an output filename and do not use `-F` or IQ-TREE `--redo` to overwrite history.
"""
    if runtime:
        handoff = handoff.replace(
            "After an approved GToTree process exits zero, run this planner's `discover` subcommand to locate and\n"
            "hash the observed alignment. Replace `<DISCOVERED_ALIGNMENT_PATH>` only with the path named by that\n"
            "receipt. Do not assume an output filename and do not use `-F` or IQ-TREE `--redo` to overwrite history.",
            "After the governed runner reports DONE, run this planner's `discover --run-dir <this run>` "
            "subcommand. It requires this plan's exact current DONE receipt, unchanged selected inputs, "
            "bound output hashes and the native v2 summary/retained-label roster. Failed or partial runs "
            "remain held; legacy output directories are never substituted. The runner already executes "
            "IQ-TREE and hard QC. Do not use `-F` or IQ-TREE `--redo` to overwrite history.")
    _write_new(run_dir / "HANDOFF.md", handoff.encode("utf-8"))
    pointer = workspace / "CURRENT_RUN.txt"
    if not pointer.exists():
        _write_new(pointer, (args.run_id + "\n").encode("utf-8"))
    emit(json.dumps({"run_dir": str(run_dir), "state": state,
                      "admitted_unique": len(admitted), "panel_cap": panel_cap,
                      "execution_authorized": False}, indent=2))
    return 0 if state == "PLANNED_AWAITING_APPROVAL" else 2


def _count_fasta_records(path: Path) -> int | None:
    try:
        count = 0
        with path.open("r", encoding="utf-8", errors="strict") as handle:
            for line in handle:
                if line.startswith(">"):
                    count += 1
        return count if count else None
    except (OSError, UnicodeError):
        return None


def _retained_count(output_root: Path) -> tuple[int | None, list[str]]:
    summaries = sorted(output_root.rglob("Genomes_summary_info.tsv"))
    if len(summaries) != 1:
        return None, [str(p) for p in summaries]
    with summaries[0].open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle, delimiter="\t"))
    return (max(0, len(rows) - 1), [str(summaries[0])])


def discover_governed_outputs(run_dir, manifest, admitted):
    """Read the exact current governed attempt; never reuse a legacy output tree."""
    receipt = {"schema_version": SCHEMA_VERSION, "run_id": manifest.get("run_id"),
               "discovery_mode": "BOUND_GOVERNED_CURRENT_ATTEMPT", "admitted_taxa": admitted,
               "status": "HOLD_GOVERNED_OUTPUT_BINDING", "alignment_candidates": [],
               "observed_files": [], "genome_summary_paths": [],
               "retained_taxa_from_summary": None}
    try:
        root = Path(run_dir).resolve(strict=True)
        paths = governed_paths(root, manifest.get("execution_layout"))
        workdir, output_root = paths["workdir_relative"], paths["gtotree_relative"]
        status_path = paths["status_relative"]

        def regular(path, inside=None):
            path = Path(path).absolute()
            if (not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)) or
                    (inside is not None and inside not in path.resolve().parents)):
                raise ValueError("GOVERNED_FILE_IDENTITY")
            return path

        def read_json(path):
            path = regular(path, root)
            if path.stat().st_size > 16 * 1024 * 1024:
                raise ValueError("GOVERNED_RECEIPT_SIZE")
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("GOVERNED_RECEIPT_OBJECT")
            return data

        state = read_json(root / "RUN_STATE.json")
        status = read_json(status_path)
        if (status.get("status") != "DONE" or state.get("approved") is not True or
                state.get("run_id") != manifest.get("run_id")):
            raise ValueError("GOVERNED_CURRENT_DONE_REQUIRED")
        expected_binding = {"schema": "GTOTREE_GOVERNED_PLAN_BINDING_V1", "plan_directory": str(root),
            "manifest_sha256": file_sha256(regular(root / "RUN_MANIFEST.json", root)),
            "state_sha256": file_sha256(regular(root / "RUN_STATE.json", root)),
            "genome_list": str(root / "input_view/genomes_absolute.txt"),
            "genome_list_sha256": file_sha256(regular(root / "input_view/genomes_absolute.txt", root)),
            "mapping": str(root / "input_view/labels.tsv"),
            "mapping_sha256": file_sha256(regular(root / "input_view/labels.tsv", root)),
            "workdir": str(workdir)}
        if status.get("plan_binding") != expected_binding:
            raise ValueError("GOVERNED_PLAN_RECEIPT_DRIFT")
        planned = plan_mapping_rows(manifest["assemblies"], manifest["toolchain"]["gtotree"]["version"])
        mapping = [line.split("\t") for line in (root / "input_view/labels.tsv").read_text().splitlines()]
        if mapping != [[name, label] for name, label, role in planned]:
            raise ValueError("GOVERNED_MAPPING_DRIFT")
        selected = (root / "input_view/genomes_absolute.txt").read_text().splitlines()
        if selected != [row["object_path"] for row in manifest["assemblies"]]:
            raise ValueError("GOVERNED_INPUT_ROSTER_DRIFT")
        for row in manifest["assemblies"]:
            if file_sha256(regular(row["object_path"], root)) != row["object_sha256"]:
                raise ValueError("GOVERNED_INPUT_DRIFT")
        binding_path = regular(workdir / "EXECUTION_BINDINGS.json", workdir)
        if file_sha256(binding_path) != status.get("execution_bindings_sha256"):
            raise ValueError("GOVERNED_EXECUTION_RECEIPT_DRIFT")
        bindings = read_json(binding_path)["files"]
        phases = status["execution_phases"]
        if not isinstance(phases, list) or not phases:
            raise ValueError("GOVERNED_PHASE_RECEIPTS_REQUIRED")
        expected_phases = [workdir / ("watch_%03d.json" % number) for number in range(1, len(phases) + 1)]
        if sorted(workdir.glob("watch_*.json")) != expected_phases:
            raise ValueError("GOVERNED_PHASE_ROSTER_DRIFT")
        for recorded, expected_path in zip(phases, expected_phases):
            if Path(recorded["path"]) != expected_path or file_sha256(regular(expected_path, workdir)) != recorded["sha256"]:
                raise ValueError("GOVERNED_PHASE_RECEIPT_DRIFT")
            phase = read_json(expected_path)
            watch = phase["watch"]
            # Advisory signoff may have a scientific nonzero exit; resource loss may not.
            if not isinstance(watch, dict) or watch.get("stop_reason") or watch.get("cleanup_error"):
                raise ValueError("GOVERNED_PHASE_RESOURCE_FAILURE")
            phase_log = regular(expected_path.with_suffix(".log"), workdir)
            if file_sha256(phase_log) != phase["log_sha256"]:
                raise ValueError("GOVERNED_PHASE_LOG_DRIFT")
        versions = regular(workdir / "TOOL_VERSIONS.json", workdir)
        if file_sha256(versions) != status["tool_versions_sha256"]:
            raise ValueError("GOVERNED_TOOL_VERSION_RECEIPT_DRIFT")
        required_inputs = [root / "RUN_MANIFEST.json", root / "RUN_STATE.json",
                           root / "input_view/genomes_absolute.txt", root / "input_view/labels.tsv",
                           *[Path(row["object_path"]) for row in manifest["assemblies"]],
                           Path(status["hmm_file"])]
        for path in required_inputs:
            key = str(path.absolute())
            row = bindings[key]
            if (str(path.resolve(strict=True)) != row["resolved"] or
                    file_sha256(path) != row["sha256"]):
                raise ValueError("GOVERNED_SELECTED_INPUT_DRIFT")
        if file_sha256(Path(status["hmm_file"])) != manifest["hmm"]["sha256"]:
            raise ValueError("GOVERNED_HMM_DRIFT")
        artifacts = status["completed_artifacts"]
        required = ("alignment", "treefile", "contree", "iqtree_log", "genome_summary")
        if not isinstance(artifacts, dict) or any(not isinstance(artifacts.get(k), dict) for k in required):
            raise ValueError("GOVERNED_OUTPUT_RECEIPT_REQUIRED")
        for row in artifacts.values():
            if row is None:
                continue
            path = regular(row["path"], workdir)
            if file_sha256(path) != row["sha256"] or path.stat().st_size != row["bytes"]:
                raise ValueError("GOVERNED_OUTPUT_DRIFT")
        alignment = regular(artifacts["alignment"]["path"], output_root)
        summary = regular(artifacts["genome_summary"]["path"], output_root)
        if summary != output_root / "genomes-summary-info.tsv" or alignment.parent != output_root:
            raise ValueError("GOVERNED_NATIVE_LAYOUT")
        # The reviewed v2 producer emits original genome IDs AND mapped labels for all inputs.
        with summary.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if (not {"genome_id", "label", "in_final_tree"}.issubset(reader.fieldnames or []) or
                    len(reader.fieldnames) != len(set(reader.fieldnames))):
                raise ValueError("GOVERNED_NATIVE_SUMMARY_SCHEMA")
            summary_rows = list(reader)
        expected = {Path(name).stem: (label, role) for name, label, role in planned}
        if (len(summary_rows) != len(expected) or
                {row["genome_id"] for row in summary_rows} != set(expected)):
            raise ValueError("GOVERNED_NATIVE_SUMMARY_ROSTER")
        retained = []
        for row in summary_rows:
            label, role = expected[row["genome_id"]]
            decision = row.get("in_final_tree")
            if row["label"] != label or not isinstance(decision, str) or decision.lower() not in ("yes", "no"):
                raise ValueError("GOVERNED_NATIVE_SUMMARY_IDENTITY")
            if decision.lower() == "yes":
                retained.append(label)
            elif role in ("QUERY", "OUTGROUP"):
                raise ValueError("GOVERNED_REQUIRED_TIP_DROPPED")
        with alignment.open(encoding="utf-8") as handle:
            observed_tips = [line[1:].strip().split()[0] for line in handle if line.startswith(">")]
        if (len(observed_tips) != len(set(observed_tips)) or len(retained) < 2 or
                set(observed_tips) != set(retained)):
            raise ValueError("GOVERNED_ALIGNMENT_MEMBERSHIP")
        candidates, files = [], []
        for path in sorted(p for p in output_root.rglob("*") if p.is_file()):
            regular(path, output_root)
            records = _count_fasta_records(path)
            row = {"path": str(path), "relative_path": path.relative_to(root).as_posix(),
                   "bytes": path.stat().st_size, "sha256": file_sha256(path), "fasta_records": records}
            files.append(row)
            if path.parent == output_root and records == len(retained):
                candidates.append(row)
        receipt.update(retained_taxa_from_summary=len(retained), genome_summary_paths=[str(summary)],
                       observed_files=files, alignment_candidates=candidates,
                       current_status_sha256=file_sha256(status_path),
                       current_execution_bindings_sha256=file_sha256(binding_path),
                       current_plan_binding=expected_binding)
        if len(candidates) != 1:
            receipt["status"] = "HOLD_AMBIGUOUS_ALIGNMENT" if candidates else "HOLD_NO_ALIGNMENT"
        elif candidates[0]["path"] != str(alignment):
            raise ValueError("GOVERNED_ALIGNMENT_RECEIPT_DRIFT")
        else:
            receipt["status"] = "PASS_UNIQUE_ALIGNMENT"
    except (OSError, ValueError, KeyError, TypeError, IndexError, csv.Error) as exc:
        receipt["status"] = "HOLD_GOVERNED_OUTPUT_BINDING"
        receipt["detail"] = type(exc).__name__ + ": " + str(exc)
    return receipt


def discover_outputs(args: argparse.Namespace) -> int:
    """Read-only inventory after execution; never chooses by a hard-coded filename."""
    run_dir = Path(args.run_dir).expanduser().resolve()
    manifest_path = run_dir / "RUN_MANIFEST.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"RUN_MANIFEST.json missing: {run_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    admitted = int(manifest["panel_policy"]["admitted_unique_assemblies"])
    if manifest.get("runtime_binding") is not None:
        receipt = discover_governed_outputs(run_dir, manifest, admitted)
        text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        if args.receipt:
            _write_new(Path(args.receipt).expanduser().resolve(), text.encode("utf-8"))
        emit(text, end="")
        return 0 if receipt["status"] == "PASS_UNIQUE_ALIGNMENT" else 2
    output_root = run_dir / "outputs" / "gtotree_alignment"
    retained, summary_paths = _retained_count(output_root) if output_root.is_dir() else (None, [])
    files: list[dict] = []
    candidates: list[dict] = []
    if output_root.is_dir():
        for path in sorted(p for p in output_root.rglob("*") if p.is_file()):
            rel = path.relative_to(run_dir).as_posix()
            records = _count_fasta_records(path)
            row = {"path": str(path), "relative_path": rel, "bytes": path.stat().st_size,
                   "sha256": file_sha256(path), "fasta_records": records}
            files.append(row)
            # The final concatenation is expected at output-root level. Individual
            # marker alignments under run_files are inventoried but never nominated.
            if (retained is not None and records == retained and retained >= 2 and
                    "individual_alignments" not in path.parts and path.parent == output_root):
                candidates.append(row)
    status = "PASS_UNIQUE_ALIGNMENT" if len(candidates) == 1 else (
        "HOLD_NO_ALIGNMENT" if not candidates else "HOLD_AMBIGUOUS_ALIGNMENT"
    )
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "run_id": manifest.get("run_id"),
        "discovery_mode": "READ_ONLY_CONTENT_INVENTORY",
        "admitted_taxa": admitted,
        "retained_taxa_from_summary": retained,
        "genome_summary_paths": summary_paths,
        "status": status,
        "alignment_candidates": candidates,
        "observed_files": files,
        "note": "Candidate selection uses observed FASTA record count and hashes, not an assumed filename.",
    }
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        out = Path(args.receipt).expanduser().resolve()
        _write_new(out, text.encode("utf-8"))
    emit(text, end="")
    return 0 if status == "PASS_UNIQUE_ALIGNMENT" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan", help="create immutable preflight; explicit runtime-probe options authorize software probes only")
    panel_source = p.add_mutually_exclusive_group(required=True)
    panel_source.add_argument(
        "--prepared-panel",
        help="canonical output directory created by build_phylo_panel.py (recommended)",
    )
    panel_source.add_argument(
        "--panel-tsv",
        help="legacy/manual direct panel TSV; must include exactly one OUTGROUP",
    )
    p.add_argument("--workspace", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--hmm", required=True)
    p.add_argument("--panel-cap", type=int, default=None,
                   help="direct TSV default 40; prepared panel derives its recorded target; hard maximum 60")
    p.add_argument("--references-per-query", type=int, choices=(1, 2, 3),
                   default=DEFAULT_REFERENCES_PER_QUERY,
                   help="ranked reference cap per focal query (default 3)")
    p.add_argument("--max-concurrent-cores", type=int, choices=(1, 2, 3, 4),
                   default=DEFAULT_MAX_CONCURRENT_CORES,
                   help="requested concurrent phase-worker budget (default and hard maximum 4)")
    p.add_argument("--threads-per-tree", type=int, choices=(1, 2, 3, 4), default=1,
                   help="requested threads for one approved tree (v1 GToTree -n/-M, IQ-TREE -T); default 1; "
                        "v2 uses max(2 * jobs, jobs * MUSCLE threads) per tree; this is not total OS/CPU usage")
    from _gtotree_runtime import add_runtime_arguments
    add_runtime_arguments(p)
    p.add_argument("--gtotree-bin", default=None)
    p.add_argument("--iqtree-bin", default=None,
                   help="explicit executable; otherwise resolve iqtree3, iqtree2, then iqtree")
    p.set_defaults(func=plan)
    d = sub.add_parser("discover", help="read-only content-based output inventory after an approved run")
    d.add_argument("--run-dir", required=True)
    d.add_argument("--receipt", default=None,
                   help="optional new receipt path; existing files are never overwritten")
    d.set_defaults(func=discover_outputs)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (ValueError, FileNotFoundError, FileExistsError, json.JSONDecodeError) as exc:
        emit(f"PREFLIGHT_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
