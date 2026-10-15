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
# Bind bundle-local tools even when mamey is already installed.
_root = str(HERE.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)


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
    """Compatibility name: validate the marker and preserve the supplied root exactly."""
    from Bio import Phylo
    tree = Phylo.read(newick_in, "newick")
    tips = [tip.name for tip in tree.get_terminals()]
    if any(not name for name in tips) or len(tips) != len(set(tips)):
        raise ValueError("DUPLICATE_OR_EMPTY_TREE_TIP")
    outgroups = [name for name in tips if marker and marker.lower() in name.lower()]
    if len(outgroups) != 1:
        raise ValueError("OUTGROUP_NOT_UNIQUE")
    with Path(newick_out).open("xb") as handle:
        handle.write(Path(newick_in).read_bytes())
    return outgroups[0]


def _run_layout(run):
    """Locate epa_result.newick, ref.aln.fasta and query.aligned.fasta in a placement run.

    `phylo_place.py all --outdir X` writes everything flat into X/ (and the refpkg beside it), while
    this tool historically required X/report/, X/refpkg/, X/place/. Both layouts are accepted; the
    first existing candidate wins and a missing file is still refused by name (first candidate)."""
    run = Path(run)
    def pick(*rels):
        for rel in rels:
            p = run / rel
            if p.exists():
                return p
        return run / rels[0]
    return (pick("report/epa_result.newick", "epa_result.newick"),
            pick("refpkg/ref.aln.fasta", "ref.aln.fasta", "../refpkg/ref.aln.fasta"),
            pick("place/query.aligned.fasta", "query.aligned.fasta"))


def _admit_run_layout(run):
    return _load("graft_integrity").admit_placement_run(run)

def _length_audit_supplements(out, admission, caller_paths):
    """Export numerical evidence, not an unadvertised second alignment payload."""
    gi = _load("graft_integrity")
    sources = admission["sources"]
    roster = [("receipt", Path(admission["receipt"]))]
    roster += [("output/" + rel, Path(admission["receipt"]).parent / rel)
               for rel in sorted(admission["outputs"])]
    roster += [("source/" + role, Path(path)) for role, path in sources.items()
               if path is not None and role not in {"reference_alignment", "query_alignment"}
               and Path(path).is_file()]
    targets = [(role, path, "F01_lengthaudit_" + hashlib.sha256(role.encode()).hexdigest()[:16] +
                "_" + path.name) for role, path in roster]
    index_name = "F01_lengthaudit_BINDINGS.json"
    # Match the existing exporter's implicit supplements before it can overwrite basenames.
    automatic = []
    for pattern in ("*_ledger.tsv", "*_selection.tsv", "custom_*.tsv", "*_pairings.tsv",
                    "required_closest_type.tsv", "reference_metadata.tsv", "host_metadata.tsv",
                    "genus_roster.tsv", "label_sanity.tsv", "resolution_gaps.tsv",
                    "PANEL_SOURCE_MANIFEST.json", "BUILD_RECEIPT.json"):
        automatic.extend(Path(out).glob(pattern))
    names = {}
    for path in list(caller_paths) + automatic:
        key = path.name.casefold()
        resolved = str(path.resolve())
        if key in names and names[key] != resolved:
            raise ValueError("DISPLAY_SUPPLEMENT_BASENAME_COLLISION")
        names[key] = resolved
    for name in [item[2] for item in targets] + [index_name]:
        if name.casefold() in names or (Path(out) / name).exists():
            raise ValueError("DISPLAY_SUPPLEMENT_BASENAME_COLLISION")
        names[name.casefold()] = name
    index, paths = [], []
    for role, source, name in targets:
        target = Path(out) / name
        gi._copy_exclusive(source, target)
        paths.append(target)
        index.append({"role": role, "export_filename": name, "sha256": digest(target)})
    index_path = Path(out) / index_name
    gi._write_json_exclusive(index_path, {
        "schema": "sapote.placement.length-export.v1", "state": admission["state"],
        "receipt_sha256": admission["receipt_sha256"], "files": index,
        "scope": "Figure replay and numerical evidence; original alignments are not included; full native readmission requires them."})
    return paths + [index_path]

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


def _publication_reference_label(row, include_location=True, detailed=False, type_evidence=None):
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
    # v9.7.444: no deposited isolation source or host -> no source word. reference_source is the joined display text and
    # can hold only the country; classifying that country string used to print 'terrestrial' (other documented).
    if not habitat.strip():
        raw_source = ""
    source = "" if not raw_source.strip() else raw_source.strip() if detailed else _concise_reference_source(raw_source, category)
    source_context = " · ".join(value for value in (source, location) if value)
    proof = (type_evidence or {}).get("roles", {}).get(row["tip"], {})
    role_value = proof.get("role", "")
    type_target = proof.get("type_strain_of", "")
    role_marker = {"type_reference": "type strain", "cultured_non_type_reference": "cultured non-type"}.get(role_value, "")
    if role_value == "type_reference" and type_target:
        role_marker = f"type strain of {type_target}"
    context = "; ".join(value for value in (role_marker, source_context) if value)
    return " ".join(value for value in (stem, f"[{context}]" if context else "", accession) if value)


def _ref_designations(db_path, builder):
    """acc key -> (deposited strain designation, is_type) from the explicitly supplied reference DB (v9.7.444 short labels)."""
    import sqlite3
    from contextlib import closing
    db = Path(db_path).resolve(strict=True)
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as con:
        cols = {row[1] for row in con.execute("PRAGMA table_info(record)")}
        if not {"designation", "is_type"} <= cols:
            raise ValueError("SHORT_LABEL_DB_COLUMNS_MISSING: record needs designation and is_type")
        return {builder._acckey(acc): ((des or "").strip(), is_type == 1)
                for acc, des, is_type in con.execute("SELECT acc_base, designation, is_type FROM record")
                if isinstance(acc, str) and builder._ACC.fullmatch(acc)}


_LABELMAP = {}


def load_labelmap(path):
    """tip -> deposited definition, from the refpkg labelmap.tsv (safe tip name, original FASTA header)."""
    _LABELMAP.clear()
    if Path(path).is_file():
        for line in open(path, encoding="utf-8"):
            tip, _, definition = line.rstrip("\n").partition("\t")
            _LABELMAP[tip] = re.sub(r"^\S+\.\d+\s+", "", definition)


def _short_reference_label(row, designations, builder):
    """'Genus species STRAIN (T)': deposited species + deposited strain designation; (T) only from record.is_type."""
    acc = builder._ref_accession(row["tip"])
    designation, is_type = designations.get(builder._acckey(acc), ("", False)) if acc else ("", False)
    species = (row.get("reference_species") or "").strip()
    if not species:
        raise ValueError(f"SHORT_LABEL_SPECIES_MISSING: {row['tip']}")
    if " sp. " in species:
        # An unnamed deposit already carries its strain from the deposited definition; the DB designation column
        # can be malformed for these (MT829740: "DT2-5-2 16SMicromonosporasp."), so it is not appended.
        designation = ""
    elif not designation:
        # v9.7.444 trial: a reference absent from the 16S DB takes its strain from the deposited definition kept in
        # the refpkg labelmap ("Micromonospora chersina strain PNSB11.3 16S ..."), exactly as deposited.
        m = re.search(r"\bstrain\s+(\S+)", _LABELMAP.get(row["tip"], ""))
        designation = m.group(1).rstrip(",") if m else ""
    return " ".join(x for x in (species, designation, "(T)" if is_type else "") if x)


def display_rows(annotation_rows, label_style="withloc", outgroup_tip=None, type_evidence=None, ref_db=None):
    if label_style not in {"withloc", "noloc", "compact", "publication", "publication-detailed", "publication-noloc", "internal", "short"}:
        raise ValueError("LABEL_STYLE_INVALID")
    output = []
    builder = _load("build_placement_ggtree_inputs")
    designations = _ref_designations(ref_db, builder) if label_style == "short" else {}
    for row in annotation_rows:
        tip = row["tip"]
        if row.get("kind") == "query":
            role, taxon = "query", ""
            if label_style == "short":
                # v9.7.444: 'Genus sp. AS-###' only; the accession goes to the label-accession ledger, not the tip.
                group = (row.get("group") or "").strip()
                label = " ".join(x for x in (f"{group} sp." if group else "", row.get("as_id") or tip) if x)
            elif label_style in {"compact", "publication", "publication-detailed", "publication-noloc", "internal"}:
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
            if label_style != "short" and not label.endswith(builder._display_accession(accession)):
                raise ValueError(f"QUERY_ACCESSION_LABEL_MISMATCH: {tip}")
        else:
            role = "outgroup" if tip == outgroup_tip or (outgroup_tip is None and "outgroup" in tip.lower()) else "reference"
            # Collapse eligibility is species-scoped. A genus-level key can merge
            # different species that share an identical or near-identical 16S segment.
            taxon = row.get("reference_species") or ""
            if label_style == "short":
                label = _short_reference_label(row, designations, builder)
                label = label.replace(" (T)", "")
                if (type_evidence or {}).get("roles", {}).get(tip, {}).get("role") == "type_reference":
                    label += " (T)"
            elif label_style in {"publication", "publication-detailed", "publication-noloc", "internal"}:
                label = _publication_reference_label(
                    row, type_evidence=type_evidence, include_location=label_style != "publication-noloc",
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
            # v9.7.444 trial (owner): short labels do not say "(outgroup)"; the short caption names the outgroup.
        normalized = builder._rect_metadata_row(tip, label, category or "", source or "")
        output.append(dict(tip=tip, label=label, role=role, taxon=taxon,
                           category=normalized[2], category_raw=normalized[4], category_state=normalized[5],
                           source="" if label_style in {"noloc", "publication-noloc"} else normalized[3],
                           reference_role=(type_evidence or {}).get("roles", {}).get(tip, {}).get("role", "") if role != "query" else "",
                           type_strain_of=(type_evidence or {}).get("roles", {}).get(tip, {}).get("type_strain_of", "") if role != "query" else ""))
    from collections import Counter
    # v9.7.444 trial: short labels carry the strain, so a type strain and another deposited strain of the same species
    # are different tips; only an identical drawn label is a duplicate.
    reference_taxa = Counter((row["label"] if label_style == "short" else row["taxon"]) for row in output
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


def type_key(rows):
    """.452: the caption keys '(T), type strain' only when a drawn reference or outgroup label carries (T); a key for
    a marker that is not on the figure would describe something that is not drawn."""
    return "; (T), type strain" if any(" (T)" in (r.get("label") or "") for r in rows
                                       if r.get("role") in ("reference", "outgroup")) else ""


_CAPTION_ACCESSION = re.compile(r"\s*\((?:[A-Z]{1,2}_?\d+(?:\.\d+)?)\)")


def grouped_reference_sentence(collapse_ledger, labels, max_nt, min_cols):
    """.452 (T1): the caption sentence that names grouped references, or '' when nothing was grouped.

    Each drawn representative is named with the strains merged into it ("A (T) (also B (T))"); accessions are left
    to the tip labels and the supplementary grouping table, which keeps every member and the measured bounds.
    """
    path = Path(collapse_ledger)
    if not path.is_file():
        return ""
    groups = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row.get("action") == "COLLAPSED_MEMBER":
                groups.setdefault(row["representative_tip"], []).append(row["tip"])
    if not groups:
        return ""
    clean = lambda tip: _CAPTION_ACCESSION.sub("", labels.get(tip, tip)).strip()
    named = [f"{clean(rep)} (also {'; '.join(clean(m) for m in sorted(members))})" for rep, members in sorted(groups.items())]
    return (f" Reference strains whose 16S sequences differ by at most {max_nt} nt over at least {min_cols} shared sites "
            f"are drawn once: {'; '.join(named)}. The measured bounds and every member are in the supplementary grouping table.")


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
        rows = [row for row in csv.DictReader(handle, delimiter="\t")
                if row.get("selection_mode") != "omitted_no_deposited_metadata"]
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
                          outgroup, args, dropped_count, png, pdf, length_admission=None):
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
    selected_tree = (Path(length_admission["selected"]["restored"]) if length_admission
                     else run / "report" / "epa_result.newick")
    analysis_tips = _tree_tip_count(selected_tree)
    molecule = "NOT_RECORDED"
    if length_admission and length_admission["sources"].get("reference_provenance"):
        provenance = json.loads(Path(length_admission["sources"]["reference_provenance"]).read_text())
        molecule = provenance.get("molecule") or "NOT_RECORDED"
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
        "workflow": f"{molecule} fixed-reference phylogenetic placement and display",
        "length_admission": ({"state": length_admission["state"], "receipt_sha256": length_admission["receipt_sha256"],
                              "selected_tree_sha256": digest(selected_tree), "scope": length_admission["qa"]["scope"]}
                             if length_admission else {"state": "NOT_RECORDED"}),
        "group": args.group,
        "tools_and_roles": [
            {"stage": "reference alignment", "tool": "MAFFT", "operation": f"aligned reference {molecule} sequences"},
            {"stage": "reference inference", "tool": inference_tool, "operation": "inferred the fixed maximum-likelihood reference tree under the recorded model"},
            {"stage": "query alignment", "tool": "MAFFT --add/--addfragments --keeplength", "operation": f"aligned query {molecule} sequences to the unchanged reference columns"},
            {"stage": "placement", "tool": "EPA-ng", "operation": "placed each query on the fixed reference topology by maximum likelihood"},
            {"stage": "graft and assignment", "tool": "gappa", "operation": "generated the grafted tree and placement summaries"},
            {"stage": "display preparation", "tool": "placement_display.py + Biopython", "operation": "retained the source root as a receipt, split the designated outgroup separation for display, joined metadata, checked tip/alignment coverage and prepared labels"},
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
        f"This record describes the fixed-reference {molecule} placement and display route for `{args.group}`. "
        "Counts are read from the bound alignments, trees and ledgers rather than copied from a caption.\n\n"
        f"Numerical length state: `{data['length_admission']['state']}`; receipt: "
        f"`{data['length_admission'].get('receipt_sha256', 'NOT_RECORDED')}`. "
        "This is numerical QA, not biological validation.\n\n"
        "## Steps and software\n\n| Stage | Tool | Operation |\n|---|---|---|\n" + stages +
        "\n\n## Exact counts\n\n| Measure | Count |\n|---|---:|\n" + counts +
        f"\n\nReference deduplication actions: {ref_actions}.\n\n"
        f"Display grouping actions: {display_actions}.\n\n"
        f"The source root was retained; the display splits the designated outgroup separation evenly across the root children; outgroup `{outgroup}`. Reference grouping allowed at most {args.max_nt} "
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
    parser.add_argument("--support-tree", default="", help="Support-labelled reference tree; default is the admitted reference tree. Root and lengths are preserved.")
    parser.add_argument("--host-table", required=True)
    parser.add_argument("--ref-source-db", required=True)
    parser.add_argument("--omit-unsourced", action="store_true",
                        help="v9.7.444 (house rule): omit reference tips with no deposited isolation source (and, for "
                             "styles with a Location strip, no deposited country). Each query takes its next eligible "
                             "reference; omitted tips go to DROPPED_TIPS.tsv (action OMITTED_NO_DEPOSITED_METADATA), "
                             "not to the caption.")
    parser.add_argument("--strip-set", choices=("source-location", "activity"), default="source-location",
                        help="v9.7.444: 'activity' draws the two strips as Candida and MRSA activity from "
                             "--bioassay-table (query tips only; references blank) instead of isolation source and location")
    parser.add_argument("--activity-palette", choices=("default", "calm"), default="default",
                        help=".452: activity strip colours, with --strip-set activity. 'default' is red / dark grey / grey "
                             "(unchanged); 'calm' is dark blue / blue-grey / pale grey (palette field activity_calm)")
    parser.add_argument("--isolate-emphasis", choices=("none", "bold", "bold-band"), default="none",
                        help="v9.7.444: bold the isolate (query) labels; 'bold-band' also shades each isolate row from label through strips")
    parser.add_argument("--caption-note", action="append", default=[], help="v9.7.444 trial: sentence appended to the short caption")
    parser.add_argument("--label-accession", action="store_true", help="v9.7.444 trial: GenBank accession on every short tip label")
    parser.add_argument("--plot-only", action="store_true", help="v9.7.444 trial: also render <prefix>_rect02_plot_only.png/pdf without the caption band")
    parser.add_argument("--support-bootstraps", type=int, default=0,
        help="v9.7.444 trial: replicate count behind the node supports (states them in the short caption)")
    parser.add_argument("--fit-width", action="store_true",
                        help="v9.7.444: size the label room from measured label widths so the tree fills the panel and the strips sit after the labels")
    parser.add_argument("--geography-level", choices=("region", "country"), default="region",
                        help="v9.7.444: 'country' draws the Location strip as the deposited country (palette field "
                             "'country') instead of the continent bin; a country with no palette colour is refused")
    parser.add_argument("--layout", default="", help="Bioassay layout profile; split_candida controls separate species strips.")
    parser.add_argument("--layout-config", default="", help="Override mamey/data/bioassay_layouts.json.")
    parser.add_argument("--bioassay-material", default="Crude extract", help="Material for a canonical long bioassay table.")
    parser.add_argument("--bioassay-table", default="",
                        help="strain-level measured activity table (strain, anti_Candida, anti_MRSA: positive / negative / "
                             "not_tested), passed to the annotation builder; required by --strip-set activity")
    parser.add_argument("--reference-role-table", default="",
                        help="Optional TSV with accession and role columns; adds auditable type/non-type markers to reference labels")
    parser.add_argument("--required-reference-table", default="",
                        help="optional TSV pairing each query strain to a required reference species")
    parser.add_argument("--genus-roster", default="", help="Explicit TSV: strain and genus (or tophit_genus)")
    parser.add_argument("--aux-table", action="append", default=[])
    parser.add_argument("--outgroup-substr", default="outgroup")
    parser.add_argument("--outgroup-registry", default="",
                        help=".452: outgroup registry TSV. When it LOCKS an outgroup for --group (genus level), the strict "
                             "gate exempts the ingroup half of the root edge to that outgroup (long_root=true) and the "
                             "renderer draws that edge shortened, with a break mark and its true length")
    parser.add_argument("--family-level", action="store_true")
    parser.add_argument("--max-nt", type=int, default=1,
                        help="display-only grouping threshold within a monophyletic deposited species (default: 1 nt)")
    parser.add_argument("--min-cols", type=int, default=500)
    parser.add_argument("--neighbors-per-query", type=int, choices=tuple(range(1, 13)), default=3,
                        help="balanced publication display: retain each query's N nearest reference tips (1-12)")
    parser.add_argument("--keep-all-references", action="store_true",
                        help="diagnostic display only: retain the full placement backbone")
    parser.add_argument("--label-style",
                        choices=["withloc", "noloc", "compact", "publication", "publication-detailed", "publication-noloc", "internal", "short"],
                        default="withloc",
                        help="publication styles use the same organism / isolate / source / accession grammar for queries and references")
    parser.add_argument("--print-width", type=float, default=7.2, help="Printed page width in inches; minimum text 8 pt, maximum height 9 inches.")
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
        os.environ["SAPOTE_GEOGRAPHY_LEVEL"] = args.geography_level
        length_admission = _admit_run_layout(run)
        src = Path(length_admission["selected"]["restored"])
        refs = Path(length_admission["sources"]["reference_alignment"])
        queries = Path(length_admission["sources"]["query_alignment"])
        activity = _load("_placement_activity")
        split_activity = args.strip_set == "activity" and activity.profile(args.layout, args.layout_config or None).get("split_candida", False)
        activity_strips = []
        if split_activity:
            pool_candida = activity.profile(args.layout, args.layout_config or None).get("tree_pool_candida", False)
            measured_activity, activity_strips = activity.load(args.bioassay_table, args.bioassay_material, pool=pool_candida)
        builder = _load("build_placement_ggtree_inputs")
        inputs = [src, refs, queries, Path(args.host_table), Path(args.ref_source_db)] + [Path(p) for p in args.aux_table]
        if args.layout:
            inputs.append(Path(args.layout_config) if args.layout_config else HERE.parent/'mamey/data/bioassay_layouts.json')
        if args.required_reference_table:
            inputs.append(Path(args.required_reference_table))
        if args.genus_roster:
            inputs.append(Path(args.genus_roster))
        if args.activity_palette != "default" and args.strip_set != "activity":
            raise ValueError("ACTIVITY_PALETTE_NEEDS_ACTIVITY_STRIPS")
        if args.strip_set == "activity" and not args.bioassay_table:
            raise ValueError("STRIP_SET_ACTIVITY_NEEDS_BIOASSAY_TABLE")
        if args.bioassay_table:
            inputs.append(Path(args.bioassay_table))
        if args.reference_role_table:
            inputs.append(Path(args.reference_role_table))
        inputs += [Path(length_admission["receipt"])]
        inputs += [Path(path) for path in length_admission["sources"].values() if path is not None and Path(path).is_file()]
        inputs += [Path(length_admission["receipt"]).parent / rel for rel in length_admission["outputs"]]
        support = Path(args.support_tree).resolve(strict=True) if args.support_tree else Path(length_admission["sources"]["reference_tree"])
        inputs.append(support)
        hashes = {str(p.resolve()): digest(p) for p in inputs}
        refused_reference_tips(src, builder)
        coverage_check(src, refs, queries)
        organisms = _reference_organisms(args.ref_source_db, builder)
        from tools._placement_report_metadata import reviewed_type_map, jplace_query_names
        from Bio import Phylo
        native_tips = [tip.name for tip in Phylo.read(str(src), "newick").get_terminals()]
        type_evidence = reviewed_type_map([args.reference_role_table] if args.reference_role_table else [],
                                          {tip: tip for tip in native_tips},
                                          query_tips=jplace_query_names(length_admission["sources"]["jplace"]))
        roster_path = args.genus_roster
        if not roster_path:
            with open(args.host_table, newline="", encoding="utf-8-sig") as handle:
                fields = next(csv.reader(handle, delimiter="\t"), [])
            if "strain" in fields and ({"genus", "tophit_genus"} & set(fields)):
                roster_path = args.host_table
        query_ids = {builder._asid(tip) for tip in _read_fasta(queries)}
        genera = {key: value for key, value in _genus_roster(roster_path).items() if key in query_ids}
        ref_genera = builder.reference_genera(src, args.outgroup_substr)
        if len(ref_genera) > 1:
            args.family_level = True
        if args.family_level or not re.fullmatch(r"[A-Z][a-z]+", args.group):
            missing = {builder._asid(tip) for tip in _read_fasta(queries)} - set(genera)
            if missing:
                raise ValueError("MIXED_GENUS_ROSTER_REQUIRED: supply --genus-roster or genus in --host-table")
        out.mkdir(parents=True, exist_ok=False)
        rooted = out / "rooted.nwk"
        outgroup = root_on_outgroup(src, rooted, args.outgroup_substr)
        transferred = out / "supported.nwk"
        _load("transfer_supports_to_graft").transfer_preserving_root(rooted, support, transferred)
        rooted = transferred
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
        if args.bioassay_table and not split_activity:
            command += ["--bioassay-table", args.bioassay_table]
        if args.omit_unsourced:
            command += ["--require-reference-metadata",
                        # Same tip set for both strip sets: eligibility follows the label (which shows the country), not the strips.
                        "source" if args.label_style in {"noloc", "publication-noloc"} else "both"]
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
                proof = type_evidence['roles'].get(row['tip'], {})
                row['reference_role'] = proof.get('role', '')
                row['type_strain_of'] = proof.get('type_strain_of', '')
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
                    # v9.7.444 trial: an unnamed deposit ("Actinomadura sp. NEAU-AAG7") is its own taxon, named
                    # exactly as deposited (genus, "sp.", strain); nothing is inferred.
                    sp_dep = None if species else re.match(r"^([A-Z][a-z]+) sp\.\s+(?:strain\s+)?(\S.*?)\s*$", organism)
                    if sp_dep:
                        # GenBank titles like "Actinomadura sp. S20-30 gene for 16S ribosomal RNA" leave "gene for".
                        _strain = re.sub(r"\s+gene\s+for$", "", sp_dep.group(2), flags=re.I)
                        row['reference_species'] = f"{sp_dep.group(1)} sp. {_strain}"
        load_labelmap(Path(run) / "refpkg" / "labelmap.tsv")
        rows = display_rows(annotations, args.label_style, outgroup, type_evidence=type_evidence, ref_db=args.ref_source_db)
        if args.strip_set == "activity" and not split_activity:
            # Query tips carry measured, strain-level activity; reference and outgroup tips are public comparators
            # and stay blank (they were not part of the screen). Values are mapped, never inferred.
            _act = {"positive": "active (\u226580%)", "negative": "tested, inactive", "not_tested": "not tested", "": "not tested"}
            _by_tip = {a["tip"]: a for a in annotations}
            for row in rows:
                if row["role"] == "query":
                    ann = _by_tip.get(row["tip"], {})
                    row["category"] = _act[(ann.get("anti_candida") or "").strip().lower()]
                    row["source"] = _act[(ann.get("anti_mrsa") or "").strip().lower()]
                    row["category_raw"] = ann.get("anti_candida", "")
                    row["category_state"] = "MEASURED_ACTIVITY"
                else:
                    row["category"] = row["source"] = row["category_raw"] = ""
                    row["category_state"] = "NOT_SCREENED"
        if split_activity:
            rows = activity.decorate(rows, measured_activity, activity_strips, builder._asid)
            # Legacy columns are blank; separate columns are bound in the same receipt.
            for row in rows:
                row['category'] = row['source'] = row['category_raw'] = ''
                row['category_state'] = 'MEASURED_ACTIVITY' if row['role']=='query' else 'NOT_SCREENED'
        if args.label_style == "short":
            # Accessions leave the tip labels, so every drawn label is tied to its accession here (ledger + supplement table).
            _acc_by_tip = {a["tip"]: (a.get("accession") or "").strip() for a in annotations if a.get("kind") == "query"}
            with (out / "LABEL_ACCESSIONS.tsv").open("w", newline="", encoding="utf-8") as handle:
                handle.write("label\trole\taccession\ttip\n")
                for row in rows:
                    acc = _acc_by_tip.get(row["tip"]) if row["role"] == "query" else builder._ref_accession(row["tip"])
                    if not acc:
                        raise ValueError(f"LABEL_ACCESSION_UNBOUND: {row['tip']}")
                    shown = builder._display_accession(acc)
                    if args.label_accession:
                        # v9.7.444 trial: GenBank 16S accession on every tip label (the owner's rule for 16S trees).
                        # versioned accession, as in the S2 and 2B trees (QA review row 26)
                        acc_txt = f"({acc})"
                        m = re.match(r"^(.*?)(\s+\(outgroup\))?$", row["label"])
                        row["label"] = f"{m.group(1)} {acc_txt}{m.group(2) or ''}"
                    handle.write(f"{row['label']}\t{row['role']}\t{shown}\t{row['tip']}\n")
        project_accessions_checked = refuse_project_strains_as_references(rows, args.host_table, builder)
        meta = out / "display_input.tsv"
        with meta.open('w', newline='') as handle:
            writer = _SafeDictWriter(handle, fieldnames=['tip','label','role','taxon','category','category_raw','category_state','source','reference_role','type_strain_of'] + [strip['column'] for strip in activity_strips], delimiter='\t')
            writer.writeheader(); writer.writerows(rows)
        aligned = out / 'display_input.fasta'
        # The complete alignment remains the inference record after the display tree is
        # pruned.  Require every displayed tip, while allowing unused reference rows here.
        sequences = coverage_check(
            f"{prefix}_pruned.nwk", refs, queries, allow_alignment_superset=True
        )
        aligned.write_text(''.join(f'>{tip}\n{seq}\n' for tip, seq in sequences.items()))
        root_variants = _load("placement_root_variants")
        locked_accession = None
        if args.outgroup_registry:
            locked_accession = _load("tree_sanity_check").registry_locked_accession(args.outgroup_registry, args.group)
            if not locked_accession:
                raise ValueError(f"OUTGROUP_REGISTRY_NOT_LOCKED: the registry locks no outgroup for {args.group}")
        gated_tree, root_receipt, root_record = root_variants.prepare(
            f'{prefix}_pruned.nwk', prefix, [outgroup], locked_accession=locked_accession)
        if not root_record["variants"]["display_rooted_split"]["gate_pass"]:
            raise ValueError("DISPLAY_ROOT_STRICT_GATE_FAIL: " + root_record["variants"]["display_rooted_split"]["gate_report"])
        _run([args.python, str(HERE/'collapse_near_identical.py'), str(aligned), str(gated_tree), str(meta),
              '--max-nt', str(args.max_nt), '--min-cols', str(args.min_cols), '--group-label', 'representative', '--out-prefix', str(prefix)])
        collapse_ledger = Path(f'{prefix}_collapse_ledger.tsv')
        dropped_path = out / 'DROPPED_TIPS.tsv'
        dropped_count = write_dropped_tips(collapse_ledger, dropped_path)
        if args.omit_unsourced:
            # Append the references the builder made ineligible, so the trail keeps them (not the caption).
            with open(f"{prefix}_reference_selection.tsv", newline="", encoding="utf-8") as handle:
                omitted = sorted({r["reference_tip"] for r in csv.DictReader(handle, delimiter="\t")
                                  if r.get("selection_mode") == "omitted_no_deposited_metadata"})
            if omitted:
                with dropped_path.open("a", newline="", encoding="utf-8") as handle:
                    for tip in omitted:
                        handle.write(f"{tip}\t\tOMITTED_NO_DEPOSITED_METADATA\t\t\t\t\t{{}}\n")
                dropped_count += len(omitted)
        receipt = f'{prefix}_display_receipt.json'
        outgroup_label = next(row["label"] for row in rows if row["role"] == "outgroup")
        caption = args.methods or f"Outgroup: {outgroup_label}."
        if args.label_style == "short" and not args.methods:
            _nq = sum(r["role"] == "query" for r in rows); _nr = sum(r["role"] == "reference" for r in rows)
            _og = re.sub(r"\s+\(outgroup\)$", "", outgroup_label)
            _ogw = _og.split(" ")
            _og = (f"*{' '.join(_ogw[:2])}* {' '.join(_ogw[2:])}".strip() if len(_ogw) >= 2 and re.match(r"^[a-z]", _ogw[1])
                   and _ogw[1] != "sp." else f"*{_ogw[0]}* {' '.join(_ogw[1:])}".strip())
            caption = (f"16S rRNA gene placement (EPA-ng) of {_nq} {os.environ.get('GG_ISOLATE_SOURCE', '')} *{', '.join(sorted(set(genera.values()))) if genera else args.group}* "
                       f"{'isolate' if _nq == 1 else 'isolates'} (bold) among {_nr} reference strains{type_key(rows)}. "
                       f"Root placed halfway along the designated outgroup separation ({_og}). Scale bar, substitutions per site.")
            if args.label_accession:
                caption += " GenBank 16S accessions in parentheses."
            # a species drawn with two or more type-strain records is named once in the caption (QA review row 25)
            _tsp = {}
            for r in rows:
                if r["role"] == "reference" and "(T)" in r["label"]:
                    _m = re.match(r"^([A-Z][a-z]+ [a-z][a-z-]+)\s", r["label"])   # epithet must end in a space: "sp." is not a species
                    if _m:
                        _tsp.setdefault(_m.group(1), []).append(re.sub(r"^\S+ \S+ ", "", r["label"]).replace(" (T)", ""))
            for _sp, _recs in sorted(_tsp.items()):
                if len(_recs) > 1:
                    _g, _e = _sp.split()
                    caption += (f" *{_g[0]}. {_e}* is represented by {len(_recs)} type-strain 16S records ("
                                + "; ".join(_recs) + ").")
            for _note in args.caption_note:
                caption += " " + _note.strip()
            if args.support_bootstraps:
                _smin = os.environ.get("GG_SUPPORT_MIN", "").strip()
                if not _smin:
                    raise ValueError("SUPPORT_BOOTSTRAPS_NEEDS_GG_SUPPORT_MIN")
                caption += (f" Node numbers, bootstrap support of the reference tree ({args.support_bootstraps:,} "
                            f"RAxML-NG replicates), shown when \u2265{_smin}.")
            if split_activity:
                caption += " Strips: " + "; ".join(strip['label'] for strip in activity_strips) + ". Recorded states are +, −, n.t. and blank; numeric readings, where present, retain the stated threshold. Reference cells are blank."
                if any(strip['label'] == activity.POOLED for strip in activity_strips):
                    caption += (" *Candida*: the strongest state recorded for *C. albicans*, *C. auris* or a reading that did not "
                                "record which of the two was used (a positive in any one is shown as positive).")
            elif args.strip_set == "activity":
                caption += (" Strips: best inhibition of *Candida* sp. (the higher of the *C. albicans* and *C. auris* readings, where some readings did not record which of the two was used) and of MRSA by crude extract or fraction; "
                            "active, \u226580% inhibition. Reference strains were not screened.")
            else:
                caption += " Strips: isolation source and country as deposited; white, no deposited value."
        # .452 (T1 caption half): tip labels no longer carry a grouping suffix, so every caption (any label style, and a
        # caption supplied with --methods) names each drawn representative and the strains merged into it; the measured
        # bounds stay in the grouping table.
        caption += grouped_reference_sentence(f'{prefix}_collapse_ledger.tsv', {r["tip"]: r["label"] for r in rows},
                                              args.max_nt, args.min_cols)
        if not 4 <= args.print_width <= 40:
            raise ValueError("PRINT_WIDTH_INVALID")
        if args.figure_width and args.figure_width != args.print_width:
            raise ValueError("FIGURE_WIDTH_MUST_EQUAL_PRINT_WIDTH")
        if args.figure_width and not 4 <= args.figure_width <= 40:
            raise ValueError("FIGURE_WIDTH_INVALID")
        if args.label_room and not 0.05 <= args.label_room <= 2.0:
            raise ValueError("LABEL_ROOM_INVALID")
        env = dict(os.environ, GG_HEXPAND=os.environ.get("GG_HEXPAND", "0.6"), SAPOTE_PYTHON=args.python, GG_DISPLAY_RECEIPT=receipt,
                   GG_DISPLAY_RECEIPT_SHA256=digest(receipt), GG_GATE_TREE=str(gated_tree),
                   GG_ROOT_POLICY='display_rooted_split', GG_DIAGNOSTIC_ROOTING_RECEIPT='', GG_DIAGNOSTIC_ROOTING_SHA256='',
                   GG_STRIPS=('2' if args.strip_set == 'activity' else '1' if args.label_style in {'noloc', 'publication-noloc'} else '2'),
                   GG_STRIP1_TITLE=('*Candida* sp.' if args.strip_set == 'activity' else 'Isolation source'),
                   GG_STRIP2_TITLE=('MRSA' if args.strip_set == 'activity' else 'Location'),
                   GG_STRIP_KIND=('activity' if args.strip_set == 'activity' else 'source'),
                   GG_ACTIVITY_PALETTE=args.activity_palette,
                   GG_STRIP1_FACE=('italic' if args.strip_set == 'activity' else 'plain'),
                   GG_BLANK_MISSING=('1' if args.omit_unsourced or split_activity else '0'),
                   GG_FOCAL_FACE=('bold' if args.isolate_emphasis in {'bold', 'bold-band'} else os.environ.get('GG_FOCAL_FACE', 'plain')),
                   GG_FOCAL_BAND=('#FFF1C4' if args.isolate_emphasis == 'bold-band' else ''),
                   GG_FIT_LABELS='1', GG_PRINT_WIDTH=str(args.print_width), GG_ACTIVITY_SPEC=json.dumps(activity_strips),
                   GG_CAPTION_MD=('1' if args.label_style == 'short' and not args.methods else ''),
                   GG_ITALIC='1', GG_FIGID=args.fig_id or args.name, GG_METHODS=caption)
        if root_record.get("locked_outgroup_accession"):
            # .452: the gate exempted the ingroup half of the root edge to the LOCKED outgroup; the renderer draws
            # the root edge shortened with a break mark and prints its true length (measured on the gated tree).
            _tsc = _load("tree_sanity_check")
            _stem = _tsc._locked_root_stem(_tsc.parse(str(gated_tree)), [outgroup], root_record["locked_outgroup_accession"])
            if not _stem:
                raise ValueError("LOCKED_ROOT_EDGE_NOT_FOUND")
            env['GG_LOCKED_ROOT_EDGE'] = f"{_stem[0].l + _stem[1].l:.4f}"
            env['GG_LOCKED_ROOT_RECEIPT'] = str(root_receipt)
            env['GG_LOCKED_ROOT_RECEIPT_SHA256'] = digest(root_receipt)
            env['GG_METHODS'] = env['GG_METHODS'] + (f" The root edge to the outgroup ({_stem[0].l + _stem[1].l:.2f} substitutions "
                                                     "per site) is drawn shortened, with a break mark.")
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
        diagnostic_artifacts = {}
        if root_record["long_root_branch"] and not root_record.get("locked_outgroup_accession"):
            diagnostic_prefix = Path(str(prefix) + '_root_as_built_GATE_FAIL_diagnostic')
            original_tree = root_receipt.parent / root_record["variants"]["root_as_built"]["tree"]["path"]
            root_variants.verify_diagnostic(root_receipt, digest(root_receipt), original_tree)
            _run([args.python, str(HERE/'collapse_near_identical.py'), str(aligned), str(original_tree), str(meta),
                  '--max-nt', str(args.max_nt), '--min-cols', str(args.min_cols), '--group-label', 'representative',
                  '--out-prefix', str(diagnostic_prefix)])
            diagnostic_receipt = Path(str(diagnostic_prefix) + '_display_receipt.json')
            diagnostic_env = dict(env, GG_DISPLAY_RECEIPT=str(diagnostic_receipt),
                                  GG_DISPLAY_RECEIPT_SHA256=digest(diagnostic_receipt), GG_GATE_TREE=str(original_tree),
                                  GG_DIAGNOSTIC_ROOTING_RECEIPT=str(root_receipt),
                                  GG_DIAGNOSTIC_ROOTING_SHA256=digest(root_receipt), GG_ROOT_POLICY='root_as_built',
                                  GG_METHODS='Root-as-built variant. Scale bar, substitutions per site.')
            result_diagnostic = _run([args.rscript, str(HERE/'ggtree_rect_heatmap.R'),
                                     str(diagnostic_prefix) + '_display.nwk', str(diagnostic_prefix) + '_display_meta.tsv',
                                     str(diagnostic_prefix) + '_rect02', focal], diagnostic_env)
            (out/'render_root_as_built_diagnostic.log').write_text(result_diagnostic.stdout + result_diagnostic.stderr)
            diagnostic_artifacts = {p.name: digest(p) for p in out.glob(diagnostic_prefix.name + '*') if p.is_file()}
        if args.plot_only:
            # v9.7.444 trial: same tree and strips, no caption band, beside the captioned figure.
            env_po = dict(env, GG_METHODS='')
            r_po = _run([args.rscript, str(HERE/'ggtree_rect_heatmap.R'), f'{prefix}_display.nwk', f'{prefix}_display_meta.tsv', f'{prefix}_rect02_plot_only', focal], env_po)
            (out/'render_plot_only.log').write_text(r_po.stdout+r_po.stderr)
            if any(not p.is_file() or not p.stat().st_size for p in (Path(f'{prefix}_rect02_plot_only.png'), Path(f'{prefix}_rect02_plot_only.pdf'))):
                raise ValueError('PLOT_ONLY_OUTPUT_MISSING')
        if caption and args.label_style == "short":
            (out/'CAPTION.md').write_text(caption + "\n")
        if any(digest(p)!=h for p,h in hashes.items()):
            raise ValueError('DISPLAY_SOURCE_CHANGED')
        methods_ledger, methods_md = write_methods_package(
            run, out, prefix, refs, queries, rows, annotations, outgroup, args,
            dropped_count, png, pdf, length_admission=length_admission)
        final = dict(schema='placement-display-v2', input_hashes=hashes, outgroup_tip=outgroup,
                     dropped_tips=dropped_count, dropped_tips_path=dropped_path.name,
                     dropped_tips_sha256=digest(dropped_path), label_style=args.label_style, display_receipt=receipt,
                     display_receipt_sha256=digest(receipt), png_sha256=digest(png), pdf_sha256=digest(pdf),
                     methods_source='caller_supplied' if args.methods else 'outgroup_from_bound_metadata',
                     methods_ledger=methods_ledger.name, methods_ledger_sha256=digest(methods_ledger),
                     complete_methods=methods_md.name, complete_methods_sha256=digest(methods_md))
        final['length_admission'] = {"state": length_admission["state"], "receipt_sha256": length_admission["receipt_sha256"],
                                     "selected_tree_sha256": digest(src), "scope": length_admission["qa"]["scope"]}
        final['activity_strips'] = activity_strips
        final['bioassay_layout'] = args.layout
        final['render_environment'] = {key: value for key, value in env.items() if key.startswith('GG_') and key not in {'GG_DISPLAY_RECEIPT','GG_DISPLAY_RECEIPT_SHA256','GG_GATE_TREE'} or key == 'SAPOTE_GEOGRAPHY_LEVEL'}
        final['root_policy'] = 'display_rooted_split'
        final['root_variants'] = {'path': root_receipt.name, 'sha256': digest(root_receipt),
                                  'accepted_variant': 'display_rooted_split',
                                  'original_gate_pass': root_record['variants']['root_as_built']['gate_pass'],
                                  'split_gate_pass': True, 'diagnostic_artifacts': diagnostic_artifacts}
        final['page_manifest'] = json.loads(Path(f'{prefix}_rect02.pages.json').read_text())
        final['page_artifacts'] = {item[key]: digest(out/item[key]) for item in final['page_manifest']['pages'] for key in ('pdf','png')}
        final['reviewed_type_evidence'] = type_evidence
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
        caller_supplements = ([Path(args.host_table)] + [Path(p) for p in args.aux_table] +
                              ([Path(args.reference_role_table)] if args.reference_role_table else []) +
                              ([Path(args.required_reference_table)] if args.required_reference_table else []) +
                              ([Path(args.genus_roster)] if args.genus_roster else []))
        if args.bioassay_table:
            caller_supplements.append(Path(args.bioassay_table))
        if args.layout:
            caller_supplements.append(Path(args.layout_config) if args.layout_config else HERE.parent/'mamey/data/bioassay_layouts.json')
        length_supplements = _length_audit_supplements(out, length_admission, caller_supplements)
        for supplement_path in caller_supplements + length_supplements:
            export_command += ['--supplement', str(supplement_path)]
        _run(export_command)
        required_package_files = final['standalone_package_contract']
        missing_package_files = [name for name in required_package_files if not (package/name).is_file()]
        if missing_package_files:
            raise ValueError('STANDALONE_PACKAGE_INCOMPLETE: ' + ','.join(missing_package_files))
        _admit_run_layout(run)
        if any(digest(p) != h for p, h in hashes.items()):
            raise ValueError('DISPLAY_SOURCE_CHANGED')
        _LOG.info(f'DISPLAY_COMPLETE {out}')
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        _LOG.error(f'DISPLAY_REFUSED: {exc}')
        return 2


if __name__ == '__main__':
    sys.exit(main())
