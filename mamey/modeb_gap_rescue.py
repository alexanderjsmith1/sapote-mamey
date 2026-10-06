"""Read existing gap-rescue evidence for current50_v2; no searches, scoring or joins.

BOUND means exact receipt identity and internally reconciled saved sources. Protein
hashes bind the saved query FASTA, not an independently validated assembly.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import math
from collections import Counter
from pathlib import Path

STATUSES = ("PRESENT_IN_CORE", "MISSING_FOUND_CLEAR", "MISSING_FOUND_AMBIGUOUS", "MISSING_NOT_FOUND")
VERDICTS = {"", "SUPPORTED", "PARALOG_FAMILY", "HOUSEKEEPING_CONTEXT", "SINGLE_GENE"}
REQUIRED = {"reference_gene", "name", "reference_gene_kind", "status", "best_locus", "best_protein",
            "best_len_aa", "best_region_identity", "best_identity_pct", "best_coverage_pct", "partner_verdict"}


def _table(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f, delimiter="\t")
        rows = list(r)
        if not r.fieldnames or any(None in row for row in rows):
            raise ValueError(f"malformed TSV: {path.name}")
        return set(r.fieldnames), rows


def _fasta(path):
    seqs, key, parts = {}, None, []
    def save():
        if key is not None:
            if key in seqs:
                raise ValueError("duplicate query protein in FASTA")
            seqs[key] = "".join("".join(parts).split()).upper().rstrip("*")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(">"):
            save(); key = line[1:].split()[0]; parts = []
        elif line.strip():
            if key is None:
                raise ValueError("sequence before FASTA identifier")
            parts.append(line)
    save()
    return seqs


def _full_identity(identity):
    parts = identity.split(" / ")
    return len(parts) == 4 and all(parts) and parts[2].startswith("region") and parts[3].startswith("BGC")


def load_gap_rescue(root, identity, verdicts_tsv=None, gene_adjudication_tsv=None):
    """Read one exact-identity run (a leaf folder or its strain parent); failures are holds."""
    sources = []
    def bound(path):
        sources.append({"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        return path
    try:
        root = Path(root)
        if not _full_identity(identity):
            raise ValueError("focal four-part identity is incomplete")
        direct = root / "gap_rescue_receipt.json"
        candidates = [direct] if direct.is_file() else sorted(root.glob("*/gap_rescue_receipt.json"))
        matches = [(p, json.loads(p.read_text(encoding="utf-8"))) for p in candidates]
        if any(not isinstance(r, dict) for _, r in matches):
            raise ValueError("receipt must be a JSON object")
        matches = [(p, r) for p, r in matches if r.get("core") == identity]
        if len(matches) != 1:
            raise ValueError(f"expected one exact-identity receipt; found {len(matches)}")
        receipt_path, receipt = matches[0]
        folder = receipt_path.parent
        bound(receipt_path)
        fields, rows = _table(bound(folder / "gap_rescue.tsv"))
        if not REQUIRED <= fields:
            raise ValueError("gene table lacks required fields")
        n = receipt["reference_genes"]
        if not isinstance(n, int) or isinstance(n, bool) or n < 1 or len(rows) != n:
            raise ValueError("reference-gene denominator disagrees with table")
        if len({r["reference_gene"] for r in rows}) != n:
            raise ValueError("duplicate reference-gene row")
        if any(r["status"] not in STATUSES for r in rows):
            raise ValueError("unknown search status")
        counts = Counter(r["status"] for r in rows)
        for status in STATUSES:
            if receipt[status.lower()] != counts[status]:
                raise ValueError(f"receipt/table count mismatch: {status}")
        faa = folder / "gap_rescue_proteins.faa"
        if not faa.is_file():
            faa = folder.parent / "gap_rescue_proteins.faa"
        seqs = _fasta(bound(faa))
        for row in rows:
            core = row["status"] == "PRESENT_IN_CORE"
            if row["status"] != "MISSING_NOT_FOUND":
                if not row["best_locus"] or not row["best_region_identity"]:
                    raise ValueError("matched gene lacks location")
                if core != (row["best_region_identity"] == identity):
                    raise ValueError("gene status disagrees with focal location")
                aa = seqs[row["best_protein"]]
                if not aa or len(aa) != int(row["best_len_aa"]):
                    raise ValueError("saved protein length disagrees with gene table")
                for field in ("best_identity_pct", "best_coverage_pct"):
                    v = float(row[field])
                    if not math.isfinite(v) or not 0 <= v <= 100:
                        raise ValueError(f"invalid {field}")
                row["protein_sha256"] = hashlib.sha256(aa.encode("ascii")).hexdigest()
            else:
                row["protein_sha256"] = ""
            if row["partner_verdict"] not in VERDICTS:
                raise ValueError("unknown partner verdict")
            row["run_partner_verdict"] = row["partner_verdict"]
            row["effective_partner_verdict"] = row["partner_verdict"]
        adjudication = (Path(gene_adjudication_tsv) if gene_adjudication_tsv else
                        folder.parent / (folder.name + "_ADJUDICATION.tsv"))
        if gene_adjudication_tsv or adjudication.is_file():
            afields, overrides = _table(bound(adjudication))
            if not {"reference_gene", "candidate_locus", "verdict"} <= afields:
                raise ValueError("adjudication lacks binding fields")
            seen = set()
            for override in overrides:
                key = (override["reference_gene"], override["candidate_locus"])
                if key in seen or override["verdict"] not in VERDICTS - {""}:
                    raise ValueError("duplicate or invalid adjudication")
                seen.add(key)
                matched = [r for r in rows if (r["name"], r["best_locus"]) == key]
                if len(matched) != 1 or matched[0]["status"] in ("PRESENT_IN_CORE", "MISSING_NOT_FOUND"):
                    raise ValueError("adjudication does not bind one external find")
                where = matched[0]["best_region_identity"]
                if override.get("contig") and override["contig"] != where.split(" / ")[1].split(" (no antiSMASH region)")[0]:
                    raise ValueError("adjudication contig disagrees with external find")
                matched[0]["effective_partner_verdict"] = override["verdict"]
        sfields, splits = _table(bound(folder / "gap_rescue_split_genes.tsv"))
        if not {"split_call", "piece1_region_identity", "piece2_region_identity"} <= sfields:
            raise ValueError("split table lacks location/call fields")
        if "split_genes" in receipt and len(receipt["split_genes"]) != len(splits):
            raise ValueError("receipt/split-table count mismatch")
        if any(s["split_call"] not in {"CLEAR", "WEAK", "RIVAL_STRONGER", "MODULAR_UNRESOLVED"} for s in splits):
            raise ValueError("unknown split ruling")
        external = [r for r in rows if r["status"] in STATUSES[1:3]]
        supported = [r for r in external if r["effective_partner_verdict"] == "SUPPORTED"]
        pair_verdicts = []
        if verdicts_tsv:
            pfields, prows = _table(bound(Path(verdicts_tsv)))
            if not {"strain", "core identity", "partner contig", "partner region", "verdict", "rule", "source"} <= pfields:
                raise ValueError("pair-verdict table lacks exact identity fields")
            pair_verdicts = [p for p in prows if p["core identity"] == identity]
            seen = set()
            for p in pair_verdicts:
                if p["strain"] != identity.split(" / ")[0] or not p["partner contig"] or not p["verdict"]:
                    raise ValueError("pair verdict lacks strain/contig/ruling binding")
                if p["partner region"]:
                    parts = p["partner region"].split(" / ")
                    if len(parts) < 2 or parts[0] != p["strain"] or parts[1] != p["partner contig"]:
                        raise ValueError("pair verdict contig/location disagreement")
                key = (p["partner contig"], p["partner region"])
                if key in seen:
                    raise ValueError("duplicate pair-verdict identity")
                seen.add(key)
        focal_splits = [s for s in splits if s["split_call"] == "CLEAR" and identity in
                        (s["piece1_region_identity"], s["piece2_region_identity"])]
        biosynthetic = [r for r in rows if r["reference_gene_kind"] in ("biosynthetic", "biosynthetic-additional")]
        return dict(state="BOUND", identity=identity, receipt=receipt, rows=rows, splits=splits,
                    reader_inputs={"root": str(folder.resolve()), "identity": identity,
                                   "verdicts_tsv": str(Path(verdicts_tsv).resolve()) if verdicts_tsv else None,
                                   "gene_adjudication_tsv": str(adjudication.resolve()) if adjudication.is_file() else None},
                    sources=sources, counts={s: counts[s] for s in STATUSES}, supported_external=len(supported),
                    pair_verdicts=pair_verdicts, pair_verdicts_supplied=bool(verdicts_tsv),
                    supported_locations=sorted({r["best_region_identity"] for r in supported}),
                    focal_clear_splits=len(focal_splits),
                    other_clear_splits=sum(s["split_call"] == "CLEAR" for s in splits) - len(focal_splits),
                    biosynthetic_reference_genes=len(biosynthetic),
                    biosynthetic_in_core=sum(r["status"] == "PRESENT_IN_CORE" for r in biosynthetic))
    except (OSError, ValueError, KeyError, TypeError, IndexError, UnicodeError) as exc:
        return dict(state="HOLD", identity=identity, reason=str(exc), sources=sources)


def _cell(value):
    return html.escape(str(value)).replace("|", "\\|").replace("\n", " ").replace("`", "\\`")


def render_impact(result):
    if result["state"] != "BOUND":
        return "**RESCUE_EVIDENCE_HOLD:** " + _cell(result["reason"])
    n, count = result["receipt"]["reference_genes"], result["counts"]["PRESENT_IN_CORE"]
    split_note = (f"{result['focal_clear_splits']} CLEAR split-gene candidate(s) involving the focal region"
                  if result["receipt"]["split_gene_check"] == "run" else
                  "split-gene assessment limited: " + _cell(result["receipt"]["split_gene_check"]))
    return (f"**Gap-rescue interpretation inputs (§26):** {count} of {n} reference genes in the focal region; "
            f"{result['supported_external']} supported external reference-gene assignment(s); "
            f"{split_note}. "
            "Gene-level support and pair-level adjudication are distinct. "
            "These are reference-guided interpretation inputs, not independent product evidence or physical joins.")


def render_section(result):
    if result["state"] != "BOUND":
        return render_impact(result) + "\n\nA source hold establishes no rescue count or biological absence."
    r, counts = result["receipt"], result["counts"]
    out = [f"**Focal identity:** {_cell(result['identity'])}",
           f"**Reference:** {_cell(r['reference'])}; {_cell(r.get('reference_name', ''))}; "
           f"selection: {_cell(r.get('reference_source', ''))}.", "", render_impact(result), "",
           f"**Biosynthetic reference genes in core:** {result['biosynthetic_in_core']} of "
           f"{result['biosynthetic_reference_genes']}. This denominator differs from all reference genes.",
           f"**Search status counts:** clear elsewhere {counts['MISSING_FOUND_CLEAR']}; ambiguous elsewhere "
           f"{counts['MISSING_FOUND_AMBIGUOUS']}; no qualifying match {counts['MISSING_NOT_FOUND']}. "
           "A clear search match is distinct from its effective partner ruling.",
           "Physical contig joins inferred: **0**. Supported assignments remain association candidates.", "",
           "**Source-bound reference proteins** (hashes bind normalized saved query FASTA, not an independent assembly audit):", "",
           "| Reference gene / role | Match / exact location | Identity / reference coverage | Search status | Run → effective partner ruling | Protein SHA-256 |",
           "|---|---|---|---|---|---|"]
    for row in result["rows"]:
        values = [f"{row['name']} / {row['reference_gene_kind']}",
                  f"{row['best_locus']} / {row['best_region_identity']}",
                  f"{row['best_identity_pct']} / {row['best_coverage_pct']}", row["status"],
                  f"{row['run_partner_verdict'] or 'within core'} → {row['effective_partner_verdict'] or 'within core'}",
                  row["protein_sha256"]]
        out.append("| " + " | ".join(_cell(v) for v in values) + " |")
    out += ["", f"**Split-gene check:** {_cell(r['split_gene_check'])}; "
            f"CLEAR candidates involving focal region {result['focal_clear_splits']}; "
            f"CLEAR candidates elsewhere {result['other_clear_splits']}."]
    if result["splits"]:
        out += ["", "| Reference gene | Piece 1 / exact location | Piece 2 / exact location | Ruling |",
                "|---|---|---|---|"]
        for s in result["splits"]:
            out.append("| " + " | ".join(_cell(v) for v in (s.get("name", ""),
                f"{s.get('piece1_locus', '')} / {s['piece1_region_identity']}",
                f"{s.get('piece2_locus', '')} / {s['piece2_region_identity']}", s["split_call"])) + " |")
    out += ["", "**Pair-level review** (kept separate from gene-level support):"]
    if result["pair_verdicts_supplied"]:
        if result["pair_verdicts"]:
            out += ["", "| Exact partner identity | Pair ruling | Reason | Review source |", "|---|---|---|---|"]
            for p in result["pair_verdicts"]:
                out.append("| " + " | ".join(_cell(v) for v in
                    (p["partner region"] or p["partner contig"], p["verdict"], p["rule"], p["source"])) + " |")
        else:
            out.append("The supplied pair-review table contains no exact focal-identity row; this is not a rejected or accepted pair.")
    else:
        out.append("A pair-review source was not supplied to this reader. Gene-level support establishes no pair-level acceptance.")
    out += ["", "**Source receipts:**"]
    out += [f"- `{_cell(s['path'])}` — SHA-256 `{s['sha256']}`" for s in result["sources"]]
    out += ["", "<!-- Author: integrate these reviewed inputs into §§3, 5–8, 10, 19, 22, 36–38, 43 and 50. "
            "Assess alternative references, functional complementarity, competing loci and boundary evidence. "
            "Shared KCB/reference homology is not independent corroboration. Supported associations do not prove "
            "one pathway, exact product, production, activity or a nucleotide join. -->"]
    return "\n\n".join(out[:2]) + "\n" + "\n".join(out[2:])
