#!/usr/bin/env python3
"""Reusable methods-caption drafts and separate operator notes.

caption(workflow, versions=..., params=..., result=..., extra=...) composes
reader-facing method/reading text. It does not verify execution provenance or
filter caller text. Check the final caption with caption_guard.check_caption.
operator_notes(workflow) returns internal interpretation/provenance reminders;
CLAIM_SAFETY remains available for compatibility and is never auto-appended.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import os, re, shutil, subprocess
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # bundle root for `import mamey` (v9.7.367 A10)
from mamey.workspace_root import workspace_root

# ---- the library. Each workflow: what it does (plain English), the tools it uses, how to read it, citation. ----
WORKFLOWS = {'phylo_placement': {'title': 'Phylogenetic placement of query sequences on a fixed reference tree',
                     'does': 'Query sequences were evaluated by maximum likelihood on a fixed reference '
                             'tree and reference alignment under the supplied evolutionary model. '
                             'Placements associate queries with reference edges while retaining the '
                             'reference topology.',
                     'tools': ['mafft', 'raxml-ng', 'epa-ng', 'gappa'],
                     'tool_roles': {'mafft': 'reference + query sequences aligned',
                                    'raxml-ng': 'maximum-likelihood reference tree + evolutionary-model '
                                                'parameters',
                                    'epa-ng': 'evolutionary placement of each query onto the fixed '
                                              'reference tree',
                                    'gappa': 'placement post-processing (grafted tree + '
                                             'nearest-neighborhood assignment)'},
                     'read': 'A likelihood-weight ratio (LWR) reports relative likelihood weight for a '
                             'placement among alternative edges for that query. Pendant length is the '
                             "fitted branch from the reference edge to the query, in the tree's "
                             'branch-length units. These values depend on reference sampling, alignment '
                             'and model settings.',
                     'cite': ['EPA-ng: Barbera et al. 2019, Syst Biol 68:365',
                              'gappa: Czech et al. 2020, Bioinformatics 36:3263',
                              'RAxML-NG: Kozlov et al. 2019, Bioinformatics 35:4453',
                              'MAFFT: Katoh & Standley 2013, Mol Biol Evol 30:772']},
 'gtotree_coregenome': {'title': 'Concatenated single-copy marker phylogeny',
                        'does': 'Conserved single-copy marker genes were identified by HMM searches, '
                                'aligned, trimmed and concatenated for phylogenetic inference using the '
                                'recorded tree-building method.',
                        'tools': ['GToTree', 'hmmer', 'muscle', 'trimal', 'FastTree/IQ-TREE'],
                        'tool_roles': {'GToTree': 'marker identification, alignment, concatenation '
                                                  'pipeline',
                                       'IQ-TREE': 'tree inference and requested support tests'},
                        'read': 'Tips identify the included genome assemblies. Interpret node labels '
                                'using the recorded support test and branch lengths using the stated '
                                'units; marker recovery and assembly completeness describe the input '
                                'sampling.',
                        'cite': ['GToTree: Lee 2019, Bioinformatics 35:4162',
                                 'IQ-TREE: Minh et al. 2020, Mol Biol Evol 37:1530']},
 'iqtree_ml': {'title': 'Maximum-likelihood gene/marker phylogeny',
               'does': 'Aligned sequences were used for maximum-likelihood tree inference under the '
                       'recorded substitution model. Model-selection and branch-support procedures are '
                       'specified by the supplied run parameters.',
               'tools': ['mafft/muscle', 'IQ-TREE'],
               'tool_roles': {'IQ-TREE': 'model specification or selection, tree inference and requested '
                                         'support tests'},
               'read': 'Node labels report the support measures requested for this run; a '
                       'substitutions-per-site scale describes the fitted branch lengths.',
               'cite': ['IQ-TREE: Minh et al. 2020, Mol Biol Evol 37:1530',
                        'ModelFinder: Kalyaanamoorthy et al. 2017, Nat Methods 14:587']},
 'domain_tree': {'title': 'Biosynthetic domain phylogeny vs MIBiG reference domains',
                 'does': 'Biosynthetic domain sequences extracted from antiSMASH regions were aligned '
                         'with selected MIBiG reference domains for tree inference, showing their '
                         'relationships within the included sequence panel.',
                 'tools': ['muscle', 'FastTree/IQ-TREE'],
                 'tool_roles': {'FastTree': 'approximate-ML domain tree'},
                 'read': 'Tips represent domain sequences, rather than whole clusters. Grouping is '
                         'evaluated for the selected domain alignment and reference panel; domain '
                         'paralogy and repeated domain architectures can affect those relationships.',
                 'cite': ['FastTree: Price et al. 2010, PLoS ONE 5:e9490',
                          'MIBiG: Terlouw et al. 2023, NAR 51:D603']},
 'ani_fastani': {'title': 'Whole-genome average nucleotide identity (ANI)',
                 'does': 'Pairwise average nucleotide identity (ANI) was estimated between the compared '
                         'genome assemblies using fastANI.',
                 'tools': ['fastANI'],
                 'tool_roles': {'fastANI': 'alignment-free ANI'},
                 'read': 'The percentage summarizes nucleotide identity for mapped fragments of each '
                         'assembly pair. Mapped-fragment and total-query-fragment counts describe the '
                         'coverage of that comparison.',
                 'cite': ['fastANI: Jain et al. 2018, Nat Commun 9:5114']}}

CLAIM_SAFETY = ("Claim-safety: results are class-level phylogenetic hypotheses; 16S/marker placement indicates a "
                "neighborhood, not a species assignment; similarity is not identity; no bioactivity or structural "
                "claim; judgment deferred.")



OPERATOR_NOTES = {
    "phylo_placement": "Verify the reference roster, type-strain aliases and sequence quality separately. LWR is relative placement weight conditional on the model/reference panel, not calibrated taxonomic certainty; pendant length alone does not diagnose assembly or alignment quality.",
    "gtotree_coregenome": "Verify marker set, recovery, alignment/trimming, actual tree engine and support settings against run receipts. More markers alone do not establish greater resolution for every dataset.",
    "iqtree_ml": "Only name automatic model selection, UFBoot or SH-aLRT when the actual command/output establishes that each procedure ran.",
    "domain_tree": "Domain homology does not establish a physical contig join or compound identity. Validate domain extraction, alignment and reference provenance independently.",
    "ani_fastani": "ANI thresholds are interpretation choices, not an automatic species verdict from this helper. Preserve mapping coverage and assembly-quality evidence; a missing fastANI row is not a measured zero.",
}


def operator_notes(workflow):
    """Internal notes only; never append these to a rendered/public caption."""
    return OPERATOR_NOTES[workflow] + "\n\n" + CLAIM_SAFETY


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
            if r.returncode != 0:
                out[tool] = ""  # failed probes cannot supply Methods versions
                continue
            txt = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
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
    """Compose a reader caption without filtering caller text or asserting run admission."""
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
    return "\n\n".join(lines)


if __name__ == "__main__":
    import sys, json
    wf = sys.argv[1] if len(sys.argv) > 1 else "phylo_placement"
    emit(caption(wf, versions=detect_versions()))
