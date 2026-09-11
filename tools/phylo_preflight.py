#!/usr/bin/env python3
"""phylo_preflight.py — validate a planned phylogenomic tree BEFORE spending CPU.

Every check here exists because the corresponding mistake actually happened on 2026-08-26 while
building the attine/bee comparator-balanced trees. Each is cheap (seconds) and each would have
prevented either a wasted multi-hour run or a wrong figure.

    CHECK                     THE MISTAKE IT PREVENTS
    E1 environment            GToTree exited: "Muscle ... not in your PATH"; then
                              "'GToTree_HMM_dir' variable is not set" — two dead runs.
    E2 gtotree version        Built on v1.8.16 while project convention is >= v1.8.19.
    G1 genome files           Broken symlinks / empty files / non-FASTA in the input set.
    G2 duplicate genomes      Byte-identical genomes entering as two tips (cf. AS-XXX_second).
    T1 taxonomy resolved      AS-XXX had EMPTY taxonomy (source folder typo "Streptomyes"),
                              entered a tree unlabelled, and nobody noticed.
    T2 family coherence       That same AS-XXX (Streptomyces) sat inside a Pseudonocardiaceae
                              /Kribbella tree — wrong family, long basal branch, wrong figure.
    T3 ingroup rank span      The "bee backbone" spanned 7 families / ~6 orders, so NO outgroup
                              could be a legitimate sister group.
    O1 outgroup present       Trees were left unrooted (IQ-TREE output order, outgroup buried).
    O2 outgroup not ingroup   Registry rule: the outgroup genus must not also appear in the ingroup.
    O3 outgroup distance      Bifidobacterium (Bifidobacteriales) used to root an ingroup of
                              Streptomycetales/Pseudonocardiales — a distant taxon, not a sister.
    C1 comparator balance     Cohort-only trees with no named references to place strains against.
    R1 registry accession     Compare exact versioned assembly identities and binomial labels
                              against explicitly supplied, hash-bound source records. Missing
                              evidence is UNVERIFIED; no accession prefix/version equivalence.

Usage
-----
    phylo_preflight.py <genomes_dir> [--scope FAMILY] [--outgroup SUBSTR] [--min-ratio 1.0]
                       [--r1-registry PATH] [--r1-evidence PATH] [--json out.json]

`--scope` is the declared family/rank of the ingroup (e.g. Pseudonocardiaceae, Streptomycetaceae).
If omitted it is inferred from the majority family and T2 becomes advisory.

Exit code 0 = all checks pass (or only warnings). Exit 1 = at least one FAIL. Nothing is written
to the genome set; this tool is read-only.
"""
from __future__ import annotations
import sys, os, re, csv, json, glob, hashlib, subprocess, argparse
from _wbio import atomic_dump_json_owned as _atomic_write_json

# Project root: env override first, then the script's own grandparent (<root>/Tools/<this>),
# then the workstation default. Keeps the tool portable for a public/bundle context (P0-8).
def _data_root():
    """Resolve an explicit data root, an exact CWD data root, or the portable bundle root.

    The CWD check is deliberately exact: do not search parent directories or bind nearby data.
    """
    env = os.environ.get("MAMEY_DATA_ROOT")
    if env:
        return env
    rel = "strain_data/_ANTISMASH_CANONICAL/STRAIN_METADATA_CONSOLIDATED.tsv"
    if os.path.exists(os.path.join(os.getcwd(), rel)):
        return os.getcwd()
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ROOT = _data_root()
SSOT = f"{ROOT}/strain_data/_ANTISMASH_CANONICAL/STRAIN_METADATA_CONSOLIDATED.tsv"
_bundle_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _bundle_root not in sys.path:
    sys.path.insert(0, _bundle_root)
from mamey.outgroup_registry_path import outgroup_registry_path, registry_binding
REGISTRY = str(outgroup_registry_path())

# Genus -> (family, order). Minimal actinomycete map covering the cohort + common outgroups.
# Extend as new genera appear; an unknown genus is reported, never silently accepted.
TAXA = {
 "Streptomyces":("Streptomycetaceae","Streptomycetales"),
 "Kitasatospora":("Streptomycetaceae","Streptomycetales"),
 "Streptacidiphilus":("Streptomycetaceae","Streptomycetales"),
 "Actinacidiphila":("Streptomycetaceae","Streptomycetales"),
 "Peterkaempfera":("Streptomycetaceae","Streptomycetales"),
 "Actinospica":("Catenulisporaceae","Streptomycetales"),
 "Catenulispora":("Catenulisporaceae","Streptomycetales"),
 "Pseudonocardia":("Pseudonocardiaceae","Pseudonocardiales"),
 "Amycolatopsis":("Pseudonocardiaceae","Pseudonocardiales"),
 "Saccharopolyspora":("Pseudonocardiaceae","Pseudonocardiales"),
 "Sciscionella":("Pseudonocardiaceae","Pseudonocardiales"),
 "Herbihabitans":("Pseudonocardiaceae","Pseudonocardiales"),
 "Labedaea":("Pseudonocardiaceae","Pseudonocardiales"),
 "Saccharothrix":("Pseudonocardiaceae","Pseudonocardiales"),
 "Actinosynnema":("Pseudonocardiaceae","Pseudonocardiales"),
 "Actinophytocola":("Pseudonocardiaceae","Pseudonocardiales"),
 "Saccharomonospora":("Pseudonocardiaceae","Pseudonocardiales"),
 "Actinopolyspora":("Pseudonocardiaceae","Pseudonocardiales"),
 "Nocardia":("Nocardiaceae","Corynebacteriales"),
 "Rhodococcus":("Nocardiaceae","Corynebacteriales"),
 "Gordonia":("Nocardiaceae","Corynebacteriales"),
 "Tsukamurella":("Tsukamurellaceae","Corynebacteriales"),
 "Mycobacterium":("Mycobacteriaceae","Corynebacteriales"),
 "Mycolicibacterium":("Mycobacteriaceae","Corynebacteriales"),
 "Micromonospora":("Micromonosporaceae","Micromonosporales"),
 "Salinispora":("Micromonosporaceae","Micromonosporales"),
 "Actinoplanes":("Micromonosporaceae","Micromonosporales"),
 "Dactylosporangium":("Micromonosporaceae","Micromonosporales"),
 "Catellatospora":("Micromonosporaceae","Micromonosporales"),
 "Solwaraspora":("Micromonosporaceae","Micromonosporales"),
 "Verrucosispora":("Micromonosporaceae","Micromonosporales"),
 "Actinomadura":("Thermomonosporaceae","Streptosporangiales"),
 "Actinocorallia":("Thermomonosporaceae","Streptosporangiales"),
 "Thermomonospora":("Thermomonosporaceae","Streptosporangiales"),
 "Streptosporangium":("Streptosporangiaceae","Streptosporangiales"),
 "Nonomuraea":("Streptosporangiaceae","Streptosporangiales"),
 "Microbispora":("Streptosporangiaceae","Streptosporangiales"),
 "Nocardiopsis":("Nocardiopsaceae","Streptosporangiales"),
 "Kribbella":("Nocardioidaceae","Propionibacteriales"),
 "Nocardioides":("Nocardioidaceae","Propionibacteriales"),
 "Aeromicrobium":("Nocardioidaceae","Propionibacteriales"),
 "Bifidobacterium":("Bifidobacteriaceae","Bifidobacteriales"),
 "Corynebacterium":("Corynebacteriaceae","Corynebacteriales"),
}

def load_ssot():
    tax, host = {}, {}
    if not os.path.exists(SSOT):
        return tax, host
    for r in csv.DictReader(open(SSOT), delimiter="\t"):
        s = (r.get("strain") or "").strip()
        if not s: continue
        tax[s] = (r.get("taxonomy") or "").strip()
        host[s] = (r.get("source") or "").strip()
    return tax, host

# Family-level taxonomy strings (e.g. "Pseudonocardiaceae sp.") are legitimate when a strain is
# resolved only to family. Map them straight to (family, order) so they do not read as unknown genera.
FAMILY_LEVEL = {
 "Pseudonocardiaceae": ("Pseudonocardiaceae", "Pseudonocardiales"),
 "Streptomycetaceae":  ("Streptomycetaceae",  "Streptomycetales"),
 "Nocardiaceae":       ("Nocardiaceae",       "Corynebacteriales"),
 "Micromonosporaceae": ("Micromonosporaceae", "Micromonosporales"),
 "Thermomonosporaceae":("Thermomonosporaceae","Streptosporangiales"),
 "Streptosporangiaceae":("Streptosporangiaceae","Streptosporangiales"),
 "Nocardioidaceae":    ("Nocardioidaceae",    "Propionibacteriales"),
 "Nocardiopsaceae":    ("Nocardiopsaceae",    "Streptosporangiales"),
}

NON_ACTINO = {
    "leucocoprinus","neurospora","penicillium","aspergillus","candida","fusarium","trichoderma",
    "saccharomyces","escovopsis","melissospora","metarhizium","beauveria","cordyceps",
    "melissococcus","paenibacillus","bacillus","enterococcus","lactobacillus","staphylococcus",
    "clostridium","burkholderia","erwinia","escherichia","pseudomonas","serratia","gilliamella",
    "snodgrassella","frischella","pantoea","enterobacter","klebsiella",
    "oscillatoria","nostoc","synechococcus","synechocystis","deinococcus","chloroflexus",
}


def genus_of(name, tax):
    """Resolve a genome filename to a genus (or family-level token). AS-#### goes through the SSOT."""
    m = re.match(r"(AS-\d+)", name)
    if m:
        t = tax.get(m.group(1), "")
        if not t:
            return None, m.group(1)          # unresolved AS strain -> T1 failure
        return t.split()[0].replace("_", ""), m.group(1)
    tok = re.split(r"[_\s.]+", name)
    return (tok[0] if tok and tok[0][:1].isupper() else None), name

def rank_of(token):
    """(family, order) for a genus OR a family-level token; None if unknown."""
    if token in TAXA: return TAXA[token]
    if token in FAMILY_LEVEL: return FAMILY_LEVEL[token]
    return None

class Report:
    def __init__(self): self.items = []
    def add(self, code, status, msg, detail=""):
        self.items.append({"check": code, "status": status, "message": msg, "detail": detail})
    def fails(self): return [i for i in self.items if i["status"] == "FAIL"]
    def warns(self): return [i for i in self.items if i["status"] == "WARN"]

def check_env(rep):
    need = ["GToTree", "muscle", "prodigal", "hmmsearch", "iqtree"]
    missing = [t for t in need if not _which(t)]
    if missing:
        rep.add("E1", "FAIL", "Required tool(s) not on PATH", ", ".join(missing)
                + "  — source tools/gtotree_env.sh first")
    else:
        rep.add("E1", "PASS", "All 5 tools on PATH")
    hmm = os.environ.get("GToTree_HMM_dir", "")
    if not hmm:
        rep.add("E1b", "FAIL", "GToTree_HMM_dir is not set", "GToTree will exit before doing any work")
    elif not os.path.exists(os.path.join(hmm, "Actinobacteria.hmm")):
        rep.add("E1b", "FAIL", "Actinobacteria.hmm not found in GToTree_HMM_dir", hmm)
    else:
        rep.add("E1b", "PASS", "GToTree_HMM_dir set and Actinobacteria.hmm present")
    # E1c: GToTree calls `file` to detect compression. A relocated conda env leaves `file`
    # pointing at a magic database that no longer exists — the run dies AFTER the HMM search.
    import subprocess as _sp
    try:
        r = _sp.run(["file", os.devnull], capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            rep.add("E1c", "FAIL", "`file` environment probe failed",
                    (r.stderr or r.stdout or f"exit {r.returncode}").strip()[:160])
        elif "magic file" in (r.stderr or "").lower() or "could not find any valid magic" in (r.stderr or "").lower():
            rep.add("E1c", "FAIL", "`file` cannot load its magic database",
                    (r.stderr or "").strip()[:160] + "  — export MAGIC=<env>/share/misc/magic.mgc "
                    "(GToTree dies at the alignment step, after the HMM search)")
        else:
            rep.add("E1c", "PASS", "`file` magic database loads", "")
    except subprocess.TimeoutExpired:
        rep.add("E1c", "FAIL", "`file` environment probe timed out",
                "20-second local probe exceeded; do not start the multi-hour tree run")
    except OSError as e:
        rep.add("E1c", "FAIL", "Could not execute required `file` probe", str(e))

    if _which("GToTree"):
        try:
            result = subprocess.run(["GToTree", "-v"], capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                rep.add("E2", "FAIL", "GToTree version UNKNOWN — probe failed",
                        f"exit {result.returncode}: {(result.stderr or result.stdout or chr(32)).strip()[:160]}")
                return
            v = (result.stdout or "") + "\n" + (result.stderr or "")
            m = re.search(r"v?(\d+)\.(\d+)\.(\d+)", v)
            if m:
                tup = tuple(int(x) for x in m.groups())
                if tup < (1, 8, 19):
                    rep.add("E2", "WARN", f"GToTree {'.'.join(map(str,tup))} < project convention 1.8.19",
                            "set GTOTREE_HOME to the 1.8.19 tree")
                else:
                    rep.add("E2", "PASS", f"GToTree {'.'.join(map(str,tup))} meets convention (>=1.8.19)")
            else:
                # v9.7.415 (rebased on the .415 draft): say UNKNOWN in the row itself. A reader
                # scanning statuses sees FAIL and looks for a version; the row must state that the
                # version was never established, not imply a wrong one.
                rep.add("E2", "FAIL", "GToTree version UNKNOWN — banner could not be parsed",
                        f"output[:160]={(v.strip()[:160] or '<no output>')!r}; the >=1.8.19 "
                        "convention is UNVERIFIED, not met")
        except Exception as e:
            rep.add("E2", "FAIL", "Could not read GToTree version", str(e))
    else:
        # v9.7.415: GToTree absent -> E1 lists the missing tool, but E2 must still APPEAR. With no
        # `else` the version row vanished from the checklist, and a checklist with no version
        # objection reads as a version check that passed. An unrun check is visible as NOT
        # MEASURED, never absent.
        rep.add("E2", "WARN", "GToTree version NOT MEASURED — GToTree not on PATH",
                "see E1; the >=1.8.19 convention is UNVERIFIED, not met")

def _which(t):
    from shutil import which
    return which(t)


def _sha256_file(path, chunk_size=1024 * 1024):
    """Bounded-memory SHA-256 for multi-megabase genome inputs."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()

def check_genomes(rep, files):
    bad, empty, dup = [], [], {}
    for f in files:
        if not os.path.exists(f): bad.append(f"{os.path.basename(f)} (broken link/missing)"); continue
        if os.path.getsize(f) < 100_000: empty.append(f"{os.path.basename(f)} ({os.path.getsize(f)}B)"); continue
        with open(f, "rb") as fh:
            if not fh.read(1).startswith(b">"): bad.append(f"{os.path.basename(f)} (not FASTA)"); continue
        h = _sha256_file(f)
        dup.setdefault(h, []).append(os.path.basename(f))
    rep.add("G1", "FAIL" if bad or empty else "PASS",
            "Genome file integrity" + ("" if not (bad or empty) else " — problems found"),
            "; ".join(bad + empty) or f"{len(files)} files readable, all FASTA, all >100KB")
    d = {k: v for k, v in dup.items() if len(v) > 1}
    rep.add("G2", "FAIL" if d else "PASS", "Duplicate (byte-identical) genomes",
            "; ".join(" == ".join(v) for v in d.values()) or "none")

# --- G3/G4 thresholds -------------------------------------------------------------------
# Calibrated on real failures observed 2026-08-26, not guessed. Actinomycete genomes run
# ~5-12 Mb; every value below was set by a file that actually broke or was silently dropped.
MIN_GENOME_BP     = 2_000_000    # Streptomyces_citricolor.fna = 37 kb (a gene accession);
                                 # Amycolatopsis_sp_WAC_04197 = 685 kb, 1 contig, 5/138 SCGs
FRAGMENTED_CONTIGS = 1_500       # AS-XXX: 2,204 contigs -> 66/138 SCGs, dropped by GToTree
BROKEN_CONTIGS     = 5_000       # AS-XXX (uncleaned): 9,133 contigs -> 37/138 SCGs, dropped
INFLATED_BP        = 14_000_000  # AS-XXX: 16.9 Mb "Nocardiaceae" ~= 2x a real one -> 11/138
LOW_N50_BP         = 20_000      # AS-XXX (removed 2026-09-01): N50 11.5 kb in 1,347 contigs —
                                 # under FRAGMENTED_CONTIGS's count-only threshold, produced a
                                 # pathological 0.33 (83%-of-depth) terminal branch; caption/warn
                                 # rather than silently letting a shred through on contig count alone

def _fasta_stats(path):
    """(total_bp, n_contigs, n50_bp) in one pass. Cheap enough for a 20-genome tree.

    N50: the contig length L such that contigs >= L cover half the assembly — a shred with many
    tiny contigs but a fine total bp/contig-count can still have a pathologically low N50.
    """
    total = n = 0
    lengths = []
    cur = 0
    with open(path, "rb") as fh:
        for line in fh:
            if line.startswith(b">"):
                if n:
                    lengths.append(cur)
                n += 1
                cur = 0
            else:
                seg = len(line.strip())
                cur += seg
                total += seg
        if n:
            lengths.append(cur)
    lengths.sort(reverse=True)
    half = total / 2
    running = 0
    n50 = 0
    for L in lengths:
        running += L
        if running >= half:
            n50 = L
            break
    return total, n, n50

def check_assembly_quality(rep, files):
    """G3 — assembly sanity BEFORE the CPU is spent.

    This is sign-off gate item 3 ("assembly-quality flag") mechanised. G1 only proves a file
    is readable FASTA over 100 KB; that passed all four genomes GToTree went on to discard
    after the full 138-marker HMM search. A dropped genome is not a neutral event: the tree
    silently loses a strain and the tip count stops matching the input.
    """
    fails, warns, stats = [], [], {}
    for f in files:
        b = os.path.basename(f)
        try: bp, nc, n50 = _fasta_stats(f)
        except Exception as e: fails.append(f"{b}: unreadable ({e})"); continue
        stats[b] = (bp, nc, n50)
        if bp < MIN_GENOME_BP:
            fails.append(f"{b}: {bp:,} bp in {nc} contig(s) — too small to be a genome "
                         f"(marker-gene or plasmid record?)")
        elif nc >= BROKEN_CONTIGS:
            fails.append(f"{b}: {nc:,} contigs — too fragmented; branch lengths untrustworthy "
                         f"and SCG recovery will collapse")
        elif bp > INFLATED_BP:
            fails.append(f"{b}: {bp/1e6:.1f} Mb — inflated for an actinomycete; suspect "
                         f"contamination or a mixed assembly")
        elif nc >= FRAGMENTED_CONTIGS:
            warns.append(f"{b}: {nc:,} contigs, {bp/1e6:.1f} Mb — fragmented; caption it and "
                         f"expect reduced SCG recovery")
        elif n50 < LOW_N50_BP:
            warns.append(f"{b}: N50 {n50/1e3:.1f} kb in {nc:,} contigs — low-N50 shred; caption "
                         f"it, expect gappy SCG recovery and an inflated terminal branch")
    # fails and warns are reported separately: a fragmented-but-usable genome still needs a
    # caption note, and folding it into a FAIL line hides it the moment anything worse exists.
    if fails:
        rep.add("G3", "FAIL", "Assembly quality — genome(s) unfit for a phylogenomic tree",
                "; ".join(fails))
    else:
        rep.add("G3", "PASS", "Assembly quality", f"{len(stats)} genomes within size/contig bounds")
    if warns:
        rep.add("G3b", "WARN", "Fragmented genome(s) — usable, but caption the assembly quality",
                "; ".join(warns))

def check_superseded(rep, files):
    """G4 — a strain with a repaired assembly must not enter a tree by its old file.

    AS-XXX was decontaminated (94.93% -> 6.52% redundancy) and the repaired file lives beside
    the original as AS-XXX_CLEANED.fna. Staging AS-XXX.fna instead is invisible to every other
    check: it is valid FASTA of plausible size and it simply produces a worse tree.
    """
    hits = []
    for f in files:
        stem = os.path.splitext(os.path.basename(f))[0]
        if stem.upper().endswith(("_CLEANED", "_DECONTAMINATED")): continue
        for suf in ("_CLEANED", "_DECONTAMINATED"):
            for ext in (".fna", ".fasta"):
                cand = os.path.join(os.path.dirname(f), stem + suf + ext)
                if os.path.exists(cand):
                    hits.append(f"{os.path.basename(f)} — a repaired assembly exists: "
                                f"{os.path.basename(cand)}")
    idx = f"{ROOT}/OFFICIAL_DATA/LOCAL_GENOME_INDEX.tsv"
    if os.path.exists(idx):
        cleaned = {}
        for ln in open(idx).read().splitlines():
            b = ln.split("\t")[0].strip()
            s = os.path.splitext(b)[0]
            if s.upper().endswith(("_CLEANED", "_DECONTAMINATED")):
                cleaned[re.sub(r"_(CLEANED|DECONTAMINATED)$", "", s, flags=re.I)] = b
        for f in files:
            stem = os.path.splitext(os.path.basename(f))[0]
            if stem in cleaned and not any(stem in h for h in hits):
                hits.append(f"{os.path.basename(f)} — repaired assembly in the local index: "
                            f"{cleaned[stem]}")
    rep.add("G4", "FAIL" if hits else "PASS",
            "Superseded assembly staged instead of its repaired version" if hits
            else "No superseded assemblies staged",
            "; ".join(hits) or f"{len(files)} genomes checked against *_CLEANED counterparts")

# --- cohort membership -------------------------------------------------------------------
# The SSOT 'source' column is a CLOSED vocabulary: 16 distinct values across all 176 strains
# (verified 2026-08-26), so a strain's cohort is decidable, not a guess. This exists because
# `tree-source-separation` is a governing rule -- moss, bees and attines get SEPARATE trees --
# and a governing rule that lives only in prose gets violated. It was, in 3 of 6 trees.
COHORT_RULES = [
    ("attine",      ("ant-associated", "atta", "acromyrmex", "attine")),
    ("substrate",   ("moss-", "liverwort-", "usnea-", "mushroom-")),
    ("hymenoptera", ("bombus", "apis", "apidae", "wasp", "hymenoptera", "bee")),
]

# THE canonical strain table. 318 rows, and it carries an explicit `cohort` column and an
# `excluded`/`exclusion_reason` pair. Everything below reads THIS, not
# strain_data/_ANTISMASH_CANONICAL/STRAIN_METADATA_CONSOLIDATED.tsv (176 rows, no cohort,
# no exclusions) -- reading the wrong table is the single root cause of the composition errors
# this file exists to catch. The cohort was never something to infer; it was a governed column
# all along, sitting one directory away.
OFFICIAL = f"{ROOT}/OFFICIAL_DATA/STRAIN_METADATA.tsv"

def load_official():
    """{strain: row} from the canonical table. Empty dict if it is missing, which is itself
    reported rather than silently degrading to the keyword fallback."""
    out = {}
    if os.path.exists(OFFICIAL):
        for r in csv.DictReader(open(OFFICIAL), delimiter="\t"):
            s = (r.get("tip_label") or "").strip()
            if s:
                out[s] = r
    return out

def cohort_of(host, official_row=None):
    """
    Cohort for a strain. The governed column wins; the keyword rules below are a fallback for
    a strain absent from the canonical table, and their use is reported as a gap, not a pass.
    """
    if official_row:
        c = (official_row.get("cohort") or "").strip()
        if c:
            return c
    h = (host or "").strip().lower()
    if not h:
        return None
    for cohort, keys in COHORT_RULES:
        if any(k in h for k in keys):
            return cohort
    return None

def load_spec(genomes_dir):
    """
    TREE_SPEC.json sitting beside the genomes dir, declaring what this tree IS.

    The root cause of a whole class of composition errors is that a tree's identity lived
    only in its folder name and in the operator's head, so nothing could check the contents
    against the intent. The spec puts the intent on disk where a machine can read it.

    Keys: scope (family|order), taxon, cohort, outgroup, min_comparators_per_genus, title.
    """
    d = os.path.dirname(os.path.abspath(genomes_dir.rstrip("/")))
    p = os.path.join(d, "TREE_SPEC.json")
    if os.path.exists(p):
        try:
            return json.load(open(p)), p
        except Exception as e:
            return {"_error": str(e)}, p
    return None, p

def check_cohort(rep, as_files, tax, host, declared):
    """H1 -- every query strain belongs to the cohort this tree declares."""
    if not declared:
        rep.add("H1", "WARN", "No cohort declared — cross-cohort contamination cannot be checked",
                "add \"cohort\" to TREE_SPEC.json (hymenoptera | attine | substrate)")
        return
    off = load_official()
    if not off:
        rep.add("H0", "FAIL", "Canonical strain table not found — cohort cannot be governed",
                OFFICIAL)
    wrong, unknown, excluded, absent = [], [], [], []
    for f in as_files:
        sid = re.match(r"(AS-\d+)", os.path.basename(f)).group(1)
        row = off.get(sid)
        if off and row is None:
            absent.append(sid)
        if row and (row.get("excluded") or "").strip().upper() == "Y":
            excluded.append(f"{sid} ({row.get('exclusion_reason','no reason given')})")
        h = host.get(sid, "")
        c = cohort_of(h, row)
        if c is None:
            unknown.append(f"{sid} (source={h!r})")
        elif c != declared:
            wrong.append(f"{sid} is {c} ({h})")
    if excluded:
        rep.add("H2", "FAIL", "Strain(s) flagged EXCLUDED in the canonical table are staged",
                "; ".join(excluded) + f"  — see {OFFICIAL}")
    else:
        rep.add("H2", "PASS", "No excluded strains staged", "")
    if absent:
        rep.add("H3", "FAIL", "Strain(s) missing from the canonical table",
                ", ".join(absent) + "  — cohort and exclusion status are unknowable for these")
    if wrong:
        rep.add("H1", "FAIL", f"Query strain(s) from outside the declared '{declared}' cohort",
                "; ".join(wrong) + "  — governing rule: moss, bees and attines get SEPARATE trees")
    elif unknown:
        rep.add("H1", "FAIL", "Query strain(s) whose host maps to no cohort",
                "; ".join(unknown) + "  — fix the SSOT source value or extend COHORT_RULES")
    else:
        rep.add("H1", "PASS", f"All {len(as_files)} query strains are {declared}", "")

def check_genus_comparators(rep, as_files, comp_files, tax, minimum, novel_genus=()):
    """
    C2 -- every ingroup genus carries at least one named comparator.

    C1 only checks a global comparator:query ratio, which a tree can pass while an entire
    genus sits alone: bee_Pseudonocardiaceae had 8 comparators for 5 query strains (C1 PASS)
    while Saccharopolyspora and Saccharothrix had none at all. Those strains cannot be placed
    against any named reference, so nothing can be said about them.

    `novel_genus` is the set of query strain ids that TREE_SPEC declares as novel-genus
    candidates. A novel genus has, by definition, no same-genus named comparator -- that is the
    finding, not a staging error -- so those strains are exempt from the FAIL and reported
    instead. This is deliberately explicit per-strain in the spec, so "no comparator" can never
    silently mean "novel genus" when it actually means "I forgot to stage one".
    """
    comp_genera = {}
    for f in comp_files:
        g = os.path.basename(f).split("_")[0]
        comp_genera[g] = comp_genera.get(g, 0) + 1
    gaps, unresolved, novel = [], [], []
    for f in as_files:
        sid = re.match(r"(AS-\d+)", os.path.basename(f)).group(1)
        g = (tax.get(sid, "").split() or [""])[0]
        if sid in novel_genus:
            novel.append(f"{sid} ({g or 'unresolved'})"); continue
        if not g:
            unresolved.append(sid); continue
        if rank_of(g) is None and g.endswith("aceae"):
            unresolved.append(f"{sid} (resolves only to family {g})"); continue
        n = comp_genera.get(g, 0)
        if n < minimum:
            gaps.append(f"{sid} ({g}): {n} comparator(s), need {minimum}")
    if novel:
        rep.add("C2n", "WARN", "Novel-genus query strain(s) — no same-genus comparator by design",
                "; ".join(novel) + "  — caption as a candidate novel genus; place against the "
                "family, and root on the family-level outgroup, not a genus sister")
    if gaps or unresolved:
        rep.add("C2", "FAIL", "Query strain(s) with no named comparator in their own genus",
                "; ".join(gaps + unresolved) +
                "  — unplaceable against any reference (if this IS a novel genus, declare it in "
                "TREE_SPEC \"novel_genus_queries\")")
    else:
        rep.add("C2", "PASS", f"Every query genus has >= {minimum} comparator(s)",
                ", ".join(f"{g} x{n}" for g, n in sorted(comp_genera.items())))


# --- R1: exact accession evidence, read-only ------------------------------------
_ASSEMBLY_ID = re.compile(r"GC[AF]_\d{9}\.[1-9]\d*")


def exact_assembly_accession(value):
    """Require the complete prefix, nine digits and explicit version."""
    text = value.strip() if isinstance(value, str) else ""
    return text if _ASSEMBLY_ID.fullmatch(text) else None


def _r1_binomial(value):
    # Deliberately bounded: a missing/abbreviated genus or unresolved epithet
    # cannot verify a label. Strain equivalence and synonyms are not inferred.
    if not isinstance(value, str):
        return None
    match = re.match(r"^([A-Z][a-z]+) ([a-z][a-z-]+)(?=\s|$)", value.strip())
    if not match or match[2] in {"sp", "spp", "strain", "subsp", "bacterium"}:
        return None
    return match[1], match[2]


def _r1_evidence(path):
    """Read a manifest of hash-bound JSON records. Never write caches or fetch data.

    Manifest: {"records": [{"path": "record.json", "sha256": "..."}]}.
    Record: {"assembly_accession": "GCF_000000001.1", "organism_name": "Genus species"}.
    Relative record paths resolve against the manifest. They are explicit inputs;
    no filename, path token, GCF/GCA numeric match or version stripping is evidence.
    """
    if not path:
        return {}, "No R1 evidence manifest supplied"
    try:
        with open(path) as fh:
            manifest = json.load(fh)
        records = manifest["records"]
        if not isinstance(records, list) or not records:
            raise ValueError("records must be a nonempty list")
        index = {}
        for item in records:
            record_path = item["path"]
            digest = item["sha256"]
            if not isinstance(record_path, str) or not record_path.strip():
                raise ValueError("record path missing")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("record SHA-256 invalid")
            resolved = os.path.join(os.path.dirname(os.path.abspath(path)), record_path)
            with open(resolved, "rb") as fh:
                raw = fh.read()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError(f"record hash mismatch: {record_path}")
            record = json.loads(raw)
            accession = exact_assembly_accession(record["assembly_accession"])
            organism = record["organism_name"]
            if not accession or not isinstance(organism, str) or not organism.strip():
                raise ValueError("record requires exact accession and organism_name")
            index.setdefault(accession, []).append({"organism": organism.strip(),
                                                    "source": record_path, "sha256": digest})
        return index, ""
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return {}, f"R1 evidence unverified: {type(exc).__name__}: {exc}"


def verify_registry_accessions(registry, evidence_path=None):
    """Return a result for every registry row; verification is binomial-only.

    Evidence is operator supplied and hash checked, not independently authenticated.
    Accession pairs and taxonomic synonyms require separately governed adjudication;
    this bounded checker supports exact identities only.
    """
    evidence, issue = _r1_evidence(evidence_path)
    results = []
    with open(registry, newline="") as fh:
        lines = (line for line in fh if line.strip() and not line.lstrip().startswith("#"))
        reader = csv.DictReader(lines, delimiter="\t")
        required = {"assembly_accession", "outgroup_species_strain"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("registry requires assembly_accession and outgroup_species_strain")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("duplicate registry columns")
        for ordinal, row in enumerate(reader, 1):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"registry row {ordinal}: column width mismatch")
            acc = row["assembly_accession"].strip()
            claimed = row["outgroup_species_strain"].strip()
            exact = exact_assembly_accession(acc)
            hits = evidence.get(exact, [])
            names = sorted({hit["organism"] for hit in hits})
            result = {"row": ordinal, "accession": acc, "claimed": claimed,
                      "resolved": names, "evidence": hits, "verdict": "UNVERIFIED",
                      "detail": issue or "No exact versioned accession evidence"}
            if not exact:
                result["detail"] = "Missing or invalid complete versioned assembly accession"
            elif len(names) > 1:
                result.update(verdict="CONFLICT", detail="Conflicting evidence for the same accession")
            elif names:
                left, right = _r1_binomial(claimed), _r1_binomial(names[0])
                if not left or not right:
                    result["detail"] = "Claimed or evidence binomial is incomplete or unsupported"
                elif left != right:
                    result.update(verdict="LABEL_MISMATCH", detail="Binomial disagreement; adjudication required")
                else:
                    result.update(verdict="VERIFIED_BINOMIAL", detail="Exact accession and binomial agree; strain and synonym equivalence not evaluated")
            results.append(result)
    return results


def check_registry_accessions(rep, registry=None, evidence_path=None):
    registry = REGISTRY if registry is None else registry
    try:
        if registry_binding(registry)["authority"] == "BUNDLED_REFERENCE_ONLY":
            rep.add("R1", "WARN", "Registry authority UNBOUND", "Bundled reference snapshot is not a selected project registry")
            return []
        results = verify_registry_accessions(registry, evidence_path)
    except (OSError, ValueError, TypeError) as exc:
        rep.add("R1", "WARN", "Registry accessions UNVERIFIED", str(exc))
        return []
    failed = any(r["verdict"] in {"CONFLICT", "LABEL_MISMATCH"} for r in results)
    verified = sum(r["verdict"] == "VERIFIED_BINOMIAL" for r in results)
    status = "FAIL" if failed else "PASS" if results and verified == len(results) else "WARN"
    rep.add("R1", status, f"{verified}/{len(results)} registry rows have exact accession and binomial evidence",
            "No scientific or strain-identity approval. " + (json.dumps(results, sort_keys=True) if results
            else "UNVERIFIED: no registry rows to evaluate"))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("genomes_dir")
    ap.add_argument("--cohort", default="", help="hymenoptera | attine | substrate (else from TREE_SPEC.json)")
    ap.add_argument("--min-genus-comparators", type=int, default=1)
    ap.add_argument("--scope", default="")
    ap.add_argument("--outgroup", default="OUTGROUP")
    ap.add_argument("--min-ratio", type=float, default=1.0)
    ap.add_argument("--tip-map", default="", help="TSV: tree_tag<TAB>species_name — resolves abbreviated tip names (e.g. 'S sp. AS-XXX')")
    ap.add_argument("--r1-registry", default=REGISTRY,
                    help="Read-only outgroup registry TSV for R1")
    ap.add_argument("--r1-evidence", default="",
                    help="Read-only manifest of hash-bound exact accession records")
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    tax, host = load_ssot()
    tipmap = {}
    if a.tip_map and os.path.exists(a.tip_map):
        for ln in open(a.tip_map).read().splitlines()[1:]:
            c = ln.split("\t")
            if len(c) >= 2 and c[0].strip(): tipmap[c[0].strip()] = c[1].strip()
    files = sorted(glob.glob(os.path.join(a.genomes_dir, "*.fna")) +
                   glob.glob(os.path.join(a.genomes_dir, "*.fasta")))
    rep = Report()
    if not files:
        rep.add("G0", "FAIL", "No genome files found", a.genomes_dir)
        _emit(rep, a); sys.exit(1)

    # S1 -- the tree's declared identity, read off disk rather than out of a folder name
    spec, spec_path = load_spec(a.genomes_dir)
    if spec is None:
        rep.add("S1", "FAIL", "No TREE_SPEC.json — this tree does not declare what it contains",
                f"expected at {spec_path}; without it cohort and title cannot be checked, which "
                f"is how an attine and a moss strain entered a tree named 'bee_*'")
        spec = {}
    elif "_error" in spec:
        rep.add("S1", "FAIL", "TREE_SPEC.json is unreadable", f"{spec_path}: {spec['_error']}")
        spec = {}
    else:
        rep.add("S1", "PASS", "Tree declares its identity",
                f"scope={spec.get('scope')} taxon={spec.get('taxon')} cohort={spec.get('cohort')}")
        # spec supplies defaults the caller did not override on the command line
        a.scope = a.scope or spec.get("taxon", "")
        a.cohort = a.cohort or spec.get("cohort", "")
        if spec.get("outgroup"): a.outgroup = a.outgroup if a.outgroup != "OUTGROUP" else spec["outgroup"]

    check_env(rep)
    check_genomes(rep, files)
    check_assembly_quality(rep, files)
    check_superseded(rep, files)

    # partition ingroup / outgroup
    og = [f for f in files if a.outgroup.lower() in os.path.basename(f).lower()]
    ing = [f for f in files if f not in og]
    as_n = [f for f in ing if re.match(r"AS-\d+", os.path.basename(f))]
    comp = [f for f in ing if f not in as_n]

    check_cohort(rep, as_n, tax, host, a.cohort)
    novel_genus = set(spec.get("novel_genus_queries", [])) if isinstance(spec, dict) else set()
    check_genus_comparators(rep, as_n, comp, tax, a.min_genus_comparators, novel_genus)

    # T1 taxonomy resolution
    unresolved, genera = [], {}
    for f in ing:
        base = os.path.basename(f)[:-4] if os.path.basename(f).endswith('.fna') else os.path.basename(f)
        resolved = tipmap.get(base, os.path.basename(f))
        g, label = genus_of(resolved, tax)
        if g is None: unresolved.append(label)
        else: genera.setdefault(g, []).append(label)
    rep.add("T1", "FAIL" if unresolved else "PASS",
            "Every ingroup genome resolves to a genus",
            ("UNRESOLVED: " + ", ".join(unresolved) +
             "  — empty/typo taxonomy in the SSOT; fix at source, do not build")
            if unresolved else f"{len(ing)} genomes -> {len(genera)} genera")

    # T0 off-target guard -- a KNOWN non-actinomycete genus is contamination (host/pathogen/fungal
    # comparators share the reference pool). Distinct from T2u (unmapped ACTINO genus = WARN):
    # hard FAIL, the fungus-among-Nocardia the sign-off gate exists to stop.
    offtarget = {g: v for g, v in genera.items() if g.lower() in NON_ACTINO}
    rep.add("T0", "FAIL" if offtarget else "PASS",
            "No non-actinomycete (off-target) genomes in the ingroup",
            ("OFF-TARGET: " + "; ".join(f"{g}: {', '.join(v)}" for g, v in offtarget.items()) +
             "  -- host/pathogen/fungal comparator; remove before building")
            if offtarget else f"{len(genera)} ingroup genera, none on the non-actinomycete blocklist")

    # T2 family coherence
    fams = {}
    unknown = []
    for g, labels in genera.items():
        rk = rank_of(g)
        if rk is None: unknown.append(g); continue
        fams.setdefault(rk[0], []).extend(labels)
    if unknown:
        rep.add("T2u", "WARN", "Genus not in the taxonomy map (extend TAXA)", ", ".join(sorted(unknown)))
    # Compare at the rank the tree actually declares. An order-scoped tree spanning several
    # families is correct by construction, and reporting that as a FAIL is the gate crying
    # wolf -- which is the very habit that let real FAILs get skipped.
    rank_level = (spec.get("scope") or "family").lower()
    if rank_level == "order":
        groups = {}
        for g, labels in genera.items():
            rk = rank_of(g)
            if rk: groups.setdefault(rk[1], []).extend(labels)
    else:
        groups = fams
    scope = a.scope or (max(groups, key=lambda k: len(groups[k])) if groups else "")
    if scope and groups:
        off = {f: v for f, v in groups.items() if f != scope}
        if off:
            det = "; ".join(f"{f}: {', '.join(v)}" for f, v in off.items())
            rep.add("T2", "FAIL" if a.scope else "WARN",
                    f"Ingroup members outside declared {rank_level} '{scope}'", det +
                    f"  — a genome from another {rank_level} will misplace and distort the root")
        else:
            det = f"{len(groups[scope])} genomes"
            if rank_level == "order" and len(fams) > 1:
                det += f"; {len(fams)} families within it: " + ", ".join(sorted(fams))
            rep.add("T2", "PASS", f"All ingroup genomes are {scope} ({rank_level} scope)", det)

    # T3 rank span
    orders = {rank_of(g)[1] for g in genera if rank_of(g)}
    if len(orders) > 1:
        rep.add("T3", "FAIL", f"Ingroup spans {len(orders)} orders — no legitimate sister outgroup exists",
                ", ".join(sorted(orders)) + "  — split into per-family trees")
    else:
        rep.add("T3", "PASS", "Ingroup within a single order", ", ".join(orders) or "n/a")

    # O1/O2/O3 outgroup
    if not og:
        rep.add("O1", "FAIL", "No outgroup genome found", f"nothing matching '{a.outgroup}' — tree cannot be rooted")
    elif len(og) > 1:
        rep.add("O1", "WARN", "More than one outgroup (multi-lineage rooting)",
                ", ".join(os.path.basename(x) for x in og) +
                "  -- intentional for e.g. Amycolatopsis+Gordonia; IQ-TREE roots on TREE_SPEC root_outgroup")
    else:
        ogn = os.path.basename(og[0])
        rep.add("O1", "PASS", "Exactly one outgroup", ogn)
        ogb = ogn[:-4] if ogn.endswith('.fna') else ogn
        ogg, _ = genus_of(tipmap.get(ogb, ogn), tax)
        if ogg in genera:
            rep.add("O2", "FAIL", "Outgroup genus also appears in the ingroup", ogg)
        else:
            rep.add("O2", "PASS", "Outgroup genus not in ingroup", ogg or "?")
        if rank_of(ogg) and orders:
            of, oo = rank_of(ogg)
            io = list(orders)[0] if len(orders) == 1 else None
            if io is None:
                rep.add("O3", "FAIL",
                        "Outgroup validity cannot be established — ingroup spans multiple orders",
                        f"outgroup {ogg} ({oo}); ingroup orders: {', '.join(sorted(orders))} — "
                        "no taxon is a sister group to all of them (this is what forces a distant "
                        "root like Bifidobacterium). Fix T3 first.")
            elif oo == io:
                rep.add("O3", "PASS", "Outgroup is same-order sister (family tree)", f"{ogg} ({of}, {oo})")
            else:
                near = {"Streptomycetales","Pseudonocardiales","Micromonosporales",
                        "Streptosporangiales","Propionibacteriales","Corynebacteriales"}
                if oo in near and io in near:
                    rep.add("O3", "PASS", "Outgroup is a near sister order", f"{ogg} ({oo}) vs ingroup {io}")
                else:
                    rep.add("O3", "FAIL", "Outgroup is a DISTANT taxon, not a sister group",
                            f"{ogg} ({oo}) vs ingroup {io} — long-branch attraction; pick from OUTGROUP_REGISTRY")

    # C1 comparator balance
    if as_n:
        ratio = len(comp) / len(as_n)
        rep.add("C1", "PASS" if ratio >= a.min_ratio else "FAIL",
                f"Comparator balance {len(comp)} references : {len(as_n)} AS (ratio {ratio:.2f})",
                f"required >= {a.min_ratio}")
    else:
        rep.add("C1", "PASS", "No AS query strains — reference-only tree", "")

    check_registry_accessions(rep, a.r1_registry, a.r1_evidence)

    _emit(rep, a)
    sys.exit(1 if rep.fails() else 0)

def _emit(rep, a):
    print(f"=== phylo_preflight: {a.genomes_dir} ===")
    for i in rep.items:
        mark = {"PASS": "  ok ", "WARN": "  ~  ", "FAIL": " FAIL"}[i["status"]]
        print(f"{mark} [{i['check']}] {i['message']}")
        if i["detail"] and i["status"] != "PASS":
            print(f"        {i['detail']}")
    n_f, n_w = len(rep.fails()), len(rep.warns())
    print(f"--- {len(rep.items)-n_f-n_w} pass / {n_w} warn / {n_f} FAIL ---")
    if n_f: print("    DO NOT BUILD until FAILs are resolved.")
    if a.json:
        _atomic_write_json(rep.items, a.json, owner_dir=os.path.dirname(os.path.abspath(a.json)), indent=1)

if __name__ == "__main__":
    main()
