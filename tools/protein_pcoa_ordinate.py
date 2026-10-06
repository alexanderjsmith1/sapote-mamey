#!/usr/bin/env python3
"""Build a protein-class PCoA kit from antiSMASH region files: cohort proteins among reference and MIBiG proteins.

The kit this writes is what tools/protein_pcoa_render.py draws and tools/pcoa_bgc_explorer.py explores:
out_<SET>/PCOA_<SET>.tsv, NEAREST_<SET>.tsv, RUN_<SET>.json, REFERENCE_CLUSTERS_<SET>.tsv, plus <SET>.faa / <SET>_META.tsv.

Subcommands (run in order; each refuses to overwrite its own outputs):
  extract  --input SOURCE=PATH (repeatable)   every CDS of every region file -> REGION_CDS.faa/.tsv, and the antiSMASH
           domain sets: KS (aSDomain PKS_KS), AT (PKS_AT), A (AMP-binding), C (Condensation) from nrps_pks_domains, and whole
           CDS carrying sec_met_domain LANC_like (LANC) or YcaO (YCAO).
           SOURCE is isolate, reference, SID or MIBiG; PATH is a folder searched recursively for *.gbk, or a .zip of them.
           The strain is the file-name prefix before "__" (MIBiG: the BGC accession). --genus-table and --cohort-table
           (strain -> genus / cohort, TSV) fill those columns; folders named after a genus also give the genus.
  pfam     --hmm Pfam-A.hmm   whole-CDS sets by Pfam gathering thresholds (pyhmmer): TERP (Terpene_synth_C,
           Terpene_syn_C_2), T3PKS (Chal_sti_synt_N), NIS (IucA_IucC), P450 (p450), HALO (Trp_halogenase), GT1 (UDPGT),
           SARP (BTAD), LUXR (GerE). A protein hit by two sets goes to the higher score.
  card     --card-fasta protein_fasta_protein_homolog_model.fasta --aro-index aro_index.tsv   CARD homologs:
           diamond blastp --more-sensitive, best hit, identity >= 40, query and subject coverage >= 70, e <= 1e-10. Families
           with >= --min-cohort (5) cohort proteins become RES01, RES02, ... (largest first); RES_SETS.tsv names them.
  ordinate --set S   reference and MIBiG sequences each clustered with diamond cluster (--approx-id; defaults KS 70;
           A, C, AT, P450, LUXR 60; GT1, SARP 70; others 90; member cover 80) and only centroids kept, with member counts;
           cohort sequences are never clustered. All-against-all diamond blastp --more-sensitive among kept sequences;
           distance = 1 - identity/100 of the best hit either way, 1 with no hit (e > 1e-3); classical PCoA, three axes,
           % = eigenvalue / trace of the centred matrix.
  nearest  --set S   each cohort protein's best hit among ALL reference and MIBiG sequences of the set (not only centroids).

DIAMOND and pyhmmer are companion tools: missing ones are refused by name, never replaced. Heavy steps run under nice with
--threads (default 4). Positions are sequence similarity only; they say nothing about function or product.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from mamey._gbk_shim import parse_genbank_text  # noqa: E402

_LOG = logging.getLogger("protein_pcoa_ordinate")
SOURCES = {"isolate": "isolate", "reference": "reference_held", "SID": "SID_held", "MIBiG": "MIBiG"}
DOMAIN_SETS = {"PKS_KS": "KS", "PKS_AT": "AT", "AMP-binding": "A", "Condensation": "C"}
SECMET_SETS = {"LANC_like": "LANC", "YcaO": "YCAO"}
PFAM_SETS = {"TERP": ["Terpene_synth_C", "Terpene_syn_C_2"], "T3PKS": ["Chal_sti_synt_N"], "NIS": ["IucA_IucC"],
             "P450": ["p450"], "HALO": ["Trp_halogenase"], "GT1": ["UDPGT"], "SARP": ["BTAD"], "LUXR": ["GerE"]}
APPROX_ID = {"KS": 70, "A": 60, "C": 60, "AT": 60, "P450": 60, "LUXR": 60, "GT1": 70, "SARP": 70}
META_COLS = ["id", "source", "group", "genus", "strain", "origin", "locus_tag", "label", "subtype", "region_product", "length", "assembly", "record_id", "region", "locus_identity", "source_sha256", "assembly_binding"]


class OrdinateRefusal(RuntimeError):
    """A missing companion tool or an input that would make the kit wrong."""


# ---------------------------------------------------------------- helpers
def read_tsv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def write_fasta(path, items):
    with open(path, "w") as fh:
        for i, s in items:
            fh.write(f">{i}\n{s}\n")


def read_fasta(path):
    seqs, cur = {}, None
    for line in open(path):
        line = line.strip()
        if line.startswith(">"):
            cur = line[1:].split()[0]; seqs[cur] = []
        elif cur is not None:
            seqs[cur].append(line)
    return {k: "".join(v) for k, v in seqs.items()}


def write_meta(path, rows):
    with open(path, "w", newline="") as fh:
        w = _SafeDictWriter(fh, META_COLS, delimiter="\t", extrasaction="ignore", lineterminator="\n")
        w.writeheader(); w.writerows(rows)


def refuse_existing(*paths):
    for p in paths:
        if Path(p).exists():
            raise OrdinateRefusal(f"{p} exists; this step never overwrites its outputs (use a new kit folder)")


def diamond_exe(explicit=None) -> str:
    exe = explicit or shutil.which("diamond")
    if not exe:
        raise OrdinateRefusal("DIAMOND not found (put diamond on PATH or pass --diamond); it is a companion tool")
    return exe


def run(cmd):
    _LOG.info("%s", " ".join(str(c) for c in cmd))
    subprocess.run(["nice", "-n", "15", *map(str, cmd)], check=True)


# ---------------------------------------------------------------- extract
def _admitted_gbk(name):
    base = Path(name).name
    return base.endswith(".gbk") and (".region" in base or base.startswith("BGC"))


def _region_entries(path, ledger):
    """One representation policy; follow directory links once, report aliases/errors."""
    path = Path(path)
    files, seen_dirs, seen_files = [], set(), set()
    followed = []
    if path.suffix == ".zip":
        files = [path]
    else:
        def walk_error(error):
            raise OrdinateRefusal(f"INPUT_TRAVERSAL_FAILED: {error}")
        for base, dirs, names in os.walk(path, followlinks=True, onerror=walk_error):
            real = Path(base).resolve()
            if real in seen_dirs:
                dirs[:] = []
                ledger.append(dict(status="DUPLICATE_DIRECTORY", path=str(base), reason="alias/loop"))
                continue
            seen_dirs.add(real)
            if Path(base).is_symlink():
                followed.append(str(base))
            keep = []
            for name in sorted(dirs):
                directory = Path(base) / name
                if directory.is_symlink() and not directory.exists():
                    raise OrdinateRefusal(f"BROKEN_DIRECTORY_ALIAS: {directory}")
                keep.append(name)
            dirs[:] = keep
            for name in sorted(names):
                candidate = Path(base) / name
                if candidate.is_symlink() and not candidate.exists():
                    raise OrdinateRefusal(f"BROKEN_INPUT_ALIAS: {candidate}")
                if candidate.suffix not in (".gbk", ".zip"):
                    continue
                if not candidate.is_file():
                    raise OrdinateRefusal(f"INPUT_FILE_UNREADABLE: {candidate}")
                identity = (candidate.stat().st_dev, candidate.stat().st_ino)
                if identity in seen_files:
                    ledger.append(dict(status="DUPLICATE_FILE_ALIAS", path=str(candidate)))
                    continue
                seen_files.add(identity)
                files.append(candidate)
        if not path.is_dir():
            raise OrdinateRefusal(f"input folder absent: {path}")
    _LOG.warning("input %s: followed %d symlinked folder(s) [%s]; found %d GBK/ZIP file(s)",
                 path, len(followed), ", ".join(followed), len(files))
    for item in sorted(files):
        folder = item.parent.name if item.parent != path else ""
        if item.suffix == ".zip":
            with zipfile.ZipFile(item) as archive:
                admitted_names = [name for name in archive.namelist() if _admitted_gbk(name)]
                if len(set(admitted_names)) != len(admitted_names):
                    raise OrdinateRefusal(f"AMBIGUOUS_ZIP_MEMBER: {item}")
                for name in sorted(archive.namelist()):
                    if not name.endswith('.gbk'):
                        continue
                    locator = f"{item}!{name}"
                    if "__MACOSX" in Path(name).parts or Path(name).name.startswith('._') or not _admitted_gbk(name):
                        ledger.append(dict(status="REJECTED_FILE", path=locator, reason="non-region/reference GBK"))
                        continue
                    raw = archive.read(name)
                    yield f"{item.stem}:{Path(name).name}", raw.decode('utf-8', 'replace'), folder, dict(
                        path=locator, file=Path(name).name, sha256=hashlib.sha256(raw).hexdigest())
        else:
            if not _admitted_gbk(item.name):
                ledger.append(dict(status="REJECTED_FILE", path=str(item), reason="non-region/reference GBK"))
                continue
            raw = item.read_bytes()
            yield item.name, raw.decode('utf-8', 'replace'), folder, dict(
                path=str(item), file=item.name, sha256=hashlib.sha256(raw).hexdigest())


def _zip_texts(zpath: Path, folder: str = ""):
    for name, text, _folder, evidence in _region_entries(zpath, []):
        yield name, text, folder


def region_texts(path: Path):
    """Representation-independent region/reference admission, with visible traversal counts."""
    for name, text, folder, evidence in _region_entries(path, []):
        yield name, text, folder


def strain_of(name: str, source: str) -> str:
    if ":" in name:                                   # a region inside a genome's result zip: the zip names the genome
        return name.split(":")[0]
    base = name
    if source == "MIBiG":
        return base.split(".")[0]
    return base.split("__")[0] if "__" in base else base.split(".")[0]


def cmd_extract(a):
    kit = Path(a.kit); kit.mkdir(parents=True, exist_ok=True)
    refuse_existing(kit / "REGION_CDS.faa", *[kit / f"{s}.faa" for s in (*DOMAIN_SETS.values(), *SECMET_SETS.values())])
    genus = {r["strain"]: r.get("genus", "") for r in read_tsv(a.genus_table)} if a.genus_table else {}
    cohort = {r["strain"]: r.get("cohort", "") for r in read_tsv(a.cohort_table)} if a.cohort_table else {}
    cds, cds_meta = [], []
    sets = {s: [] for s in (*DOMAIN_SETS.values(), *SECMET_SETS.values())}
    counts = collections.Counter()
    admission, seen_records = [], {}
    assembly_table = {}
    assembly_path = getattr(a, "assembly_table", None)
    if assembly_path:
        for row in read_tsv(assembly_path):
            if not row.get("input") or not row.get("assembly", "").strip():
                raise OrdinateRefusal("assembly table requires nonempty input and assembly columns")
            bound_input = str(Path(row["input"]).resolve())
            if bound_input in assembly_table:
                raise OrdinateRefusal(f"ambiguous repeated assembly binding: {bound_input}")
            assembly_table[bound_input] = row["assembly"].strip()
    for spec in a.input:
        label, _, path = spec.partition("=")
        if label not in SOURCES or not path:
            raise OrdinateRefusal(f"--input {spec!r}: use SOURCE=PATH with SOURCE one of {sorted(SOURCES)}")
        src = SOURCES[label]
        for name, text, folder, evidence in _region_entries(Path(path), admission):
            strain = strain_of(name, label)
            g = genus.get(strain, "") or ("" if label == "MIBiG" else folder)
            group = cohort.get(strain, "") if src == "isolate" else src
            records = list(parse_genbank_text(text))
            if not records:
                raise OrdinateRefusal(f"REGION_PARSE_UNVERIFIED: {evidence['path']}")
            if len({str(rec.id) for rec in records}) != len(records):
                raise OrdinateRefusal(f"AMBIGUOUS_RECORD_IDENTITY: {evidence['path']}")
            for rec in records:
                # Default identity is the record/region supplied by the source, not a
                # inferred biological assembly. Independent assemblies with identical
                # identifiers/bytes require explicit input-to-assembly bindings.
                assembly = assembly_table.get(str(Path(path).resolve()), str(rec.id))
                identity = (src, assembly, str(rec.id), evidence["file"])
                if identity in seen_records:
                    if seen_records[identity]["sha256"] != evidence["sha256"]:
                        raise OrdinateRefusal(f"CONFLICTING_REGION_IDENTITY: {identity}")
                    admission.append(dict(status="DUPLICATE_SOURCE_MATERIAL", identity=list(identity),
                                          **evidence, duplicate_of=seen_records[identity]["path"]))
                    continue
                seen_records[identity] = evidence
                admission.append(dict(status="ADMITTED_REGION", identity=list(identity), **evidence))
                products = []
                for f in rec.features:
                    q = f.qualifiers
                    if f.type == "region":
                        products = sorted(set(p for v in q.get("product", []) for p in v.split()))
                    base = dict(source=src, group=group, genus=g, strain=strain, origin=name,
                                locus_tag=(q.get("locus_tag") or [""])[0], label=(q.get("label") or [""])[0],
                                region_product="+".join(products), assembly=assembly, record_id=str(rec.id),
                                region=evidence["file"], source_sha256=evidence["sha256"],
                                assembly_binding="EXPLICIT_INPUT_TABLE" if str(Path(path).resolve()) in assembly_table else "SOURCE_RECORD_ID",
                                locus_identity=" / ".join(map(str, identity)) + " / " +
                                    ((q.get("locus_tag") or [""])[0] or str(f.location)))
                    tr = (q.get("translation") or [""])[0]
                    if not tr:
                        continue
                    if f.type == "aSDomain" and (q.get("aSTool") or [""])[0] == "nrps_pks_domains":
                        t = DOMAIN_SETS.get((q.get("aSDomain") or [""])[0])
                        if t:
                            spec_v = " | ".join(q.get("specificity", []))
                            sub = (q.get("domain_subtypes") or [""])[0] or next(
                                (x.split(":", 1)[1].strip() for x in spec_v.split(" | ") if x.startswith("consensus")), "")
                            sets[t].append(dict(base, subtype=sub, seq=tr))
                    if f.type == "CDS":
                        counts[src] += 1
                        cid = f"CDS{len(cds) + 1:07d}"
                        cds.append((cid, tr))
                        cds_meta.append(dict(base, id=cid, subtype=(q.get("gene_kind") or [""])[0], length=len(tr)))
                        dom = " ".join(q.get("sec_met_domain", []))
                        for key, t in SECMET_SETS.items():
                            if re.search(rf"\b{re.escape(key)}\s*\(", dom):
                                sets[t].append(dict(base, subtype="", seq=tr))
    if not cds:
        raise OrdinateRefusal("no CDS with a translation in any input")
    write_fasta(kit / "REGION_CDS.faa", cds); write_meta(kit / "REGION_CDS_META.tsv", cds_meta)
    for t, rows in sets.items():
        for i, r in enumerate(rows, 1):
            r["id"] = f"{t}{i:06d}"; r["length"] = len(r["seq"])
        write_fasta(kit / f"{t}.faa", [(r["id"], r["seq"]) for r in rows]); write_meta(kit / f"{t}_META.tsv", rows)
    summary = dict(cds_by_source=dict(counts), sets={t: len(v) for t, v in sets.items()})
    (kit / "EXTRACT_RECEIPT.json").write_text(json.dumps(dict(summary, inputs=a.input,
        assembly_table=None if not assembly_path else dict(path=str(Path(assembly_path).resolve()),
            sha256=hashlib.sha256(Path(assembly_path).read_bytes()).hexdigest()), admission=admission,
        population_policy="region/reference filenames only; exact source record/region copies deduplicated; "
                          "explicit assembly-table bindings preserve independent copies"), indent=1))
    return summary


# ---------------------------------------------------------------- pfam
def cmd_pfam(a):
    kit = Path(a.kit)
    refuse_existing(*[kit / f"{s}.faa" for s in PFAM_SETS])
    try:
        import pyhmmer
        from pyhmmer.easel import Alphabet, TextSequence
        from pyhmmer.plan7 import HMMFile
    except ImportError as exc:
        raise OrdinateRefusal("pyhmmer is required for the Pfam sets (a companion dependency)") from exc
    want = {p: s for s, ps in PFAM_SETS.items() for p in ps}
    hmms = []
    with HMMFile(a.hmm) as fh:
        for h in fh:
            name = h.name.decode() if isinstance(h.name, bytes) else h.name
            if name in want:
                hmms.append(h)
    missing = set(want) - {(h.name.decode() if isinstance(h.name, bytes) else h.name) for h in hmms}
    if missing:
        raise OrdinateRefusal(f"{a.hmm} lacks {sorted(missing)}")
    seqs = read_fasta(kit / "REGION_CDS.faa")
    meta = {r["id"]: r for r in read_tsv(kit / "REGION_CDS_META.tsv")}
    alpha = Alphabet.amino()
    digital = [TextSequence(name=i.encode(), sequence=s).digitize(alpha) for i, s in seqs.items()]
    best = {}
    for top in pyhmmer.hmmer.hmmsearch(hmms, digital, cpus=a.threads, bit_cutoffs="gathering"):
        qn = getattr(top, "query_name", None) or top.query.name
        pf = qn.decode() if isinstance(qn, bytes) else qn
        for hit in top:
            if not hit.included:
                continue
            hid = hit.name.decode() if isinstance(hit.name, bytes) else hit.name
            if hid not in best or hit.score > best[hid][1]:
                best[hid] = (pf, hit.score)
    out = {}
    for s in PFAM_SETS:
        ids = sorted(i for i, (pf, _) in best.items() if want[pf] == s)
        rows = [dict(meta[i], subtype=best[i][0]) for i in ids]
        write_fasta(kit / f"{s}.faa", [(i, seqs[i]) for i in ids]); write_meta(kit / f"{s}_META.tsv", rows)
        out[s] = len(ids)
    return out


# ---------------------------------------------------------------- card
def cmd_card(a):
    kit = Path(a.kit)
    refuse_existing(kit / "RES_SETS.tsv")
    dmd = diamond_exe(a.diamond)
    work = kit / "_card"; work.mkdir(exist_ok=True)
    run([dmd, "makedb", "--in", a.card_fasta, "-d", work / "card", "--quiet"])
    run([dmd, "blastp", "-q", kit / "REGION_CDS.faa", "-d", work / "card", "-o", work / "hits.tsv", "--more-sensitive", "-k", "1",
         "--id", "40", "--query-cover", "70", "--subject-cover", "70", "--evalue", "1e-10", "--threads", a.threads,
         "--tmpdir", work, "--quiet", "-f", "6", "qseqid", "sseqid", "pident", "qcovhsp", "scovhsp", "evalue"])
    aro = {}
    for r in read_tsv(a.aro_index):
        aro[r.get("ARO Accession", "").replace("ARO:", "")] = r.get("AMR Gene Family", "")
    meta = {r["id"]: r for r in read_tsv(kit / "REGION_CDS_META.tsv")}
    seqs = read_fasta(kit / "REGION_CDS.faa")
    fam_of = {}
    for line in open(work / "hits.tsv"):
        q, s = line.split("\t")[:2]
        m = re.search(r"ARO:(\d+)", s)
        if m and q not in fam_of and aro.get(m.group(1)):
            fam_of[q] = aro[m.group(1)]
    cohort_n = collections.Counter(f for q, f in fam_of.items() if meta[q]["source"] == "isolate")
    fams = [f for f, n in sorted(cohort_n.items(), key=lambda x: (-x[1], x[0])) if n >= a.min_cohort]
    rows = []
    for k, f in enumerate(fams, 1):
        s = f"RES{k:02d}"
        ids = sorted(q for q, ff in fam_of.items() if ff == f)
        write_fasta(kit / f"{s}.faa", [(i, seqs[i]) for i in ids])
        write_meta(kit / f"{s}_META.tsv", [dict(meta[i], subtype=f.split(";")[0][:40]) for i in ids])
        rows.append(dict(set=s, amr_gene_family=f, proteins=len(ids), isolate_proteins=cohort_n[f]))
    with open(kit / "RES_SETS.tsv", "w", newline="") as fh:
        w = _SafeDictWriter(fh, ["set", "amr_gene_family", "proteins", "isolate_proteins"], delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    return {r["set"]: r["isolate_proteins"] for r in rows}


# ---------------------------------------------------------------- ordinate
def classical_pcoa(D, k=3):
    """Classical PCoA of a symmetric distance matrix (numpy, modified in place). Returns (coords n x k, % per axis)."""
    import numpy as np
    D **= 2; D *= -0.5
    D -= D.mean(axis=0, keepdims=True); D -= D.mean(axis=1, keepdims=True)
    tr = float(np.trace(D))
    n = D.shape[0]
    if n <= 400:
        vals, vecs = np.linalg.eigh(D.astype(np.float64))
    else:
        from scipy.sparse.linalg import eigsh
        vals, vecs = eigsh(D.astype(np.float64) if n < 8000 else D, k=k, which="LA")
    o = np.argsort(vals)[::-1][:k]
    vals, vecs = vals[o], vecs[:, o]
    # a fixed sign per axis (largest-magnitude loading positive) so reruns give the same picture
    for j in range(vecs.shape[1]):
        if vecs[np.argmax(np.abs(vecs[:, j])), j] < 0:
            vecs[:, j] *= -1
    X = vecs * np.sqrt(np.clip(vals, 0, None))
    return X, [100 * v / tr if tr else 0.0 for v in vals]


def cmd_ordinate(a):
    import numpy as np
    kit = Path(a.kit); T = a.set; out = kit / f"out_{T}"
    refuse_existing(out / f"PCOA_{T}.tsv")
    out.mkdir(parents=True, exist_ok=True)
    dmd = diamond_exe(a.diamond); approx = a.approx_id or APPROX_ID.get(T, 90); t0 = time.time()
    meta = {r["id"]: r for r in read_tsv(kit / f"{T}_META.tsv")}
    seqs = read_fasta(kit / f"{T}.faa")
    cohort = [i for i, r in meta.items() if r["source"] == "isolate"]
    refs = [i for i, r in meta.items() if r["source"] not in ("isolate", "MIBiG")]
    mibig = [i for i, r in meta.items() if r["source"] == "MIBiG"]
    members = {}
    for name, group in (("refs", refs), ("mibig", mibig)):
        if not group:
            continue
        write_fasta(out / f"{name}.faa", [(i, seqs[i]) for i in group])
        run([dmd, "cluster", "-d", out / f"{name}.faa", "-o", out / f"{name}_clusters.tsv", "--approx-id", approx,
             "--member-cover", "80", "--threads", a.threads, "--tmpdir", out, "--quiet"])
        for line in open(out / f"{name}_clusters.tsv"):
            c, m = line.split()
            members.setdefault(c, []).append(m)
    with open(out / f"REFERENCE_CLUSTERS_{T}.tsv", "w") as fh:
        fh.write("centroid\tn_members\tmembers\n")
        for c, ms in members.items():
            fh.write(f"{c}\t{len(ms)}\t{','.join(ms)}\n")
    ids = cohort + list(members); idx = {i: k for k, i in enumerate(ids)}; n = len(ids)
    if n < 4:
        raise OrdinateRefusal(f"{T}: only {n} points to ordinate")
    write_fasta(out / "kept.faa", [(i, seqs[i]) for i in ids])
    run([dmd, "makedb", "--in", out / "kept.faa", "-d", out / "kept", "--threads", a.threads, "--quiet"])
    run([dmd, "blastp", "-q", out / "kept.faa", "-d", out / "kept", "-o", out / "allvsall.tsv", "--more-sensitive", "-k", n,
         "--evalue", "1e-3", "--threads", a.threads, "--tmpdir", out, "--quiet", "-f", "6", "qseqid", "sseqid", "pident"])
    D = np.ones((n, n), dtype=np.float32)
    for line in open(out / "allvsall.tsv"):
        q, s, p = line.split("\t")
        i, j, d = idx[q], idx[s], 1 - float(p) / 100
        if d < D[i, j]:
            D[i, j] = D[j, i] = d
    np.fill_diagonal(D, 0)
    for x in ("allvsall.tsv", "kept.dmnd", "kept.faa", "refs.faa", "mibig.faa"):
        (out / x).unlink(missing_ok=True)
    X, pct = classical_pcoa(D)
    cnt = {c: len(ms) for c, ms in members.items()}
    cols = ["id", "PC1", "PC2", "PC3", "n_represented", "source", "group", "genus", "strain", "subtype", "region_product",
            "locus_tag", "origin", "length"]
    with open(out / f"PCOA_{T}.tsv", "w", newline="") as fh:
        w = _SafeDictWriter(fh, cols, delimiter="\t", extrasaction="ignore", lineterminator="\n"); w.writeheader()
        for k, i in enumerate(ids):
            w.writerow(dict(meta[i], id=i, PC1=f"{X[k, 0]:.5f}", PC2=f"{X[k, 1]:.5f}",
                            PC3=f"{X[k, 2]:.5f}" if X.shape[1] > 2 else "0", n_represented=cnt.get(i, 1)))
    run_rec = dict(set=T, points=n, isolate_sequences=len(cohort), reference_sequences=len(refs), mibig_sequences=len(mibig),
                   centroids=len(members), approx_id=approx, pct_axes=[round(float(p), 2) for p in pct],
                   seconds=round(time.time() - t0))
    (out / f"RUN_{T}.json").write_text(json.dumps(run_rec, indent=1))
    return run_rec


# ---------------------------------------------------------------- nearest
def cmd_nearest(a):
    kit = Path(a.kit); T = a.set; out = kit / f"out_{T}"
    refuse_existing(out / f"NEAREST_{T}.tsv")
    out.mkdir(parents=True, exist_ok=True)
    dmd = diamond_exe(a.diamond)
    meta = {r["id"]: r for r in read_tsv(kit / f"{T}_META.tsv")}
    seqs = read_fasta(kit / f"{T}.faa")
    iso = [i for i in meta if meta[i]["source"] == "isolate"]; oth = [i for i in meta if meta[i]["source"] != "isolate"]
    write_fasta(out / "near_iso.faa", [(i, seqs[i]) for i in iso]); write_fasta(out / "near_oth.faa", [(i, seqs[i]) for i in oth])
    run([dmd, "makedb", "--in", out / "near_oth.faa", "-d", out / "near_oth", "--quiet"])
    run([dmd, "blastp", "-q", out / "near_iso.faa", "-d", out / "near_oth", "-o", out / "near_hits.tsv", "--more-sensitive",
         "-k", "1", "--evalue", "1e-3", "--threads", a.threads, "--tmpdir", out, "--quiet", "-f", "6", "qseqid", "sseqid", "pident",
         "qcovhsp"])
    best = {}
    for line in open(out / "near_hits.tsv"):
        q, s, p, c = line.rstrip("\n").split("\t")
        if q not in best:
            best[q] = (s, float(p), float(c))
    with open(out / f"NEAREST_{T}.tsv", "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["id", "strain", "genus", "locus_tag", "region_product", "subtype", "nearest_pident", "nearest_qcov",
                    "nearest_id", "nearest_source", "nearest_strain", "nearest_genus"])
        for i in iso:
            s, p, c = best.get(i, ("", 0.0, 0.0)); m = meta[i]; nb = meta.get(s, {})
            w.writerow([i, m["strain"], m["genus"], m["locus_tag"], m["region_product"], m["subtype"], p, c, s,
                        nb.get("source", ""), nb.get("strain", ""), nb.get("genus", "")])
    for x in ("near_iso.faa", "near_oth.faa", "near_oth.dmnd", "near_hits.tsv"):
        (out / x).unlink(missing_ok=True)
    return dict(set=T, cohort_proteins=len(iso), below_70=sum(1 for i in iso if best.get(i, ("", 0.0))[1] < 70))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--kit", required=True, help="kit folder (created by extract)")
    common.add_argument("--threads", type=int, default=4)
    common.add_argument("--diamond", help="path to the diamond binary (default: on PATH)")
    e = sub.add_parser("extract", parents=[common]); e.add_argument("--input", action="append", required=True)
    e.add_argument("--genus-table"); e.add_argument("--cohort-table")
    e.add_argument("--assembly-table", help="TSV input/assembly bindings; required to retain independently sampled identical region copies")
    p = sub.add_parser("pfam", parents=[common]); p.add_argument("--hmm", required=True)
    c = sub.add_parser("card", parents=[common]); c.add_argument("--card-fasta", required=True); c.add_argument("--aro-index", required=True)
    c.add_argument("--min-cohort", type=int, default=5)
    o = sub.add_parser("ordinate", parents=[common]); o.add_argument("--set", required=True); o.add_argument("--approx-id", type=float)
    n = sub.add_parser("nearest", parents=[common]); n.add_argument("--set", required=True)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        result = {"extract": cmd_extract, "pfam": cmd_pfam, "card": cmd_card, "ordinate": cmd_ordinate,
                  "nearest": cmd_nearest}[a.cmd](a)
    except (OrdinateRefusal, OSError, zipfile.BadZipFile, UnicodeError) as exc:
        _LOG.error("REFUSED: %s", exc)
        return 2
    _LOG.info("%s", json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
