#!/usr/bin/env python3
"""phylo_place.py — reference-backbone phylogenetic PLACEMENT of query 16S (or protein) sequences.

The method the Developer or User asked for: build a strong reference tree from high-quality data (type strains), then
*place* the lab test strains onto that fixed backbone and report which clade / neighborhood each falls in —
WITHOUT letting the low-quality queries perturb the reference topology. This is the standard "phylogenetic
placement" workflow (EPA-ng + gappa; SEPP for fragmentary queries).

HARD RULES baked in (Sapote-Mamey governing gates):
  * DATA-TYPE MATCH: a 16S query places only onto a 16S reference tree; a protein/core-gene query places only
    onto a protein backbone. This tool refuses to mix nt queries with an aa reference and vice-versa.
  * SOURCE SEPARATION: one reference package per cohort (streptomyces / nocardia / rare_genera / attines /
    moss / bees). --group is required and stamped into every output; the tool never merges cohorts.
  * 16S = ANCHOR, NOT SPECIES: every report carries the claim-safety header. Placement states a neighborhood
    (genus/clade) with a likelihood-weight ratio (LWR); it is not a species assignment and not an ANI call.
  * TREE-APPROVAL GATE: `build-ref` (the only CPU-heavy step) prints the approval reminder and refuses to run
    unless --approved-by is supplied (records who authorized the CPU, per the standing tree-approval rule).

Pipeline (subcommands):
  build-ref  ref_typestrains.fasta  --group streptomyces --approved-by the Developer or User
             -> align (mafft) -> ML reference tree + model (raxml-ng, else iqtree) -> a frozen refpkg/ dir.
  place      --refpkg <dir> --query lab_16S.fasta
             -> align queries into ref coordinates (mafft --add --keeplength; hmmalign for --fragmentary)
             -> epa-ng -> query.jplace
  report     --refpkg <dir> --jplace query.jplace
             -> gappa examine graft (grafted tree) + gappa examine assign (per-query neighborhood)
             -> <group>_placements.tsv + grafted .newick + claim-safe README; runs the advisory sign-off gate.
  all        one-shot: build-ref (if needed) -> place -> report.

Depends on a `placement` conda env (epa-ng, gappa, sepp, raxml-ng, mafft) + phylo env (iqtree, hmmer, muscle).
Set PLACEMENT_BIN to that env's bin (default below). Nothing here is engine-wired; it is a Tools/ workflow.
"""
import argparse, json, os, re, shutil, subprocess, sys, datetime
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # bundle root for `import mamey` (v9.7.367 A10)
import sys
from mamey.workspace_root import workspace_root
try:
    from _console import emit
except ImportError:  # foreign-cwd import: tools/ not on sys.path
    from tools._console import emit

ROOT = str(workspace_root())


def official_data_root(marker="OFFICIAL_DATA/STRAIN_METADATA.tsv"):
    """Where OFFICIAL_DATA/ actually is. workspace_root() deliberately falls back to cwd (portability
    design, shared by ~12 modules; do not change it) — so a run launched from inside a placement
    directory used to look for OFFICIAL_DATA *there*, hard-fail on --add-outgroup and SILENTLY drop the
    enriched tip labels (AMBER-409 F2/F3, observed live 2026-09-04). Order: SAPOTE_WORKSPACE_ROOT /
    SAPOTE_ROOT if set; then cwd and every parent of it (the caller's workspace); then ROOT; then every
    parent of this file (the bundle's install site, last resort). First directory holding the marker wins;
    None if nowhere. Before all of that, mamey.external_data.resolve('official_data') is honoured, so
    MAMEY_OFFICIAL_DATA / MAMEY_DATA_ROOT (the engine's convention) pin it too. Env wins so an unusual
    nested layout can be pinned."""
    seen = []
    cands = []
    try:  # the engine's own resolver first: MAMEY_OFFICIAL_DATA / MAMEY_DATA_ROOT (mamey.external_data)
        from mamey.external_data import resolve as _resolve
        r = _resolve("official_data")
        if r is not None and os.path.exists(os.path.join(str(r), os.path.basename(marker))):
            return os.path.dirname(os.path.abspath(str(r)))
    except Exception:  # resolver absent or its probe missing: fall through to the walk
        r = None
    for var in ("SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT"):
        v = os.environ.get(var)
        if v:
            cands.append(v)
    _P = __import__("pathlib").Path
    cwd = os.path.abspath(os.getcwd())
    cands += [cwd] + [str(q) for q in _P(cwd).parents]      # the caller's workspace wins over the bundle's
    cands.append(ROOT)
    here = os.path.dirname(os.path.abspath(__file__))
    cands += [here] + [str(q) for q in _P(here).parents]    # last resort: wherever the bundle is installed
    for c in cands:
        c = os.path.abspath(c)
        if c in seen:
            continue
        seen.append(c)
        if os.path.exists(os.path.join(c, marker)):
            return c
    return None
PLACEMENT_BIN = os.environ.get("PLACEMENT_BIN", f"{ROOT}/miniconda3/envs/placement/bin")
PHYLO_BIN = os.environ.get("PHYLO_BIN", f"{ROOT}/miniconda3/envs/phylo/bin")
# Cohort-specific groups keep sources separate (the default, per the source-separation rule). The `combined_*`
# groups are a DELIBERATE opt-in for the Developer or User's broader cross-cohort research trees — allowed, but named so a
# combined tree is never produced by accident and always carries its own chosen outgroup.
COHORT_GROUPS = {"streptomyces", "nocardia", "rare_genera", "attines", "moss", "bees"}
COMBINED_GROUPS = {"combined", "combined_hymenoptera", "combined_all", "combined_moss_bees"}
GROUPS = COHORT_GROUPS | COMBINED_GROUPS

# A single capitalized Latin genus token (e.g. "Actinomadura") is a PER-GENUS placement cohort:
# the strictest form of source separation — one genus, never a mix of cohorts. It is accepted
# outside the named GROUPS set only when it carries its own registry outgroup (--add-outgroup),
# so a per-genus tree can never be produced by accident and always roots on a named sister
# lineage (sign-off gate #1).
def _is_per_genus_group(g):
    return bool(re.match(r"^[A-Z][a-z]+$", g or ""))

CLAIM_SAFE = (
    "CLAIM-SAFETY: 16S rRNA is a phylogenetic ANCHOR, not a species assignment. A placement states the "
    "genus/clade NEIGHBORHOOD a query falls into on a fixed reference backbone, with a likelihood-weight "
    "ratio (LWR) and pendant length as confidence. It is NOT an ANI/species call, NOT a bioactivity or "
    "structure claim. Low LWR or long pendant = uncertain placement. Judgment deferred."
)


def _env(extra_first):
    e = dict(os.environ)
    e["PATH"] = extra_first + ":" + PHYLO_BIN + ":" + e.get("PATH", "")
    return e


def _which(name, *bins):
    for b in bins:
        p = os.path.join(b, name)
        if os.path.exists(p):
            return p
    return shutil.which(name)


def _safe_token(name, seen):
    """Newick/raxml-safe tip label: keep [A-Za-z0-9_], collapse the rest to '_', ensure uniqueness."""
    t = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_") or "seq"
    base = t
    i = 2
    while t in seen:
        t = f"{base}_{i}"; i += 1
    seen.add(t)
    return t


def _sanitize_fasta(src, dst, labelmap_path, seen, append=False):
    """Write dst with Newick-safe headers; record safe<TAB>original in labelmap. Returns n written."""
    n = 0
    with open(dst, "w") as out, open(labelmap_path, "a" if append else "w") as lm:
        if not append:
            lm.write("safe\toriginal\n")
        nm = None; buf = []
        def flush():
            nonlocal n
            if nm is None:
                return
            safe = _safe_token(nm, seen)
            # Keep the labelmap strictly 2-column: a header exported from a LIMS/spreadsheet can carry
            # an embedded literal tab (or an embedded CR/LF), which .strip() at read time does NOT
            # remove. Written verbatim it would split the "original" field into extra columns, and that
            # tab-bearing value then flows into best_edge_hits.tsv and shifts every column right by one
            # (silent numeric corruption). Collapse any embedded tab/newline/CR to a single space so the
            # same clean value is what downstream (_load_labelmap → best-hit TSV) reads.
            orig = re.sub(r"[\t\r\n]+", " ", nm)
            out.write(f">{safe}\n" + "".join(buf) + "\n")
            lm.write(f"{safe}\t{orig}\n")
            n += 1
        for ln in open(src, encoding="utf-8", errors="replace"):
            if ln.startswith(">"):
                flush(); nm = ln[1:].strip(); buf = []
            else:
                buf.append(ln.strip())
        flush()
    return n


def _load_labelmap(path):
    m = {}
    if os.path.exists(path):
        for i, ln in enumerate(open(path)):
            if i == 0 or "\t" not in ln:
                continue
            s, o = ln.rstrip("\n").split("\t", 1)
            if s in m and m[s] != o:
                raise ValueError("LABELMAP_KEY_CONFLICT")
            m[s] = o
    return m


def _is_protein(fasta):
    """Heuristic: sample residues; >15% non-ACGTUN- => protein."""
    seq = []
    for ln in open(fasta):
        if ln.startswith(">"):
            if len(seq) > 4000:
                break
            continue
        seq.append(ln.strip().upper())
    s = "".join(seq)
    s = re.sub(r"[^A-Z]", "", s)
    if not s:
        return False
    nt = sum(c in "ACGTUN" for c in s)
    return (nt / len(s)) < 0.85


def _stamp(d, group, kind, extra=None):
    meta = {"group": group, "kind": kind, "tool": "phylo_place.py",
            "created": datetime.datetime.now().isoformat(timespec="seconds"),
            "engine_context": "candidate (not engine-wired)"}
    if extra:
        meta.update(extra)
    with open(os.path.join(d, "_provenance.json"), "w") as fh:
        json.dump(meta, fh, indent=2)


# ---------------------------------------------------------------- reference dedup
# Culture-collection acronyms used to recognise "the same strain under a different accession".
# Real multi-letter collection codes only; single-letter isolate codes (W30, S137) are caught by
# the "strain <TOKEN>" fallback instead, so we never over-merge distinct isolates. Matched on
# UNDERSCORE-tokenised headers (NCBI 16S RefSeq titles use '_' separators, so a regex \b after '_'
# would never fire — token comparison is used instead).
_CC_CODES = {"ATCC", "DSM", "JCM", "NRRL", "NBRC", "IFO", "CIP", "IMMIB", "YIM", "KCTC", "KACC",
             "CGMCC", "CCTCC", "NEAU", "KLBMP", "CAP", "CCUG", "LMG", "VKM", "CECT", "NCIMB",
             "NCTC", "BCRC", "MTCC", "CBS"}
_ACC_TOK = re.compile(r"^(NR|[A-Z]{1,2})\d", re.I)   # accession-like token to skip in the fallback


def _read_fasta_pairs(path):
    recs, nm, buf = [], None, []
    for ln in open(path, encoding="utf-8", errors="replace"):
        if ln.startswith(">"):
            if nm is not None:
                recs.append((nm, "".join(buf)))
            nm = ln[1:].strip(); buf = []
        else:
            buf.append(ln.strip())
    if nm is not None:
        recs.append((nm, "".join(buf)))
    return recs


def _species_key(header):
    """'Genus species' (plus subsp/var epithet when present) — lowercased. Subspecies stay DISTINCT
    from the parent species so a real subsp. (e.g. N. salmonicida subsp. cummidelens) is never
    silently merged into the species.

    AMBER_396 fix: NCBI 16S RefSeq titles LEAD with the accession ('NR_######.#  Genus species ...').
    The old code read toks[0] toks[1] = 'NR 115365.1' as the binomial, so every reference got a
    UNIQUE species key = its own accession and `one_per_species` collapsed NOTHING by species
    (2x S. kasugaensis, 2x S. albiaxialis, 6x S. griseus all survived). Strip a leading accession
    token first so the binomial is read from the organism name."""
    h = re.sub(r"^\s*(?:NR_\d+(?:[._]\d+)?|[A-Z]{1,2}\d{5,}(?:\.\d+)?)[ _]+", "", header.strip(), flags=re.I)
    toks = re.split(r"[ _]+", h.strip())
    if len(toks) < 2:
        return h.strip().lower()
    key = f"{toks[0]} {toks[1]}".lower()
    for i, t in enumerate(toks[:-1]):
        if t.lower().rstrip(".") in ("subsp", "var", "subspecies", "biovar", "pv"):
            key += f" {t.lower().rstrip('.')} {toks[i+1].lower()}"
    return key


def _strain_key(header):
    """Normalised culture-collection / isolate designation, so the SAME strain deposited under
    several accessions collapses to one key (e.g. ATCC 33726 under three NR_ accessions -> ATCC33726).
    '' when no strain token is present (then only exact-sequence identity can merge it). Works on the
    underscore-tokenised header and never folds the trailing accession into the key."""
    toks = [t for t in re.split(r"[ _]+", header.strip()) if t]
    up = [t.upper() for t in toks]
    for i, t in enumerate(up):
        if t in _CC_CODES:
            parts = [t]
            j = i + 1
            # gather the collection number (and a split letter+number, e.g. IMMIB R 1434)
            while j < len(up) and not up[j].startswith("NR") \
                    and re.fullmatch(r"[0-9][0-9A-Za-z]*|[A-Z]", up[j]):
                parts.append(up[j]); j += 1
                if len(parts) >= 3:
                    break
            key = "".join(parts)
            if any(c.isdigit() for c in key):
                return key
    for i, t in enumerate(up[:-1]):     # fallback: first non-accession token after 'STRAIN'
        if t == "STRAIN" and not _ACC_TOK.match(up[i + 1]):
            return up[i + 1].replace("-", "")
    return ""


def _accession(header):
    """Heuristic candidate for reporting only; not an authoritative accession identity."""
    from mamey.tip_label import accession_candidates
    result = accession_candidates(header)
    return result["candidates"][0] if result["state"] == "HEURISTIC_CANDIDATE" else ""


def _dedup_reference(src, dst, report_path, one_per_species=False):
    """Collapse redundant reference entries BEFORE tree inference. Returns (n_kept, n_dropped).

    Two always-on, PROVABLE-same-strain passes (never drops a genuinely distinct taxon):
      1. exact ungapped-sequence identity  -> keep the longest, drop the rest;
      2. same (species, strain designation) across different accessions -> keep the longest.
    Opt-in `one_per_species` additionally keeps ONE representative per species (longest 16S) for a
    strict type-strain backbone. Residual same-species multiplicity is always WARNed (not dropped)
    so the curator adjudicates it. Every decision is written to report_path (sign-off gate #4:
    documented comparator provenance)."""
    import hashlib
    recs = _read_fasta_pairs(src)
    info = []
    for h, s in recs:
        useq = re.sub(r"[^A-Za-z]", "", s).upper()
        info.append({"h": h, "seq": s, "len": len(useq),
                     "md5": hashlib.md5(useq.encode()).hexdigest(),
                     "sp": _species_key(h), "strain": _strain_key(h), "acc": _accession(h),
                     "action": "kept", "rep": ""})

    def _collapse(records, keyfn, reason):
        groups = {}
        for r in records:
            k = keyfn(r)
            if k is None:
                continue
            groups.setdefault(k, []).append(r)
        for k, g in groups.items():
            if len(g) < 2:
                continue
            rep = max(g, key=lambda r: (bool(r["strain"]), r["len"]))  # prefer a strain-designated, most-complete 16S
            for r in g:
                if r is not rep and r["action"] == "kept":
                    r["action"] = reason; r["rep"] = rep["h"]

    _collapse(info, lambda r: r["md5"] if r["action"] == "kept" else None,
              "dropped:identical-sequence")
    _collapse(info, lambda r: (r["sp"], r["strain"]) if (r["action"] == "kept" and r["strain"]) else None,
              "dropped:same-strain-diff-accession")
    if one_per_species:
        _collapse(info, lambda r: r["sp"] if r["action"] == "kept" else None,
                  "dropped:one-per-species")

    kept = [r for r in info if r["action"] == "kept"]
    with open(dst, "w") as out:
        for r in kept:
            out.write(f">{r['h']}\n{r['seq']}\n")
    with open(report_path, "w") as rep:
        rep.write("action\tspecies\tstrain\taccession\tlen\tmd5\theader\trepresentative\n")
        for r in info:
            rep.write("\t".join([r["action"], r["sp"], r["strain"], r["acc"],
                                 str(r["len"]), r["md5"][:8], r["h"], r["rep"]]) + "\n")

    # WARN: same accession on >1 distinct header (data-integrity red flag) ...
    acc_seen = {}
    for r in info:
        if r["acc"]:
            acc_seen.setdefault(r["acc"], []).append(r["h"])
    for acc, hs in sorted(acc_seen.items()):
        if len(hs) > 1:
            sys.stdout.write((f"[build-ref] WARN accession {acc} on {len(hs)} different headers "
                  f"(likely a mislabelled entry): {', '.join(hs)}") + "\n")
    # ... and residual same-species multiplicity that was NOT auto-collapsed (curator to adjudicate).
    sp_kept = {}
    for r in kept:
        sp_kept.setdefault(r["sp"], []).append(r)
    for sp, g in sorted(sp_kept.items()):
        if len(g) > 1:
            sys.stdout.write((f"[build-ref] WARN species '{sp}' still has {len(g)} reference tips after "
                  f"same-strain dedup ({', '.join(_strain_key(r['h']) or '?' for r in g)}); "
                  f"if these are the same type strain, re-run with --one-per-species.") + "\n")
    return len(kept), len(info) - len(kept)


_AS_META = None


def _as_meta():
    """Lazy {AS-####: {host, loc, acc}} from the GOVERNED spine OFFICIAL_DATA/STRAIN_METADATA.tsv —
    host_common (clean ecological category), isolation location, and the 16S GenBank accession. Used
    to enrich AS query tip labels. Returns {} if the spine is absent (labels then fall back to id)."""
    global _AS_META
    if _AS_META is None:
        _AS_META = {}
        base = official_data_root()
        if base is None:
            emit("WARN phylo_place: OFFICIAL_DATA/STRAIN_METADATA.tsv not found from the env, the bundle "
                 "or any parent of the current directory — tip labels will be BARE IDs (no host / "
                 "location / accession). Set SAPOTE_WORKSPACE_ROOT or run from the workspace.",
                 file=sys.stderr)
            return _AS_META
        ssot = f"{base}/OFFICIAL_DATA/STRAIN_METADATA.tsv"
        try:
            import csv
            for r in csv.DictReader(open(ssot), delimiter="\t"):
                t = (r.get("tip_label") or "").strip()
                if t.startswith("AS"):
                    _AS_META[t] = {"host": (r.get("host_common") or "").strip(),
                                   "loc": (r.get("location") or "").strip(),
                                   "acc": (r.get("genbank_accession") or "").strip()}
        except Exception as exc:
            _AS_META = {}
            emit(f"WARN phylo_place: could not read {ssot} ({type(exc).__name__}: {exc}) — tip labels "
                 "will be BARE IDs.", file=sys.stderr)
    return _AS_META


def _dedup_queries(src, dst):
    """Collapse duplicate QUERY sequences before placement: same query id, or byte-identical sequence,
    placed twice just clutters the grafted tree. Keeps the first, WARNs each drop. Returns (kept, dropped)."""
    import hashlib
    recs = _read_fasta_pairs(src)
    seen_seq, seen_id, kept, dropped = {}, set(), [], 0
    for h, s in recs:
        qid = h.split()[0]
        key = hashlib.md5(re.sub(r"[^A-Za-z]", "", s).upper().encode()).hexdigest()
        if qid in seen_id or key in seen_seq:
            dropped += 1
            sys.stdout.write((f"[place] WARN duplicate query dropped: {qid} (== {seen_seq.get(key, qid)})") + "\n")
            continue
        seen_id.add(qid); seen_seq[key] = qid; kept.append((h, s))
    with open(dst, "w") as o:
        for h, s in kept:
            o.write(f">{h}\n{s}\n")
    return len(kept), dropped


def _ref_length_warn(fasta, min_len, drop):
    """WARN (and, if drop, remove) reference 16S shorter than min_len — partial/short reads make an
    unreliable backbone branch. Returns the path to use (possibly a filtered copy) and n_short."""
    recs = _read_fasta_pairs(fasta)
    short = [(h, len(re.sub(r"[^A-Za-z]", "", s))) for h, s in recs
             if len(re.sub(r"[^A-Za-z]", "", s)) < min_len]
    if short:
        sys.stdout.write((f"[build-ref] WARN {len(short)} reference sequence(s) shorter than {min_len} bp "
              f"(partial 16S weakens the backbone): "
              + ", ".join(f"{h.split()[0]}={n}bp" for h, n in short[:6])
              + (" ..." if len(short) > 6 else "")) + "\n")
    if drop and short:
        keep = [(h, s) for h, s in recs if len(re.sub(r"[^A-Za-z]", "", s)) >= min_len]
        filtered = fasta + ".minlen"
        with open(filtered, "w") as o:
            for h, s in keep:
                o.write(f">{h}\n{s}\n")
        sys.stdout.write((f"[build-ref] dropped {len(short)} short reference(s); {len(keep)} remain.") + "\n")
        return filtered, len(short)
    return fasta, len(short)


def _dedup_summary(refpkg):
    """Read reference_dedup.tsv (written by build-ref) → counts for the report, or None. Lets the
    deliverable (caption + README) STATE that the backbone was deduplicated and how — sign-off gate #4
    (documented comparator provenance) instead of an unexplained tip count."""
    path = os.path.join(refpkg or "", "reference_dedup.tsv")
    if not refpkg or not os.path.exists(path):
        return None
    kept = dropped = 0
    reasons = {}
    for i, ln in enumerate(open(path)):
        if i == 0:
            continue
        act = ln.split("\t", 1)[0]
        if act == "kept":
            kept += 1
        elif act.startswith("dropped"):
            dropped += 1
            reasons[act] = reasons.get(act, 0) + 1
    if kept == 0 and dropped == 0:
        return None
    return {"n_input": kept + dropped, "n_kept": kept, "n_dropped": dropped,
            "one_per_species": "dropped:one-per-species" in reasons, "reasons": reasons}


# ---------------------------------------------------------------- build-ref
def _placement_tip_is_query(tip):
    """Use the same accession guard for neighborhood rows and rendered tip roles."""
    name = tip.name or ""
    if re.match(r"^(NR|NG|NZ|NC)[_ ]?\d|^[A-Z]{2}\d{6}", name.strip()):
        return False
    return re.search(r"(^|[_-])(AS|SID)[_-]?\d", name) is not None


def cmd_build_ref(a):
    if a.group not in GROUPS:
        if _is_per_genus_group(a.group):
            if not getattr(a, "add_outgroup", ""):
                sys.exit(f"per-genus group '{a.group}' requires --add-outgroup <sister genus> "
                         "(source-separation rule: a single-genus tree must root on a named sister lineage)")
            sys.stdout.write((f"[build-ref] NOTE: '{a.group}' is a PER-GENUS placement cohort — strictest "
                              "source separation (one genus); rooting on its registry outgroup.") + "\n")
        else:
            sys.exit(f"--group must be one of {sorted(GROUPS)}, or a single-genus name "
                     "(e.g. Actinomadura) with --add-outgroup (source-separation rule)")
    if a.group in COMBINED_GROUPS:
        sys.stdout.write((f"[build-ref] NOTE: '{a.group}' is a DELIBERATE cross-cohort tree — ensure your reference set "
              "carries a correct, single outgroup lineage (sign-off gate #1) and consistent tip labels.") + "\n")
    if not a.approved_by:
        sys.exit("TREE-APPROVAL GATE: build-ref does CPU-heavy ML inference. Re-run with "
                 "--approved-by <name> to record who authorized this tree (standing tree-approval rule).")
    prot = _is_protein(a.ref_fasta)
    outdir = a.refpkg or f"{ROOT}/strain_data/_PLACEMENT/{a.group}/refpkg"
    os.makedirs(outdir, exist_ok=True)
    mafft = _which("mafft", PLACEMENT_BIN, PHYLO_BIN)
    if not mafft:
        sys.exit("mafft not found; install the placement env first (see INSTALL.md)")
    ref_fasta = a.ref_fasta
    # optional: auto-append the decided outgroup 16S from the outgroup registry (outgroup_registry.py)
    if getattr(a, "add_outgroup", ""):
        if prot:
            sys.exit("--add-outgroup pulls a 16S sequence; it applies only to a nucleotide (16S) reference set.")
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            import outgroup_registry as OG
        except Exception as e:
            sys.exit(f"--add-outgroup needs outgroup_registry.py beside phylo_place.py: {e}")
        og_fa = OG.get_16s(a.add_outgroup, scope=getattr(a, "outgroup_scope", "genus"))
        combined = os.path.join(outdir, "ref.with_outgroup.fasta")
        with open(combined, "w") as out:
            for src in (a.ref_fasta, og_fa):
                with open(src) as fh:
                    out.write(fh.read().rstrip("\n") + "\n")
        ref_fasta = combined
        sys.stdout.write((f"[build-ref] appended registry outgroup for '{a.add_outgroup}' -> {os.path.basename(og_fa)}") + "\n")
        # Capture the APPENDED outgroup's record IDs so rooting can find the right tip. --add-outgroup
        # names the INGROUP genus (looked up above); the outgroup taxon differs (e.g. Actinomadura ->
        # Actinocorallia). Rooting must match the outgroup tip, never the ingroup-genus string.
        a._outgroup_ids = [ln[1:].split()[0] for ln in open(og_fa) if ln.startswith('>')]
    # v9.7.395 (AMBER): collapse duplicate reference entries BEFORE inference. A Nocardia backbone
    # carried the same type strain several times under different accessions (N. nova x4 = ATCC 33726
    # x3 + JCM 6044; N. exalbida x2) — _safe_token only *uniquifies the label*, so the duplicates
    # otherwise survive as extra tips and the identical-label collision left one rendered at the
    # default (giant) font. Provable same-strain dups drop automatically; residual same-species
    # multiplicity is WARNed; --one-per-species enforces a strict one-tip-per-species backbone.
    # EGGPLANT_411-E: on a PER-GENUS backbone that carries its own registry outgroup, strip any
    # reference record whose genus is neither the ingroup genus (== the group name) nor the appended
    # outgroup. The .408 autopilot seeds distant "sentinels" (Streptomyces/Nocardia) into every genus
    # reference; on a genus that already has a proper sister-genus outgroup those sentinels are redundant
    # AND create a dominating branch that FAILs tree_sanity_check. Guarded: only per-genus + --add-outgroup.
    if _is_per_genus_group(a.group) and getattr(a, "add_outgroup", ""):
        _ogset = set(getattr(a, "_outgroup_ids", []) or [])
        _kept, _dropped = [], []
        _cur = None
        for _ln in open(ref_fasta):
            if _ln.startswith(">"):
                _tok = _ln[1:].split()[0]
                _gen = ""
                _mrest = _ln[1:].split()
                # genus = first alpha word after an optional leading accession token
                _rest = " ".join(_mrest)
                import re as _re
                _rest = _re.sub(r"^[A-Z]{2}[ _]?\d+(?:[ _.]?\d+)?\s+", "", _rest)
                _mg = _re.match(r"([A-Za-z]+)", _rest)
                _gen = _mg.group(1) if _mg else ""
                _cur = (_tok in _ogset) or (_gen.lower() == a.group.lower())
                (_kept if _cur else _dropped).append(_tok)
            if _cur:
                pass
        if _dropped:
            _keepset = set(_kept)
            _tmp = ref_fasta + ".genusfilt"
            with open(_tmp, "w") as _out:
                _emit_line = False
                for _ln in open(ref_fasta):
                    if _ln.startswith(">"):
                        _emit_line = (_ln[1:].split()[0] in _keepset)
                    if _emit_line:
                        _out.write(_ln)
            ref_fasta = _tmp
            sys.stdout.write((f"[build-ref] per-genus filter: dropped {len(_dropped)} foreign-genus "
                              f"sentinel record(s) not in '{a.group}' or the outgroup") + "\n")
    ref_dedup = os.path.join(outdir, "ref.dedup.fasta")
    dedup_report = os.path.join(outdir, "reference_dedup.tsv")
    n_kept, n_drop = _dedup_reference(ref_fasta, ref_dedup, dedup_report,
                                      one_per_species=getattr(a, "one_per_species", False))
    sys.stdout.write((f"[build-ref] reference dedup: {n_kept} kept, {n_drop} dropped "
          f"(see {os.path.basename(dedup_report)})") + "\n")
    ref_fasta = ref_dedup
    # v9.7.395 (AMBER): flag (and optionally drop) short/partial reference 16S that make a weak backbone.
    ref_fasta, _ = _ref_length_warn(ref_fasta, getattr(a, "min_ref_len", 0) or 1200,
                                    drop=bool(getattr(a, "min_ref_len", 0)))
    # sanitize headers → Newick/raxml-safe tokens; keep a label map for the report
    labelmap = os.path.join(outdir, "labelmap.tsv")
    ref_safe = os.path.join(outdir, "ref.safe.fasta")
    _sanitize_fasta(ref_fasta, ref_safe, labelmap, seen=set(), append=False)
    ref_aln = os.path.join(outdir, "ref.aln.fasta")
    sys.stdout.write((f"[build-ref] {a.group}  ({'protein' if prot else 'nucleotide'})  aligning reference…") + "\n")
    with open(ref_aln, "w") as fh:
        rc = subprocess.call([mafft, "--auto", "--anysymbol", ref_safe], env=_env(PLACEMENT_BIN),
                             stdout=fh, stderr=subprocess.DEVNULL)
    if rc != 0 or not os.path.getsize(ref_aln):
        sys.exit("mafft reference alignment failed")

    raxml = _which("raxml-ng", PLACEMENT_BIN)
    ref_tree = os.path.join(outdir, "ref.tree")
    # v9.7.412 (EGGPLANT): 16S reference alignments are dominated by invariant sites (the
    # bee-Streptomyces backbone measured 77.8% invariant over 1,652 sites), and without +I the
    # ML fit compensates with a pathological Gamma shape (alpha 0.139). GTR+I+G fits better on
    # every reference set measured 2026-09-07 -- 12 alignments, 5 to 217 taxa, delta logL +5.1
    # (Peterkaempfera, n=5) to +434.1 (Nocardioides, n=160) for ONE extra parameter.
    # Two things this change is NOT: it is not branch-length-neutral and it is not a pure
    # reparameterisation. Total tree length moved in BOTH directions across those sets (ratio
    # GTR+G : GTR+I+G from 0.379 on Actinomycetospora to 1.578 on Pseudonocardia; the 217-taxon
    # Streptomyces set was 6.260 -> 3.180), and TOPOLOGY moves too (Robinson-Foulds up to
    # 86/184 bipartitions on Amycolatopsis, 104/314 on Nocardioides). Rebuilding a backbone
    # under this model can therefore move EPA-ng placements onto different edges: downstream
    # neighbourhood calls must be re-derived, never assumed to carry over. Per-set receipts are
    # in each refpkg's MODEL_COMPARISON_GTRIG.md.
    model = "GTR+I+G" if not prot else "LG+I+G"
    if raxml:
        pre = os.path.join(outdir, "ref.raxml")
        # v9.7.412 (EGGPLANT): --redo is REQUIRED here. RAxML-NG refuses to overwrite existing
        # output files and exits BEFORE writing its log, so rebuilding into a refpkg that already
        # holds ref.raxml.* fails with a bare "raxml-ng failed" and no diagnosable cause. Worse,
        # mafft has by then already overwritten ref.aln.fasta, leaving the refpkg pairing a NEW
        # alignment with an OLD tree -- a wrong-but-plausible package. Observed 2026-09-07 on
        # a local reference package (35-tip tree beside a 217-taxon MSA).
        cmd = [raxml, "--all", "--msa", ref_aln, "--model", model, "--seed", "12345",
               "--bs-trees", str(a.bootstrap), "--threads", str(a.threads), "--prefix", pre,
               "--redo", "--force", "perf_threads"]
        sys.stdout.write((f"[build-ref] raxml-ng ML tree ({model}, {a.bootstrap} BS)…") + "\n")
        if subprocess.call(cmd, env=_env(PLACEMENT_BIN)) != 0:
            sys.exit("raxml-ng failed")
        shutil.copy(pre + ".raxml.bestTree", ref_tree)
        bestmodel = pre + ".raxml.bestModel"
    else:  # fall back to IQ-TREE (house standard) — epa-ng re-evaluates the model from ref.aln + tree
        iq = _which("iqtree3", PHYLO_BIN) or _which("iqtree", PHYLO_BIN) or _which("iqtree2", PHYLO_BIN)
        if not iq:
            sys.exit("neither raxml-ng nor iqtree found")
        pre = os.path.join(outdir, "ref.iq")
        mset = "GTR" if not prot else "LG,WAG,JTT"
        cmd = [iq, "-s", ref_aln, "-m", "MFP", "-mset", mset, "-B", str(max(1000, a.bootstrap)),
               "-T", str(a.threads), "-seed", "12345", "-redo", "-pre", pre]
        sys.stdout.write(("[build-ref] iqtree ML tree (raxml-ng absent; epa-ng will re-evaluate model)…") + "\n")
        if subprocess.call(cmd, env=_env(PHYLO_BIN)) != 0:
            sys.exit("iqtree failed")
        shutil.copy(pre + ".treefile", ref_tree)
        bestmodel = ""
    with open(os.path.join(outdir, "MODEL"), "w") as fh:
        fh.write(model + "\n")
    if bestmodel:
        shutil.copy(bestmodel, os.path.join(outdir, "ref.bestModel"))
    elif os.path.exists(os.path.join(outdir, "ref.bestModel")):
        # A successful IQ-TREE rebuild must not reuse a previous RAxML fit.
        os.remove(os.path.join(outdir, "ref.bestModel"))
    # Root the backbone on the appended registry outgroup so EPA-ng placements land on a ROOTED
    # reference (PHYLOGENETICS_WORKFLOW.md). The outgroup 16S was added via --add-outgroup above;
    # its tip carries the outgroup genus. Best-effort: rooting must never fail the build, and with no
    # --add-outgroup the backbone is left as-is (backward compatible).
    if getattr(a, "add_outgroup", ""):
        # FAIL CLOSED (Codex C399-15 / the patch-pool review .400 review): the operator ASKED for a
        # registry-rooted backbone. Silently continuing with an unrooted tree would hand EPA-ng an
        # unrooted reference while the provenance says otherwise — a wrong-but-plausible refpkg, the
        # exact failure class this lane's gates exist to prevent. Any failure to root is a typed
        # REFUSAL and no refpkg is stamped; the operator re-runs with a resolvable outgroup.
        def _norm(s): return re.sub(r'[^A-Za-z0-9]', '_', s or '').lower()
        _og_ids = [_norm(i) for i in getattr(a, '_outgroup_ids', []) or []]
        try:
            from Bio import Phylo as _Phylo
            _bt = _Phylo.read(ref_tree, "newick")
            if _og_ids:
                _og_hits = [x for x in _bt.get_terminals()
                            if any(o in _norm(x.name) for o in _og_ids)]
            else:
                _og_hits = [x for x in _bt.get_terminals()
                            if a.add_outgroup.lower() in (x.name or "").lower()]
        except Exception as _e:
            sys.exit(f"BACKBONE_ROOTING_UNAVAILABLE: --add-outgroup was requested but the backbone "
                     f"could not be read for rooting ({_e}). Refusing to stamp an unrooted refpkg; "
                     f"no placement package written.")
        if len(_og_hits) != 1:
            sys.exit(f"BACKBONE_OUTGROUP_UNRESOLVED: --add-outgroup '{a.add_outgroup}' matched "
                     f"{len(_og_hits)} backbone tips (need exactly 1). Refusing to stamp an unrooted "
                     f"refpkg; re-run with a substring that resolves to one tip.")
        try:
            _bt.root_with_outgroup(_og_hits[0])
            _Phylo.write(_bt, ref_tree, "newick")
        except Exception as _e:
            sys.exit(f"BACKBONE_ROOTING_FAILED: could not root on '{_og_hits[0].name}' ({_e}). "
                     f"Refusing to stamp an unrooted refpkg; no placement package written.")
        sys.stdout.write((f"[build-ref] rooted backbone on registry outgroup tip: {_og_hits[0].name}") + "\n")
    _stamp(outdir, a.group, "refpkg",
           {"molecule": "protein" if prot else "nucleotide", "model": model,
            "approved_by": a.approved_by, "n_ref": sum(1 for l in open(ref_fasta) if l.startswith(">"))})
    sys.stdout.write((f"[build-ref] refpkg ready: {outdir}\n            ref.aln.fasta · ref.tree · MODEL · _provenance.json") + "\n")
    return 0


# ---------------------------------------------------------------- place
def cmd_place(a):
    prov = json.load(open(os.path.join(a.refpkg, "_provenance.json")))
    ref_prot = prov.get("molecule") == "protein"
    q_prot = _is_protein(a.query)
    if ref_prot != q_prot:
        sys.exit(f"DATA-TYPE MISMATCH: refpkg is {'protein' if ref_prot else 'nucleotide'} but query is "
                 f"{'protein' if q_prot else 'nucleotide'}. A 16S query places only onto a 16S backbone.")
    epa = _which("epa-ng", PLACEMENT_BIN)
    if not epa:
        sys.exit("epa-ng not found; install the placement env first (see INSTALL.md)")
    ref_aln = os.path.join(a.refpkg, "ref.aln.fasta")
    ref_tree = os.path.join(a.refpkg, "ref.tree")
    outdir = a.outdir or os.path.join(a.refpkg, "..", "placements")
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    # sanitize query headers too (same safe-token scheme); extend the refpkg label map
    labelmap = os.path.join(a.refpkg, "labelmap.tsv")
    seen = set(_load_labelmap(labelmap).keys())
    q_safe = os.path.join(outdir, "query.safe.fasta")
    # v9.7.395 (AMBER): drop duplicate queries (same id / identical sequence) before placing.
    q_dedup = os.path.join(outdir, "query.dedup.fasta")
    nq_keep, nq_drop = _dedup_queries(a.query, q_dedup)
    if nq_drop:
        sys.stdout.write((f"[place] query dedup: {nq_keep} kept, {nq_drop} duplicate quer{'y' if nq_drop == 1 else 'ies'} dropped") + "\n")
    _sanitize_fasta(q_dedup, q_safe, labelmap, seen=seen, append=os.path.exists(labelmap))
    a.query = q_safe
    q_aln = os.path.join(outdir, "query.aligned.fasta")

    if a.fragmentary:  # SEPP-style: hmmalign query against a profile of the ref alignment
        hmmbuild = _which("hmmbuild", PHYLO_BIN, PLACEMENT_BIN)
        hmmalign = _which("hmmalign", PHYLO_BIN, PLACEMENT_BIN)
        hmm = os.path.join(outdir, "ref.hmm")
        subprocess.check_call([hmmbuild, "--dna" if not ref_prot else "--amino", hmm, ref_aln],
                              env=_env(PHYLO_BIN), stdout=subprocess.DEVNULL)
        subprocess.check_call([hmmalign, "--trim", "--outformat", "afa", "-o", q_aln, hmm, a.query],
                              env=_env(PHYLO_BIN), stdout=subprocess.DEVNULL)
    else:  # mafft --add --keeplength: align queries into the frozen reference coordinate system
        mafft = _which("mafft", PLACEMENT_BIN, PHYLO_BIN)
        with open(q_aln, "w") as fh:
            subprocess.check_call([mafft, "--add", a.query, "--keeplength", "--anysymbol", ref_aln],
                                  env=_env(PLACEMENT_BIN), stdout=fh, stderr=subprocess.DEVNULL)
        # epa-ng --split separates the combined alignment back into ref + query in identical columns
        subprocess.check_call([epa, "--redo", "--split", ref_aln, q_aln, "--outdir", outdir],
                              env=_env(PLACEMENT_BIN), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cand = os.path.join(outdir, "query.fasta")
        if os.path.exists(cand):
            q_aln = cand

    cmd = [epa, "--redo", "--tree", ref_tree, "--ref-msa", ref_aln, "--query", q_aln, "--outdir", outdir]
    bm = os.path.join(a.refpkg, "ref.bestModel")
    if os.path.exists(bm):                       # raxml-ng bestModel = optimized params epa-ng needs
        cmd += ["--model", bm]
    else:                                        # iqtree fallback: give epa-ng the generic model to optimize
        model = open(os.path.join(a.refpkg, "MODEL")).read().strip() if \
            os.path.exists(os.path.join(a.refpkg, "MODEL")) else "GTR+G"
        cmd += ["--model", model]
    sys.stdout.write(("[place] epa-ng placing queries onto the fixed reference backbone…") + "\n")
    if subprocess.call(cmd, env=_env(PLACEMENT_BIN)) != 0:
        sys.exit("epa-ng failed")
    jp = os.path.join(outdir, "epa_result.jplace")
    sys.stdout.write((f"[place] jplace: {jp}") + "\n")
    _stamp(outdir, prov["group"], "placement",
           {"n_query": sum(1 for l in open(a.query) if l.startswith(">")), "fragmentary": a.fragmentary})
    return 0


# ---------------------------------------------------------------- report
def cmd_report(a):
    gappa = _which("gappa", PLACEMENT_BIN)
    if not gappa:
        sys.exit("gappa not found; install the placement env first (see INSTALL.md)")
    outdir = a.outdir or os.path.dirname(os.path.abspath(a.jplace))
    grp = "unknown"
    pj = os.path.join(os.path.dirname(a.jplace), "_provenance.json")
    if os.path.exists(pj):
        grp = json.load(open(pj)).get("group", "unknown")
    # 1) grafted tree: queries attached to the backbone (the picture)
    from tools.graft_integrity import generate_checked_graft
    graft = generate_checked_graft(gappa, a.jplace, outdir, _env(PLACEMENT_BIN))
    # 2) per-query neighborhood + confidence table
    subprocess.call([gappa, "examine", "assign", "--jplace-path", a.jplace,
                     "--out-dir", outdir, "--allow-file-overwriting"], env=_env(PLACEMENT_BIN)) \
        if a.taxonomy else None
    # 3) best-hit table straight from the jplace (always available, no taxonomy file needed)
    tsv = os.path.join(outdir, f"{grp}_placements.tsv")
    lm = {}
    for cand in (os.path.join(a.refpkg or "", "labelmap.tsv") if a.refpkg else "",
                 os.path.join(os.path.dirname(a.jplace), "..", "refpkg", "labelmap.tsv")):
        if cand and os.path.exists(cand):
            lm = _load_labelmap(cand); break
    _jplace_besthit_tsv(a.jplace, tsv, lm)
    # 4) readable neighborhoods: each query's nearest REFERENCE tip on the grafted tree
    nbtsv = os.path.join(outdir, f"{grp}_neighborhoods.tsv")
    n_nb = _grafted_neighborhoods(graft, lm, nbtsv) if os.path.exists(graft) else 0
    # 5) figure: grafted tree, queries highlighted
    fig_png = os.path.join(outdir, f"{grp}_placement_tree.png")
    if os.path.exists(graft):
        try:
            _render_tree(graft, lm, fig_png, fig_png.replace(".png", ".svg"), grp)
        except Exception as e:
            sys.stdout.write((f"[report] figure skipped: {e}") + "\n"); fig_png = None
    else:
        fig_png = None
    # 6) METHODS CAPTION for the figure (self-explanatory; not just program names)
    cap_path = os.path.join(outdir, f"{grp}_placement_FIGURE_CAPTION.txt")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import figure_methods as FM
        prov = {}
        pjson = os.path.join(a.refpkg or "", "_provenance.json") if a.refpkg else ""
        if pjson and os.path.exists(pjson):
            prov = json.load(open(pjson))
        # result summary: n placed + LWR range from the besthit table
        lwrs = []
        for i, ln in enumerate(open(tsv)):
            if i == 0:
                continue
            c = ln.rstrip("\n").split("\t")
            if len(c) > 2:
                try:
                    lwrs.append(float(c[2]))
                except ValueError:
                    pass
        res = (f"{len(lwrs)} {grp} query sequences placed onto the reference backbone "
               f"(LWR {min(lwrs):.2f}-{max(lwrs):.2f})." if lwrs else None)
        params = {"molecule": prov.get("molecule", "16S"), "model": prov.get("model", ""),
                  "n_reference": prov.get("n_ref", ""), "cohort": grp}
        extra = (f"Reference backbone = {prov.get('n_ref','?')} type strains for cohort '{grp}' (source-separated); "
                 "nearest reference is nearest AMONG these — enrich the reference set before species-level reading.")
        _ded = _dedup_summary(a.refpkg)
        if _ded:
            _mode = "one representative per species" if _ded["one_per_species"] \
                else "provable same-strain duplicates collapsed"
            extra += (f" Reference deduplicated before inference: {_ded['n_input']} input records → "
                      f"{_ded['n_kept']} tips ({_mode}; {_ded['n_dropped']} dropped, see reference_dedup.tsv).")
        cap = FM.caption("phylo_placement", versions=FM.detect_versions(), params=params, result=res, extra=extra)
        with open(cap_path, "w") as fh:
            fh.write(f"Figure. {grp} 16S phylogenetic placement.\n\n" + cap + "\n")
    except Exception as e:
        sys.stdout.write((f"[report] caption skipped: {e}") + "\n"); cap_path = None
    readme = os.path.join(outdir, f"{grp}_PLACEMENT_README.md")
    with open(readme, "w") as fh:
        fh.write(f"# {grp} — 16S phylogenetic placement onto type-strain backbone\n\n{CLAIM_SAFE}\n\n"
                 "## How to read\n- **best_edge_lwr** = likelihood-weight ratio of the top placement "
                 "(0–1; higher = more confident which branch).\n- **pendant_length** = branch length from the "
                 "backbone to the query (long = query is divergent / poorly represented).\n- A query with high "
                 "LWR + short pendant sits confidently *within* that clade's neighborhood; low LWR = ambiguous, "
                 "report as 'near' not 'in'.\n\nSource-separated: this backbone is "
                 f"**{grp} only** — never merged with other cohorts (moss/bees/attines/etc. are separate trees).\n")
        _ded = _dedup_summary(a.refpkg)
        if _ded:
            _byreason = ", ".join(f"{k.split(':', 1)[1]}={v}" for k, v in sorted(_ded["reasons"].items()))
            fh.write(f"\n## Reference provenance (dedup)\n"
                     f"- input reference records: **{_ded['n_input']}**\n"
                     f"- backbone tips after dedup: **{_ded['n_kept']}** "
                     f"({'one representative per species' if _ded['one_per_species'] else 'provable same-strain collapse only'})\n"
                     f"- dropped: **{_ded['n_dropped']}** ({_byreason})\n"
                     f"- full per-record decisions: `reference_dedup.tsv` in the refpkg.\n")
    # advisory sign-off gate (never blocks)
    chk = f"{ROOT}/Tools/signoff_check.py"
    if os.path.exists(chk):
        subprocess.call([_which("python3", PHYLO_BIN) or "python3", chk, "--quiet-if-clean", "--minutes", "90"],
                        env=_env(PHYLO_BIN))
    sys.stdout.write((f"[report] {tsv}") + "\n")
    if n_nb:
        sys.stdout.write((f"[report] {nbtsv}  ({n_nb} queries → named nearest reference / neighborhood)") + "\n")
    if fig_png:
        sys.stdout.write((f"[report] {fig_png}  (figure: queries red, outgroup grey, refs blue)") + "\n")
    if cap_path:
        sys.stdout.write((f"[report] {cap_path}  (methods caption — paste under the figure)") + "\n")
    sys.stdout.write((f"[report] {readme}\n[report] grafted tree + gappa outputs in {outdir}") + "\n")
    return 0


def _jplace_besthit_tsv(jplace, tsv, labelmap=None):
    labelmap = labelmap or {}
    d = json.load(open(jplace))
    fields = d["fields"]
    ei = fields.index("edge_num"); li = fields.index("like_weight_ratio")
    pi = fields.index("pendant_length"); di = fields.index("distal_length") if "distal_length" in fields else None
    key = "nm" if "nm" in (d["placements"][0] if d["placements"] else {}) else "n"
    rows = []
    for p in d["placements"]:
        name = p.get("n", p.get("nm", [["?"]]))
        name = name[0][0] if key == "nm" else name[0]
        best = max(p["p"], key=lambda r: r[li])
        rows.append((labelmap.get(name, name), best[ei], f"{best[li]:.3f}", f"{best[pi]:.4f}",
                     f"{best[di]:.4f}" if di is not None else ""))
    rows.sort(key=lambda r: -float(r[2]))
    with open(tsv, "w") as fh:
        fh.write("query\tbest_edge\tbest_edge_lwr\tpendant_length\tdistal_length\n")
        for r in rows:
            fh.write("\t".join(map(str, r)) + "\n")




def _grafted_neighborhoods(graft_newick, labelmap, out_tsv):
    """From the gappa-grafted tree, name each query's nearest REFERENCE tip (the readable neighborhood)."""
    from Bio import Phylo
    def pretty(n):
        if n in labelmap:
            return labelmap[n]
        return labelmap.get(re.sub(r"_\d+$", "", n), n)   # gappa may suffix grafted queries with _N
    t = Phylo.read(graft_newick, "newick")
    tips = t.get_terminals()
    # v9.7.374 fix: was AS-only -- docs/phylogenomics.md's own convention names "focal AS/SID
    # genome" as the two legitimate query-tip prefixes for this workflow. A SID-prefixed query was
    # silently misclassified as a reference tip: excluded from this neighborhood table entirely
    # (never gets a "nearest reference tip" row) and, in the sibling _render_tree() use of this
    # same lambda, miscolored blue ("reference") instead of red/bold ("query") on the rendered
    # figure. Reproduced live: is_q("SID10815") was False before this fix.
    # v9.7.412 (EGGPLANT): the widened pattern also matches CULTURE-COLLECTION codes embedded in a
    # reference name. Observed live on the bee-Streptomyces graft: the type strain
    # "NR_027222.1 Streptomyces anthocyanicus strain AS 4.1594" matched via "_AS_4" and was reported
    # as a 101st query in Streptomyces_neighborhoods.tsv, against 100 actually placed. A reference
    # tip silently promoted to a query inflates every count taken from that file.
    # Fix: a tip whose name begins with a RefSeq/GenBank accession is a REFERENCE, never a query.
    # This keeps the .374 behaviour that made SID-prefixed queries work, and rules out the
    # "AS 4.xxxx" culture code the sibling producer already guards against.
    is_q = _placement_tip_is_query
    refs = [x for x in tips if not is_q(x)]
    qs = [x for x in tips if is_q(x)]
    rows = []
    for q in qs:
        if not refs:
            break
        best = min(refs, key=lambda r: t.distance(q, r))
        rows.append((pretty(q.name), pretty(best.name).replace("_", " "), f"{t.distance(q, best):.4f}"))
    rows.sort(key=lambda r: float(r[2]))
    with open(out_tsv, "w") as fh:
        fh.write("as_query\tnearest_type_strain\tpatristic_dist\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    return len(rows)


def _graft_sane(graft_newick, outgroup=None):
    """HARD pre-render gate for placement grafts (PHYLOGENETICS_WORKFLOW.md step 6): returns
    tree_sanity_check.check()'s (ok, msg). Importable/testable without matplotlib. `outgroup` is the
    graft's outgroup genus (the non-modal reference genus) so a correct sister taxon is exempt."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tree_sanity_check as _tsc
    return _tsc.check(graft_newick, outgroup=outgroup)


def _placement_display_labels(tips, labelmap, og_names, *, tip_fields=None, width=58):
    """Reuse exact labelmap keys and existing query/outgroup owners for display only.

    Callers without structured source fields receive explicit unbound holds. This
    does not infer a species, source accession or metadata join from a tip string.
    """
    from mamey.tip_label import make_label, unique_labels
    from tools.tree_sanity_check import _is_outgroup_tip
    tip_fields = tip_fields or {}
    known = {tip.name for tip in tips}
    if set(tip_fields) - known:
        raise ValueError("SOURCE_FIELDS_TIP_KEY_UNBOUND")
    records = []
    for tip in tips:
        key = tip.name
        record = make_label(key, labelmap.get(key, key),
                            query=_placement_tip_is_query(tip),
                            outgroup=key in og_names or _is_outgroup_tip(key),
                            fields=tip_fields.get(key), width=width)
        if key not in labelmap:
            record["holds"].append("LABELMAP_KEY_UNBOUND")
        records.append(record)
    return unique_labels(records)


def _render_tree(graft_newick, labelmap, png, svg, group, *, tip_fields=None):
    """Render the grafted tree: queries red/bold, outgroup grey, reference blue. Claim-safe title."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from Bio import Phylo

    def pretty(n):
        if not n:
            return ""
        return labelmap.get(n, n)  # no unbound suffix-based source substitution

    # v9.7.374 fix: same AS-only gap as the sibling use of this lambda above (docs/
    # phylogenomics.md's "focal AS/SID genome" convention names both prefixes as legitimate
    # queries); here it drives the rendered figure's query-vs-reference coloring.
    is_q = _placement_tip_is_query

    def lab(x):
        return labels[x.name]["label"] if x.name else ""

    def genus(x):
        m = re.match(r"([A-Za-z]+)", pretty(x.name) or "")
        return m.group(1) if m else ""

    t = Phylo.read(graft_newick, "newick")
    tips = t.get_terminals()
    ref_tips = [x for x in tips if not is_q(x)]
    # outgroup = reference tips whose genus differs from the cohort's MODAL reference genus
    import collections as _c
    genera = _c.Counter(genus(x) for x in ref_tips if genus(x))
    modal = genera.most_common(1)[0][0] if genera else ""
    og_tips = [x for x in ref_tips if genus(x) and genus(x) != modal]
    og_names = {x.name for x in og_tips}
    # HARD pre-render gate: refuse a pathological graft before drawing. Pass the outgroup genus (when
    # a single non-modal genus) so tree_sanity exempts the designated outgroup. cmd_report wraps this
    # call and reports "figure skipped: <reason>" — a FAILing placement tree never reaches a figure.
    _og_genera = {genus(x) for x in og_tips if genus(x)}
    _ok, _msg = _graft_sane(graft_newick, next(iter(_og_genera)) if len(_og_genera) == 1 else None)
    if not _ok:
        raise RuntimeError("tree_sanity_check FAILED — refusing to render placement figure:\n" + _msg)
    try:
        if len(og_tips) == 1:
            t.root_with_outgroup(og_tips[0])
        elif og_tips:
            t.root_with_outgroup(*og_tips)
        else:
            t.root_at_midpoint()
    except Exception:
        try:
            t.root_at_midpoint()
        except Exception:
            pass
    t.ladderize()
    labels = _placement_display_labels(t.get_terminals(), labelmap, og_names,
                                       tip_fields=tip_fields)
    n = len(t.get_terminals())
    fig, ax = plt.subplots(figsize=(11, max(5, n * 0.34)))
    Phylo.draw(t, axes=ax, do_show=False, label_func=lab, show_confidence=False)
    # v9.7.395 (AMBER): key on the STRIPPED label — Phylo.draw renders lab(x), but a lab() truncated
    # at [:48] can end in a space, so a lookup on the un-stripped key missed and the text object kept
    # matplotlib's default (large) font. That orphan is the "much larger font" tip. Strip both sides,
    # and give any still-unmatched text the same 8pt so nothing renders oversized.
    by = {lab(x).strip(): x for x in t.get_terminals()}
    for txt in ax.texts:
        x = by.get(txt.get_text().strip())
        if x is None:
            txt.set_fontsize(8)
            continue
        if is_q(x):
            txt.set_color("#d62728"); txt.set_fontweight("bold")
        elif x.name in og_names:
            txt.set_color("#7f7f7f")
        else:
            txt.set_color("#1f4e79")
        txt.set_fontsize(8)
    ax.set_title(f"{group} 16S — AS strains (red) PLACED on type-strain backbone (blue); outgroup grey\n"
                 "EPA-ng placement; 16S = anchor, not a species call; neighborhood only; judgment deferred",
                 fontsize=8.5)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_yticks([]); ax.set_xlabel("substitutions/site")
    fig.tight_layout()
    fig.savefig(png, dpi=200, bbox_inches="tight"); fig.savefig(svg, bbox_inches="tight")
    plt.close(fig)
    # A label-to-machine-key receipt is distinct from a tree or taxonomic assertion.
    from pathlib import Path
    import hashlib
    Path(str(svg) + ".labels.json").write_text(json.dumps({
        "schema": "placement_display_labels/1",
        "tree_sha256": hashlib.sha256(Path(graft_newick).read_bytes()).hexdigest(),
        "labelmap": labelmap, "records": list(labels.values()),
        "topology_changes_by_label_helper": False,
        "authority": "Display source fields only; accession existence and sequence identity unverified"
    }, indent=2, sort_keys=True))


def cmd_all(a):
    if not (a.refpkg and os.path.exists(os.path.join(a.refpkg, "ref.tree"))):
        cmd_build_ref(a)
        a.refpkg = a.refpkg or f"{ROOT}/strain_data/_PLACEMENT/{a.group}/refpkg"
    cmd_place(a)
    a.jplace = os.path.join(os.path.abspath(a.outdir or os.path.join(a.refpkg, "..", "placements")),
                            "epa_result.jplace")
    cmd_report(a)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Reference-backbone phylogenetic placement (EPA-ng/gappa/SEPP).", allow_abbrev=False)  # v9.7.412: no silent prefix matching
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build-ref", allow_abbrev=False, help="build the frozen reference backbone from type strains")
    b.add_argument("ref_fasta"); b.add_argument("--group", required=True)
    b.add_argument("--refpkg"); b.add_argument("--threads", default="2")
    b.add_argument("--bootstrap", type=int, default=10,
                   help="reference-backbone bootstraps. Default 10: this is a PLACEMENT backbone — "
                        "EPA-ng reports its own per-query support (LWR), so reference-node bootstraps "
                        "are not shown in the placement figure. 100 BS on a few-hundred-taxon 16S "
                        "reference costs hours for no placement benefit. Raise it only if you will "
                        "publish the reference tree itself with node support.")
    b.add_argument("--approved-by", default="")
    b.add_argument("--add-outgroup", default="", metavar="GENUS",
                   help="auto-append the decided outgroup 16S for GENUS from OUTGROUP_REGISTRY (via outgroup_registry.py)")
    b.add_argument("--outgroup-scope", default="genus")
    b.add_argument("--one-per-species", action="store_true",
                   help="collapse the reference to ONE representative per species (longest 16S) for a "
                        "strict type-strain backbone. Default keeps only provable same-strain dedup "
                        "and WARNs on residual same-species multiplicity.")
    b.add_argument("--min-ref-len", type=int, default=0, metavar="BP",
                   help="drop reference sequences shorter than BP (partial 16S). Default 0 = WARN only "
                        "(threshold 1200 bp) without dropping.")
    b.set_defaults(func=cmd_build_ref)

    p = sub.add_parser("place", allow_abbrev=False, help="place query sequences onto a frozen backbone")
    p.add_argument("--refpkg", required=True); p.add_argument("--query", required=True)
    p.add_argument("--outdir"); p.add_argument("--fragmentary", action="store_true",
                                               help="hmmalign path for short/partial 16S (SEPP-style)")
    p.set_defaults(func=cmd_place)

    r = sub.add_parser("report", allow_abbrev=False, help="grafted tree + neighborhood table + claim-safe README")
    r.add_argument("--refpkg"); r.add_argument("--jplace", required=True); r.add_argument("--outdir")
    r.add_argument("--taxonomy", action="store_true", help="also run gappa examine assign (needs a taxonomy file)")
    r.set_defaults(func=cmd_report)

    a1 = sub.add_parser("all", allow_abbrev=False, help="build-ref (if needed) -> place -> report")
    for x in (a1,):
        x.add_argument("ref_fasta", nargs="?"); x.add_argument("--group", required=True)
        x.add_argument("--refpkg"); x.add_argument("--query", required=True); x.add_argument("--outdir")
        x.add_argument("--threads", default="2"); x.add_argument("--bootstrap", type=int, default=10)
        x.add_argument("--approved-by", default=""); x.add_argument("--fragmentary", action="store_true")
        x.add_argument("--taxonomy", action="store_true")
        x.add_argument("--add-outgroup", default="", metavar="GENUS"); x.add_argument("--outgroup-scope", default="genus")
        x.add_argument("--one-per-species", action="store_true")
        x.add_argument("--min-ref-len", type=int, default=0)
    a1.set_defaults(func=cmd_all)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
