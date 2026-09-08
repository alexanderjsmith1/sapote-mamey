#!/usr/bin/env python3
"""figure_methods.py — reusable, versioned METHODS-CAPTION library for Sapote-Mamey figure tools.

A figure that only prints a program name ("EPA-ng") is opaque to a reader who has never used it. This module
gives every figure generator a **default methods caption**: a plain-English sentence of what the tool does, the
tool + version + key parameters, how to read the figure, and the standing claim-safety line. Especially for
phylogeny, where the same few programs recur, this keeps captions consistent and self-explanatory.

Use:
    import figure_methods as FM
    cap = FM.caption("phylo_placement",
                     versions=FM.detect_versions(),           # auto from conda envs, or pass your own
                     params={"model": "GTR+G", "bootstrap": 100, "n_ref": 12, "outgroup": "Rhodococcus"},
                     result="13/13 AS query 16S placed (LWR 0.68-1.00).")
    open("fig_caption.txt","w").write(cap)

`caption()` always ends with the claim-safety line. `blurb()` returns just the plain-English method sentence
(for embedding a short line on the figure itself). Add new workflows to WORKFLOWS below — data, not code.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import os, re, shutil, subprocess
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # bundle root for `import mamey` (v9.7.367 A10)
from mamey.workspace_root import workspace_root

# ---- the library. Each workflow: what it does (plain English), the tools it uses, how to read it, citation. ----
WORKFLOWS = {
    "phylo_placement": {
        "title": "Phylogenetic placement of query sequences on a fixed reference tree",
        "does": ("A reference phylogeny was built from high-quality type-strain sequences and then held FIXED; "
                 "each query sequence was attached ('placed') onto the branch of that reference tree where it "
                 "fits best by maximum likelihood. The queries do not alter the reference topology — the method "
                 "reports which part of the reference tree each query falls into, not a re-inferred tree."),
        "tools": ["mafft", "raxml-ng", "epa-ng", "gappa"],
        "tool_roles": {
            "mafft": "reference + query sequences aligned",
            "raxml-ng": "maximum-likelihood reference tree + evolutionary-model parameters",
            "epa-ng": "evolutionary placement of each query onto the fixed reference tree",
            "gappa": "placement post-processing (grafted tree + nearest-neighborhood assignment)",
        },
        "read": ("Each query's placement carries a likelihood-weight ratio (LWR, 0-1: confidence in which branch) "
                 "and a pendant length (branch length from the backbone to the query; long = divergent/poorly "
                 "represented). High LWR + short pendant = the query sits confidently within that clade's "
                 "neighborhood; low LWR = report as 'near', not 'in'."),
        "cite": ["EPA-ng: Barbera et al. 2019, Syst Biol 68:365",
                 "gappa: Czech et al. 2020, Bioinformatics 36:3263",
                 "RAxML-NG: Kozlov et al. 2019, Bioinformatics 35:4453",
                 "MAFFT: Katoh & Standley 2013, Mol Biol Evol 30:772"],
    },
    "gtotree_coregenome": {
        "title": "Core-genome (concatenated single-copy gene) maximum-likelihood phylogeny",
        "does": ("Genomes were placed in a phylogeny built from a set of conserved single-copy marker genes: each "
                 "marker was identified by HMM, aligned, trimmed, and concatenated into a supermatrix from which a "
                 "maximum-likelihood tree was inferred. This is a genome-scale tree (many genes), higher "
                 "resolution than any single-gene tree."),
        "tools": ["GToTree", "hmmer", "muscle", "trimal", "FastTree/IQ-TREE"],
        "tool_roles": {"GToTree": "marker identification, alignment, concatenation pipeline",
                       "IQ-TREE": "maximum-likelihood tree + support"},
        "read": ("Tip = one genome. Branch support (SH-aLRT / UFBoot) is shown at nodes; treat thinly-sampled or "
                 "low-support nodes cautiously. Draft/fragmented genomes carry a quality note (branch lengths "
                 "less trustworthy)."),
        "cite": ["GToTree: Lee 2019, Bioinformatics 35:4162", "IQ-TREE: Minh et al. 2020, Mol Biol Evol 37:1530"],
    },
    "iqtree_ml": {
        "title": "Maximum-likelihood gene/marker phylogeny",
        "does": ("Sequences were aligned and a maximum-likelihood tree inferred under the best-fit substitution "
                 "model (selected automatically), with branch support from ultrafast bootstrap and SH-aLRT."),
        "tools": ["mafft/muscle", "IQ-TREE"],
        "tool_roles": {"IQ-TREE": "model selection (ModelFinder) + ML tree + UFBoot/SH-aLRT support"},
        "read": ("Node labels = SH-aLRT / UFBoot support (higher = stronger); scale bar = substitutions per site."),
        "cite": ["IQ-TREE: Minh et al. 2020, Mol Biol Evol 37:1530",
                 "ModelFinder: Kalyaanamoorthy et al. 2017, Nat Methods 14:587"],
    },
    "domain_tree": {
        "title": "Biosynthetic domain phylogeny vs MIBiG reference domains",
        "does": ("Individual biosynthetic domains (e.g. PKS-KS, NRPS-C/A) extracted from antiSMASH regions were "
                 "aligned and placed in a tree alongside domains from characterized MIBiG reference clusters, to "
                 "show which reference neighborhood each query domain groups with."),
        "tools": ["muscle", "FastTree/IQ-TREE"],
        "tool_roles": {"FastTree": "approximate-ML domain tree"},
        "read": ("Domain identity is homology-guided linkage between paralogous sequences — NOT a nucleotide join, "
                 "NOT a compound identity. cis-AT KS domains can cluster by substrate (programming convergence)."),
        "cite": ["FastTree: Price et al. 2010, PLoS ONE 5:e9490", "MIBiG: Terlouw et al. 2023, NAR 51:D603"],
    },
    "ani_fastani": {
        "title": "Whole-genome average nucleotide identity (ANI)",
        "does": ("Pairwise average nucleotide identity was computed between genomes; ~95-96% ANI is the standard "
                 "species boundary."),
        "tools": ["fastANI"],
        "tool_roles": {"fastANI": "alignment-free ANI"},
        "read": ("Values within ~1% of 95% are boundary/indeterminate, not confident same-species. ANI (nucleotide) "
                 "is not AAI (amino-acid identity) — do not conflate."),
        "cite": ["fastANI: Jain et al. 2018, Nat Commun 9:5114"],
    },
}

CLAIM_SAFETY = ("Claim-safety: results are class-level phylogenetic hypotheses; 16S/marker placement indicates a "
                "neighborhood, not a species assignment; similarity is not identity; no bioactivity or structural "
                "claim; judgment deferred.")


def detect_versions(env_bins=None):
    """Best-effort tool versions from conda envs (placement + phylo). Returns {tool: 'x.y.z' or ''}."""
    root = str(workspace_root())
    env_bins = env_bins or [os.environ.get("PLACEMENT_BIN", f"{root}/miniconda3/envs/placement/bin"),
                            os.environ.get("PHYLO_BIN", f"{root}/miniconda3/envs/phylo/bin")]
    out = {}
    for tool in ("epa-ng", "gappa", "raxml-ng", "mafft", "muscle", "iqtree3", "iqtree", "FastTree", "fastANI", "GToTree"):
        path = None
        for b in env_bins:
            if b and os.path.exists(os.path.join(b, tool)):
                path = os.path.join(b, tool); break
        path = path or shutil.which(tool)
        if not path:
            continue
        try:
            r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=8)
            txt = (r.stdout or r.stderr or "").strip()
            m = re.search(r"(\d+\.\d+(\.\d+)?)", txt)
            out[tool] = m.group(1) if m else ""
        except Exception:
            out[tool] = ""
    return out


def _fmt_tools(wf, versions):
    parts = []
    for t in wf["tools"]:
        key = t.split("/")[0]
        v = ""
        for cand in (key, key.lower(), key + "3"):
            if versions.get(cand):
                v = f" v{versions[cand]}"; break
        role = wf.get("tool_roles", {}).get(key, "")
        parts.append(f"{t}{v}" + (f" ({role})" if role else ""))
    return "; ".join(parts)


def blurb(workflow):
    """Just the plain-English method sentence (for a short on-figure line)."""
    return WORKFLOWS[workflow]["does"]


def caption(workflow, versions=None, params=None, result=None, extra=None):
    """Full methods caption paragraph, always ending with the claim-safety line."""
    wf = WORKFLOWS[workflow]
    versions = versions or {}
    params = params or {}
    lines = [f"{wf['title']}.", wf["does"], f"Tools: {_fmt_tools(wf, versions)}."]
    if params:
        pretty = ", ".join(f"{k}={v}" for k, v in params.items())
        lines.append(f"Parameters: {pretty}.")
    lines.append(f"How to read: {wf['read']}")
    if result:
        lines.append(f"Result: {result}")
    if extra:
        lines.append(extra)
    lines.append(f"References: {'; '.join(wf['cite'])}.")
    lines.append(CLAIM_SAFETY)
    return "\n\n".join(lines)


if __name__ == "__main__":
    import sys, json
    wf = sys.argv[1] if len(sys.argv) > 1 else "phylo_placement"
    emit(caption(wf, versions=detect_versions()))
