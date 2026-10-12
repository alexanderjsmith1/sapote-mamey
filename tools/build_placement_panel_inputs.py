#!/usr/bin/env python3
"""build_placement_panel_inputs — turn a gated EPA-ng display tree into the inputs of
tools/render_placement_COLOR_STRIPS.R (the required colour-strip placement figure).

Writes, into <out>/<panel>/: tree_input.newick, metadata.tsv, outgroup.txt, exclude_tips.txt,
title.txt, METADATA_PROVENANCE.tsv (per displayed tip and field: category, verbatim text,
provenance state, evidence URL) and OMITTED_TIPS.tsv (every tip left out, by full record title,
with the reason). `phylo_place.py report` calls this when an owner query table is supplied.

Category sources, in order of precedence per field:
  DEPOSITED (named bin)      the record's own /isolation_source, /host, /country or /geo_loc_name
                             (resolve_reference_metadata.py output) that matches a named rule
  COLLECTION_OR_LITERATURE   a reviewed culture-collection or species-description value carried
                             with its URL (--reviewed), or a reviewed owner/reference table
  DEPOSITED (outside bins)   a documented deposited source matching no named rule -> "Other documented"
  OWNER_REGISTRY / OWNER_RULING  query rows from the owner table / the owner override table
  (none)                     the tip is omitted and listed; the registry outgroup still roots the tree

Binning goes only through the ordered keyword tables SOURCE_RULES and GEO_RULES below, and every
cell keeps its verbatim text, so a rule change is a rerun, not a re-lookup. No science is inferred:
a colour is a documented category, judgment stays with the owner.
"""
import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, re, json, shutil  # noqa: E402
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path  # noqa: E402

# Verbatim deposited text -> shared registry category. Ordered keyword rules on the isolation_source
# (or "host:<organism>") text; the first match wins. A documented source that matches no rule is shown
# as "Other documented" (documented, not binned), never guessed into a named bin. Empty text = omitted.
SOURCE_RULES = [
    ("Honeybee", r"honey ?bee|apis mellifera|\bapis\b"), ("Bumblebee", r"bumble ?bee|bombus"), ("Wasp", r"\bwasp|vespid|polistes"),
    ("Ant", r"\bants?\b|attine|acromyrmex|\batta\b|formic|myrmic|trachymyrmex|cyphomyrmex"), ("Termite", r"termite"),
    ("Beehive pollen", r"bee ?hive|pollen|honeycomb|propolis"), ("Bryophyte", r"\bmoss|bryophyt|sphagnum"), ("Lichen", r"lichen"),
    ("Mangrove", r"mangrove"), ("Salt lake", r"salt lake|saline lake|hypersaline|salt ?pan|salt flat|dead sea|salt mine|saltern|solar salt"),
    ("Coastal sediment", r"(coastal|intertidal|beach|estuar|tidal).*sediment|sediment.*(coast|beach|intertidal)"),
    ("Marine-associated", r"marine|sea ?water|sea sediment|ocean|sponge|coral|seaweed|\bsea\b|deep-sea|hydrothermal|algae|ascidian|tunicate|starfish|sea cucumber|mussel|oyster"),
    ("Freshwater sediment", r"(lake|river|pond|reservoir|freshwater).*sediment|sediment.*(lake|river|pond)"),
    ("Freshwater-associated", r"fresh ?water|lake water|river|pond|spring water|stream|hot spring|waterfall"),
    ("Fungal-associated", r"fung|mushroom|mycel|basidio|truffle"),
    ("Animal/clinical", r"human|clinical|patient|blood|sputum|lavage|wound|urine|feces|faeces|dung|\bgut\b|intestin|skin|milk|cheese|animal|\bcow\b|cattle|sheep|goat|pig|chicken|\bfish\b|shrimp|bird|bat\b|insect|larva|beetle|worm|snail|dog|cat\b|horse|mouse|rat\b|tick|caterpillar|silkworm|earthworm|manure"),
    ("Built environment", r"water-damaged|indoor|building|house dust|hospital|clean ?room|spacecraft|air conditioner|wall"),
    ("Waste-associated", r"waste|sludge|sewage|landfill|effluent|compost"), ("Air-associated", r"\bair\b|atmospher|aerosol|dust"),
    ("Rock-associated", r"\brock|stone|cave|tufa|karst|volcanic|lava|sandstone|mineral|\bore\b|mine\b|speleo"),
    ("Plant-associated", r"root|rhizosphere|stem|leaf|leaves|plant|endophyt|nodule|seed|flower|bark|wood|rice|wheat|maize|corn|potato|tomato|grass|hay|straw|tree|bamboo|fruit|tuber|herb|medicinal|cactus|orchid|lupinus|oryza|jatropha|artemisia|gloriosa|callistemon|peucedanum|rhizome|tissue"),
    ("Soil", r"soil|sand|desert|arid|earth|humus|peat|loam|sediment|mud|clay|dune|permafrost|regolith|field|farm|garden|forest floor|land"),
]
GEO_RULES = [
    ("US", r"^(usa|united states|u\.s\.a\.?|u\.s\.)\b|^united states of america"), ("Canada", r"^canada"),
    ("Virgin Islands", r"virgin islands"), ("Costa Rica", r"^costa rica"), ("Northern Cyprus", r"northern cyprus"),
    ("Russia", r"^russia|^russian federation"), ("Turkey", r"^turkey|^t[üu]rkiye"), ("Europe / Asia", r"^ussr|^soviet"),
    ("Antarctica", r"^antarctica"), ("Pacific Ocean", r"^pacific ocean"), ("Indian Ocean", r"^indian ocean"),
    ("Asia", r"^(china|japan|south korea|korea|republic of korea|india|thailand|indonesia|mongolia|iran|saudi arabia|viet ?nam|malaysia|philippines|taiwan|pakistan|israel|kazakhstan|uzbekistan|turkmenistan|kyrgyzstan|tajikistan|nepal|bangladesh|sri lanka|myanmar|cambodia|laos|singapore|oman|yemen|iraq|jordan|lebanon|syria|kuwait|qatar|united arab emirates|bhutan|hong kong|tibet|azerbaijan|armenia)\b"),
    ("Europe", r"^(germany|italy|finland|france|spain|united kingdom|uk|england|scotland|wales|ireland|greece|poland|czech|slovakia|belgium|netherlands|sweden|norway|denmark|austria|switzerland|portugal|ukraine|bulgaria|romania|hungary|croatia|serbia|slovenia|estonia|latvia|lithuania|iceland|belarus|moldova|georgia|cyprus|malta|luxembourg|montenegro|bosnia|albania|north macedonia)\b"),
    ("Africa", r"^(algeria|south africa|egypt|morocco|tunisia|nigeria|kenya|namibia|tanzania|ethiopia|ghana|cameroon|senegal|uganda|zimbabwe|zambia|madagascar|mozambique|libya|sudan|mali|niger|chad|botswana|angola|congo|ivory coast|c[oô]te d'ivoire|malawi|rwanda|burkina faso|benin|togo|gabon|mauritius|reunion|seychelles)\b"),
    ("Oceania", r"^(australia|new zealand|papua new guinea|fiji|samoa|tonga|vanuatu|new caledonia|solomon islands|micronesia|palau|guam)\b"),
    ("South America", r"^(brazil|argentina|chile|colombia|peru|venezuela|ecuador|bolivia|uruguay|paraguay|guyana|suriname|french guiana)\b"),
    ("North America", r"^(mexico|panama|guatemala|honduras|nicaragua|el salvador|belize|cuba|jamaica|haiti|dominican republic|puerto rico|bahamas|greenland|bermuda|trinidad|barbados)\b"),
]
OTHER_DOCUMENTED = "Other documented"


def bin_source(text):
    t = (text or "").strip()
    if not t or t.lower() in ("not recorded", "missing", "n/a", "na", "none", "unknown", "not applicable", "not collected"):
        return "", False
    body = re.sub(r"^host:\s*", "", t, flags=re.I)
    for cat, rx in SOURCE_RULES:
        if re.search(rx, body, re.I):
            return cat, True
    return OTHER_DOCUMENTED, False       # documented, not binned


def bin_geo(location):
    loc = (location or "").strip()
    if not loc or loc.lower() in ("not recorded", "missing", "n/a", "na", "none", "unknown", "not applicable", "not collected"):
        return ""
    for cat, rx in GEO_RULES:
        if re.search(rx, loc, re.I):
            return cat
    return ""


def acc_of(tip):
    m = re.match(r"^([A-Z]{1,2}_?\d+)_(\d+)_", tip)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    m = re.search(r"(NR_\d+)_(\d+)_outgroup", tip)
    return f"{m.group(1)}.{m.group(2)}" if m else ""


def species_strain(title):
    t = re.sub(r"^\S+\s+", "", title)                     # drop accession
    t = re.sub(r"\s+(gene for\s+)?16S (ribosomal RNA|rRNA).*$", "", t)
    t = re.sub(r"\s+\[outgroup for [^\]]*\].*$", "", t)
    t = t.replace(" strain ", " ")
    return t.strip()


def read_tsv(p):
    with open(p, encoding="utf-8") as h:
        return list(csv.DictReader(h, delimiter="\t"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--genus", required=True, help="panel name; also the output subfolder and the figure stem")
    ap.add_argument("--tree", required=True, help="gated display tree (*.rooted_split.newick or the checked graft)")
    ap.add_argument("--labelmap", required=True, help="labelmap.tsv (safe -> original title)")
    ap.add_argument("--resolved", action="append", default=[], help="resolve_reference_metadata.py output (repeatable)")
    ap.add_argument("--outgroup-resolved", action="append", default=[])
    ap.add_argument("--owner-table", required=True, action="append",
                    help="owner query table (tip, label, sample_id, role, source_category, geography_category, Candida, MRSA, "
                         "type_display, label_original); repeatable, first file wins per tip")
    ap.add_argument("--owner-table-original", action="append", default=[],
                    help="companion table with accession, host, location, metadata_evidence_url per reference row (reviewed values)")
    ap.add_argument("--query-override", action="append", default=[],
                    help="TSV (tip, label, sample_id, source_category, geography_category, Candida, MRSA, label_original, provenance) "
                         "for query rows absent from, or ruled differently than, the owner tables; wins over them")
    ap.add_argument("--reviewed", action="append", default=[],
                    help="TSV (accession, isolation_source, location, source_category, geography_category, evidence_url, note) of "
                         "culture-collection or species-description values reviewed for this panel; used after deposited values")
    ap.add_argument("--query-prefix", default="AS", help="owner strain-id prefix; query tips are <prefix>_<n> or '..._strain_<prefix>_<n>_16S...'")
    ap.add_argument("--outgroup-source", default="", help="category for the outgroup if not deposited")
    ap.add_argument("--outgroup-geo", default="")
    ap.add_argument("--outgroup-evidence", default="", help="URL + verbatim text for the outgroup categories")
    ap.add_argument("--metadata-context", default="", help="internal source-bound report context; omitted means unrecorded length/molecule")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    from Bio import Phylo

    from _placement_report_metadata import reviewed_type_map, file_binding, normalize_options, TYPE_FIELDS
    from types import SimpleNamespace
    options = normalize_options(SimpleNamespace(owner_table=a.owner_table, owner_table_original=a.owner_table_original,
                                resolved_metadata=a.resolved + a.outgroup_resolved, reviewed=a.reviewed,
                                query_override=a.query_override, query_prefix=a.query_prefix, rscript="Rscript"))
    for raw in [a.tree, a.labelmap] + ([a.metadata_context] if a.metadata_context else []):
        path = Path(raw).absolute()
        if any(part.is_symlink() for part in (path, *path.parents)) or not path.is_file():
            raise ValueError("PANEL_INPUT_PATH_INVALID")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", a.genus):
        raise ValueError("PANEL_NAME_INVALID")
    out = Path(a.out) / a.genus
    if out.exists() or any(path.is_symlink() for path in (out, *out.parents)):
        raise ValueError("PANEL_OUTPUT_EXISTS_OR_SYMLINK")
    source_paths = [a.tree, a.labelmap] + a.resolved + a.outgroup_resolved + a.owner_table + a.owner_table_original + a.reviewed + a.query_override
    if a.metadata_context:
        source_paths.append(a.metadata_context)
    source_bindings = {str(Path(path).absolute()): file_binding(path) for path in source_paths}
    tree = Phylo.read(a.tree, "newick")
    tips = [t.name for t in tree.get_terminals()]
    if len(set(tips)) != len(tips) or any(not tip for tip in tips):
        raise ValueError("PANEL_TIP_INVENTORY_INVALID")
    context = {"molecule": "NOT_RECORDED", "length_state": "NOT_RECORDED", "length_receipt_sha256": "NOT_RECORDED"}
    native_queries = None
    if a.metadata_context:
        context = json.loads(Path(a.metadata_context).read_text())
        if context.get("schema") != "sapote.placement.panel-context.v1":
            raise ValueError("PANEL_CONTEXT_INVALID")
        native_queries = context.get("query_tips")
        if not isinstance(native_queries, list) or any(not isinstance(tip, str) for tip in native_queries) or len(set(native_queries)) != len(native_queries) or not set(native_queries) <= set(tips):
            raise ValueError("PANEL_QUERY_ROSTER_INVALID")
        if context.get("length_state") == "PASS_LENGTH_QA":
            from tools.graft_integrity import admit_graft_length_evidence, _metric, _tips, _close_length
            admission = admit_graft_length_evidence(context["length_receipt"], context["length_sources"])
            if admission["receipt_sha256"] != context["length_receipt_sha256"]:
                raise ValueError("PANEL_LENGTH_RECEIPT_CHANGED")
            admitted_tree = Phylo.read(admission["selected"]["restored"], "newick")
            if _tips(admitted_tree) != set(tips):
                raise ValueError("PANEL_LENGTH_TREE_MEMBERSHIP_CHANGED")
            expected_metric = _metric(admitted_tree, set(tips)); actual_metric = _metric(tree, set(tips))
            if expected_metric.keys() != actual_metric.keys() or any(not _close_length(actual_metric[key][0], value[0]) for key, value in expected_metric.items()):
                raise ValueError("PANEL_LENGTH_TREE_METRIC_CHANGED")
    titles = {r["safe"]: r["original"] for r in read_tsv(a.labelmap)}
    labels = {tip: titles.get(tip, tip) for tip in tips}
    type_evidence = reviewed_type_map(a.reviewed, labels, query_tips=native_queries or (), resolved_paths=a.resolved + a.outgroup_resolved)
    if a.metadata_context and context.get("reviewed_type_evidence") != type_evidence:
        raise ValueError("PANEL_TYPE_EVIDENCE_CHANGED")
    resolved = {}
    for p in a.resolved + a.outgroup_resolved:
        for r in read_tsv(p):
            if r.get("verification_status") in {"STRAIN_CONFIRMED", "STRAIN_CONFIRMED_NO_METADATA", "STRAIN_CONFIRMED_NULL_DECLARED"}:
                resolved.setdefault(r["exact_accession"], r)
    codex = {}
    reviewed = {}
    for p in a.reviewed:
        for r in read_tsv(p):
            reviewed.setdefault(r["accession"], r)
    overrides = {}
    for p in a.query_override:
        for r in read_tsv(p):
            overrides[r["tip"]] = r
    for p in a.owner_table:
        for r in read_tsv(p):
            codex.setdefault(r["tip"], r)
    codex_acc = {}
    for p in a.owner_table_original:
        for r in read_tsv(p):
            acc = r.get("accession") or (re.search(r"\b([A-Z]{1,2}_?\d+\.\d+)\b", r["label"]) or [None, ""])[1]
            codex_acc.setdefault(acc, r)
    codex_by_acc = {}
    for tip, r in codex.items():
        m = re.search(r"\(([A-Z]{1,2}_?\d+\.\d+)\)\s*$", r["label"])
        codex_by_acc[m.group(1) if m else tip] = r

    rows, prov, omitted = [], [], []
    outgroup_tip = ""
    owner_joins = {}
    P = re.escape(a.query_prefix)
    for tip in tips:
        qm = re.match(rf"^{P}_(\d+)$", tip) or re.search(rf"_strain_{P}_(\d+)_16S", tip)
        if ((tip in native_queries) if native_queries is not None else bool(qm)):
            sid = tip
            if not (overrides.get(tip) or codex.get(tip)) and qm:
                sid = f"{a.query_prefix}-{qm.group(1)}"
            r = overrides.get(sid) or codex.get(sid)
            if r:
                if sid in owner_joins and owner_joins[sid] != tip:
                    raise ValueError("PANEL_QUERY_OWNER_ALIAS_AMBIGUOUS")
                owner_joins[sid] = tip
            if not r:
                omitted.append((tip, sid, "query row absent from the owner tables and no override supplied")); continue
            if not r.get("source_category") or not r.get("geography_category"):
                omitted.append((tip, sid, "owner row lacks a source or geography category")); continue
            rows.append({"tip": tip, "label": r["label"], "sample_id": r.get("sample_id", ""), "role": "query",
                         "source_category": r["source_category"], "geography_category": r["geography_category"],
                         "Candida": r.get("Candida", ""), "MRSA": r.get("MRSA", ""), "type_display": "", "label_original": r.get("label_original", r["label"])})
            basis = r.get("provenance") or "owner query table"
            state = "OWNER_RULING" if sid in overrides else "OWNER_REGISTRY"
            prov.append((tip, "source", r["source_category"], basis, state, ""))
            prov.append((tip, "geography", r["geography_category"], basis, state, ""))
            continue
        acc = acc_of(tip)
        title = titles.get(tip, tip)
        is_out = "outgroup" in tip
        name = species_strain(title)
        res = resolved.get(acc, {})
        cx = codex_by_acc.get(acc, {})
        cxo = codex_acc.get(acc, {})
        src = geo = ""
        # source: a deposited value that lands in a named bin wins; then reviewed/Codex values; then a
        # deposited value that is documented but outside every named bin ("Other documented").
        dep_src = (res.get("isolation_source") or "").strip()
        dep_host = (res.get("host") or "").strip()
        d_cat, d_named = bin_source(dep_src)
        h_cat, h_named = bin_source("host:" + dep_host) if dep_host else ("", False)
        if d_cat and d_named:
            src = d_cat; prov.append((tip, "source", src, dep_src, "DEPOSITED:" + res.get("isolation_source_provenance", ""), res.get("evidence_url", "")))
        elif h_cat and h_named:
            src = h_cat; prov.append((tip, "source", src, "host: " + dep_host, "DEPOSITED:nuccore:/host", res.get("evidence_url", "")))
        elif reviewed.get(acc, {}).get("source_category"):
            rv = reviewed[acc]; src = rv["source_category"]; prov.append((tip, "source", src, rv.get("isolation_source", ""), "COLLECTION_OR_LITERATURE", rv.get("evidence_url", "")))
        elif cx.get("source_category"):
            src = cx["source_category"]; prov.append((tip, "source", src, cxo.get("host", ""), "COLLECTION_OR_LITERATURE", cxo.get("metadata_evidence_url", "")))
        elif is_out and a.outgroup_source:
            src = a.outgroup_source; prov.append((tip, "source", src, a.outgroup_evidence, "COLLECTION_OR_LITERATURE", a.outgroup_evidence))
        elif d_cat:
            src = d_cat; prov.append((tip, "source", src, dep_src, "DEPOSITED:" + res.get("isolation_source_provenance", "") + " (outside named bins)", res.get("evidence_url", "")))
        elif h_cat:
            src = h_cat; prov.append((tip, "source", src, "host: " + dep_host, "DEPOSITED:nuccore:/host (outside named bins)", res.get("evidence_url", "")))
        # geography
        dep_loc = (res.get("location") or "").strip()
        g_cat = bin_geo(dep_loc)
        if g_cat:
            geo = g_cat; prov.append((tip, "geography", geo, dep_loc, "DEPOSITED:" + res.get("location_provenance", ""), res.get("evidence_url", "")))
        elif reviewed.get(acc, {}).get("geography_category"):
            rv = reviewed[acc]; geo = rv["geography_category"]; prov.append((tip, "geography", geo, rv.get("location", ""), "COLLECTION_OR_LITERATURE", rv.get("evidence_url", "")))
        elif cx.get("geography_category"):
            geo = cx["geography_category"]; prov.append((tip, "geography", geo, cxo.get("location", ""), "COLLECTION_OR_LITERATURE", cxo.get("metadata_evidence_url", "")))
        elif is_out and a.outgroup_geo:
            geo = a.outgroup_geo; prov.append((tip, "geography", geo, a.outgroup_evidence, "COLLECTION_OR_LITERATURE", a.outgroup_evidence))
        if not src or not geo:
            why = []
            if not src: why.append("no deposited or reviewed isolation source")
            if not geo: why.append("no deposited or reviewed geography" + (f" (deposited location not in the geography rules: {dep_loc})" if dep_loc and dep_loc != "Not recorded" else ""))
            if is_out:
                # The registry outgroup still roots the display tree (outgroup.txt), then it is dropped
                # like any other tip without both categories; the caption must say so.
                outgroup_tip = tip
                why.append("registry outgroup: used for rooting, then dropped from the display")
            omitted.append((tip, title, "; ".join(why)))
            continue
        type_row = type_evidence["roles"].get(tip)
        typ = "Type" if type_row else ""
        if type_row:
            name = type_row["taxon"] + " " + type_row["strain"]
            prov.append((tip, "type_material", "type strain of " + type_row["type_strain_of"], type_row["type_evidence"], "SOURCE_REVIEWED", type_row["source_url"]))
        else:
            prov.append((tip, "type_material", "", title, "NOT_RECORDED", ""))
            if re.search(r"\[Type(?:;|\])|\btype\s+strain\b", name, re.I):
                raise ValueError("PANEL_UNVERIFIED_TYPE_LABEL_ANCHOR_REQUIRED")
        tags = [x for x in [typ, "outgroup" if is_out else "", src, geo] if x]
        label = f"{name} [{'; '.join(tags)}] ({acc})"
        rows.append({"tip": tip, "label": label, "sample_id": "", "role": "outgroup" if is_out else "reference",
                     "source_category": src, "geography_category": geo, "Candida": "", "MRSA": "",
                     "type_display": typ, "label_original": title})
        if is_out:
            outgroup_tip = tip

    out.mkdir(parents=True, exist_ok=False)
    cols = ["tip", "label", "sample_id", "role", "source_category", "geography_category", "Candida", "MRSA", "type_display", "label_original"]
    with open(out / "metadata.tsv", "w", encoding="utf-8", newline="") as h:
        w = _SafeDictWriter(h, fieldnames=cols, delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(rows)
    with open(out / "METADATA_PROVENANCE.tsv", "w", encoding="utf-8", newline="") as h:
        w = _SafeWriter(h, delimiter="\t", lineterminator="\n"); w.writerow(["tip", "field", "category", "verbatim", "provenance", "evidence_url"]); w.writerows(prov)
    with open(out / "OMITTED_TIPS.tsv", "w", encoding="utf-8", newline="") as h:
        w = _SafeWriter(h, delimiter="\t", lineterminator="\n"); w.writerow(["tip", "record_title", "reason"]); w.writerows(omitted)
    (out / "exclude_tips.txt").write_text("".join(t + "\n" for t, _, _ in omitted), encoding="utf-8")
    (out / "outgroup.txt").write_text(outgroup_tip + "\n", encoding="utf-8")
    (out / "title.txt").write_text(f"{a.genus} {context['molecule']} EPA-ng placement\n", encoding="utf-8")
    shutil.copyfile(a.tree, out / "tree_input.newick")
    query_set = set(native_queries) if native_queries is not None else {tip for tip in tips if re.match(rf"^{P}_(\d+)$", tip) or re.search(rf"_strain_{P}_(\d+)_16S", tip)}
    context.update(input_tips=len(tips), kept_tips=len(rows), input_queries=len(query_set),
                   kept_queries=sum(row["role"] == "query" for row in rows),
                   omitted_queries=len(query_set - {row["tip"] for row in rows}),
                   query_role_basis="exact jplace roster" if native_queries is not None else "legacy prefix compatibility; no native receipt claim")
    with (out / "figure_context.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeWriter(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["field", "value"])
        for field in ("molecule", "length_state", "length_receipt_sha256", "input_tips", "kept_tips", "input_queries", "kept_queries", "omitted_queries", "query_role_basis"):
            writer.writerow([field, context[field]])
    (out / "TYPE_EVIDENCE.json").write_text(json.dumps(type_evidence, indent=2, sort_keys=True) + "\n")
    with (out / "TYPE_EVIDENCE.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=sorted(TYPE_FIELDS), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(type_evidence["roles"].values())
    if source_bindings != {str(Path(path).absolute()): file_binding(path) for path in source_paths}:
        raise ValueError("PANEL_INPUT_CHANGED_DURING_BUILD")
    dep = sum(p[4].startswith('DEPOSITED') for p in prov); lit = sum(p[4] == 'COLLECTION_OR_LITERATURE' for p in prov)
    emit(f"[build_placement_panel_inputs] {a.genus}: {len(tips)} tips in tree; kept {len(rows)} ({sum(r['role']=='query' for r in rows)} query, "
         f"{sum(r['role']=='reference' for r in rows)} reference, {sum(r['role']=='outgroup' for r in rows)} outgroup); omitted {len(omitted)}",
         f"[build_placement_panel_inputs] field provenance: {dep} DEPOSITED, {lit} COLLECTION_OR_LITERATURE, "
         f"{sum(p[4]=='OWNER_REGISTRY' for p in prov)} OWNER_REGISTRY, {sum(p[4]=='OWNER_RULING' for p in prov)} OWNER_RULING",
         sep="\n")
    input_files = ["metadata.tsv", "METADATA_PROVENANCE.tsv", "OMITTED_TIPS.tsv", "exclude_tips.txt", "outgroup.txt", "title.txt", "tree_input.newick", "figure_context.tsv", "TYPE_EVIDENCE.json", "TYPE_EVIDENCE.tsv"]
    result = {"schema": "sapote.placement.panel-inputs.v1", "state": "INPUTS_PRODUCED", "kept": len(rows),
              "omitted": len(omitted), "query_kept": sum(row["role"] == "query" for row in rows),
              "input_tips": tips, "kept_tips": [row["tip"] for row in rows], "omitted_tips": [row[0] for row in omitted],
              "query_role_basis": "exact jplace roster" if native_queries is not None else "legacy prefix compatibility; no native receipt claim",
              "owner_joins": owner_joins, "outgroup": outgroup_tip, "dir": str(out), "source_bindings": source_bindings,
              "input_files": input_files, "artifacts": [file_binding(out / name) for name in input_files]}
    if set(result["kept_tips"]) & set(result["omitted_tips"]) or set(result["kept_tips"]) | set(result["omitted_tips"]) != set(tips):
        raise ValueError("PANEL_TIP_PARTITION_INVALID")
    with (out / "BUILD_RECEIPT.json").open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result


if __name__ == "__main__":
    main()
