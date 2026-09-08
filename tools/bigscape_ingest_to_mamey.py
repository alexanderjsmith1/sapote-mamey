#!/usr/bin/env python3
"""bigscape_ingest_to_mamey.py -- write BiG-SCAPE GCF context INTO the Mamey layer.

This is the missing half of the "prep -> run -> ingest" loop. bigscape_cross_strain.py
produces a locator-keyed TSV; this tool takes that same anchored BiG-SCAPE 2 SQLite DB (or,
with --from-tsv, the portable per-BGC annotation TSV) and *writes* a cross-strain GCF context
block into each per-BGC Mode B card, and adds GCF columns to the triage board -- joining on the
`node.region` assembly locator that both layers share.

The join key is `strain:NODE_..._length_....regionNN` (COV-INDEPENDENT -- see canon_locator).
Mode B cards are named `<STRAIN>_BGC###_ModeB.md` and carry a BGC number, not a locator, so the
triage board (which has BOTH the BGC number and the node.region) is the bridge. No triage board
-> nothing to join on -> tool refuses (it does not guess).

Everything written is capacity-level and provenance-tagged `[store-backed GCF | BiG-SCAPE]`.
KNOWN means the family shares a bin with a MIBiG reference (architecture-consistent), NOT a
compound-identity call. Distances are BiG-SCAPE GCF distances (0 identical .. 1 maximal).

Usage:
  # DB path (full context incl. cohort co-members):
  python bigscape_ingest_to_mamey.py --db anchored.db --package <Mamey_pkg_dir> \
      [--cutoff 0.5] [--mibig-index mamey/data/mibig/mibig_reference_index.bacterial.json] \
      [--triage triage_board.csv] [--cards-dir cards/] [--dry-run]

  # Portable path (no 400 MB DB; co-members unavailable -- see note):
  python bigscape_ingest_to_mamey.py --from-tsv AS_per_BGC_annotation.tsv --strain AS-XXX \
      --package <Mamey_pkg_dir> [--cutoff 0.5]

Stdlib only (sqlite3, csv, re, json, argparse, os, glob). Builder tool; no gate row.

v9.7.292 fixes (see docs/BIGSCAPE_MAMEY_INTEGRATION.md "v9.7.292" + README_PATCH):
  - load_triage() now sources the locator from Contig + antiSMASH_Region (the real join
    components), not the display `Assembly_Locator` column (which carries spaces + a "(BGC###)"
    suffix and never matched). It also tolerates a triage board with NO strain column
    (single-strain packages) by keying on ("", bgc) and letting main() fall back to it.
  - canon_locator() strips the `_cov_<float>` segment so the join is COV-INDEPENDENT. This is
    immune to the engine's triage-board cov formatting (leading-zero drop, e.g.
    cov_73.020183 -> cov_73.20183) that otherwise broke ~1/5 of rows.
  - --from-tsv: source context from the portable AS_per_BGC_annotation.tsv when no DB is present.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, sqlite3, re, os, csv, json, glob, sys, contextlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.bigscape_namespace import (
    NamespaceError, build_family_identity, normalize_cutoff, normalize_run_id,
    public_error, validate_membership_rows,
)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_write_text

LOCATOR = re.compile(r"_(NODE_.+)\.(region\d+)\.gbk$", re.I)
BEGIN = "<!-- BIGSCAPE_GCF_CONTEXT:BEGIN -->"
END = "<!-- BIGSCAPE_GCF_CONTEXT:END -->"


def canon_locator(loc):
    """Cov-INDEPENDENT join key. A contig is uniquely identified by its NODE number + length;
    coverage is not identity and is formatted lossily by the triage board. Reduce any locator
    to `NODE_<n>_length_<L>.region<NN>`.

      NODE_402_length_4883_cov_73.020183.region001 -> NODE_402_length_4883.region001
      NODE_402_length_4883_cov_73.20183.region001  -> NODE_402_length_4883.region001  (engine bug)
      NODE_402_length_4883_cov_73.region001         -> NODE_402_length_4883.region001  (Node_ID form)
    """
    if not loc:
        return loc
    m = re.match(r"(NODE_\d+_length_\d+).*?\.(region\d+)\b", loc, re.I)
    return f"{m.group(1)}.{m.group(2)}" if m else loc


def _is_mibig(base):
    return base.upper().startswith("BGC")


def parse_locator(path):
    b = os.path.basename(path)
    if _is_mibig(b):
        return "MIBiG", b.split(".")[0], True
    strain = b.split("_")[0]
    m = LOCATOR.search(b)
    if m:
        loc = canon_locator(f"{m.group(1)}.{m.group(2)}")
    else:
        # Fallback for non-SPAdes contig names that carry no NODE_<n>_length_<L>
        # token -- e.g. NCBI WGS accession contigs like "WEGH01000001.1". Strip the
        # "<strain>_" prefix and the ".regionNN.gbk" suffix to recover the contig, then
        # let canon_locator pass it through unchanged (it only rewrites NODE_ forms).
        rest = b[len(strain) + 1:] if b.startswith(f"{strain}_") else b
        m2 = re.search(r"^(.+)\.(region\d+)\.gbk$", rest, re.I)
        loc = canon_locator(f"{m2.group(1)}.{m2.group(2)}") if m2 else None
    return strain, loc, False


def load_mibig_names(index_path):
    if not index_path or not os.path.exists(index_path):
        return {}
    try:
        with open(index_path) as _f:
            data = json.load(_f)
        entries = data["entries"] if isinstance(data, dict) and "entries" in data else data
        return {e["accession"]: (e.get("compounds") or ["?"])[0] for e in entries}
    except Exception:
        return {}


def gcf_context(db, cutoff, names, run_id=None):
    """Return contexts for one explicit run and exact cutoff, refusing collisions."""
    # COMP-P09: close the sqlite connection even if a query raises mid-way (malformed/partial db).
    # The prior code only reached c.close() on the happy path, leaking the handle on any error.
    with contextlib.closing(sqlite3.connect(db)) as c:
        selected_cutoff = normalize_cutoff(cutoff)
        # Probe the database contract before argument normalization so malformed SQLite inputs
        # retain their native query error while still closing the connection. A valid database
        # never proceeds without an explicit canonical run id; no run is inferred here.
        c.execute("select 1 from run limit 0").fetchone()
        selected_run = normalize_run_id(run_id)
        fam_members = {}
        rec = {}
        assignments = {}
        for fid, raw_cutoff, path, record_id in c.execute(
            "select fam.id, fam.cutoff, g.path, br.id from bgc_record_family rf "
            "join family fam on fam.id=rf.family_id "
            "join bgc_record br on br.id=rf.record_id "
            "join gbk g on g.id=br.gbk_id "
            "where fam.run_id=? and br.record_type='region' order by fam.cutoff,fam.id,br.id,g.path",
            (selected_run,),
        ):
            identity = build_family_identity(selected_run, raw_cutoff, fid)
            if identity.normalized_cutoff != selected_cutoff:
                continue
            prior = assignments.get(record_id)
            if prior is not None and prior != identity.qualified_family_id:
                raise NamespaceError("DUPLICATE_CONFLICT", "one database record has conflicting family assignments")
            assignments[record_id] = identity.qualified_family_id
            label, ident, ismibig = parse_locator(path)
            key = ident if ismibig else f"{label}:{ident}"
            if key in rec and rec[key][0] != identity:
                raise NamespaceError("DUPLICATE_CONFLICT", "one portable locator has conflicting family assignments")
            rec[key] = (identity, label, ident, ismibig)
            fam_members.setdefault(identity.qualified_family_id, {"strains": set(), "mibig": set(), "keys": []})
            d = fam_members[identity.qualified_family_id]
            d["keys"].append(key)
            if ismibig:
                d["mibig"].add(ident)
            else:
                d["strains"].add(label)
        id2key = {}
        for rid, path in c.execute("select br.id, g.path from bgc_record br join gbk g on g.id=br.gbk_id where br.record_type='region'"):
            label, ident, ismibig = parse_locator(path)
            id2key[rid] = (ident if ismibig else f"{label}:{ident}", ismibig, ident if ismibig else label)
        mibig_ids = {rid for rid, v in id2key.items() if v[1]}
        nearest = {}
        for a, b, dist in c.execute("select record_a_id, record_b_id, distance from distance"):
            for x, y in ((a, b), (b, a)):
                if x in id2key and not id2key[x][1] and y in mibig_ids:
                    cur = nearest.get(x)
                    if cur is None or dist < cur[0]:
                        nearest[x] = (dist, id2key[y][2])
        key2nearest = {}
        for rid, (d, macc) in nearest.items():
            key2nearest[id2key[rid][0]] = (d, macc)
    out = {}
    for key, (identity, strain, loc, ismibig) in rec.items():
        if ismibig:
            continue
        d = fam_members[identity.qualified_family_id]
        mibig_acc = sorted(d["mibig"])
        others = sorted(s for s in d["strains"] if s != strain)
        nd = key2nearest.get(key)
        out[key] = {
            "family_id": identity.family_id,
            "run_id": identity.run_id,
            "normalized_cutoff": identity.normalized_cutoff,
            "qualified_family_id": identity.qualified_family_id,
            "gcf_namespace": identity.gcf_namespace,
            "cutoff": identity.normalized_cutoff,
            "status": "KNOWN" if mibig_acc else "NOVEL",
            "mibig": [(a, names.get(a, "?")) for a in mibig_acc],
            "cross_strain_members": others,
            "n_strains": len(d["strains"]),
            "nearest_mibig": (nd[1], names.get(nd[1], "?"), round(nd[0], 3)) if nd else None,
        }
    return out


def _parse_anchor_field(s):
    """'BGC0002010 (streptophenazine B); BGC0001 (foo)' -> [('BGC0002010','streptophenazine B'),...]"""
    out = []
    for part in [p.strip() for p in (s or "").split(";") if p.strip()]:
        m = re.match(r"(BGC\d+)\s*\(([^)]*)\)", part)
        if m:
            out.append((m.group(1), m.group(2)))
        elif part:
            out.append((part, "?"))
    return out


def tsv_context(tsv_path, strain, cutoff):
    """Portable path: build {strain:locator -> context} from AS_per_BGC_annotation.tsv.
    Co-members are NOT available in this mode (the portable export carries no per-BGC family_id);
    the block states that explicitly rather than implying strain-uniqueness."""
    out = {}
    with open(tsv_path, newline="") as fh:
        candidates = []
        for r in csv.DictReader(fh, delimiter="\t"):
            if strain and r.get("strain") != strain:
                continue
            loc = canon_locator((r.get("locator") or "").strip())
            if not loc:
                continue
            r = dict(r)
            r["_portable_key"] = f'{r.get("strain")}:{loc}'
            candidates.append(r)
        rows = validate_membership_rows(
            candidates, key_fields=("_portable_key",), expected_cutoff=cutoff, allow_absent=True,
        )
        for r in rows:
            loc = r["_portable_key"].split(":", 1)[1]
            mib = _parse_anchor_field(r.get("MIBiG_family_anchors"))
            near = None
            na = _parse_anchor_field(r.get("nearest_MIBiG"))
            nd = (r.get("nearest_distance") or "").strip()
            if na and nd:
                near = (na[0][0], na[0][1], round(float(nd), 3))
            family_id = r.get("family_id") or None
            out[f'{r.get("strain")}:{loc}'] = {
                "family_id": family_id,
                "run_id": int(r["run_id"]) if family_id else None,
                "normalized_cutoff": r.get("normalized_cutoff") or None,
                "qualified_family_id": r.get("qualified_family_id") or None,
                "gcf_namespace": r.get("gcf_namespace") or None,
                "cutoff": r.get("normalized_cutoff") or None,
                "status": "KNOWN" if (r.get("family_status") or "").upper() == "KNOWN" else "NOVEL",
                "mibig": mib,
                "cross_strain_members": None,  # signals "unavailable" to render_block
                "n_strains": None,
                "nearest_mibig": near,
            }
    return out


def render_block(ctx):
    lines = [BEGIN,
             "### GCF cross-strain context  `[store-backed GCF | BiG-SCAPE]`",
             ""]
    st = ctx["status"]
    fam = ctx.get("family_id")
    span = f", spanning {ctx['n_strains']} cohort strain(s)" if ctx.get("n_strains") else ""
    if fam is None:
        lines.append(f"- Family membership: **{st}** context only; no portable family namespace is available{span}.")
    else:
        lines.append(f"- Family: **{st}** GCF (literal id {fam}; namespace `{ctx['qualified_family_id']}`){span}.")
    if ctx["mibig"]:
        anch = "; ".join(f"{a} ({n})" for a, n in ctx["mibig"])
        lines.append(f"- MIBiG anchor(s) in family (architecture-consistent, capacity-level): {anch}.")
    else:
        lines.append("- No MIBiG reference shares this family (no characterized analog at this cutoff).")
    if ctx["nearest_mibig"]:
        a, n, d = ctx["nearest_mibig"]
        lines.append(f"- Nearest characterized cluster: {a} ({n}), GCF distance {d} (0 identical .. 1 maximal).")
    # co-members: None => unavailable (portable); [] => strain-unique; [..] => list
    members = ctx.get("cross_strain_members")
    if members is None:
        lines.append("- Cohort co-members: unavailable from the portable export (no per-BGC family_id); "
                     "use the anchored DB for cohort co-membership.")
    elif members:
        lines.append(f"- Shared with cohort strains: {', '.join(members)}.")
    else:
        lines.append("- Strain-unique at this cutoff (no other cohort strain in this family).")
    lines.append("")
    lines.append("_Capacity-level: GCF membership is domain-architecture similarity, not compound "
                 "identity. Confirm per-BGC against the KCB/Mode B evidence above._")
    lines.append(END)
    return "\n".join(lines)


def inject(card_text, block):
    """Idempotent: replace an existing GCF block, else append under §8 if present, else at end."""
    if BEGIN in card_text and END in card_text:
        pre = card_text.split(BEGIN)[0]
        post = card_text.split(END, 1)[1]
        return pre + block + post
    m = re.search(r"(^##\s*§?8\b.*$)", card_text, re.M)
    if m:
        idx = card_text.find("\n\n", m.end())
        if idx != -1:
            return card_text[:idx + 2] + block + "\n\n" + card_text[idx + 2:]
    return card_text.rstrip() + "\n\n" + block + "\n"


def load_triage(path):
    """Return {(strain_or_blank, bgc_number_str) -> canon locator} from a triage board CSV.

    v9.7.292: the locator is reconstructed from Contig + antiSMASH_Region (canon'd cov-free),
    NOT the display Assembly_Locator column. Tolerates a board with no strain column."""
    out = {}
    with open(path, newline="") as fh:
        rdr = csv.DictReader(fh)
        cols = {c.lower(): c for c in (rdr.fieldnames or [])}
        def col(*names):
            for n in names:
                if n in cols:
                    return cols[n]
            return None
        sc = col("strain", "strain_id")
        bc = col("bgc", "bgc_number", "bgc_id", "region")
        lc = col("locator", "node.region", "node_region")          # explicit locator if present
        contig_c = col("contig", "node_id", "node")                # else reconstruct from these
        region_c = col("antismash_region", "region_id")
        for row in rdr:
            strain = (row.get(sc) or "").strip() if sc else ""
            digits = re.sub(r"\D", "", (row.get(bc) or "")) if bc else ""
            bgc = str(int(digits)) if digits else ""
            loc = ""
            if lc and (row.get(lc) or "").strip():
                loc = canon_locator((row.get(lc) or "").strip())
            elif contig_c and region_c:
                cg = (row.get(contig_c) or "").strip()
                rg = (row.get(region_c) or "").strip()
                if cg and rg:
                    loc = canon_locator(f"{cg}.{rg}")
            if bgc and loc:
                out[(strain, bgc)] = loc
    return out


def main():
    ap = argparse.ArgumentParser(description="Write BiG-SCAPE GCF context into Mamey Mode B cards + triage board.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--db", help="anchored BiG-SCAPE 2 SQLite DB (full context incl. co-members)")
    src.add_argument("--from-tsv", help="portable AS_per_BGC_annotation.tsv (no co-members)")
    ap.add_argument("--strain", help="strain id (required with --from-tsv; also fills a strain-less triage board)")
    ap.add_argument("--package", help="Mamey package dir (auto-finds triage CSV + Mode B cards)")
    ap.add_argument("--triage", help="triage board CSV (overrides package auto-find)")
    ap.add_argument("--cards-dir", help="dir of *_ModeB.md cards (overrides package auto-find)")
    ap.add_argument("--cutoff", default="0.5")
    ap.add_argument("--run-id", help="exact BiG-SCAPE run id (required with --db)")
    ap.add_argument("--mibig-index", help="mibig_reference_index.bacterial.json for compound names")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    triage = a.triage
    cards_dir = a.cards_dir
    if a.package:
        if not triage:
            cands = glob.glob(os.path.join(a.package, "**", "*riage*.csv"), recursive=True)
            triage = cands[0] if cands else None
        if not cards_dir:
            cands = glob.glob(os.path.join(a.package, "**", "*_ModeB.md"), recursive=True)
            cards_dir = os.path.dirname(cands[0]) if cands else None
    if not triage:
        sys.exit("ERROR: no triage board found (need BGC#->node.region bridge). Pass --triage.")
    if not cards_dir:
        sys.exit("ERROR: no Mode B cards found. Pass --cards-dir.")

    names = load_mibig_names(a.mibig_index)
    if a.db:
        if a.run_id is None:
            raise NamespaceError("RUN_ID_REQUIRED", "--db requires an explicit run_id")
        ctx = gcf_context(a.db, a.cutoff, names, run_id=a.run_id)
    else:
        if not a.strain:
            sys.exit("ERROR: --from-tsv requires --strain.")
        ctx = tsv_context(a.from_tsv, a.strain, a.cutoff)
    bridge = load_triage(triage)

    cards = glob.glob(os.path.join(cards_dir, "*_ModeB.md"))
    updated = skipped = 0
    fname = re.compile(r"^(?P<strain>.+?)_BGC0*(?P<num>\d+)_ModeB\.md$", re.I)
    for card in cards:
        m = fname.match(os.path.basename(card))
        if not m:
            skipped += 1
            continue
        strain, num = m.group("strain"), m.group("num")
        # bridge may be keyed on (strain, num) or ("", num) for a strain-less board
        loc = bridge.get((strain, num))
        if loc is None:
            loc = bridge.get(("", num))
        key = f"{strain}:{loc}" if loc else None
        if not key or key not in ctx:
            skipped += 1
            continue
        block = render_block(ctx[key])
        with open(card, encoding="utf-8") as _f:
            text = _f.read()
        new = inject(text, block)
        if new != text:
            if not a.dry_run:
                # v9.7.374 fix: was a bare open(card,"w") -- this rewrites a real Mode-B card
                # in place inside a package directory (confirmed production-invoked by
                # tools/bigscape_pipeline.py), potentially in a batch over many cards. An
                # interrupted write mid-batch (kill, disk full) truncates a card that may already
                # be inside a sealed/checksummed package, with no tmp+replace protection.
                atomic_write_text(card, new)
            updated += 1
    emit(f"cards updated: {updated} | skipped (no locator match): {skipped} | "
          f"GCF contexts available: {len(ctx)}{' [DRY RUN]' if a.dry_run else ''}")


if __name__ == "__main__":
    try:
        main()
    except NamespaceError as error:
        # v9.7.405: sys.stderr.write, not print() — a typed-refusal diagnostic, and the
        # print ratchet is at ceiling. Registering these front doors as EXCLUDED files
        # would have dropped their PRE-EXISTING prints from the count too: a lower
        # measure without paying anything.
        sys.stderr.write(public_error(error) + "\n")
        sys.exit(2)
