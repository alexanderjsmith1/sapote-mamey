#!/usr/bin/env python3
"""outgroup_registry.py — the "outgroup generator": genus -> a decided, reproducible outgroup.

the Developer or User's ask: "an outgroup generator that hosts the sequences of the outgroups, where you enter a genus
and you get a specific outgroup sequence to use for your tree. For genomes it could be accession numbers
and then automatically download the ones needed."

This tool is the lookup + sequence-cache layer on TOP of the already-curated
`OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv` (the decided taxon->outgroup table with REAL accessions). It does
NOT modify that TSV — it reads it, and it caches the actual 16S sequence for each registered outgroup so
that any tree (any time an Actinomadura / Nocardia / Streptomyces / ... is in Sapote-Mamey) can pull its
correct, consistent outgroup with one call.

Two molecule tracks, matching the registry's two row kinds:
  * 16S track   — extract the outgroup species' 16S rRNA from the local ncbi_16S_RefSeq BLAST DB (offline),
                  cache it, and hand it back as FASTA. This is what feeds a 16S placement tree.
  * genome track — hand back the GC[AF]_ assembly accession, and (only on explicit request) write a fetch
                  script (NCBI datasets/efetch) for genome-level trees. Downloads are NOT auto-run
                  (download = a permissioned action); the tool emits the command for the user to run.

Subcommands:
  lookup   <genus> [--scope genus|family]     -> the registry row (outgroup genus + species + accession)
  get-16s  <genus> [--scope ...] [--out F]    -> cached 16S FASTA for the outgroup (extracts if not cached)
  genome   <genus> [--scope ...] [--fetch]    -> GC[AF]_ accession; --fetch writes a datasets fetch script
  cache-16s [--all|--genus G ...]             -> pre-populate the 16S cache for registered outgroups
  list     [--scope ...]                      -> every registered taxon->outgroup pair

The 16S track needs the `blast` conda env (blastdbcmd) + the local ncbi_16S_RefSeq DB. Nothing here is
engine-wired; it is a Tools/ asset used by phylo_place.py / phylo_refset.py and available standalone.
"""
import argparse, os, re, subprocess, sys
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # bundle root for `import mamey` (v9.7.367 A10)
from mamey.workspace_root import workspace_root

ROOT = str(workspace_root())


def _registry_default():
    """AMBER-409 F2: workspace_root() falls back to cwd by design, so a run from inside a placement
    directory hard-failed with 'registry not found'. Walk env -> ROOT -> this file's parents -> cwd's
    parents for OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv; fall back to the old ROOT-relative path so the
    error message still names a concrete location."""
    marker = "OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv"
    from pathlib import Path as _P
    cands = [os.environ.get(v) for v in ("SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT")]
    here = os.path.dirname(os.path.abspath(__file__)); cwd = os.path.abspath(os.getcwd())
    cands += [cwd] + [str(q) for q in _P(cwd).parents] + [ROOT, here] + [str(q) for q in _P(here).parents]
    for c in cands:
        if c and os.path.exists(os.path.join(c, marker)):
            return os.path.join(c, marker)
    return f"{ROOT}/{marker}"


REGISTRY = os.environ.get("OUTGROUP_REGISTRY") or _registry_default()
CACHE = os.environ.get("OUTGROUP_CACHE", f"{ROOT}/OFFICIAL_DATA/outgroup_cache")
DB16S = os.environ.get("NCBI_16S_DB", f"{ROOT}/Tools/databases/ncbi_16S_RefSeq/16S_ribosomal_RNA")
BLAST_BIN = os.environ.get("BLAST_BIN", f"{ROOT}/miniconda3/envs/blast/bin")

COLS = ["tree_scope", "ingroup_taxon", "family", "outgroup_genus",
        "outgroup_species_strain", "assembly_accession", "status", "rationale"]


def _blastdbcmd():
    p = os.path.join(BLAST_BIN, "blastdbcmd")
    return p if os.path.exists(p) else (__import__("shutil").which("blastdbcmd") or "")


def load_registry(path=REGISTRY):
    """Return list of dict rows (skips comment/blank/header lines)."""
    rows = []
    if not os.path.exists(path):
        sys.exit(f"registry not found: {path}")
    for ln in open(path, encoding="utf-8"):
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        c = ln.rstrip("\n").split("\t")
        if c[0] == "tree_scope":            # header
            continue
        if len(c) < len(COLS):
            c += [""] * (len(COLS) - len(c))
        rows.append(dict(zip(COLS, c)))
    return rows


def find_row(genus, scope="genus", path=REGISTRY):
    r"""Match on ingroup_taxon == genus for the requested scope; genus scope falls back to any match.

    v9.7.374 fix: the registry format legitimately allows MORE THAN ONE exact-scope row for the
    same ingroup taxon -- a LOCKED primary plus a CONFIRM "alternate sister genus" (e.g.
    Micromonospora carries both an Actinoplanes LOCKED row and a Dactylosporangium CONFIRM row;
    OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv itself documents this with the "alternate sister genus"
    rationale text). This previously returned exact[0] -- whichever row happened to come FIRST in
    the TSV -- with no preference for status and no warning. Live-reproduced: against the real
    registry (LOCKED row listed first) this correctly returns Actinoplanes/LOCKED; against a
    reordered scratch copy (CONFIRM row moved first, content otherwise identical) it silently
    flips to Dactylosporangium/CONFIRM. Nothing enforces the ordering that makes the real registry
    currently return the right answer -- a future edit that adds a new alternate row above the
    LOCKED one, for any reason, would silently change which outgroup this "decided, reproducible"
    lookup (this file's own docstring) hands back, with zero error or warning. Given the project's
    own CLAUDE.md sign-off gate treats outgroup correctness as consequential enough to require
    explicit human review, a silent file-order-dependent flip is a real fragility. Now explicitly
    prefers a LOCKED row among exact ties, and prints a stderr warning whenever ambiguity had to be
    resolved so it is visible instead of silent.
    """
    rows = load_registry(path)
    g = genus.strip().lower()
    exact = [r for r in rows if r["ingroup_taxon"].lower() == g and r["tree_scope"] == scope]
    if exact:
        if len(exact) > 1:
            locked = [r for r in exact if r["status"] == "LOCKED"]
            if locked:
                if len(locked) > 1:
                    sys.stderr.write((f"WARNING: outgroup_registry: {len(locked)} LOCKED rows for '{genus}' "
                          f"(scope={scope}); using the first by file order "
                          f"({locked[0]['outgroup_genus']}) -- registry should have only one") + "\n")
                return locked[0]
            sys.stderr.write((f"WARNING: outgroup_registry: {len(exact)} candidate rows for '{genus}' "
                  f"(scope={scope}), none LOCKED; using the first by file order "
                  f"({exact[0]['outgroup_genus']}, status={exact[0]['status']}) -- verify this is "
                  f"the intended outgroup") + "\n")
        return exact[0]
    anyscope = [r for r in rows if r["ingroup_taxon"].lower() == g]
    if anyscope:
        return anyscope[0]
    return None


# ---------------------------------------------------------------- 16S extraction
def _title_index(db=DB16S):
    """Map accession -> title for every 16S DB entry (one blastdbcmd pass)."""
    bdc = _blastdbcmd()
    if not bdc:
        sys.exit("blastdbcmd not found; set BLAST_BIN or install the 'blast' env")
    out = subprocess.run([bdc, "-db", db, "-entry", "all", "-outfmt", "%a@@@%t"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"blastdbcmd failed on {db}:\n{out.stderr[:400]}")
    idx = {}
    for ln in out.stdout.splitlines():
        if "@@@" in ln:
            acc, title = ln.split("@@@", 1)
            idx[acc.strip()] = title.strip()
    return idx


def _pick_accession(idx, out_genus, species_strain):
    """Choose the best 16S accession for the outgroup: match genus+species, prefer the exact strain token,
    prefer RefSeq NR_/NG_ type-strain records, prefer 'strain'/'type' titles."""
    parts = species_strain.split()
    sp = parts[1].lower() if len(parts) > 1 else ""
    strain_tokens = [re.sub(r"[^A-Za-z0-9]", "", t).lower() for t in parts[2:]] if len(parts) > 2 else []
    cands = []
    for acc, title in idx.items():
        tl = title.lower()
        if out_genus.lower() not in tl:
            continue
        if sp and sp not in tl:
            continue
        score = 0
        if acc.startswith(("NR_", "NG_")):
            score += 3
        tnorm = re.sub(r"[^A-Za-z0-9]", "", tl)
        if strain_tokens and any(st and st in tnorm for st in strain_tokens):
            score += 5
        if "type strain" in tl or "(t)" in tl:
            score += 2
        score += min(len(title), 120) / 1000.0        # tie-break: richer title
        cands.append((score, acc, title))
    if not cands:
        return None
    cands.sort(reverse=True)
    return cands[0]


def get_16s(genus, scope="genus", out=None, force=False, quiet=False):
    row = find_row(genus, scope)
    if not row:
        sys.exit(f"no registry row for '{genus}' (scope={scope}); add it to {REGISTRY} first")
    og_genus = row["outgroup_genus"]
    species_strain = row["outgroup_species_strain"]
    safe = re.sub(r"[^A-Za-z0-9]+", "_", f"{og_genus}_{species_strain}").strip("_")
    os.makedirs(os.path.join(CACHE, "16S"), exist_ok=True)
    cache_fa = os.path.join(CACHE, "16S", f"{safe}.fasta")
    if os.path.exists(cache_fa) and os.path.getsize(cache_fa) and not force:
        if not quiet:
            sys.stdout.write((f"[cache-hit] {cache_fa}") + "\n")
    else:
        idx = _title_index()
        pick = _pick_accession(idx, og_genus, species_strain)
        if not pick:
            sys.exit(f"no 16S record found in ncbi_16S_RefSeq for '{og_genus} {species_strain}'. "
                     "16S DBs are type-strain-sparse — either the species isn't represented, or add its "
                     "NR_ accession by hand. (Genome track is unaffected.)")
        score, acc, title = pick
        bdc = _blastdbcmd()
        seq = subprocess.run([bdc, "-db", DB16S, "-entry", acc], capture_output=True, text=True)
        if seq.returncode != 0 or not seq.stdout.strip():
            sys.exit(f"blastdbcmd could not fetch {acc}")
        # rewrite header to a clean, tree-ready label carrying genus/species/strain + accession
        body = "".join(l for l in seq.stdout.splitlines()[1:])
        header = f">{safe}_{acc}  [outgroup for {row['ingroup_taxon']}; {title}]"
        with open(cache_fa, "w") as fh:
            fh.write(header + "\n")
            for i in range(0, len(body), 80):
                fh.write(body[i:i + 80] + "\n")
        if not quiet:
            sys.stdout.write((f"[cached] {og_genus} {species_strain} -> {acc}\n         {cache_fa}") + "\n")
    if out:
        __import__("shutil").copy(cache_fa, out)
        if not quiet:
            sys.stdout.write((f"[wrote] {out}") + "\n")
    return cache_fa


# ---------------------------------------------------------------- subcommands
def cmd_lookup(a):
    row = find_row(a.genus, a.scope)
    if not row:
        sys.exit(f"no registry row for '{a.genus}' (scope={a.scope})")
    sys.stdout.write(("\n".join(f"{k:24s} {row[k]}" for k in COLS)) + "\n")
    if row["status"] == "CONFIRM":
        sys.stdout.write(("\nNOTE: status=CONFIRM — accession is real but verify the type-strain representative before use.") + "\n")
    return 0


def cmd_get16s(a):
    fa = get_16s(a.genus, a.scope, out=a.out, force=a.force)
    if not a.out:
        sys.stdout.write((f"\n# 16S FASTA ready: {fa}\n# append to your reference set, or use phylo_refset.py --add-outgroup {a.genus}") + "\n")
    return 0


def cmd_genome(a):
    row = find_row(a.genus, a.scope)
    if not row:
        sys.exit(f"no registry row for '{a.genus}' (scope={a.scope})")
    acc = row["assembly_accession"]
    sys.stdout.write((f"{row['outgroup_genus']} {row['outgroup_species_strain']}\t{acc}\t(status={row['status']})") + "\n")
    if a.fetch:
        os.makedirs(os.path.join(CACHE, "genomes"), exist_ok=True)
        sh = os.path.join(CACHE, "genomes", f"fetch_{re.sub(r'[^A-Za-z0-9]+','_',acc)}.sh")
        with open(sh, "w") as fh:
            fh.write("#!/bin/bash\n# Outgroup genome fetch (run with network; download is a permissioned action).\n")
            fh.write("set -euo pipefail\n")
            fh.write(f'ACC="{acc}"\n')
            fh.write('datasets download genome accession "$ACC" --include genome '
                     f'--filename "{CACHE}/genomes/${{ACC}}.zip" || \\\n')
            fh.write('  echo "datasets not found — use NCBI web or efetch for $ACC"\n')
        os.chmod(sh, 0o755)
        sys.stdout.write((f"[fetch-script] {sh}\n  (NOT auto-run: downloading is a permissioned action — run it yourself)") + "\n")
    return 0


def cmd_cache16s(a):
    rows = load_registry()
    if a.genus:
        want = {g.lower() for g in a.genus}
        rows = [r for r in rows if r["ingroup_taxon"].lower() in want]
    elif not a.all:
        sys.exit("cache-16s: pass --all or --genus <G> [<G> ...]")
    idx = _title_index()          # one pass, reused
    done, miss = [], []
    seen = set()
    for r in rows:
        key = (r["outgroup_genus"], r["outgroup_species_strain"])
        if key in seen:
            continue
        seen.add(key)
        pick = _pick_accession(idx, r["outgroup_genus"], r["outgroup_species_strain"])
        if not pick:
            miss.append(f"{r['ingroup_taxon']} -> {r['outgroup_genus']} {r['outgroup_species_strain']} (no 16S in RefSeq)")
            continue
        try:
            fa = get_16s(r["ingroup_taxon"], r["tree_scope"], force=a.force, quiet=True)
            done.append(f"{r['ingroup_taxon']:22s} -> {os.path.basename(fa)}  ({pick[1]})")
        except SystemExit as e:
            miss.append(f"{r['ingroup_taxon']}: {e}")
    sys.stdout.write((f"== cached {len(done)} outgroup 16S sequences into {CACHE}/16S ==") + "\n")
    for d in done:
        sys.stdout.write(("  " + d) + "\n")
    if miss:
        sys.stdout.write((f"\n== {len(miss)} not in the 16S RefSeq DB (genome track still fine; add NR_ by hand if needed) ==") + "\n")
        for m in miss:
            sys.stdout.write(("  - " + m) + "\n")
    return 0


def cmd_list(a):
    for r in load_registry():
        if a.scope and r["tree_scope"] != a.scope:
            continue
        sys.stdout.write((f"{r['tree_scope']:7s} {r['ingroup_taxon']:20s} -> {r['outgroup_genus']:18s} "
              f"{r['outgroup_species_strain']:34s} {r['assembly_accession']:18s} [{r['status']}]") + "\n")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Outgroup generator: genus -> decided outgroup 16S/genome.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    lk = sub.add_parser("lookup"); lk.add_argument("genus"); lk.add_argument("--scope", default="genus")
    lk.set_defaults(func=cmd_lookup)

    g16 = sub.add_parser("get-16s"); g16.add_argument("genus"); g16.add_argument("--scope", default="genus")
    g16.add_argument("--out"); g16.add_argument("--force", action="store_true")
    g16.set_defaults(func=cmd_get16s)

    gn = sub.add_parser("genome"); gn.add_argument("genus"); gn.add_argument("--scope", default="genus")
    gn.add_argument("--fetch", action="store_true", help="write a datasets fetch script (does NOT download)")
    gn.set_defaults(func=cmd_genome)

    c16 = sub.add_parser("cache-16s"); c16.add_argument("--all", action="store_true")
    c16.add_argument("--genus", nargs="*"); c16.add_argument("--force", action="store_true")
    c16.set_defaults(func=cmd_cache16s)

    ls = sub.add_parser("list"); ls.add_argument("--scope", default="")
    ls.set_defaults(func=cmd_list)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
