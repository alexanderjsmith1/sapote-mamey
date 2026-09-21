#!/usr/bin/env python3
"""tools/chitinase_hmm_confirm.py -- HMMER confirmation pass for chitinolytic capacity.

WHY THIS EXISTS
    mamey/source_scans.py returns, on every scan it performs:
        "Annotation/keyword-derived first pass; confirm with HMMER/BLAST before manuscript use."
    and tools/build_chitinase_screen.py says in its own docstring:
        "Counts are annotation-derived ...; exact GH-family partition needs an HMM scan."
    Nothing in the bundle currently performs that confirmation, and nothing writes the
    cohort/chitinase.json that build_chitinase_screen.py reads. This tool does both.

    It does NOT replace CHITINASE_PATTERNS or touch the CGAD scan. The keyword pass is
    correct for what it is. This is the second channel, kept separate.

WHY A PROFILE PASS FINDS WHAT A KEYWORD PASS CANNOT, ON THIS INPUT
    _hay() deliberately excludes /translation -- regex over protein sequence is slow and
    backtracking-prone -- so the keyword scan reads product and locus_tag. antiSMASH
    annotates product only for CDS inside its regions; genome-wide CDS carry locus_tag,
    transl_table and translation only. A profile pass consumes exactly the field the
    keyword scan skips by design.

WHAT COUNTS AS WHAT
    Catalytic (a chitinase candidate requires one): GH18 PF00704, GH19 PF00182, ChiC PF06483.
    Accessory (context, never sufficient alone): ChitinaseA_N, CBM_5_12, Chitin_bind_1,
    CBM_14, ChiW_Ig_like, LysM. A binding module binds chitin; it does not cut it.
    Chitin SYNTHASES are excluded by design -- fungal/insect biosynthesis, opposite biology.

CLAIM CEILING
    Chitinolytic capacity is a whole-genome ecological trait. It does not establish chitin
    utilisation, expression, antifungal phenotype, novelty, or any link to a BGC. A
    predicted signal peptide is a localisation hypothesis, not demonstrated export.
"""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _console import emit
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

CATALYTIC = {"Glyco_hydro_18": "GH18", "Glyco_hydro_19": "GH19", "ChiC": "ChiC"}
ACCESSORY = {"ChitinaseA_N", "CBM_5_12", "Chitin_bind_1", "CBM_14", "ChiW_Ig_like", "LysM"}
PROFILES = ["PF00704", "PF00182", "PF06483", "PF08329",
            "PF02839", "PF00187", "PF01607", "PF18683", "PF01476"]
GH18_MOTIF = re.compile(r"D..D.D.E")
KD = {'A':1.8,'R':-4.5,'N':-3.5,'D':-3.5,'C':2.5,'Q':-3.5,'E':-3.5,'G':-0.4,'H':-3.2,
      'I':4.5,'L':3.8,'K':-3.9,'M':1.9,'F':2.8,'P':-1.6,'S':-0.8,'T':-0.7,'W':-0.9,
      'Y':-1.3,'V':4.2}
TAT = re.compile(r"[ST]RR.[FGAVML][LIVMF]")
LIPOBOX = re.compile(r"[LVIFA][ASTVIG][GAS]C")
GC_DELTA_PP = 10.0        # midpoint of an observed empty gap (8-15 pp); see the card
MIN_CORE_LEN = 20000


class ChitinaseConfirmError(RuntimeError):
    """Refuse rather than return a zero count. A zero here reads as 'no chitinase',
    which is the missing-evidence-as-negative failure this project guards against."""


def _require(tool: str) -> str:
    p = shutil.which(tool)
    if not p:
        raise ChitinaseConfirmError(
            f"{tool} not found on PATH. This tool performs an HMMER confirmation pass and "
            f"cannot substitute a keyword scan for it. Install HMMER3 (the bundle's phylo "
            f"env carries it) or pass --skip-if-unavailable to emit an explicit "
            f"HMMER_UNAVAILABLE state instead of counts.")
    return p


def build_profiles(pfam_hmm: str, out_hmm: str) -> int:
    _require("hmmfetch")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write("\n".join(PROFILES) + "\n")
        keyfile = fh.name
    try:
        with open(out_hmm, "wb") as out:
            r = subprocess.run(["hmmfetch", "-f", pfam_hmm, keyfile],
                               stdout=out, stderr=subprocess.PIPE)
        if r.returncode != 0:
            raise ChitinaseConfirmError(f"hmmfetch failed: {r.stderr.decode()[:400]}")
    finally:
        os.unlink(keyfile)
    n = sum(1 for line in open(out_hmm, encoding="utf-8", errors="replace")
            if line.startswith("NAME"))
    if n != len(PROFILES):
        raise ChitinaseConfirmError(
            f"expected {len(PROFILES)} profiles, fetched {n}. Pfam accession drift -- "
            f"check PROFILES against the local Pfam-A release before trusting counts.")
    return n


def kd_windows(seq, length, thresh):
    out, vals, run = [], [KD.get(c, 0.0) for c in seq], None
    for i in range(max(0, len(seq) - length + 1)):
        m = sum(vals[i:i+length]) / length
        if m >= thresh:
            run = [i, i+length, m] if run is None else [run[0], i+length, max(run[2], m)]
        elif run is not None:
            out.append(tuple(run)); run = None
    if run is not None:
        out.append(tuple(run))
    return out


def secretion_state(seq: str) -> tuple[str, str]:
    """Rule-based Sec/Tat/lipobox/TM screen. THIS IS NOT SignalP OR TMHMM."""
    nc = sum(1 for c in seq[:8] if c in "KR") - sum(1 for c in seq[:8] if c in "DE")
    # n-region may be as short as 1-5 residues, which is common in actinobacterial Sec
    # signals, so the h-region is allowed to begin from the 2nd residue. An earlier bound
    # of 4 rejected a textbook signal whose core started at index 3.
    h = [w for w in kd_windows(seq[:45], 7, 1.6) if 1 <= w[0] <= 20]
    tat, lip = TAT.search(seq[:35]), LIPOBOX.search(seq[:44])
    lip_ok = bool(lip) and 14 <= lip.end() - 1 <= 40
    cleave = None
    if h:
        for p in range(max(15, h[0][1]), min(46, len(seq))):
            if seq[p-1] in "AGS" and p >= 3 and seq[p-3] in "AGS":
                cleave = p; break
    tm_late = [w for w in kd_windows(seq, 19, 1.6) if w[0] >= 60]
    if tat and h:
        return "TAT_SIGNAL_PREDICTED", f"twin-arginine {tat.group(0)}@{tat.start()+1}"
    if lip_ok and h:
        return "LIPOPROTEIN_PREDICTED", f"lipobox {lip.group(0)} Cys@{lip.end()}"
    if h and nc >= 1 and cleave:
        return "SEC_SIGNAL_PREDICTED", f"n +{nc}; h {h[0][0]+1}-{h[0][1]}; A-X-A ~{cleave}"
    if tm_late:
        return "MEMBRANE_ANCHORED_PREDICTED", f"{len(tm_late)} TM after res 60"
    if h and nc >= 1:
        return "SIGNAL_AMBIGUOUS_NO_CLEAVAGE_SITE", f"n +{nc}; h present; no A-X-A"
    return "NO_SIGNAL_DETECTED", f"n {nc:+d}; {'h present' if h else 'no h-region'}"


def gc_pct(seq: str) -> float:
    s = seq.upper()
    return 100.0 * (s.count("G") + s.count("C")) / len(s) if s else 0.0


def core_profile(contigs: dict[str, dict]) -> tuple[float | None, float | None]:
    import statistics as st
    big = [c for c in contigs.values()
           if c.get("length", 0) >= MIN_CORE_LEN and c.get("gc") is not None]
    if not big:
        return None, None
    covs = [c["cov"] for c in big if c.get("cov") is not None]
    return st.median([c["gc"] for c in big]), (st.median(covs) if covs else None)


def run_hmmsearch(hmm: str, faa: str, domtbl: str, cpu: int = 4) -> None:
    _require("hmmsearch")
    r = subprocess.run(["hmmsearch", "--cpu", str(cpu), "--domtblout", domtbl,
                        "-E", "1e-5", "--domE", "1e-5", hmm, faa],
                       capture_output=True)
    if r.returncode != 0:
        raise ChitinaseConfirmError(f"hmmsearch failed: {r.stderr.decode()[:400]}")


def parse_domtbl(path: str) -> dict[str, list[dict]]:
    hits = defaultdict(list)
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith("#"):
            continue
        p = line.split()
        if len(p) < 23:
            continue
        hits[p[0]].append(dict(domain=p[3], acc=p[4], tlen=int(p[2]),
                               iEval=float(p[12]), score=float(p[13]),
                               s=int(p[17]), e=int(p[18])))
    return hits


def classify(proteins: dict[str, str], hits: dict[str, list[dict]],
             contig_of: dict[str, str] | None = None,
             contigs: dict[str, dict] | None = None) -> list[dict]:
    core_gc, core_cov = core_profile(contigs) if contigs else (None, None)
    rows = []
    for target, hs in hits.items():
        doms = sorted(hs, key=lambda d: d["s"])
        cat = [d for d in doms if d["domain"] in CATALYTIC]
        seq = proteins.get(target, "")
        fam = "/".join(sorted({CATALYTIC[d["domain"]] for d in cat}))
        cls = f"CHITINASE_CANDIDATE_{fam}" if cat else "CHITIN_BINDING_ACCESSORY_ONLY"
        motif, motif_seq = "NOT_APPLICABLE", ""
        g18 = [d for d in cat if d["domain"] == "Glyco_hydro_18"]
        if g18 and seq:
            m = GH18_MOTIF.search(seq[g18[0]["s"]-1:g18[0]["e"]])
            motif = "DxxDxDxE_PRESENT" if m else "DxxDxDxE_ABSENT"
            motif_seq = m.group(0) if m else ""
        prov, basis = "NOT_ASSESSED", ""
        if contigs and contig_of and core_gc is not None:
            c = contigs.get(contig_of.get(target, ""), {})
            if c.get("gc") is not None:
                d = abs(c["gc"] - core_gc)
                prov = "FOREIGN_CONTIG_SUSPECT" if d > GC_DELTA_PP else "CONSISTENT_WITH_CORE_GENOME"
                basis = (f"GC {c['gc']:.1f}% vs core {core_gc:.1f}% (d{d:.1f}pp)"
                         + (f"; cov {c['cov']:.1f}x vs core {core_cov:.1f}x"
                            if c.get("cov") is not None and core_cov else ""))
        sec, sec_ev = secretion_state(seq) if seq else ("NOT_ASSESSED", "")
        rows.append(dict(
            protein=target, classification=cls,
            catalytic_domains=";".join(sorted({d["domain"] for d in cat})) or "NONE",
            accessory_domains=";".join(sorted({d["domain"] for d in doms
                                               if d["domain"] in ACCESSORY})) or "NONE",
            domain_architecture=" + ".join(d["domain"] for d in doms),
            protein_length_aa=len(seq),
            best_catalytic_evalue=(min(d["iEval"] for d in cat) if cat else ""),
            gh18_catalytic_motif=motif, gh18_motif_seq=motif_seq,
            contig_provenance=prov, contig_provenance_basis=basis,
            secretion_state=sec, secretion_evidence=sec_ev,
            secretion_method="RULE_BASED_SCREEN_NOT_SIGNALP",
            claim_ceiling=("Profile-supported chitin-active or chitin-binding capacity. "
                           "Strain-level ecological context; not linked to any BGC, not an "
                           "antifungal activity claim; judgment deferred.")))
    return rows


def summarise(rows: list[dict]) -> dict:
    keep = [r for r in rows if r["contig_provenance"] != "FOREIGN_CONTIG_SUSPECT"]
    cat = [r for r in keep if r["classification"].startswith("CHITINASE_CANDIDATE")]
    acc = [r for r in keep if not r["classification"].startswith("CHITINASE_CANDIDATE")]
    motif = Counter(r["gh18_catalytic_motif"] for r in cat)
    return {
        # the two fields tools/build_chitinase_screen.py already reads
        "chitinase": len(cat),
        "chitin_binding": len(acc),
        # additive detail the keyword pass cannot provide
        "families": dict(Counter(r["classification"].replace("CHITINASE_CANDIDATE_", "")
                                 for r in cat)),
        "gh18_motif_present": motif.get("DxxDxDxE_PRESENT", 0),
        "gh18_motif_absent": motif.get("DxxDxDxE_ABSENT", 0),
        "predicted_secreted": sum(1 for r in cat if r["secretion_state"] in
                                  {"SEC_SIGNAL_PREDICTED", "TAT_SIGNAL_PREDICTED",
                                   "LIPOPROTEIN_PREDICTED"}),
        "excluded_foreign_contig": len(rows) - len(keep),
        "evidence": "HMMER3_PROFILE_CONFIRMED",
        "claim_safety": ("Profile-confirmed chitinolytic capacity. Whole-genome ecological "
                         "context only; not expression, phenotype, or a BGC link."),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--proteome", required=True, help="protein FASTA for one strain")
    ap.add_argument("--strain", required=True)
    ap.add_argument("--pfam-hmm", required=True, help="local pressed Pfam-A.hmm; never downloaded")
    ap.add_argument("--out-dir", default="cohort")
    ap.add_argument("--contigs-json", help="optional {contig: {length, gc, cov}} for provenance")
    ap.add_argument("--skip-if-unavailable", action="store_true")
    a = ap.parse_args(argv)
    try:
        _require("hmmsearch"); _require("hmmfetch")
    except ChitinaseConfirmError as e:
        if a.skip_if_unavailable:
            emit(f"  [chitinase-hmm] {e}", file=sys.stderr)
            os.makedirs(a.out_dir, exist_ok=True)
            p = os.path.join(a.out_dir, "chitinase.json")
            d = json.load(open(p)) if os.path.exists(p) else {}
            d[a.strain] = {"evidence": "HMMER_UNAVAILABLE",
                           "claim_safety": "No profile confirmation performed. "
                                           "Absence of counts here is not absence of chitinase."}
            json.dump(d, open(p, "w"), indent=1)
            return 0
        raise

    proteins, k, buf = {}, None, []
    contig_of = {}
    for line in open(a.proteome):
        if line.startswith(">"):
            if k: proteins[k] = "".join(buf)
            parts = line[1:].strip().split("|")
            k = line[1:].split()[0]; buf = []
            if len(parts) >= 3: contig_of[k] = parts[2]
        else:
            buf.append(line.strip())
    if k: proteins[k] = "".join(buf)
    if not proteins:
        raise ChitinaseConfirmError(f"no sequences parsed from {a.proteome}")

    contigs = json.load(open(a.contigs_json)) if a.contigs_json else None
    with tempfile.TemporaryDirectory() as td:
        hmm = os.path.join(td, "chitin.hmm"); dt = os.path.join(td, "hits.domtbl")
        build_profiles(a.pfam_hmm, hmm)
        run_hmmsearch(hmm, a.proteome, dt)
        rows = classify(proteins, parse_domtbl(dt), contig_of, contigs)

    os.makedirs(a.out_dir, exist_ok=True)
    jp = os.path.join(a.out_dir, "chitinase.json")
    d = json.load(open(jp)) if os.path.exists(jp) else {}
    d[a.strain] = summarise(rows)
    json.dump(d, open(jp, "w"), indent=1)

    tp = os.path.join(a.out_dir, f"chitinase_evidence_{a.strain}.tsv")
    if rows:
        with open(tp, "w", newline="", encoding="utf-8") as fh:
            w = _SafeDictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
            w.writeheader(); w.writerows(rows)
    emit(f"  [chitinase-hmm] {a.strain}: {d[a.strain]['chitinase']} catalytic, "
         f"{d[a.strain]['chitin_binding']} binding-only -> {jp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
