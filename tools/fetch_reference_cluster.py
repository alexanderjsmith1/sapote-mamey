#!/usr/bin/env python3
r"""fetch_reference_cluster — reconstruct a cluster GenBank from the BiG-SCAPE DB or NCBI.

The comparative tools (clinker, cluster_gene_compare, extract_cluster) all consume GBKs, but
there was no first-class way to *get* a reference or cohort cluster as a GBK — the DB->CDS logic
was trapped inside bgc_reference_align (returning internal dicts, not files), so every
comparison against a MIBiG reference or a cohort member meant hand-reconstructing a GBK. This
exposes that as a shared step, and improves on the hand-rolled version: the anchored BiG-SCAPE
DB stores Pfam domains (`hsp`) alongside every CDS (`cds.aa_seq`), so the reconstructed GBK comes
out **annotated** — gene names flow straight into clinker and cluster_gene_compare's label logic.

    fetch_reference_cluster.py \
        --db anchored.db \
        --acc BGC0000877:polyoxin \        # MIBiG or cohort cluster from the DB (repeatable)
        --ncbi MF055656.1:nikkomycin \      # NCBI nucleotide efetch (repeatable)
        --outdir refs/

Produces refs/<label>.gbk (annotated, ready to compare). Capacity/architecture-level: a
reconstructed reference is the characterised cluster's genes; comparison to it is homology.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, hashlib, json, sqlite3, sys, urllib.parse, urllib.request, tempfile, os, re
from contextlib import contextmanager
from pathlib import Path
try:  # v9.7.438 output-label containment (see mamey/path_safety.py)
    from mamey.path_safety import contained_output_path, safe_label
except ImportError:  # bare-script run: bundle root is one level up
    import os as _ps_os, sys as _ps_sys
    _ps_sys.path.insert(0, _ps_os.path.dirname(_ps_os.path.dirname(_ps_os.path.abspath(__file__))))
    from mamey.path_safety import contained_output_path, safe_label

# minimal Pfam accession -> short name map for common BGC domains (falls back to the accession)
PFAM = {
    "PF04055": "radical_SAM", "PF00155": "aminotransferase", "PF00583": "GNAT_acetyltransferase",
    "PF13302": "acetyltransferase", "PF00743": "FMO_monooxygenase", "PF00440": "TetR_regulator",
    "PF00561": "ab_hydrolase", "PF00106": "SDR", "PF13561": "SDR", "PF01408": "oxidoreductase",
    "PF00696": "aa_kinase", "PF02543": "carbamoyltransferase", "PF02786": "carbamoylP_synthase",
    "PF07690": "MFS_transporter", "PF00291": "PLP_enzyme", "PF00202": "aminotransferase_III",
    "PF00483": "nucleotidyltransferase", "PF13439": "glycosyltransferase", "PF00534": "glycosyltransferase",
    "PF00296": "luciferase_monooxygenase", "PF08240": "alcohol_dehydrogenase", "PF00107": "ADH",
    "PF01266": "FAD_oxidoreductase", "PF00990": "GGDEF", "PF00196": "LuxR_regulator",
    "PF03704": "BTAD_regulator", "PF00702": "HAD_hydrolase", "PF13508": "acetyltransferase",
    "PF00501": "AMP_binding", "PF00668": "condensation", "PF00109": "ketosynthase",
    "PF02801": "ketosynthase_C", "PF08659": "KR_domain", "PF00975": "thioesterase",
    "PF13193": "AMP_binding_C", "PF00550": "PP_binding", "PF00733": "asparagine_synthase",
    "PF13471": "lasso_B2_peptidase", "PF05147": "lanthionine_LanC", "PF04738": "lanthionine_LanB",
}


def _pfam_name(acc):
    return PFAM.get(acc, acc)


def select_gbk(c, acc):
    """Select one path-bound reference, with exact accession-token admission.

    MIBiG requires its seven-digit identity. NCBI-shaped selectors require an
    explicit version and exact token boundaries; other selectors are literal
    path substrings and assert only the chosen source path, not accession identity.

    `acc` is matched as plain text: SQL wildcards in it (`_`, `%`) are escaped, so `AS-1_NODE_4` cannot match
    `AS-1xNODE_4`. Zero matches raise KeyError; more than one raises ValueError naming them. The first match is
    never taken silently, because a comparison against the wrong locus still looks like a successful run."""
    if not isinstance(acc, str) or not acc.strip():
        raise ValueError("reference selector must be nonempty")
    accession = re.fullmatch(r"(?:BGC[0-9]{7}|[A-Z]{1,6}[0-9]{5,12}|[A-Z]{2}_(?:[A-Z]{1,6})?[0-9]+)(?:\.[0-9]+)?", acc)
    if re.fullmatch(r"BGC[0-9]+", acc) and not re.fullmatch(r"BGC[0-9]{7}", acc):
        raise ValueError("MIBiG accession must contain all seven digits; prefixes and BGC aliases are not accession identities")
    if accession and not acc.startswith("BGC") and "." not in acc:
        raise ValueError("NCBI accession selection requires its explicit version")
    pat = "%" + acc.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    rows = c.execute("SELECT id, path FROM gbk WHERE path LIKE ? ESCAPE '\\'", (pat,)).fetchall()
    if accession:
        boundary = re.compile(r"(?<![A-Za-z0-9])" + re.escape(acc) + r"(?![A-Za-z0-9]|\.[0-9])")
        rows = [(identifier, path) for identifier, path in rows if boundary.search(path)]
    if not rows:
        raise KeyError(f"{acc} not found in DB gbk.path")
    if len(rows) > 1:
        shown = "; ".join(p for _, p in rows[:5]) + (f"; +{len(rows) - 5} more" if len(rows) > 5 else "")
        raise ValueError(f"{acc} matches {len(rows)} records in gbk.path ({shown}). Give a substring that "
                         "selects exactly one record, e.g. the full region file name.")
    return rows[0]


def file_binding(path):
    """Bind a local source or output to its bytes, without embedding sequence data."""
    p = Path(path).resolve()
    digest = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(p), "sha256": digest.hexdigest()}


def write_selection_receipt(path, references, outputs, *, output_paths=None, **context):
    bindings = [file_binding(p) for p in outputs]
    if output_paths is not None:
        if len(output_paths) != len(bindings):
            raise ValueError("receipt output binding count mismatch")
        for binding, final in zip(bindings, output_paths):
            binding["path"] = str(Path(final).resolve())
    receipt = {"schema": "sapote.reference_selection.v1", "references": references,
               "outputs": bindings, **context}
    Path(path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")



def output_destinations(outdir, names):
    """Preflight an entirely new output set; existing files are never replaced."""
    root = Path(outdir).resolve()
    if root.exists() and not root.is_dir():
        raise ValueError(f"output root is not a directory: {root}")
    paths = []
    for name in names:
        if Path(name).name != name or name in ("", ".", ".."):
            raise ValueError(f"invalid output basename: {name!r}")
        raw = root / name
        target = raw.resolve()
        if target.parent != root or raw.is_symlink():
            raise ValueError(f"output path escapes root or is a symlink: {raw}")
        if raw.exists():
            raise ValueError(f"output already exists; use a fresh output directory: {raw}")
        paths.append(target)
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate output destinations")
    return paths


@contextmanager
def stage_output_set(outdir, names):
    """Stage every artifact before publishing a new set, rolling back ordinary failures.

    Sources must remain stable and the output root must have no concurrent writer. This is
    not a concurrent atomic multi-file transaction. Exclusive hard links refuse overwrite;
    existing output/receipt pairs remain intact. A process crash can leave partial links.
    """
    final = output_destinations(outdir, names)
    root = Path(outdir).resolve()
    root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".sapote-reference-stage-", dir=root.parent) as tmp:
        stage = Path(tmp)
        yield stage, final
        for name in names:
            if not (stage / name).is_file() or (stage / name).is_symlink():
                raise ValueError(f"staged output missing or invalid: {name}")
        output_destinations(outdir, names)  # recheck immediately before publication
        created = not root.exists()
        root.mkdir(parents=True, exist_ok=True)
        published = []
        try:
            for name, target in zip(names, final):
                os.link(stage / name, target)  # exclusive; never overwrite a prior artifact
                published.append(target)
        except Exception:
            for target in reversed(published):
                target.unlink()
            if created:
                root.rmdir()
            raise

def ref_from_db(db_path, acc, label, provenance=None):
    """Reconstruct CDS (+ Pfam domains) for the one cluster whose gbk.path contains `acc` (see select_gbk)."""
    c = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        gid, gpath = select_gbk(c, acc)
    except (KeyError, ValueError):
        c.close()
        raise
    print(f"fetch_reference_cluster: {acc} -> {gpath}", file=sys.stderr)  # the bound source record
    cds = c.execute(
        "SELECT id, nt_start, nt_stop, strand, aa_seq, orf_num FROM cds "
        "WHERE gbk_id=? ORDER BY nt_start", (gid,)).fetchall()
    genes = []
    for cid, s, e, st, aa, orf in cds:
        doms = c.execute(
            "SELECT accession, bit_score FROM hsp WHERE cds_id=? ORDER BY bit_score DESC",
            (cid,)).fetchall()
        label_gene = _pfam_name(doms[0][0]) if doms else None
        genes.append({"tag": f"{label}_{orf}", "start": int(s), "end": int(e),
                      "strand": 1 if st in (1, "+") else -1, "aa": aa or "",
                      "gene": label_gene, "domains": ",".join(d[0] for d in doms[:3])})
    c.close()
    if not genes:
        raise ValueError(f"{acc}: selected DB record {gpath} has no CDS")
    if provenance is not None:
        provenance.update({"kind": "DB", "requested_selector": acc, "label": label,
                           "database": file_binding(db_path), "selected_id": gid,
                           "selected_source_path": gpath, "cds_count": len(genes)})
        wal = Path(str(db_path) + "-wal")
        if wal.exists():
            provenance["database_wal"] = file_binding(wal)
    return genes


def validate_ncbi_accession(acc):
    """Admit an exact versioned accession, including NZ_ nucleotide prefixes.

    This validates selector syntax only. Both retrieval tools separately require
    the fetched record identity to equal the full requested accession/version.
    """
    pattern = r"(?:[A-Z]{1,6}_?[0-9]{5,12}|NZ_[A-Z]{1,6}[0-9]{5,12})\.[0-9]+"
    if not isinstance(acc, str) or not re.fullmatch(pattern, acc):
        raise ValueError("NCBI reference requires a complete versioned accession")
    return acc


def ref_from_ncbi(acc, label, timeout=60, provenance=None):
    """efetch exactly the requested versioned nucleotide record."""
    validate_ncbi_accession(acc)
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    import io
    url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" +
           urllib.parse.urlencode({"db": "nucleotide", "id": acc, "rettype": "gb", "retmode": "text"}))
    for _ in range(3):
        try:
            txt = urllib.request.urlopen(url, timeout=timeout).read().decode()
            break
        except Exception:
            import time; time.sleep(3)
    else:
        raise RuntimeError(f"NCBI efetch failed for {acc}")
    genes = []
    records = list(SeqIO.parse(io.StringIO(txt), "genbank"))
    if len(records) != 1:
        raise ValueError(f"{acc}: expected exactly one fetched GenBank record, got {len(records)}")
    if records[0].id != acc:
        raise ValueError(f"NCBI reference identity mismatch: requested {acc}, fetched {records[0].id}")
    record_ids = []
    for rec in records:
        record_ids.append(rec.id)
        i = 0
        for f in rec.features:
            if f.type == "CDS" and "translation" in f.qualifiers:
                i += 1
                name = (f.qualifiers.get("gene", [None])[0]
                        or (f.qualifiers.get("product", [None])[0] or "")[:30] or None)
                genes.append({"tag": f"{label}_{i}", "start": int(f.location.start),
                              "end": int(f.location.end), "strand": f.location.strand or 1,
                              "aa": f.qualifiers["translation"][0], "gene": name, "domains": ""})
    if not genes:
        raise ValueError(f"{acc}: fetched record has no translated CDS")
    if provenance is not None:
        provenance.update({"kind": "NCBI", "requested_selector": acc, "label": label,
                           "source_url": url, "selected_record_ids": record_ids,
                           "response_sha256": hashlib.sha256(txt.encode()).hexdigest(),
                           "cds_count": len(genes)})
    return genes


def genes_to_gbk(genes, label, outdir):
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    if not genes:
        raise ValueError(f"no CDS reconstructed for {label}")
    span = max(g["end"] for g in genes)
    rec = SeqRecord(Seq("N" * (span + 10)), id=f"{label}", name=label[:16],
                    description=f"{label} reference cluster (reconstructed)")
    rec.annotations["molecule_type"] = "DNA"
    for g in genes:
        f = SeqFeature(FeatureLocation(max(0, g["start"]), g["end"], strand=g["strand"]), type="CDS")
        f.qualifiers["locus_tag"] = [g["tag"]]
        if g.get("gene"):
            f.qualifiers["gene"] = [g["gene"]]
        if g.get("domains"):
            f.qualifiers["sec_met_domain"] = [g["domains"]]
        f.qualifiers["translation"] = [g["aa"]]
        rec.features.append(f)
    # v9.7.438: same containment guard as fetch_mibig_reference -- the label names the file.
    p = contained_output_path(outdir, label, ".gbk")
    SeqIO.write(rec, str(p), "genbank")
    return str(p), len(genes), sum(1 for g in genes if g.get("gene"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Reconstruct reference cluster GBKs from the BiG-SCAPE DB or NCBI.")
    ap.add_argument("--db", help="anchored BiG-SCAPE DB (for --acc)")
    ap.add_argument("--acc", action="append", default=[], metavar="ACCESSION:label",
                    help="cluster in the DB (MIBiG or cohort), repeatable")
    ap.add_argument("--ncbi", action="append", default=[], metavar="ACCESSION:label",
                    help="NCBI nucleotide accession, repeatable")
    ap.add_argument("--outdir", default="refs", help="new output files only; existing destinations are refused")
    a = ap.parse_args(argv)
    # Resolve every requested source before creating any reference output.
    pending, seen = [], set()
    try:
        for kind, specs in (("DB", a.acc), ("NCBI", a.ncbi)):
            for spec in specs:
                acc, label = spec.split(":", 1)
                if not acc or not label or label in seen:
                    raise ValueError("reference selectors and labels must be nonempty; labels must be unique")
                seen.add(label)
                contained_output_path(a.outdir, label, ".gbk")
                provenance = {}
                if kind == "DB":
                    if not a.db:
                        raise ValueError("--acc needs --db")
                    genes = ref_from_db(a.db, acc, label, provenance)
                else:
                    genes = ref_from_ncbi(acc, label, provenance=provenance)
                pending.append((label, genes, kind, provenance))
        if not pending:
            raise ValueError("no references requested")
    except (KeyError, ValueError, OSError, sqlite3.Error, RuntimeError) as exc:
        emit(f"[fetch_reference_cluster] ERROR: {exc}", file=sys.stderr)
        return 2
    names = [label + suffix for label, *_ in pending
             for suffix in (".gbk", ".reference_selection.json")]
    made = []
    try:
        with stage_output_set(a.outdir, names) as (stage, final):
            for index, (label, genes, kind, provenance) in enumerate(pending):
                p, n, na = genes_to_gbk(genes, label, stage)
                receipt = contained_output_path(stage, label, ".reference_selection.json")
                target = final[2 * index]
                write_selection_receipt(receipt, [provenance], [p], output_paths=[target],
                                        tool="fetch_reference_cluster")
                made.append((label, str(target), n, na, kind))
    except (ValueError, OSError, RuntimeError) as exc:
        emit(f"[fetch_reference_cluster] ERROR: output publication failed: {exc}", file=sys.stderr)
        return 2
    for label, p, n, na, src in made:
        emit(f"[fetch_reference_cluster] {label} <- {src}: {n} CDS, {na} annotated -> {p}")
    emit(f"[fetch_reference_cluster] {len(made)} reference GBK(s) ready for "
          f"cluster_gene_compare / clinker / bgc_reference_align.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
