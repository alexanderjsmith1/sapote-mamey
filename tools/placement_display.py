#!/usr/bin/env python3
"""Render a placement run in a new output directory, preserving every input tip.

Metadata comes from explicitly supplied tables. Existing run files and displays are
never overwritten. An accession conflict refuses the display instead of pruning a tip.
"""
import argparse
import csv
# Use the bundle's spreadsheet-safe writers for all tabular exports.
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ModuleNotFoundError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from contextlib import closing
import logging
_LOG = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    # A dynamically loaded sibling may itself import another tool sibling (for
    # example collapse_near_identical imports _console).  The script directory is
    # naturally on sys.path for CLI execution, but not when this module is loaded
    # through importlib in tests or another library consumer.
    inserted = str(HERE) not in sys.path
    if inserted:
        sys.path.insert(0, str(HERE))
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted:
            sys.path.remove(str(HERE))
    return module


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def root_on_outgroup(newick_in, newick_out, marker="outgroup"):
    from Bio import Phylo
    tree = Phylo.read(newick_in, "newick")
    tips = [c.name for c in tree.get_terminals()]
    if any(not n for n in tips) or len(tips) != len(set(tips)):
        raise ValueError("DUPLICATE_OR_EMPTY_TREE_TIP")
    outgroups = [c for c in tree.get_terminals() if marker.lower() in c.name.lower()]
    if not marker or len(outgroups) != 1:
        raise ValueError("OUTGROUP_NOT_UNIQUE")
    tree.root_with_outgroup(outgroups[0])
    Phylo.write(tree, newick_out, "newick")
    return outgroups[0].name


def refused_reference_tips(newick, builder):
    """Validate all reference accessions. No automatic exclusion is supported."""
    from Bio import Phylo
    for tip in Phylo.read(newick, "newick").get_terminals():
        if not builder._is_query(tip.name):
            builder._ref_accession(tip.name)
    return []


def _without_location(row):
    label = row.get("ref_label_noloc")
    if label is None:
        label = row.get("ref_label") or row["tip"]
        habitat = (row.get("reference_habitat") or "").strip()
        country = (row.get("reference_country") or "").strip()
        source = (row.get("reference_source") or "").strip()
        if country:
            candidates = {source, f"{habitat} · {country}", f"{habitat} - {country}", country}
            for old in sorted(candidates, key=len, reverse=True):
                if old and f" [{old}]" in label:
                    label = label.replace(f" [{old}]", f" [{habitat}]" if habitat else "")
                    break
    country = (row.get("reference_country") or "").strip()
    if country and re.search(rf"(?<![A-Za-z]){re.escape(country)}(?![A-Za-z])", label, flags=re.I):
        raise ValueError("LOCATION_LABEL_UNRESOLVED")
    return label


_SHORT_SOURCE = {
    "plant-associated": "plant",
    "soil/rock/sediment": "soil",
    "bryophyte/lichen-associated": "bryophyte/lichen",
    "clinical/animal-associated": "animal/clinical",
    "insect-associated": "insect",
    "fungal-associated": "fungal",
    "built environment": "built environment",
    "other documented": "terrestrial",
    "aquatic": "water",
}

_QUERY_SOURCE_LABELS = {
    "honeybee": "honeybee",
    "bumblebee": "bumblebee",
    "solitary bee": "solitary bee",
    "other bee": "other bee",
    "attine ant": "attine ant",
    "moss": "moss",
    "liverwort": "liverwort",
    "lichen": "lichen",
    "mushroom": "mushroom",
}


def _publication_query_source(raw_host, builder):
    """Preserve controlled project isolation sources on AS query tips."""
    raw = (raw_host or "").strip()
    controlled = _QUERY_SOURCE_LABELS.get(raw.casefold())
    if controlled:
        return controlled
    return builder._phylo_meta.normalize_isolation_source(raw)["display_category"]


def _concise_reference_source(raw, category):
    """Choose one short, evidence-preserving source phrase for a figure label."""
    raw = (raw or "").strip()
    if re.search(r"\b(?:marine|ocean|sea water|seawater|sponge)\b", raw, flags=re.I):
        return "marine"
    if re.search(r"\b(?:stratal waters?|formation water|oil (?:field|reservoir))\b", raw, flags=re.I):
        return "water"
    if re.search(r"\b(?:endophyt|plant|root|stem|leaf|rhizosphere)\b", raw, flags=re.I):
        return "plant"
    if re.search(r"\b(?:fodder|hay|pasture|field)\b", raw, flags=re.I):
        return "terrestrial"
    if re.search(r"\bSolanum\s+tuberosum\b", raw, flags=re.I):
        return "Solanum tuberosum"
    if re.search(r"\b(?:bamboo|Sasa\s+boreali|Sasamorpha\s+borealis)\b", raw, flags=re.I):
        return "bamboo"
    return _SHORT_SOURCE.get(category, category)


def _publication_reference_label(row, include_location=True, detailed=False):
    """Use the same controlled source/location grammar as publication query labels."""
    builder = _load("build_placement_ggtree_inputs")
    original = row.get("ref_label") or row["tip"]
    accession = builder._display_accession(builder._ref_accession(row["tip"]))
    stem = (row.get("reference_species") or "").strip()
    if not stem:
        plain = re.sub(r"\s*\[[^]]*\]", "", original).strip()
        plain = re.sub(r"\s+gene for(?:\s+.*)?$", "", plain, flags=re.I)
        if accession and plain.endswith(accession):
            plain = plain[:-len(accession)].rstrip()
        species = re.match(r"^([A-Z](?:\.|[a-z-]+)\s+[a-z][a-z-]+)(?:\s|$)", plain)
        stem = species.group(1) if species else plain
    habitat = row.get("reference_habitat") or ""
    raw_source = (row.get("reference_source") or habitat).strip()
    category = builder._phylo_meta.normalize_isolation_source(habitat or raw_source)["display_category"]
    location = (builder._phylo_meta.normalize_geography(
        row.get("reference_country") or "")["display_location"] if include_location else "")
    if location:
        raw_source = re.sub(rf"\s*[·-]\s*{re.escape(location)}\s*$", "", raw_source,
                            flags=re.I)
    source = raw_source.strip() if detailed else _concise_reference_source(raw_source, category)
    source_context = " · ".join(value for value in (source, location) if value)
    role_value = (row.get("reference_role") or "").strip().lower()
    type_target = (row.get("type_strain_of") or "").strip()
    role_marker = {"type_reference": "type strain", "cultured_non_type_reference": "cultured non-type"}.get(role_value, "")
    if role_value == "type_reference" and type_target:
        role_marker = f"type strain of {type_target}"
    context = "; ".join(value for value in (role_marker, source_context) if value)
    return " ".join(value for value in (stem, f"[{context}]" if context else "", accession) if value)


def display_rows(annotation_rows, label_style="withloc", outgroup_tip=None):
    if label_style not in {"withloc", "noloc", "compact", "publication", "publication-detailed", "publication-noloc", "internal"}:
        raise ValueError("LABEL_STYLE_INVALID")
    output = []
    builder = _load("build_placement_ggtree_inputs")
    for row in annotation_rows:
        tip = row["tip"]
        if row.get("kind") == "query":
            role, taxon = "query", ""
            if label_style in {"compact", "publication", "publication-detailed", "publication-noloc", "internal"}:
                aid = row.get("as_id") or tip
                group = (row.get("group") or "").strip()
                organism = f"{group} sp." if group else ""
                raw_host = (row.get("host") or "").strip()
                host = (raw_host if label_style == "publication-detailed" else
                        _publication_query_source(raw_host, builder))
                region = builder._phylo_meta.normalize_geography(row.get("region") or "")["display_location"]
                if label_style == "publication-noloc":
                    region = ""
                context = " · ".join(x for x in (host, region) if x)
                if label_style == "internal":
                    experiment = (row.get("experiment_id") or "").strip()
                    sample = (row.get("sample_id") or "").strip()
                    internal = " ".join(x for x in (
                        experiment, f"#{sample}" if sample else "") if x)
                    context = "; ".join(x for x in (context, internal) if x)
                label = " ".join(x for x in (
                    organism, aid, f"[{context}]" if context else "",
                    builder._display_accession(row.get("accession") or ""),
                ) if x)
            else:
                label = row.get(f"label_{label_style}") or row.get("label_full") or tip
            category, source = row.get("host", ""), row.get("region", "")
            accession = (row.get("accession") or "").strip()
            if not accession:
                raise ValueError(f"QUERY_ACCESSION_MISSING: {tip}; supply an accession in the host table or an explicit auxiliary table")
            if not builder._ACC.fullmatch(accession):
                raise ValueError(f"QUERY_ACCESSION_INVALID: {tip}")
            if not label.endswith(builder._display_accession(accession)):
                raise ValueError(f"QUERY_ACCESSION_LABEL_MISMATCH: {tip}")
        else:
            role = "outgroup" if tip == outgroup_tip or (outgroup_tip is None and "outgroup" in tip.lower()) else "reference"
            # Collapse eligibility is species-scoped. A genus-level key can merge
            # different species that share an identical or near-identical 16S segment.
            taxon = row.get("reference_species") or ""
            if label_style in {"publication", "publication-detailed", "publication-noloc", "internal"}:
                label = _publication_reference_label(
                    row, include_location=label_style != "publication-noloc",
                    detailed=label_style == "publication-detailed")
            else:
                label = _without_location(row) if label_style == "noloc" else row.get("ref_label") or tip
            if label_style in {"compact", "publication", "publication-detailed", "publication-noloc", "internal"}:
                group = (row.get("group") or "").strip()
                if group and label.startswith(group[0] + ". "):
                    label = group + label[2:]
            category, source = row.get("reference_habitat", ""), row.get("reference_country", "")
        if role == "outgroup":
            label = re.sub(r"\s+\(outgroup\)\s*$", "", label, flags=re.I)
        normalized = builder._rect_metadata_row(tip, label, category or "", source or "")
        output.append(dict(tip=tip, label=label, role=role, taxon=taxon,
                           category=normalized[2],
                           source="" if label_style in {"noloc", "publication-noloc"} else normalized[3]))
    from collections import Counter
    reference_taxa = Counter(row["taxon"] for row in output
                             if row["role"] == "reference" and row["taxon"])
    duplicates = sorted(taxon for taxon, count in reference_taxa.items() if count > 1)
    if duplicates:
        raise ValueError("DUPLICATE_REFERENCE_SPECIES:" + ",".join(duplicates))
    return output


def refuse_project_strains_as_references(rows, host_table, builder):
    """Keep project-query accessions out of the reference role."""
    project_accessions = {
        builder._acckey(meta.get("acc", ""))
        for meta in builder._load_hosts(host_table).values() if meta.get("acc")
    }
    conflicts = []
    for row in rows:
        if row["role"] != "reference":
            continue
        accession = builder._ref_accession(row["tip"])
        if accession and builder._acckey(accession) in project_accessions:
            conflicts.append(accession)
    if conflicts:
        raise ValueError("PROJECT_STRAIN_IN_REFERENCE_ROLE:" + ",".join(sorted(conflicts)))
    return len(project_accessions)


def write_dropped_tips(collapse_ledger, destination):
    """Write the compatibility dropped-tip ledger, including a header when no tips were dropped."""
    collapse_ledger, destination = Path(collapse_ledger), Path(destination)
    allowed = {"RETAINED", "COLLAPSED_REPRESENTATIVE", "COLLAPSED_MEMBER",
               "OUTGROUP_PRUNED_FOR_DISPLAY"}
    with collapse_ledger.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not {"tip", "representative_tip", "action"} <= set(fields):
            raise ValueError("COLLAPSE_LEDGER_SCHEMA")
        rows = list(reader)
    if any(None in row or row.get("action") not in allowed for row in rows):
        raise ValueError("COLLAPSE_LEDGER_ROW_INVALID")
    if len({row["tip"] for row in rows}) != len(rows):
        raise ValueError("COLLAPSE_LEDGER_DUPLICATE_TIP")
    dropped = [row for row in rows if row["action"] in {"COLLAPSED_MEMBER", "OUTGROUP_PRUNED_FOR_DISPLAY"}]
    with destination.open("x", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(dropped)
    return len(dropped)


def _read_fasta(path):
    return _load("collapse_near_identical").read_fasta(path)


def coverage_check(tree_newick, *fastas, allow_alignment_superset=False):
    from Bio import Phylo
    sequences = {}
    for path in fastas:
        rows = _read_fasta(path)
        if set(rows) & set(sequences):
            raise ValueError("ALIGNMENT_DUPLICATE_TIP")
        sequences.update(rows)
    tips = [c.name for c in Phylo.read(tree_newick, "newick").get_terminals()]
    if len(tips) != len(set(tips)) or any(not tip for tip in tips):
        raise ValueError("DUPLICATE_OR_EMPTY_TREE_TIP")
    covered = set(tips) <= set(sequences)
    if not covered or (not allow_alignment_superset and set(tips) != set(sequences)):
        raise ValueError("ALIGNMENT_COVERAGE")
    if len({len(v) for v in sequences.values()}) != 1:
        raise ValueError("ALIGNMENT_WIDTH")
    return {tip: sequences[tip] for tip in tips}


def _genus_roster(path):
    if not path:
        return {}
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames or []
        genus_field = "genus" if "genus" in fields else "tophit_genus"
        if len(fields) != len(set(fields)) or not {"strain", genus_field} <= set(fields):
            raise ValueError("GENUS_ROSTER_SCHEMA")
        rows = {}
        for row in reader:
            strain, genus = row.get("strain"), row.get(genus_field)
            if None in row or not strain or not genus or not re.fullmatch(r"[A-Z][a-z]+", genus):
                raise ValueError("GENUS_ROSTER_ROW_INVALID")
            key = _load("build_placement_ggtree_inputs")._asid(strain)
            if key in rows:
                raise ValueError("GENUS_ROSTER_DUPLICATE")
            rows[key] = genus
        return rows


def _reference_organisms(path, builder):
    rows = {}
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)) as con:
        columns = {r[1] for r in con.execute("PRAGMA table_info(record)")}
        if "definition" not in columns:
            return rows
        for accession, definition in con.execute("SELECT acc_base, definition FROM record"):
            if not isinstance(accession, str) or not builder._ACC.fullmatch(accession):
                continue
            if not isinstance(definition, str) or any(c in definition for c in "\t\r\n"):
                raise ValueError("REFERENCE_ORGANISM_FIELD_INVALID")
            identity = re.split(r"\s+16S\b", definition, maxsplit=1, flags=re.I)[0].strip().rstrip(",")
            # Some GenBank definitions begin with their own accession (for example
            # ``MW444761.1 Micromonospora ...``).  The display grammar appends the
            # accession separately, so retaining that prefix prints it twice and
            # makes the organism label begin with an identifier instead of a genus.
            identity = re.sub(
                rf"^{re.escape(accession)}(?:\.\d+)?\s+", "", identity,
                count=1, flags=re.I,
            ).strip()
            key = builder._acckey(accession)
            if key in rows and rows[key] != identity:
                raise ValueError("REFERENCE_ORGANISM_CONFLICT")
            rows[key] = identity
    return rows


def _run(command, env=None):
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    if result.returncode:
        raise ValueError(f"DISPLAY_COMMAND_REFUSED: {result.stderr or result.stdout}")
    return result


def _fasta_shape(path):
    rows = _read_fasta(path)
    widths = {len(seq) for seq in rows.values()}
    return len(rows), (next(iter(widths)) if len(widths) == 1 else None)


def _tree_tip_count(path):
    from Bio import Phylo
    return len(Phylo.read(path, "newick").get_terminals())


def _action_counts(path):
    counts = {}
    if not Path(path).is_file():
        return counts
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            action = (row.get("action") or "UNSPECIFIED").strip()
            counts[action] = counts.get(action, 0) + 1
    return counts


def _reference_selection_counts(path):
    if not Path(path).is_file():
        return {"pairings": 0, "queries_with_pairings": 0, "unique_references_selected": 0}
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return {
        "pairings": len(rows),
        "queries_with_pairings": len({row.get("query_tip", "") for row in rows if row.get("query_tip")}),
        "unique_references_selected": len({row.get("reference_tip", "") for row in rows if row.get("reference_tip")}),
    }


def _upstream_methods(run, group):
    path = run / "report" / f"{group}_placement_FIGURE_CAPTION.txt"
    if not path.is_file():
        candidates = sorted((run / "report").glob("*_placement_FIGURE_CAPTION.txt"))
        if len(candidates) == 1:
            path = candidates[0]
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    tools = ""
    match = re.search(r"^Tools:\s*(.+)$", text, flags=re.MULTILINE)
    if match:
        tools = match.group(1).strip()
    return path, text, tools


def write_methods_package(run, out, prefix, refs, queries, rows, annotations,
                          outgroup, args, dropped_count, png, pdf):
    """Write exact workflow counts and full publication methods beside a tree."""
    run, out, prefix = Path(run), Path(out), Path(prefix)
    n_ref, ref_width = _fasta_shape(refs)
    n_query, query_width = _fasta_shape(queries)
    role_counts = {role: sum(row["role"] == role for row in rows)
                   for role in ("query", "reference", "outgroup")}
    collapse = _action_counts(f"{prefix}_collapse_ledger.tsv")
    ref_dedup = _action_counts(run / "refpkg" / "reference_dedup.tsv")
    selection = _reference_selection_counts(f"{prefix}_reference_selection.tsv")
    source_states = {}
    for row in annotations:
        state = (row.get("reference_source_status") or row.get("metadata_status") or "").strip()
        if state:
            source_states[state] = source_states.get(state, 0) + 1
    upstream_path, upstream_text, tool_versions = _upstream_methods(run, args.group)
    final_tips = _tree_tip_count(f"{prefix}_display.nwk")
    analysis_tips = _tree_tip_count(run / "report" / "epa_result.newick")
    raxml_log = run / "refpkg" / "ref.raxml.raxml.log"
    inference_tool = ("RAxML-NG" if raxml_log.is_file() or
                      re.search(r"\braxml-ng\b", tool_versions, flags=re.I)
                      else "maximum-likelihood tree engine")
    inference_details = {}
    if raxml_log.is_file():
        log_text = raxml_log.read_text(encoding="utf-8", errors="replace")
        version = re.search(r"RAxML-NG v\.\s*([^\s]+)", log_text)
        bs = re.search(r"bootstrap replicates:\s*\w+\s*\((\d+)\)", log_text)
        threads = re.search(r"Parallelization scheme:\s*(\d+) worker", log_text)
        inference_details = {
            "tool": inference_tool,
            "version": version.group(1) if version else "UNAVAILABLE",
            "model": (run / "refpkg" / "MODEL").read_text(encoding="utf-8").strip()
                     if (run / "refpkg" / "MODEL").is_file() else "UNAVAILABLE",
            "bootstrap_replicates": int(bs.group(1)) if bs else "UNAVAILABLE",
            "worker_threads": int(threads.group(1)) if threads else "UNAVAILABLE",
        }
    data = {
        "schema": "sapote.placement.methods.v1",
        "workflow": "16S fixed-reference phylogenetic placement and display",
        "group": args.group,
        "tools_and_roles": [
            {"stage": "reference alignment", "tool": "MAFFT", "operation": "aligned reference 16S sequences"},
            {"stage": "reference inference", "tool": inference_tool, "operation": "inferred the fixed maximum-likelihood reference tree under the recorded model"},
            {"stage": "query alignment", "tool": "MAFFT --add/--addfragments --keeplength", "operation": "aligned query 16S sequences to the unchanged reference columns"},
            {"stage": "placement", "tool": "EPA-ng", "operation": "placed each query on the fixed reference topology by maximum likelihood"},
            {"stage": "graft and assignment", "tool": "gappa", "operation": "generated the grafted tree and placement summaries"},
            {"stage": "display preparation", "tool": "placement_display.py + Biopython", "operation": "rooted on the single bound outgroup, joined metadata, checked tip/alignment coverage and prepared labels"},
            {"stage": "display grouping", "tool": "collapse_near_identical.py", "operation": "grouped eligible reference tips at the recorded mismatch and shared-column thresholds; retained all query tips"},
            {"stage": "render", "tool": "R + ggtree + ggplot2", "operation": "rendered the rectangular tree and metadata strips to PDF and PNG"},
        ],
        "counts": {
            "reference_alignment_records": n_ref,
            "query_alignment_records": n_query,
            "alignment_columns": ref_width,
            "analysis_tree_tips": analysis_tips,
            "display_input_tips": len(rows),
            "display_query_tips": role_counts["query"],
            "display_reference_tips": role_counts["reference"],
            "display_outgroup_tips": role_counts["outgroup"],
            "final_display_tips": final_tips,
            "dropped_or_grouped_tips": dropped_count,
            "unique_nonempty_habitat_or_host_categories": len({r["category"] for r in rows if r["category"]}),
            "unique_nonempty_locations": len({r["source"] for r in rows if r["source"]}),
            "query_reference_pairings": selection["pairings"],
            "queries_with_reference_pairings": selection["queries_with_pairings"],
            "unique_references_selected_by_pairing": selection["unique_references_selected"],
        },
        "reference_dedup_actions": ref_dedup,
        "display_grouping_actions": collapse,
        "reference_metadata_states": source_states,
        "reference_inference": inference_details or {"tool": inference_tool},
        "parameters": {
            "outgroup_tip": outgroup,
            "label_style": args.label_style,
            "display_group_max_mismatches": args.max_nt,
            "display_group_min_shared_columns": args.min_cols,
            "figure_width_inches": getattr(args, "figure_width", 0) or "automatic",
            "label_room_tree_depth_fraction": getattr(args, "label_room", 0) or "automatic",
            "reference_and_query_alignment_width_match": ref_width == query_width,
            "reference_selection_mode": ("keep_all_references" if getattr(args, "keep_all_references", False)
                                         else f"{getattr(args, 'neighbors_per_query', 2)}_nearest_per_query"),
        },
        "software_versions_from_upstream_methods": tool_versions or "UNAVAILABLE",
        "upstream_methods_source": str(upstream_path.relative_to(run)) if upstream_text else "UNAVAILABLE",
        "outputs": {"png": png.name, "pdf": pdf.name},
    }
    ledger = out / "METHODS_LEDGER.json"
    ledger.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    stages = "\n".join(
        f"| {item['stage']} | {item['tool']} | {item['operation']} |"
        for item in data["tools_and_roles"])
    counts = "\n".join(f"| {key.replace('_', ' ')} | {value} |" for key, value in data["counts"].items())
    ref_actions = ", ".join(f"{key}={value}" for key, value in sorted(ref_dedup.items())) or "not available"
    display_actions = ", ".join(f"{key}={value}" for key, value in sorted(collapse.items())) or "not available"
    upstream = ("\n\n## Upstream placement caption\n\n" + upstream_text.strip()) if upstream_text else ""
    methods = out / "METHODS.md"
    methods.write_text(
        f"# {args.name} — complete computational methods\n\n"
        f"This record describes the exact fixed-reference 16S placement and display route for `{args.group}`. "
        "Counts are read from the bound alignments, trees and ledgers rather than copied from a caption.\n\n"
        "## Steps and software\n\n| Stage | Tool | Operation |\n|---|---|---|\n" + stages +
        "\n\n## Exact counts\n\n| Measure | Count |\n|---|---:|\n" + counts +
        f"\n\nReference deduplication actions: {ref_actions}.\n\n"
        f"Display grouping actions: {display_actions}.\n\n"
        f"The display was rooted on `{outgroup}`. Reference grouping allowed at most {args.max_nt} "
        f"mismatches over at least {args.min_cols} shared A/C/G/T columns. All query tips were protected. "
        f"Reference selection used `{data['parameters']['reference_selection_mode']}` and its per-query "
        f"assignments are recorded in `{prefix.name}_reference_selection.tsv`. "
        f"The final files are `{pdf.name}` and `{png.name}`.\n\n"
        "## Interpretation boundary\n\nThe tree supports phylogenetic-neighborhood interpretation within the sampled reference panel. "
        "It does not by itself establish species identity, ecological origin, biosynthetic capacity, metabolite production or bioactivity."
        + upstream + "\n",
        encoding="utf-8",
    )
    return ledger, methods


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("run_dir")
    parser.add_argument("--name", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--host-table", required=True)
    parser.add_argument("--ref-source-db", required=True)
    parser.add_argument("--reference-role-table", default="",
                        help="Optional TSV with accession and role columns; adds auditable type/non-type markers to reference labels")
    parser.add_argument("--required-reference-table", default="",
                        help="optional TSV pairing each query strain to a required reference species")
    parser.add_argument("--genus-roster", default="", help="Explicit TSV: strain and genus (or tophit_genus)")
    parser.add_argument("--aux-table", action="append", default=[])
    parser.add_argument("--outgroup-substr", default="outgroup")
    parser.add_argument("--family-level", action="store_true")
    parser.add_argument("--max-nt", type=int, default=1,
                        help="display-only grouping threshold within a monophyletic deposited species (default: 1 nt)")
    parser.add_argument("--min-cols", type=int, default=500)
    parser.add_argument("--neighbors-per-query", type=int, choices=tuple(range(1, 13)), default=2,
                        help="balanced publication display: retain each query's N nearest reference tips (1-12)")
    parser.add_argument("--keep-all-references", action="store_true",
                        help="diagnostic display only: retain the full placement backbone")
    parser.add_argument("--label-style",
                        choices=["withloc", "noloc", "compact", "publication", "publication-detailed", "publication-noloc", "internal"],
                        default="withloc",
                        help="publication styles use the same organism / isolate / source / accession grammar for queries and references")
    parser.add_argument("--figure-width", type=float, default=0.0,
                        help="render width in inches; 0 chooses from tip count and label length")
    parser.add_argument("--label-room", type=float, default=0.0,
                        help="exact horizontal label expansion as a fraction of tree depth (0=automatic; 0.05-2.0)")
    parser.add_argument("--fig-id", default="", help="caption prefix; use '-' to render the supplied caption without a machine-name prefix")
    parser.add_argument("--methods", default="")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--rscript", default="Rscript")
    parser.add_argument("--out", help="New output directory; existing paths refuse")
    args = parser.parse_args(argv)
    try:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.name):
            raise ValueError("DISPLAY_NAME_INVALID")
        run = Path(args.run_dir).resolve(strict=True)
        out = Path(args.out).resolve() if args.out else run / f"display_{args.label_style}"
        if out.exists():
            raise ValueError("OUTPUT_EXISTS")
        builder = _load("build_placement_ggtree_inputs")
        src = run / "report/epa_result.newick"
        refs, queries = run / "refpkg/ref.aln.fasta", run / "place/query.aligned.fasta"
        inputs = [src, refs, queries, Path(args.host_table), Path(args.ref_source_db)] + [Path(p) for p in args.aux_table]
        if args.required_reference_table:
            inputs.append(Path(args.required_reference_table))
        if args.genus_roster:
            inputs.append(Path(args.genus_roster))
        if args.reference_role_table:
            inputs.append(Path(args.reference_role_table))
        hashes = {str(p.resolve()): digest(p) for p in inputs}
        refused_reference_tips(src, builder)
        coverage_check(src, refs, queries)
        genera = _genus_roster(args.genus_roster)
        organisms = _reference_organisms(args.ref_source_db, builder)
        reference_roles = {}
        reference_type_targets = {}
        if args.reference_role_table:
            with open(args.reference_role_table, newline='') as handle:
                for item in csv.DictReader(handle, delimiter='\t'):
                    accession = (item.get('accession') or '').strip()
                    role = (item.get('role') or '').strip()
                    if accession and role:
                        key = builder._acckey(accession)
                        reference_roles[key] = role
                        reference_type_targets[key] = (item.get('type_strain_of') or '').strip()
        out.mkdir(parents=True, exist_ok=False)
        rooted = out / "rooted.nwk"
        outgroup = root_on_outgroup(src, rooted, args.outgroup_substr)
        prefix = out / args.name
        command = [args.python, str(HERE / "build_placement_ggtree_inputs.py"), "--graft", str(rooted),
                   "--group", args.group, "--outgroup-substr", args.outgroup_substr,
                   "--host-table", args.host_table, "--ref-source-db", args.ref_source_db,
                   "--out-prefix", str(prefix)]
        if args.required_reference_table:
            command += ["--required-reference-table", args.required_reference_table]
        command += (["--keep-all-refs"] if args.keep_all_references
                    else ["--neighbors", str(args.neighbors_per_query)])
        if args.family_level:
            command.append("--family-level")
        for path in args.aux_table:
            command += ["--aux-table", path]
        _run(command)
        with open(f"{prefix}_ggtree_annotation.tsv") as handle:
            annotations = list(csv.DictReader(handle, delimiter="\t"))
        for row in annotations:
            if row["kind"] == "query":
                genus = genera.get(row["as_id"])
                if genus:
                    # Publication labels are rebuilt from ``group`` below. Keep
                    # the explicit per-strain genus authoritative there as well
                    # as in the legacy label fields; otherwise a cross-genus
                    # inference cohort name leaks into the visible organism name.
                    row["group"] = genus
                    for key in ("label_withloc", "label_noloc"):
                        row[key] = f"{genus} sp. {row[key]}"
            else:
                acc = builder._ref_accession(row["tip"])
                key = builder._acckey(acc) if acc else ""
                row['reference_role'] = reference_roles.get(key, '')
                row['type_strain_of'] = reference_type_targets.get(key, '')
                organism = organisms.get(key, "")
                if organism:
                    habitat = row["reference_habitat"]
                    source = row["reference_source"]
                    row['ref_label'] = organism + (f" [{source}]" if source else "") + (" " + builder._display_accession(acc) if acc else "")
                    row['ref_label_noloc'] = organism + (f" [{habitat}]" if habitat else "") + (" " + builder._display_accession(acc) if acc else "")
                    match = re.match(r"^([A-Z][a-z]+)\s", organism)
                    row['reference_genus'] = match.group(1) if match else ""
                    species = re.match(r"^([A-Z][a-z-]+\s+[a-z][a-z-]+)(?:\s|$)", organism)
                    row['reference_species'] = species.group(1) if species else ""
        rows = display_rows(annotations, args.label_style, outgroup)
        project_accessions_checked = refuse_project_strains_as_references(rows, args.host_table, builder)
        meta = out / "display_input.tsv"
        with meta.open('w', newline='') as handle:
            writer = _SafeDictWriter(handle, fieldnames=['tip','label','role','taxon','category','source','reference_role','type_strain_of'], delimiter='\t')
            writer.writeheader(); writer.writerows(rows)
        aligned = out / 'display_input.fasta'
        # The complete alignment remains the inference record after the display tree is
        # pruned.  Require every displayed tip, while allowing unused reference rows here.
        sequences = coverage_check(
            f"{prefix}_pruned.nwk", refs, queries, allow_alignment_superset=True
        )
        aligned.write_text(''.join(f'>{tip}\n{seq}\n' for tip, seq in sequences.items()))
        _run([args.python, str(HERE/'collapse_near_identical.py'), str(aligned), f'{prefix}_pruned.nwk', str(meta),
              '--max-nt', str(args.max_nt), '--min-cols', str(args.min_cols), '--group-label', 'representative', '--out-prefix', str(prefix)])
        collapse_ledger = Path(f'{prefix}_collapse_ledger.tsv')
        dropped_path = out / 'DROPPED_TIPS.tsv'
        dropped_count = write_dropped_tips(collapse_ledger, dropped_path)
        receipt = f'{prefix}_display_receipt.json'
        outgroup_label = next(row["label"] for row in rows if row["role"] == "outgroup")
        caption = args.methods or f"Outgroup: {outgroup_label}."
        if args.figure_width and not 8 <= args.figure_width <= 40:
            raise ValueError("FIGURE_WIDTH_INVALID")
        if args.label_room and not 0.05 <= args.label_room <= 2.0:
            raise ValueError("LABEL_ROOM_INVALID")
        env = dict(os.environ, GG_HEXPAND=os.environ.get("GG_HEXPAND", "0.6"), SAPOTE_PYTHON=args.python, GG_DISPLAY_RECEIPT=receipt,
                   GG_DISPLAY_RECEIPT_SHA256=digest(receipt), GG_GATE_TREE=f'{prefix}_pruned.nwk',
                   GG_STRIPS='1' if args.label_style in {'noloc', 'publication-noloc'} else '2', GG_STRIP1_TITLE='Isolation source', GG_STRIP2_TITLE='Location',
                   GG_ITALIC='1', GG_FIGID=args.fig_id or args.name, GG_METHODS=caption)
        if args.figure_width:
            env['GG_FIG_WIDTH'] = str(args.figure_width)
        if args.label_room:
            env['GG_HEXPAND_EXACT'] = str(args.label_room)
        focal = ','.join(row['tip'] for row in rows if row['role']=='query')
        result = _run([args.rscript, str(HERE/'ggtree_rect_heatmap.R'), f'{prefix}_display.nwk', f'{prefix}_display_meta.tsv', f'{prefix}_rect02', focal], env)
        (out/'render.log').write_text(result.stdout+result.stderr)
        png, pdf = Path(f'{prefix}_rect02.png'), Path(f'{prefix}_rect02.pdf')
        if any(not p.is_file() or not p.stat().st_size for p in (png,pdf)):
            raise ValueError('RENDER_OUTPUT_MISSING')
        if any(digest(p)!=h for p,h in hashes.items()):
            raise ValueError('DISPLAY_SOURCE_CHANGED')
        methods_ledger, methods_md = write_methods_package(
            run, out, prefix, refs, queries, rows, annotations, outgroup, args,
            dropped_count, png, pdf)
        final = dict(schema='placement-display-v2', input_hashes=hashes, outgroup_tip=outgroup,
                     dropped_tips=dropped_count, dropped_tips_path=dropped_path.name,
                     dropped_tips_sha256=digest(dropped_path), label_style=args.label_style, display_receipt=receipt,
                     display_receipt_sha256=digest(receipt), png_sha256=digest(png), pdf_sha256=digest(pdf),
                     methods_source='caller_supplied' if args.methods else 'outgroup_from_bound_metadata',
                     methods_ledger=methods_ledger.name, methods_ledger_sha256=digest(methods_ledger),
                     complete_methods=methods_md.name, complete_methods_sha256=digest(methods_md))
        final['project_accessions_checked_against_reference_role'] = project_accessions_checked
        final['reference_selection_mode'] = ('keep_all_references' if args.keep_all_references
                                             else f'{args.neighbors_per_query}_nearest_per_query')
        final['standalone_collaborator_package'] = 'standalone_R_package'
        final['standalone_package_contract'] = [
            f'{args.name}_render_figure.R', f'{args.name}_tree.nwk', f'{args.name}_analysis_tree.nwk',
            f'{args.name}_metadata.tsv', f'{args.name}_aligned_sequences.fasta',
            f'{args.name}_caption.txt', f'{args.name}_methods.md',
            f'{args.name}_clean.png', f'{args.name}_clean.pdf',
            f'{args.name}_rerender_captioned.sh', 'MANIFEST.json',
        ]
        (out/'placement_display_receipt.json').write_text(json.dumps(final,indent=2)+'\n')
        package = out / 'standalone_R_package'
        export_command = [args.python, str(HERE/'export_tree_figure_source_package.py'),
                          str(out), '--out', str(package)]
        for supplement_path in ([Path(args.host_table)] + [Path(p) for p in args.aux_table] +
                                ([Path(args.reference_role_table)] if args.reference_role_table else []) +
                                ([Path(args.required_reference_table)] if args.required_reference_table else []) +
                                ([Path(args.genus_roster)] if args.genus_roster else [])):
            export_command += ['--supplement', str(supplement_path)]
        _run(export_command)
        required_package_files = final['standalone_package_contract']
        missing_package_files = [name for name in required_package_files if not (package/name).is_file()]
        if missing_package_files:
            raise ValueError('STANDALONE_PACKAGE_INCOMPLETE: ' + ','.join(missing_package_files))
        _LOG.info(f'DISPLAY_COMPLETE {out}')
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        _LOG.error(f'DISPLAY_REFUSED: {exc}')
        return 2


if __name__ == '__main__':
    sys.exit(main())
