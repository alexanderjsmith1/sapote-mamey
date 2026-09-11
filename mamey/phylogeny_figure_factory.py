"""Consume existing phylogeny receipts in Figure Factory without a new tree engine."""
from __future__ import annotations
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import html
import importlib.util
import json
import re
import shutil
import tempfile
from pathlib import Path

from .phylo_evidence import PHYLO_EVIDENCE_REQUIRED_KEYS, PHYLO_EVIDENCE_SCHEMA

SCHEMA = "sapote.phylogeny-figure-factory.v1"
TRACK_KIND = "phylogeny_annotation_tracks_v1"
CONCORDANCE_KIND = "phylogeny_shared_tip_concordance_v1"
EVIDENCE_WIDGET_KIND = "phylogeny_evidence_receipt_widget_v1"
CHANNELS = {"BGC_ANNOTATION", "DOMAIN", "CASSETTE", "ANI", "MODEB_JUDGMENT"}
STATES = {"PRESENT", "NOT_RUN", "NOT_PROVIDED", "CONTRADICTED"}


class PhylogenyFigureHold(ValueError):
    """Typed refusal for an unbound or failed phylogeny evidence object."""

    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__(code + ": " + detail)


def hold(code, detail):
    raise PhylogenyFigureHold(code, detail)

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return h.hexdigest()

def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def bound(root, item, name):
    if not isinstance(item, dict): raise ValueError(name + ": descriptor required")
    loc, expected = item.get("logical_locator"), item.get("sha256")
    if not isinstance(loc, str) or not loc or Path(loc).is_absolute() or ".." in Path(loc).parts: raise ValueError(name + ": unsafe locator")
    path = (root / loc).resolve()
    try: path.relative_to(root)
    except ValueError as e: raise ValueError(name + ": escaped root") from e
    if not path.is_file() or not isinstance(expected, str) or len(expected) != 64: raise ValueError(name + ": bound file required")
    if sha256_file(path) != expected: raise ValueError(name + ": SHA-256 mismatch")
    return path

def tsv(path, needed, name):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if reader.fieldnames is None or not needed <= set(reader.fieldnames): raise ValueError(name + ": schema mismatch")
        return list(reader)


def json_object(path, name):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        hold("PHYLO_RECEIPT_INVALID", name + ": unreadable JSON receipt: " + str(exc))
    if not isinstance(value, dict):
        hold("PHYLO_RECEIPT_INVALID", name + ": JSON object required")
    return value


def validate_package_tree_join(value, n_tips, name):
    if not isinstance(value, dict):
        hold("PHYLO_PACKAGE_TREE_JOIN_INVALID", name + ": object required")
    for key in ("crosswalk_sha256", "host_table_sha256"):
        digest = value.get(key)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            hold("PHYLO_PACKAGE_TREE_JOIN_INVALID", name + ": " + key + " must be SHA-256")
    rows = value.get("rows")
    if not isinstance(rows, list) or len(rows) != n_tips:
        hold("PHYLO_PACKAGE_TREE_JOIN_INCOMPLETE", name + ": exactly one row per receipt tip required")
    tree_tips, canonical_tips, package_count, reference_count = set(), set(), 0, 0
    tip_strain_map = {}
    required = {
        "tree_tip", "canonical_tip", "role", "strain_id", "manifest_sha256",
        "host_label", "host_provenance",
    }
    for index, row in enumerate(rows):
        row_name = name + ".rows[" + str(index) + "]"
        if not isinstance(row, dict) or not required <= set(row):
            hold("PHYLO_PACKAGE_TREE_JOIN_INVALID", row_name + ": required fields missing")
        tree_tip = row.get("tree_tip")
        canonical_tip = row.get("canonical_tip")
        strain_id = row.get("strain_id")
        role = row.get("role")
        if not all(isinstance(item, str) and item.strip()
                   for item in (tree_tip, canonical_tip, strain_id)):
            hold("PHYLO_PACKAGE_TREE_JOIN_INVALID", row_name + ": typed identity required")
        if tree_tip in tree_tips or canonical_tip in canonical_tips:
            hold("PHYLO_PACKAGE_TREE_JOIN_INVALID", row_name + ": duplicate tip identity")
        tree_tips.add(tree_tip)
        canonical_tips.add(canonical_tip)
        tip_strain_map[tree_tip] = strain_id
        if role == "PACKAGE":
            digest = row.get("manifest_sha256")
            provenance = row.get("host_provenance")
            if (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
                    or not isinstance(row.get("host_label"), str) or not row["host_label"].strip()
                    or provenance not in {"AUTHORITATIVE_TABLE", "PI_WORD_ONLY"}):
                hold("PHYLO_PACKAGE_TREE_JOIN_INVALID", row_name + ": incomplete package provenance")
            package_count += 1
        elif role == "REFERENCE":
            if (row.get("manifest_sha256") is not None or row.get("host_label") != ""
                    or row.get("host_provenance") != "NOT_APPLICABLE_REFERENCE"):
                hold("PHYLO_PACKAGE_TREE_JOIN_INVALID", row_name + ": invalid reference provenance")
            reference_count += 1
        else:
            hold("PHYLO_PACKAGE_TREE_JOIN_INVALID", row_name + ": role must be PACKAGE or REFERENCE")
    return {
        "crosswalk_sha256": value["crosswalk_sha256"],
        "host_table_sha256": value["host_table_sha256"],
        "host_table_sheet": value.get("host_table_sheet"),
        "row_count": len(rows),
        "package_count": package_count,
        "reference_count": reference_count,
        "tree_tips": sorted(tree_tips),
        "tip_strain_map": tip_strain_map,
    }


def validate_signoff(payload, tree_path, alignment_path, outgroup_tip, name):
    missing = sorted(PHYLO_EVIDENCE_REQUIRED_KEYS - set(payload))
    if payload.get("schema_version") != PHYLO_EVIDENCE_SCHEMA or missing:
        hold("PHYLO_RECEIPT_INVALID", name + ": schema mismatch; missing=" + repr(missing))
    status = payload.get("status", payload.get("state"))
    if status != "PASS":
        hold("PHYLO_SIGNOFF_HOLD", name + ": explicit PASS required; observed " + repr(status))
    expected = {
        "tree_sha256": sha256_file(tree_path),
        "alignment_sha256": sha256_file(alignment_path),
        "outgroup_tip": outgroup_tip,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            hold("PHYLO_SIGNOFF_MISMATCH", name + ": " + key + " does not match admitted evidence")
    checks = payload.get("checks", [])
    if not isinstance(checks, list):
        hold("PHYLO_RECEIPT_INVALID", name + ": checks must be a list when present")
    blockers = [
        str(check.get("check_id", check.get("check", "UNKNOWN")))
        for check in checks
        if isinstance(check, dict) and check.get("status") in {"FAIL", "HOLD"}
    ]
    if blockers:
        hold("PHYLO_SIGNOFF_HOLD", name + ": blocking checks: " + ", ".join(sorted(blockers)))
    n_tips = payload.get("n_tips")
    if isinstance(n_tips, bool) or not isinstance(n_tips, int) or n_tips <= 0:
        hold("PHYLO_RECEIPT_INVALID", name + ": n_tips must be a positive integer")
    package_tree_join = validate_package_tree_join(
        payload.get("package_tree_join"), n_tips, name + ".package_tree_join")
    return {
        "status": status,
        "tree_sha256": expected["tree_sha256"],
        "alignment_sha256": expected["alignment_sha256"],
        "outgroup_tip": outgroup_tip,
        "marker_set": payload.get("marker_set", "NOT_RECORDED"),
        "support": payload.get("support", "NOT_RECORDED"),
        "reference_dedup": payload.get("reference_dedup", "NOT_RECORDED"),
        "assembly_quality": payload.get("assembly_quality_flags", "NOT_RECORDED"),
        "comparator_provenance": payload.get("comparator_provenance", "NOT_RECORDED"),
        "package_tree_join": package_tree_join,
        "gtotree": payload["gtotree"],
        "iqtree": payload["iqtree"],
        "n_tips": n_tips,
        "outgroup_registry": payload["outgroup_registry"],
    }

def overlay():
    path = Path(__file__).resolve().parents[1] / "tools" / "tree_bgc_overlay.py"
    spec = importlib.util.spec_from_file_location("sapote_existing_tree_overlay", path)
    if spec is None or spec.loader is None: raise RuntimeError("tree_bgc_overlay unavailable")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def tree(root, obj, name):
    required = ("tree", "alignment", "tool_receipt", "signoff_receipt", "roster", "tool_name", "tool_version", "tool_sha256", "model", "model_sha256", "seed", "seed_sha256", "outgroup_tip", "outgroup_sha256")
    if not isinstance(obj, dict) or any(not obj.get(k) for k in required): raise ValueError(name + ": complete evidence receipt required")
    if obj["tool_sha256"] != sha256_text(obj["tool_name"] + "\n" + obj["tool_version"]): raise ValueError(name + ": tool hash mismatch")
    for key, hash_key in (("model", "model_sha256"), ("seed", "seed_sha256"), ("outgroup_tip", "outgroup_sha256")):
        if obj[hash_key] != sha256_text(obj[key]): raise ValueError(name + ": " + key + " hash mismatch")
    tree_path, alignment, tool_receipt, signoff_receipt, roster = (bound(root, obj[key], name + "." + key) for key in ("tree", "alignment", "tool_receipt", "signoff_receipt", "roster"))
    signoff = validate_signoff(
        json_object(signoff_receipt, name + ".signoff_receipt"),
        tree_path,
        alignment,
        obj["outgroup_tip"],
        name + ".signoff_receipt",
    )
    tree_text = tree_path.read_text(encoding="utf-8")
    if not re.fullmatch(r"[A-Za-z0-9_.:,;()\\-\\s]+", tree_text) or not tree_text.rstrip().endswith(";"):
        raise ValueError(name + ": unsupported Newick syntax; normalize quoted/comments before admission")
    o = overlay(); tips = o.tip_order(o.parse_newick(tree_text))
    roster_tips = {r["tree_tip"].strip() for r in tsv(roster, {"tree_tip"}, name + ".roster") if r["tree_tip"].strip()}
    if not tips or len(set(tips)) != len(tips) or set(tips) != roster_tips or obj["outgroup_tip"] not in roster_tips: raise ValueError(name + ": tree/roster/outgroup mismatch")
    if signoff["n_tips"] != len(tips):
        hold("PHYLO_SIGNOFF_MISMATCH", name + ": n_tips does not match admitted tree")
    if set(signoff["package_tree_join"]["tree_tips"]) != set(tips):
        hold("PHYLO_PACKAGE_TREE_JOIN_INCOMPLETE", name + ": package/tree join does not match admitted tree tips")
    return {"tips": tips, "obj": obj, "signoff": signoff}

def crosswalk(root, descriptor, tips, name):
    rows = tsv(bound(root, descriptor, name), {"tree_tip", "strain_id", "tip_missingness", "strain_missingness"}, name)
    mapping, strains = {}, set()
    for r in rows:
        tip, strain = r["tree_tip"].strip(), r["strain_id"].strip()
        if r["tip_missingness"] != "PRESENT" or r["strain_missingness"] != "PRESENT" or not tip or not strain: raise ValueError(name + ": typed PRESENT identity required")
        if tip in mapping or strain in strains: raise ValueError(name + ": one-to-one mapping required")
        mapping[tip] = strain; strains.add(strain)
    if set(mapping) != set(tips): raise ValueError(name + ": exact tree-tip coverage required; silent dropping prohibited")
    return mapping

def require_admitted_join_mapping(evidence, mapping, name):
    admitted = evidence["signoff"]["package_tree_join"]["tip_strain_map"]
    if admitted != mapping:
        hold("PHYLO_PACKAGE_TREE_JOIN_MISMATCH", name + ": crosswalk differs from admitted package/tree join")

def write_tsv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = _SafeDictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(rows)

def evidence_summary(e):
    o = e["obj"]
    return {
        **{k: o[k] for k in ("tree", "alignment", "tool_receipt", "signoff_receipt", "roster", "tool_name", "tool_version", "tool_sha256", "model", "model_sha256", "seed", "seed_sha256", "outgroup_tip", "outgroup_sha256")},
        "admitted_signoff": e["signoff"],
    }


def evidence_widget(out, ident, title, evidence):
    signoff = evidence["signoff"]
    obj = evidence["obj"]
    rows = (
        ("Sign-off", signoff["status"]),
        ("Tree SHA-256", signoff["tree_sha256"]),
        ("Alignment SHA-256", signoff["alignment_sha256"]),
        ("Outgroup", signoff["outgroup_tip"]),
        ("Marker set", signoff["marker_set"]),
        ("Support", signoff["support"]),
        ("Reference dedup", signoff["reference_dedup"]),
        ("Assembly quality", signoff["assembly_quality"]),
        ("Comparator provenance", signoff["comparator_provenance"]),
        ("Package/tree join", signoff["package_tree_join"]),
        ("Tree tool", obj["tool_name"] + " " + obj["tool_version"]),
        ("Model / seed", obj["model"] + " / " + obj["seed"]),
        ("Tips", len(evidence["tips"])),
    )
    cards = "".join(
        "<dt>" + html.escape(str(label)) + "</dt><dd>" +
        html.escape(json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)) +
        "</dd>" for label, value in rows
    )
    claim = (
        "This widget reports provenance and gate state for an existing tree. It does not build a tree "
        "or establish product identity, HGT, ancestry direction, activity, or topology equivalence."
    )
    path = out / (ident + "_phylogeny_evidence_widget.html")
    path.write_text(
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
        "content=\"width=device-width,initial-scale=1\"><title>" + html.escape(title) + "</title>"
        "<style>body{font:15px/1.45 system-ui;margin:0;background:#f4f6f8;color:#17212b}main{max-width:900px;"
        "margin:auto;padding:24px}article{background:white;border:1px solid #d8dee5;border-radius:8px;padding:20px}"
        "dl{display:grid;grid-template-columns:180px 1fr;gap:8px 16px}dt{font-weight:700;color:#176b73}dd{margin:0;"
        "overflow-wrap:anywhere}.claim{margin-top:20px;padding:12px;background:#fbf2dd;border-left:4px solid #c48a20}</style>"
        "</head><body><main><article><h1>" + html.escape(title) + "</h1><p><strong>Figure ID:</strong> " +
        html.escape(ident) + "</p><dl>" + cards + "</dl><p class=\"claim\">" + html.escape(claim) +
        "</p></article></main></body></html>",
        encoding="utf-8",
    )
    return path


def build_evidence_widget(config, root, out):
    ident = config.get("figure_id")
    if not isinstance(ident, str) or not ident:
        raise ValueError("figure_id required")
    evidence = tree(root, config.get("tree_evidence"), "tree_evidence")
    title = config.get("title", "Phylogenomics evidence receipt")
    widget = evidence_widget(out, ident, title, evidence)
    inputs = {"tree_evidence": evidence_summary(evidence)}
    return {
        "schema_version": SCHEMA,
        "figure_kind": EVIDENCE_WIDGET_KIND,
        "status": "PASS_EVIDENCE_WIDGET_READY",
        "figure_id": ident,
        "tip_count": len(evidence["tips"]),
        "outgroup_tip": evidence["obj"]["outgroup_tip"],
        "bound_inputs": inputs,
        "outputs": [{"logical_locator": widget.name, "sha256": sha256_file(widget), "bytes": widget.stat().st_size}],
        "claim_ceiling": "Provenance checklist only; tree construction and biological inference are not performed.",
        "authority_state": "PROPOSAL_ONLY_NOT_ACCEPTED_NOT_INTEGRATED_NOT_RELEASED",
    }

def caption(out, ident, title, method, inputs):
    p = out / (ident + "_caption_methods.md")
    p.write_text("# " + ident + " — " + title + "\n\n" + method + "\n\nInterpretation limit: separate evidence channels join only by an explicit hash-bound crosswalk. Visual proximity is not product identity, HGT, ancestry, or topology equivalence.\n\n## Bound inputs\n\n~~~json\n" + json.dumps(inputs, indent=2, sort_keys=True) + "\n~~~\n", encoding="utf-8")
    return p

def build_tracks(config, root, out):
    ident = config.get("figure_id")
    if not isinstance(ident, str) or not ident: raise ValueError("figure_id required")
    e = tree(root, config.get("tree_evidence"), "tree_evidence")
    mapping = crosswalk(root, config.get("tip_strain_crosswalk"), e["tips"], "tip_strain_crosswalk")
    require_admitted_join_mapping(e, mapping, "tip_strain_crosswalk")
    tracks = config.get("tracks")
    if not isinstance(tracks, list) or len(tracks) != len(CHANNELS) or {x.get("channel") for x in tracks if isinstance(x, dict)} != CHANNELS: raise ValueError("exactly five unique independent tracks required")
    rows, sources = [], []
    for item in tracks:
        channel = item["channel"]; path = bound(root, item, "track." + channel)
        seen = set()
        for r in tsv(path, {"strain_id", "feature_id", "count", "count_missingness"}, "track." + channel):
            strain, feature, count, state = r["strain_id"].strip(), r["feature_id"].strip(), r["count"].strip(), r["count_missingness"]
            if strain not in mapping.values() or not feature or state not in STATES: raise ValueError("track." + channel + ": unknown value")
            if state == "PRESENT":
                if not count or int(count) < 0: raise ValueError("track." + channel + ": invalid present count")
            elif count: raise ValueError("track." + channel + ": non-present count must be blank")
            rows.append({"tree_tip": next(t for t,s in mapping.items() if s == strain), "strain_id": strain, "channel": channel, "feature_id": feature, "count": count, "count_missingness": state}); seen.add(strain)
        if seen != set(mapping.values()): raise ValueError("track." + channel + ": missing typed row")
        sources.append({"channel": channel, "logical_locator": item["logical_locator"], "sha256": item["sha256"]})
    index = {tip: n for n, tip in enumerate(e["tips"])}
    for r in rows: r["tree_tip_index"] = index[r["tree_tip"]]
    rows.sort(key=lambda r: (r["tree_tip_index"], r["channel"], r["feature_id"]))
    data = out / (ident + "_annotation_tracks.tsv"); write_tsv(data, ["tree_tip_index","tree_tip","strain_id","channel","feature_id","count","count_missingness"], rows)
    inputs = {"tree_evidence": evidence_summary(e), "tip_strain_crosswalk": config["tip_strain_crosswalk"], "tracks": sources}
    cap = caption(out, ident, config.get("title", "Core-genome tree annotation tracks"), "One existing tree tip is the observation unit. Raw channel rows and typed missingness are exported; this adapter neither builds nor changes a tree.", inputs)
    return {"schema_version": SCHEMA, "figure_kind": TRACK_KIND, "status": "PASS_FIGURE_FACTORY_DATA_READY", "figure_id": ident, "tip_count": len(e["tips"]), "track_row_count": len(rows), "bound_inputs": inputs, "outputs": [{"logical_locator": data.name, "sha256": sha256_file(data)}, {"logical_locator": cap.name, "sha256": sha256_file(cap)}], "claim_ceiling": "Annotation tracks only; no product, HGT, ancestry, or topology-equivalence claim.", "authority_state": "PROPOSAL_ONLY_NOT_ACCEPTED_NOT_INTEGRATED_NOT_RELEASED"}

def build_concordance(config, root, out):
    ident = config.get("diagnostic_id")
    if not isinstance(ident, str) or not ident: raise ValueError("diagnostic_id required")
    mlsa, core = tree(root, config.get("mlsa_tree_evidence"), "mlsa_tree_evidence"), tree(root, config.get("core_tree_evidence"), "core_tree_evidence")
    rows = tsv(bound(root, config.get("shared_tip_crosswalk"), "shared_tip_crosswalk"), {"tree_kind","tree_tip","strain_id","tip_missingness","strain_missingness","disposition","reason"}, "shared_tip_crosswalk")
    expected, mappings = {"MLSA": set(mlsa["tips"]), "CORE_GENOME": set(core["tips"])}, {"MLSA": {}, "CORE_GENOME": {}}
    for r in rows:
        k, tip, strain = r["tree_kind"], r["tree_tip"].strip(), r["strain_id"].strip()
        if k not in mappings or r["tip_missingness"] != "PRESENT" or r["strain_missingness"] != "PRESENT" or not tip or not strain: raise ValueError("shared_tip_crosswalk: invalid typed identity")
        if tip in mappings[k] or strain in mappings[k].values(): raise ValueError("shared_tip_crosswalk: mapping must be one-to-one")
        mappings[k][tip] = strain
    if any(set(mappings[k]) != expected[k] for k in expected): raise ValueError("shared_tip_crosswalk: each roster must be exact")
    require_admitted_join_mapping(mlsa, mappings["MLSA"], "shared_tip_crosswalk.MLSA")
    require_admitted_join_mapping(core, mappings["CORE_GENOME"], "shared_tip_crosswalk.CORE_GENOME")
    reverse = {k: {s:t for t,s in x.items()} for k,x in mappings.items()}
    result = []
    for strain in sorted(set(reverse["MLSA"]) | set(reverse["CORE_GENOME"])):
        a,b = reverse["MLSA"].get(strain,""), reverse["CORE_GENOME"].get(strain,"")
        status = "SHARED" if a and b else ("MLSA_ONLY" if a else "CORE_GENOME_ONLY")
        declared = {r["disposition"] for r in rows if r["strain_id"].strip() == strain}
        if declared != {status}: raise ValueError("shared_tip_crosswalk: incorrect disposition")
        reason = next(r["reason"] for r in rows if r["strain_id"].strip() == strain)
        result.append({"strain_id":strain,"mlsa_tip":a,"core_genome_tip":b,"sampling_disposition":status,"reason":reason})
    data = out / (ident + "_shared_tip_concordance.tsv"); write_tsv(data, ["strain_id","mlsa_tip","core_genome_tip","sampling_disposition","reason"], result)
    inputs = {"mlsa_tree_evidence": evidence_summary(mlsa), "core_tree_evidence": evidence_summary(core), "shared_tip_crosswalk": config["shared_tip_crosswalk"]}
    cap = caption(out, ident, config.get("title", "MLSA and core-genome shared-tip diagnostic"), "This reports explicit shared and method-specific sampled tips only. It deliberately calculates no topology-equivalence statistic and does not force agreement between MLSA and core-genome inference.", inputs)
    return {"schema_version":SCHEMA,"figure_kind":CONCORDANCE_KIND,"status":"PASS_FIGURE_FACTORY_DIAGNOSTIC_READY","diagnostic_id":ident,"shared_tip_count":sum(x["sampling_disposition"]=="SHARED" for x in result),"mlsa_only_count":sum(x["sampling_disposition"]=="MLSA_ONLY" for x in result),"core_genome_only_count":sum(x["sampling_disposition"]=="CORE_GENOME_ONLY" for x in result),"bound_inputs":inputs,"outputs":[{"logical_locator":data.name,"sha256":sha256_file(data)},{"logical_locator":cap.name,"sha256":sha256_file(cap)}],"claim_ceiling":"Sampling concordance only; topology, ancestry, HGT, and product claims are not assessed.","authority_state":"PROPOSAL_ONLY_NOT_ACCEPTED_NOT_INTEGRATED_NOT_RELEASED"}

def build(config_path):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if config.get("schema_version") != SCHEMA: raise ValueError("schema_version mismatch")
    root = Path(config.get("external_data_root","")).expanduser().resolve()
    if not root.is_dir(): raise FileNotFoundError("external_data_root is not a directory")
    out = Path(config.get("output_dir",""))
    if not out.is_absolute(): out = (Path(config_path).parent / out).resolve()
    if out.exists(): raise FileExistsError("output_dir already exists")
    if not out.parent.is_dir(): raise FileNotFoundError("output_dir parent must already exist")
    # Validate inputs and render into a private staging dir; the real output_dir is
    # created (via one atomic replace) only after a run fully succeeds. A refusal
    # therefore leaves no stray output_dir behind — mirroring the aggregate arm.
    stage = Path(tempfile.mkdtemp(prefix=".phylogeny_figure_factory.", dir=out.parent))
    try:
        if config.get("figure_kind") == TRACK_KIND: receipt, ident = build_tracks(config,root,stage), config["figure_id"]
        elif config.get("figure_kind") == CONCORDANCE_KIND: receipt, ident = build_concordance(config,root,stage), config["diagnostic_id"]
        elif config.get("figure_kind") == EVIDENCE_WIDGET_KIND: receipt, ident = build_evidence_widget(config,root,stage), config["figure_id"]
        else: raise ValueError("unsupported phylogeny Figure Factory kind")
        rp = stage / (ident + "_phylogeny_figure_factory_receipt.json"); rp.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        stage.replace(out)
        return receipt
    except BaseException as exc:
        shutil.rmtree(stage, ignore_errors=True)
        # A structural refusal must exit through the typed REFUSED contract (CLI exit 2),
        # not escape as a raw traceback at exit 1. PhylogenyFigureHold is already typed;
        # promote any other plain ValueError raised by the validators to the same type so
        # the CLI's `except PhylogenyFigureHold` routes it to REFUSED like the aggregate arm.
        if isinstance(exc, ValueError) and not isinstance(exc, PhylogenyFigureHold):
            raise PhylogenyFigureHold("PHYLO_STRUCTURAL_REFUSED", str(exc)) from exc
        raise
