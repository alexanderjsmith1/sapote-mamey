"""Source-bound Mode B interpretation across supported contig neighbourhoods.

This reader grants interpretation context, never physical linkage or production.
It uses effective gene adjudications, not an invented rescue probability.
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

SCHEMA = "modeb_locus_scope_v1"
ROUTED_SECTIONS = {3, 5, 6, 7, 8, 10, 19, 22, 26, 36, 37, 38, 43, 44, 50}
MARKER = re.compile(r"<!-- MODEB_LOCUS_SCOPE_V1 (\{[^\n]+\}) -->")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _hash_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def assembly_cds(source, member=None):
    """Read one unambiguous offline GenBank source without deriving gene function."""
    from Bio import SeqIO
    source = Path(source)
    if zipfile.is_zipfile(source):
        if not member:
            raise ValueError("ZIP requires an explicit whole-assembly member")
        with zipfile.ZipFile(source) as archive:
            matches = [info for info in archive.infolist() if info.filename == member]
            if len(matches) != 1 or matches[0].is_dir():
                raise ValueError("whole-assembly member must name one unique regular ZIP member")
            raw = archive.read(matches[0])
    else:
        if member:
            raise ValueError("whole-assembly member is only valid with a ZIP")
        raw = source.read_bytes()
    genes, seen, contigs = [], set(), set()
    for record in SeqIO.parse(io.StringIO(raw.decode("utf-8")), "genbank"):
        contig = record.name if record.name.startswith("NODE_") else record.id
        if contig in contigs:
            raise ValueError("duplicate whole-assembly contig identity")
        contigs.add(contig)
        for feature in record.features:
            if feature.type != "CDS" or not feature.qualifiers.get("translation"):
                continue
            tag = feature.qualifiers.get("locus_tag", [""])[0]
            if not tag or (contig, tag) in seen:
                raise ValueError("missing or duplicate whole-assembly locus tag")
            seen.add((contig, tag))
            seq = "".join(feature.qualifiers["translation"][0].split()).upper().rstrip("*")
            if not seq or feature.location is None or feature.location.strand not in {-1, 1}:
                raise ValueError("whole-assembly CDS lacks translation or oriented location")
            genes.append(dict(locus_tag=tag, contig=contig, genbank_record_id=record.id,
                              contig_length_bp=len(record.seq), start_1based=int(feature.location.start)+1,
                              end_1based=int(feature.location.end), strand=feature.location.strand,
                              aa_sequence=seq, aa_length=len(seq), aa_sha256=hashlib.sha256(seq.encode("ascii")).hexdigest()))
    if not genes:
        raise ValueError("whole-assembly source contains no translated CDS")
    return genes, hashlib.sha256(raw).hexdigest()


def canonical_identity(value):
    """Normalize only the documented unflagged-contig forms; never infer aliases."""
    parts = str(value).split(" / ")
    if len(parts) == 2 and parts[1].endswith(" (no antiSMASH region)"):
        parts = [parts[0], parts[1].removesuffix(" (no antiSMASH region)"), "no antiSMASH region", "no BGC alias"]
    elif len(parts) == 3 and parts[2] == "no antiSMASH region":
        parts.append("no BGC alias")
    if len(parts) != 4 or not all(parts):
        raise ValueError("incomplete locus identity")
    if (parts[2], parts[3]) != ("no antiSMASH region", "no BGC alias") and not (
            parts[2].startswith("region") and parts[3].startswith("BGC")):
        raise ValueError("invalid region and alias identity")
    return " / ".join(parts)


def load_inventory(path, strain):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("assembly_source"), dict) or not isinstance(data.get("genes"), list):
        raise ValueError("inventory must contain an object source and CDS list")
    if data.get("schema") != "modeb_locus_inventory_v1" or data.get("strain") != strain:
        raise ValueError("inventory schema or strain disagreement")
    source = data["assembly_source"]
    if _hash_file(source["path"]) != source["sha256"]:
        raise ValueError("inventory assembly source hash changed")
    assembly, member_hash = assembly_cds(source["path"], source.get("gbk_member"))
    if source.get("gbk_sha256") and source["gbk_sha256"] != member_hash:
        raise ValueError("inventory GenBank member hash changed")
    assembly_by_key = {(g["contig"], g["locus_tag"]): g for g in assembly}
    seen, genes = set(), []
    for item in data["genes"]:
        if not isinstance(item, dict):
            raise ValueError("inventory CDS must be an object")
        g = dict(item)
        seq = "".join(g.pop("aa_sequence").split()).upper().rstrip("*")
        if not seq or len(seq) != g["aa_length"] or hashlib.sha256(seq.encode("ascii")).hexdigest() != g["aa_sha256"]:
            raise ValueError("inventory amino-acid hash or length disagreement")
        if any(not isinstance(g[key], int) or isinstance(g[key], bool) for key in
               ("start_1based", "end_1based", "contig_length_bp", "strand", "aa_length")) or not (
                1 <= g["start_1based"] <= g["end_1based"] <= g["contig_length_bp"]) or g["strand"] not in {-1, 1}:
            raise ValueError("inventory CDS geometry disagreement")
        g["identities"] = [canonical_identity(x) for x in g["identities"]]
        if not g["identities"] or any(x.split(" / ")[:2] != [strain, g["contig"]] for x in g["identities"]):
            raise ValueError("inventory identity and contig disagreement")
        key = (g["contig"], g["locus_tag"])
        if key in seen:
            raise ValueError("duplicate inventory CDS")
        actual = assembly_by_key.get(key)
        fields = ("start_1based", "end_1based", "strand", "contig_length_bp", "aa_length", "aa_sha256")
        if actual is None or any(g[k] != actual[k] for k in fields):
            raise ValueError("inventory differs from pinned whole-assembly translated CDS")
        if "genbank_record_id" in g and g["genbank_record_id"] != actual["genbank_record_id"]:
            raise ValueError("inventory GenBank record identity disagreement")
        seen.add(key); genes.append(g)
    if not genes or seen != set(assembly_by_key):
        raise ValueError("inventory omits pinned whole-assembly translated CDS")
    sources = [{"path": str(path), "sha256": _hash_file(path)},
               {"path": str(Path(source["path"]).resolve()), "sha256": source["sha256"]}]
    if data.get("package_cds_source"):
        package = data["package_cds_source"]
        if _hash_file(package["path"]) != package["sha256"]:
            raise ValueError("inventory package CDS source hash changed")
        # A file hash pins bytes, not the inventory's claimed canonical membership.
        # Reconcile the exact CDS rows independently before granting core identities.
        with Path(package["path"]).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"strain", "contig", "locus_tag", "start", "end", "strand", "length_aa", "region", "bgc_id"}
            if not required <= set(reader.fieldnames or ()):
                raise ValueError("package CDS source lacks canonical binding columns")
            package_rows = list(reader)
        canonical = defaultdict(set)
        by_key = {(g["contig"], g["locus_tag"]): g for g in genes}
        for row in package_rows:
            if None in row or row["strain"] != strain:
                raise ValueError("package CDS source row or strain disagreement")
            key = (row["contig"], row["locus_tag"])
            g = by_key.get(key)
            if g is None or tuple(int(row[k]) for k in ("start", "end", "strand", "length_aa")) != tuple(
                    g[k] for k in ("start_1based", "end_1based", "strand", "aa_length")):
                raise ValueError("inventory differs from canonical package CDS geometry")
            identity = canonical_identity(" / ".join(row[k] for k in ("strain", "contig", "region", "bgc_id")))
            if identity in canonical[key]:
                raise ValueError("duplicate canonical package CDS membership")
            canonical[key].add(identity)
        for key, g in by_key.items():
            expected = canonical.get(key) or {f"{strain} / {g['contig']} / no antiSMASH region / no BGC alias"}
            if set(g["identities"]) != expected:
                raise ValueError("inventory canonical membership differs from pinned package CDS rows")
        sources.append({"path": str(Path(package["path"]).resolve()), "sha256": package["sha256"]})
    return genes, sources


def build_scope(inventory_path, rescue, core_rows, window_bp=2500):
    """Select core plus SUPPORTED-anchor intervals and retain complete overlapping CDS.

    External matches must agree on sequence hash AND exact contig/locus location.
    Context neighbours are displayed without promotion to accepted pathway genes.
    """
    sources = []
    try:
        if rescue.get("state") != "BOUND":
            raise ValueError("gap-rescue evidence does not bind the focal identity")
        if not isinstance(window_bp, int) or isinstance(window_bp, bool) or window_bp < 0:
            raise ValueError("invalid neighbourhood window")
        focal = canonical_identity(rescue["identity"]); strain, core_contig = focal.split(" / ")[:2]
        genes, sources = load_inventory(inventory_path, strain)
        by_hash = defaultdict(list)
        for g in genes:
            by_hash[g["aa_sha256"]].append(g)
        core = [g for g in genes if focal in g["identities"]]
        expected = {r["locus_tag"] for r in core_rows}
        if not core or {g["locus_tag"] for g in core} != expected:
            raise ValueError("complete core inventory differs from package gene roster")
        by_tag = {g["locus_tag"]: g for g in core}
        for r in core_rows:
            g = by_tag[r["locus_tag"]]
            for key, own in [("start", "start_1based"), ("end", "end_1based"), ("strand", "strand"), ("aa_length", "aa_length")]:
                if key in r and int(r[key]) != g[own]:
                    raise ValueError("core package geometry or length differs from inventory")
        matched, anchors = [], defaultdict(list)
        for row in rescue["rows"]:
            if not row.get("protein_sha256"):
                continue
            where = canonical_identity(row["best_region_identity"])
            candidates = [g for g in by_hash[row["protein_sha256"]]
                          if g["locus_tag"] == row["best_locus"] and where in g["identities"]]
            if len(candidates) != 1:
                raise ValueError("rescue query sequence and exact inventory location do not bind uniquely")
            g = candidates[0]; matched.append((g, row))
            if row["status"] != "PRESENT_IN_CORE" and row["effective_partner_verdict"] == "SUPPORTED":
                anchors[g["contig"]].append(g)
        intervals = [dict(contig=core_contig, start_1based=min(g["start_1based"] for g in core),
                          end_1based=max(g["end_1based"] for g in core), tier="CORE", anchors=[],
                          identities=[focal])]
        selected = {(g["contig"], g["locus_tag"]): {**g, "scope_role": "CORE"} for g in core}
        for contig, aa in sorted(anchors.items()):
            seeds = sorted((max(1, g["start_1based"] - window_bp),
                            min(g["contig_length_bp"], g["end_1based"] + window_bp)) for g in aa)
            merged = []
            for lo, hi in seeds:
                if merged and lo <= merged[-1][1] + 1:
                    merged[-1][1] = max(merged[-1][1], hi)
                else:
                    merged.append([lo, hi])
            for lo, hi in merged:
                neighbours = [g for g in genes if g["contig"] == contig and g["end_1based"] >= lo and g["start_1based"] <= hi]
                if not neighbours:
                    raise ValueError("supported anchor has no neighbourhood CDS")
                anchor_keys = {(g["contig"], g["locus_tag"]) for g in aa}
                for g in neighbours:
                    if selected.get((contig, g["locus_tag"]), {}).get("scope_role") == "CORE":
                        continue
                    selected[(contig, g["locus_tag"])] = {**g, "scope_role": "SUPPORTED_ANCHOR" if (contig, g["locus_tag"]) in anchor_keys else "NEIGHBOUR_CONTEXT"}
                intervals.append(dict(contig=contig, start_1based=min(lo, *(g["start_1based"] for g in neighbours)),
                                      end_1based=max(hi, *(g["end_1based"] for g in neighbours)),
                                      tier="SUPPORTED_CONTEXT", anchors=sorted({g["locus_tag"] for g in aa if g["end_1based"] >= lo and g["start_1based"] <= hi}),
                                      identities=sorted({x for g in neighbours for x in g["identities"]})))
        # Overlapping windows may extend into the same complete CDS. Count that CDS once.
        evidence = defaultdict(list)
        for g, row in matched:
            evidence[(g["contig"], g["locus_tag"])].append({k: row[k] for k in (
                "name", "status", "best_identity_pct", "best_coverage_pct", "run_partner_verdict", "effective_partner_verdict")})
        roster = []
        for key, g in sorted(selected.items()):
            roster.append({**g, "reference_assignments": evidence[key]})
        if len({g["locus_tag"] for g in roster}) != len(roster):
            raise ValueError("selected CDS locus tags are ambiguous across contigs for the gene evidence matrix")
        alternatives = []
        for g, row in matched:
            if (g["contig"], g["locus_tag"]) not in selected:
                alternatives.append(dict(locus_tag=g["locus_tag"], identities=g["identities"], aa_sha256=g["aa_sha256"],
                                         reference=row["name"], ruling=row["effective_partner_verdict"]))
        # Split pieces are existence-bound rival context, never automatic anchors.
        # The saved split table has locations but no q-id; require the inventory
        # translation to exist in the pinned complete query FASTA collection.
        from .modeb_gap_rescue import _fasta
        query_hashes = {hashlib.sha256(seq.encode("ascii")).hexdigest()
                        for source in rescue["sources"] if Path(source["path"]).suffix == ".faa"
                        for seq in _fasta(Path(source["path"])).values()}
        split_context = []
        for row in rescue["splits"]:
            for piece in ("piece1", "piece2"):
                if not row.get(piece + "_locus"):
                    continue
                where = canonical_identity(row[piece + "_region_identity"])
                matches = [g for g in genes if g["locus_tag"] == row[piece + "_locus"] and where in g["identities"]]
                if len(matches) != 1 or matches[0]["aa_sha256"] not in query_hashes:
                    raise ValueError("split piece location and inventory AA sequence do not bind the saved query collection")
                g = matches[0]
                split_context.append(dict(locus_tag=g["locus_tag"], identities=g["identities"], aa_sha256=g["aa_sha256"],
                                          reference=row.get("name", ""), ruling=row["split_call"], piece=piece))
        payload = dict(schema=SCHEMA, state="BOUND", focal_identity=focal, window_bp=window_bp,
                       recipe={"inventory_path": str(Path(inventory_path).resolve()),
                               "gap_rescue": rescue["reader_inputs"]},
                       intervals=intervals, genes=roster, alternatives=alternatives, split_context=split_context,
                       selected_contigs=len({i["contig"] for i in intervals}), selected_cds=len(roster),
                       selected_unique_aa_sequences=len({g["aa_sha256"] for g in roster}),
                       physical_joins=0, membership_policy="Core plus effective SUPPORTED-anchor neighbourhood context",
                       sources=sources + rescue["sources"])
        payload["scope_sha256"] = _digest(payload)
        return payload
    except (OSError, ValueError, KeyError, TypeError, IndexError, UnicodeError) as exc:
        return dict(schema=SCHEMA, state="HOLD", reason=str(exc), sources=sources)


def marker(scope):
    return "<!-- MODEB_LOCUS_SCOPE_V1 " + json.dumps(scope, sort_keys=True, separators=(",", ":")) + " -->"


def _cell(value):
    return html.escape(str(value)).replace("|", "\\|").replace("\n", " ")


def render_scope(scope, section):
    if scope["state"] != "BOUND":
        return "**EXPANDED_LOCUS_SOURCE_HOLD:** " + _cell(scope["reason"])
    intro = (f"**Expanded-locus interpretation scope:** {scope['selected_cds']} distinct CDS across "
             f"{scope['selected_contigs']} contigs ({scope['selected_unique_aa_sequences']} distinct AA sequences). "
             "Core-region counts remain separate. Supported anchors select neighbourhood context, not accepted "
             "membership for every neighbour; no physical join or product is inferred.")
    if section not in {3, 26, 50}:
        guide = {22: "GECCO probabilities and called membership must be interpreted across every selected interval; reference gene names are a separate layer.",
                 44: "Integrate PCoA membership and figures for supported and contextual proteins across this scope; projection distance is not pathway membership.",
                 19: "Evaluate core-only and expanded-locus completeness separately without summing overlapping modular placements.",
                 43: "Separate supported context, weaker alternatives, repeated-module rivals and physical-link evidence."}.get(section,
                 "Assess the pathway role and competing models over the selected intervals, retaining locus-specific sources.")
        return intro + "\n\n" + guide
    lines = [intro, "", "| Complete locus identity | Selected interval bp | Scope | Supported anchors |", "|---|---|---|---|"]
    for i in scope["intervals"]:
        lines.append("| " + " | ".join(_cell(x) for x in ("; ".join(i["identities"]),
            f"{i['start_1based']}-{i['end_1based']}", i["tier"], "; ".join(i["anchors"]))) + " |")
    if section == 50:
        lines += ["", "#### Complete expanded-locus CDS roster", "",
                  "| Locus and exact identity | Geometry and length | Scope role and reference rulings | Normalized AA SHA-256 |",
                  "|---|---|---|---|"]
        for g in scope["genes"]:
            assignments = "; ".join(f"{r['name']} {r['best_identity_pct']}% identity / {r['best_coverage_pct']}% reference coverage; {r['run_partner_verdict'] or 'core'} to {r['effective_partner_verdict'] or 'core'}" for r in g["reference_assignments"])
            lines.append("| " + " | ".join(_cell(x) for x in (g["locus_tag"] + "; " + "; ".join(g["identities"]),
                f"{g['start_1based']}-{g['end_1based']}; strand {g['strand']}; {g['aa_length']} aa",
                g["scope_role"] + "; " + (assignments or "Neighbourhood context; no admitted reference assignment"), g["aa_sha256"])) + " |")
    if section == 26 and scope["alternatives"]:
        lines += ["", "**Other reference finds retained outside the primary interpretation scope:**", "",
                  "| Locus and exact identity | Reference | Effective ruling | AA SHA-256 |", "|---|---|---|---|"]
        for g in scope["alternatives"]:
            lines.append("| " + " | ".join(_cell(x) for x in (g["locus_tag"] + "; " + "; ".join(g["identities"]),g["reference"],g["ruling"],g["aa_sha256"])) + " |")
    if section == 26 and scope.get("split_context"):
        lines += ["", "**Split-piece rival context (genomic existence only; not a completed gene or primary anchor):**", "",
                  "| Locus and exact identity | Reference / piece | Saved split ruling | Inventory AA SHA-256 |", "|---|---|---|---|"]
        for g in scope["split_context"]:
            lines.append("| " + " | ".join(_cell(x) for x in (g["locus_tag"] + "; " + "; ".join(g["identities"]),
                g["reference"] + " / " + g["piece"],g["ruling"],g["aa_sha256"])) + " |")
    return "\n".join(lines)


def findings(md, *, require_expanded=False):
    """Structural checks pin scope sources and reject dropped selected genes.

    This verifies roster persistence, not scientific truth of authored prose.
    """
    from .modeb_markdown import active_markdown
    metadata = active_markdown(md, preserve_comments=True)
    matches = MARKER.findall(metadata)
    if not matches:
        if require_expanded or "<!-- MODEB_EXPANDED_LOCUS_REQUIRED -->" in metadata:
            return [dict(severity="ERROR", code="LOCUS_SCOPE_MISSING", section=3,
                         message="Expanded-locus card lost its source-bound scope declaration.")]
        return []  # Existing v2 cards remain backward compatible.
    def f(code, section, msg):
        return dict(severity="ERROR", code=code, section=section, message=msg)
    if len(matches) != 1:
        return [f("LOCUS_SCOPE_DUPLICATE", 3, "Expected one expanded-locus scope declaration.")]
    try:
        scope = json.loads(matches[0]);expected = scope.pop("scope_sha256", None)
        if scope.get("state") != "BOUND":
            return [f("LOCUS_SCOPE_HOLD", 3, scope.get("reason", "Unbound scope"))]
        if expected != _digest(scope):
            raise ValueError("scope declaration hash changed")
        if scope.get("schema") != SCHEMA or scope.get("physical_joins") != 0:
            raise ValueError("invalid scope schema or unsupported physical join")
        # Check every saved source, so edited inventory or adjudication requires re-emission.
        for source in scope["sources"]:
            if _hash_file(source["path"]) != source["sha256"]:
                raise ValueError("scope source changed: " + source["path"])
        # Recompute from pinned inputs: changing both a hidden roster and its checksum
        # must not erase a selected neighbour or promote an unsupported alternative.
        from .modeb_gap_rescue import load_gap_rescue
        recipe = scope["recipe"]
        inventory, _ = load_inventory(recipe["inventory_path"], scope["focal_identity"].split(" / ")[0])
        core = [{"locus_tag": g["locus_tag"], "start": g["start_1based"],
                 "end": g["end_1based"], "aa_length": g["aa_length"]}
                for g in inventory if scope["focal_identity"] in g["identities"]]
        rebuilt = build_scope(recipe["inventory_path"], load_gap_rescue(**recipe["gap_rescue"]), core,
                              scope["window_bp"])
        if rebuilt.get("scope_sha256") != expected:
            raise ValueError("scope roster or intervals differ from recomputed pinned inputs")
        keys = [(g["contig"], g["locus_tag"]) for g in scope["genes"]]
        if len(set(keys)) != len(keys) or scope["selected_cds"] != len(keys):
            raise ValueError("scope roster count or identity disagreement")
        from .modeb_markdown import active_markdown
        active = active_markdown(md)
        bodies = {int(n): b for n,b in re.findall(r"^## §(\d+) [^\n]*\n(.*?)(?=^## §\d+ |\Z)", active, re.M | re.S)}
        found = []
        for n in (3, 26, 50):
            visible = re.sub(r"<!--.*?-->", "", bodies.get(n, ""), flags=re.S)
            for i in scope["intervals"]:
                for identity in i["identities"]:
                    if _cell(identity) not in visible:
                        found.append(f("LOCUS_SCOPE_CONTIG_DROPPED", n, "Selected locus identity omitted: " + identity))
        tail = re.sub(r"<!--.*?-->", "", bodies.get(50, ""), flags=re.S)
        for g in scope["genes"]:
            rows = [line for line in tail.splitlines() if re.search(r"(?<![A-Za-z0-9_])"+re.escape(g["locus_tag"])+r"(?![A-Za-z0-9_])", line)]
            if not any(g["aa_sha256"] in line and all(_cell(x) in line for x in g["identities"]) for line in rows):
                found.append(f("LOCUS_SCOPE_GENE_DROPPED", 50, "Selected CDS lacks a bound exact-identity AA-hash evidence row: " + g["locus_tag"]))
        return found
    except (OSError, ValueError, KeyError, TypeError, IndexError, UnicodeError) as exc:
        return [f("LOCUS_SCOPE_SOURCE_INVALID", 3, str(exc))]


def context_loci(md, package=None, bgc=None):
    """Validated genomic existence only; never extend the core membership roster."""
    if not MARKER.search(md) or findings(md):
        return set()
    scope = json.loads(MARKER.findall(md)[0])
    strain, _, _, alias = scope["focal_identity"].split(" / ")
    declared = re.findall(r"<!-- MODE B \| canonical_identity: (.*?) \| contract: current50_v2 \|", md)
    first = md.splitlines()[0] if md else ""
    if declared != [scope["focal_identity"]] or not first.startswith("<!-- MODE B | canonical_identity: " + scope["focal_identity"] + " |"):
        return set()
    from .modeb_markdown import active_markdown
    header = re.search(r"^#\s*Mode B\s*[\u2014-]\s*([^/\n]+?)\s*/", active_markdown(md), re.M)
    if not header or header.group(1).strip() != strain or (bgc and alias != bgc):
        return set()
    if package:
        inventory = json.loads(Path(scope["recipe"]["inventory_path"]).read_text())
        pin = inventory.get("package_cds_source", {})
        if not pin or Path(pin["path"]).resolve().parent != Path(package).resolve():
            return set()
    return {g["locus_tag"] for g in scope["genes"] + scope["alternatives"] + scope.get("split_context", [])}
