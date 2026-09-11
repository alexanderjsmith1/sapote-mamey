#!/usr/bin/env bash
# gtotree_env.sh — canonical environment for a GToTree/IQ-TREE phylogenomic run.
#
# PORTABLE VARIANT. Carries no personal paths: the project root is derived from this script's
# own location (it is expected to live in <project>/Tools/), and every other path is either
# derived from that or overridable. This is the change Codex held AMBER_380 at Tier-C for.
#
# WHY THIS EXISTS — every failure below was observed live on 2026-08-26, not hypothesised:
#   1. Calling GToTree by absolute path without the conda env on PATH =>
#      "Muscle is an essential dependency but does not seem to be in your PATH :(" and it exits.
#   2. PATH correct but no HMM dir => "The 'GToTree_HMM_dir' variable is not set :(" and it exits
#      before doing any work.
#   3. A RELOCATED conda env leaves `file` looking for its magic database at the ORIGINAL prefix:
#      "file: could not find any valid magic files!". GToTree calls `file` to detect input
#      compression, so this kills a run AFTER the entire 138-marker HMM search completes — the
#      most expensive possible moment, with an error that names nothing relevant.
#   4. `gtt-data-locations check` fails one variable at a time, hiding four more behind the first.
#      An `-f` FASTA run succeeds with only GToTree_HMM_dir set, which is exactly why this stayed
#      hidden; any GTDB or NCBI-accession (-a) workflow breaks.
#   5. The standalone GToTree v1.8.19 tree ships NO hmm_sets, so it must borrow the conda env's,
#      while the conda env's own GToTree is v1.8.16 — PATH order alone decides which version runs.
#
# v2 COMPATIBILITY: GToTree v2.0.0 renamed three of the data-location variables
# (NCBI_assembly_data_dir -> NCBI_ASSEMBLY_DATA_DIR, GTDB_dir -> GTDB_DIR), dropped TAXONKIT_DB,
# and added Pfam_data_dir. This script exports BOTH spellings so one environment serves either
# version. Setting a variable a given version ignores costs nothing; missing one costs a run.
#
# Usage:
#   source tools/gtotree_env.sh
#   gtotree_preflight || exit 1
#   GToTree -f genome_list.txt -H "$GToTree_HMM_dir/Actinobacteria.hmm" -n 4 -j 2 -o gtotree
#
# Overridable before sourcing:
#   PROJECT_ROOT   project root            (default: the parent of this script's directory)
#   PHYLO_ENV      conda env with the deps (default: $PROJECT_ROOT/miniconda3/envs/phylo)
#   GTOTREE_HOME   GToTree >=1.8.19 tree   (default: $PROJECT_ROOT/Tools/GToTree-1.8.19)
#   GTOTREE_GTDB_DIR, GTOTREE_HMM_SETS

# --- locate ourselves, so nothing below needs a personal path ----------------------------
_gte_src="${BASH_SOURCE[0]:-$0}"
while [ -L "$_gte_src" ]; do
    _gte_dir="$(cd -P "$(dirname "$_gte_src")" && pwd)"
    _gte_src="$(readlink "$_gte_src")"
    case "$_gte_src" in /*) ;; *) _gte_src="$_gte_dir/$_gte_src" ;; esac
done
_gte_dir="$(cd -P "$(dirname "$_gte_src")" && pwd)"

: "${PROJECT_ROOT:=$(cd -P "${_gte_dir}/.." && pwd)}"
: "${PHYLO_ENV:=${PROJECT_ROOT}/miniconda3/envs/phylo}"
: "${GTOTREE_HOME:=${PROJECT_ROOT}/Tools/GToTree-1.8.19}"
: "${GTOTREE_GTDB_DIR:=${PROJECT_ROOT}/gtotree_gtdb}"
: "${GTOTREE_HMM_SETS:=${PHYLO_ENV}/share/gtotree/hmm_sets}"
export PROJECT_ROOT

# phylo_preflight.py and phylo_postflight.py may need a governed external-data root that is
# different from this portable code tree. Preserve and export an operator override. Otherwise,
# bind only a root that actually contains the canonical strain table: the launch directory first
# (the normal run-from-workspace case), then PROJECT_ROOT. Do not invent a non-resolving default,
# because an invalid exported value would suppress the Python tools' safe local fallbacks.
if [ -n "${MAMEY_DATA_ROOT:-}" ]; then
    export MAMEY_DATA_ROOT
else
    _gte_ssot_rel="strain_data/_ANTISMASH_CANONICAL/STRAIN_METADATA_CONSOLIDATED.tsv"
    _gte_launch_root="$(pwd -P)"
    if [ -f "${_gte_launch_root}/${_gte_ssot_rel}" ]; then
        export MAMEY_DATA_ROOT="${_gte_launch_root}"
    elif [ -f "${PROJECT_ROOT}/${_gte_ssot_rel}" ]; then
        export MAMEY_DATA_ROOT="${PROJECT_ROOT}"
    fi
    unset _gte_ssot_rel _gte_launch_root
fi

# --- PATH: 1.8.19 first (the version we want), conda env second (the deps live there) -----
if [ -x "${GTOTREE_HOME}/bin/GToTree" ]; then
    export PATH="${GTOTREE_HOME}/bin:${PHYLO_ENV}/bin:${PATH}"
else
    export PATH="${PHYLO_ENV}/bin:${PATH}"
fi

# --- the relocated-env `file` bug (failure 3 above) ---------------------------------------
if [ -f "${PHYLO_ENV}/share/misc/magic.mgc" ]; then
    export MAGIC="${PHYLO_ENV}/share/misc/magic.mgc"
fi

# --- data locations: both v1 and v2 spellings ---------------------------------------------
# 1.8.19 ships no HMM sets, so the conda env's directory serves both versions.
export GToTree_HMM_dir="${GTOTREE_HMM_SETS}/"                       # same name in v1 and v2

_gte_ncbi="${PHYLO_ENV}/share/gtotree/ncbi_assembly_summaries"
if [ -d "$_gte_ncbi" ]; then
    export NCBI_assembly_data_dir="${_gte_ncbi}/"                   # v1 spelling
    export NCBI_ASSEMBLY_DATA_DIR="${_gte_ncbi}/"                   # v2 spelling
fi
if [ -d "${GTOTREE_GTDB_DIR}" ]; then
    export GTDB_dir="${GTOTREE_GTDB_DIR}/"                          # v1 spelling
    export GTDB_DIR="${GTOTREE_GTDB_DIR}/"                          # v2 spelling
fi
[ -f "${PHYLO_ENV}/share/gtotree/ncbi_tax_info/nodes.dmp" ] && \
    export TAXONKIT_DB="${PHYLO_ENV}/share/gtotree/ncbi_tax_info/"  # v1 only; dropped in v2
[ -d "${PHYLO_ENV}/share/gtotree/kofamscan_data" ] && \
    export KO_data_dir="${PHYLO_ENV}/share/gtotree/kofamscan_data/" # same name in v1 and v2
[ -d "${PHYLO_ENV}/share/gtotree/gtdb_tax_info" ] && \
    export GTDB_tax_info_dir="${PHYLO_ENV}/share/gtotree/gtdb_tax_info/"
# v2 only. Created on demand rather than probed: v2 exits if it is unset, and an empty
# directory is the correct starting state for a cache it populates itself.
: "${Pfam_data_dir:=${PROJECT_ROOT}/gtotree_pfam/}"
export Pfam_data_dir
unset _gte_src _gte_dir _gte_ncbi

gtotree_preflight() {
    local missing=0 t
    for t in GToTree muscle prodigal hmmsearch iqtree; do
        command -v "$t" >/dev/null 2>&1 || { echo "  MISSING: $t (not on PATH)" >&2; missing=1; }
    done
    if [ ! -f "${GToTree_HMM_dir}/Actinobacteria.hmm" ]; then
        echo "  MISSING: Actinobacteria.hmm not in ${GToTree_HMM_dir}" >&2; missing=1
    fi
    local ver; ver="$(GToTree -v 2>&1 | head -1 | tr -d '\r')"
    case "$ver" in
        *v2.*)
            # v2 has no 138-gene Actinobacteria set: its 46 prepackaged sets are GTDB r232
            # derived, and the nearest equivalent is Actinomycetota (92 genes). Passing the
            # 138-gene FILE path keeps a v2 run comparable with every earlier project tree.
            echo "  NOTE: ${ver} — pass -H \"\$GToTree_HMM_dir/Actinobacteria.hmm\" (the FILE)," >&2
            echo "        not -H Actinobacteria. v2's own sets are GTDB r232; Actinomycetota" >&2
            echo "        is 92 genes and is NOT the project's 138-gene set." >&2 ;;
        *1.8.19*|*1.8.2*|*1.9*) : ;;
        *) echo "  WARNING: ${ver} — project convention is GToTree >= 1.8.19; set GTOTREE_HOME" >&2 ;;
    esac
    if [ "$missing" -eq 0 ]; then
        echo "  gtotree_preflight OK — ${ver}; deps from ${PHYLO_ENV}; HMM dir ${GToTree_HMM_dir}"
        return 0
    fi
    return 1
}
