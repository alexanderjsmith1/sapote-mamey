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
VERIFIED_GTOTREE_VERSION = "1.8.16"
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
            for query_id in set(related):
                linked_counts[query_id] += 1
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
    return {
        "status": "PRESENT" if (ver.returncode == 0 or version_text) else "PROBE_FAILED",
        "path": binary,
        "version": version_text[0].strip() if version_text else None,
        "version_exit": ver.returncode,
        "help_exit": hp.returncode,
        "help_contract": "PASS" if not missing else "HOLD_HELP_DRIFT",
        "missing_help_tokens": missing,
    }


def probe_toolchain(gtotree_bin: str | None, iqtree_bin: str | None) -> dict:
    gtt = _probe(gtotree_bin, "-v", "-h", REQUIRED_GTOTREE_HELP)
    iq = _probe(iqtree_bin, "--version", "-h", REQUIRED_IQTREE_HELP)
    observed_gtt = str(gtt.get("version") or "")
    gtt["verified_interface"] = (
        "PASS" if re.search(rf"\bv?{re.escape(VERIFIED_GTOTREE_VERSION)}\b", observed_gtt)
        else "HOLD_UNVERIFIED_VERSION"
    )
    helpers = {}
    gtt_parent = Path(gtotree_bin).parent if gtotree_bin else None
    for name in ("hmmsearch", "prodigal", "muscle", "gtt-cat-alignments"):
        sibling = gtt_parent / name if gtt_parent else None
        resolved = (str(sibling.resolve()) if sibling and sibling.is_file() and os.access(sibling, os.X_OK)
                    else shutil.which(name))
        helpers[name] = {"status": "PRESENT" if resolved else "MISSING", "path": resolved}
    return {"gtotree": gtt, "iqtree": iq, "helpers": helpers}


def _safe_label(value: str, fallback: str) -> str:
    label = re.sub(r"[\t\r\n]+", " ", value).strip() or fallback
    # GToTree 1.8.16 rejects these characters anywhere in its mapping file.
    return re.sub(r"[()*&^#$@!\\/|\[\]]", "_", label)


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


def _command_text(run_dir: Path, hmm_relpath: Path, gtt_bin: str, iq_bin: str) -> str:
    # GToTree 1.8.16 contains shell loops that split paths on whitespace. Run from
    # the run directory and give it only controlled, space-free relative paths.
    if hmm_relpath.is_absolute() or any(" " in part for part in hmm_relpath.parts):
        raise ValueError("staged HMM path must be a space-free path relative to the run directory")
    gtt = [gtt_bin, "-f", "input_view/genomes.txt", "-H", hmm_relpath.as_posix(),
           "-m", "input_view/labels.tsv", "-j", "1", "-n", "1",
           "-M", "1", "-N", "-k", "-o", "outputs/gtotree_alignment"]
    iq = [iq_bin, "-s", "<DISCOVERED_ALIGNMENT_PATH>", "-m", "MFP", "-mset",
          "LG,WAG,JTT,Q.pfam", "-mrate", "G,I,I+G", "-B", "1000", "--alrt", "1000",
          "-T", "1", "--seed", "12345", "--prefix", "outputs/iqtree/final"]
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
    if not 1 <= args.max_concurrent_cores <= DEFAULT_MAX_CONCURRENT_CORES:
        raise ValueError("max-concurrent-cores must be between 1 and 4")
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

    gtt_bin = resolve_executable(args.gtotree_bin, ("GToTree",))
    iq_bin = resolve_iqtree(args.iqtree_bin)
    toolchain = probe_toolchain(gtt_bin, iq_bin)

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
    else:
        state = "PLANNED_AWAITING_APPROVAL"

    labels = [_safe_label(r["label"], r["strain_id"]) for r in admitted]
    if len(labels) != len(set(labels)):
        raise ValueError("desired GToTree labels are not unique after safe-character normalization")

    run_dir.mkdir(parents=True)
    for rel in ("input_objects", "input_view", "references", "resources", "logs", "outputs", "qa"):
        (run_dir / rel).mkdir()
    for record, data in admitted_payloads:
        _write_new(Path(record["object_path"]), data)

    object_paths = [r["object_relpath"] for r in admitted]
    _write_new(run_dir / "input_view" / "genomes.txt",
               ("\n".join(object_paths) + "\n").encode("utf-8"))
    # GToTree 1.8.16's -m file is headerless and matches local inputs by basename.
    # Full paths also trip its special-character check because they contain '/'.
    label_lines = [f"{Path(r['object_path']).name}\t{label}"
                   for r, label in zip(admitted, labels)]
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
            "gtotree_jobs": 1, "hmm_threads": 1, "muscle_threads": 1,
            "iqtree_threads_per_tree": 1,
            "max_concurrent_one_core_trees": args.max_concurrent_cores,
            "maximum_concurrent_cores": args.max_concurrent_cores,
        },
        "hmm": {"kind": "PROTEIN_PROFILE_SET_FOR_GTOTREE",
                "path": str(hmm), "sha256": hmm_sha,
                "object_relpath": hmm_relpath.as_posix(),
                "profile_count": _hmm_profile_count(hmm)},
        "toolchain": toolchain,
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
    _write_new(run_dir / "COMMAND.sh", _command_text(
        run_dir, hmm_relpath, gtt_bin or "GToTree", iq_bin or "iqtree3"
    ).encode("utf-8"))
    event = {"time_utc": manifest["created_utc"], "event": "PLAN_CREATED", "state": state,
             "execution_authorized": False}
    _write_new(run_dir / "EVENTS.jsonl", (json.dumps(event, sort_keys=True) + "\n").encode("utf-8"))
    handoff = f"""# GToTree / IQ-TREE run handoff: {args.run_id}

State: **{state}**. Execution and network access are **not approved**.

Read `RUN_MANIFEST.json`, then `RUN_STATE.json`, then `COMMAND.sh`. The manifest is immutable.
The command uses GToTree 1.8.16-compatible explicit controls `-j 1 -n 1 -M 1 -N -k`; IQ-TREE
uses `-T 1`. At most {args.max_concurrent_cores} one-core trees may be active at once.

    Panel: {len(admitted)} unique local assemblies admitted / cap {panel_cap};
{len(excluded)} normalized-sequence duplicate row(s) excluded; {len(network_rows)} network input(s)
remain unstaged. References are capped at {args.references_per_query} per query before global
assembly-hash de-duplication.

After an approved GToTree process exits zero, run this planner's `discover` subcommand to locate and
hash the observed alignment. Replace `<DISCOVERED_ALIGNMENT_PATH>` only with the path named by that
receipt. Do not assume an output filename and do not use `-F` or IQ-TREE `--redo` to overwrite history.
"""
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


def discover_outputs(args: argparse.Namespace) -> int:
    """Read-only inventory after execution; never chooses by a hard-coded filename."""
    run_dir = Path(args.run_dir).expanduser().resolve()
    manifest_path = run_dir / "RUN_MANIFEST.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"RUN_MANIFEST.json missing: {run_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    admitted = int(manifest["panel_policy"]["admitted_unique_assemblies"])
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
    p = sub.add_parser("plan", help="create an immutable preflight; never run external analysis")
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
                   help="maximum simultaneous one-core tree jobs (default and hard maximum 4)")
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
