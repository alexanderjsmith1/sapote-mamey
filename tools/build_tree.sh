#!/usr/bin/env bash
# build_tree.sh — the ONLY sanctioned way to build a phylogenomic tree in this project.
#
# WHY THIS EXISTS
# ---------------
# phylo_preflight.py was written on 2026-08-26 to stop exactly the composition errors that
# had been reaching rendered figures. Within hours of writing it, the same operator (me)
# shipped two more bad figures: once by running the gate and then changing the inputs, and
# once by never running it at all on a 72-genome set where it would have reported 6 FAILs
# in under a second -- including 24 byte-identical duplicate genomes.
#
# The lesson is not "remember to run the gate". A gate you invoke by hand is not a gate; it
# is a suggestion, and suggestions lose to time pressure every time. So the gate lives HERE,
# between the operator and GToTree, on the FINAL staged directory, immediately before the
# CPU is spent. There is no argument to skip it.
#
# USAGE
#   tools/build_tree.sh <tree_dir> [extra GToTree args...]
#
#   <tree_dir> must contain:
#       genomes/         the final staged genomes, exactly as they will be used
#       TREE_SPEC.json   what this tree IS -- scope, taxon, cohort, outgroup, title
#
# The spec is mandatory because the second root cause is that a tree's identity used to live
# only in its folder name and in the operator's head. Nothing could compare contents against
# intent, which is how a tree named 'bee_*' came to hold an attine strain and a moss strain.

set -euo pipefail

TREE_DIR="${1:?usage: build_tree.sh <tree_dir> [gtotree args...]}"
shift || true

HERE="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${PROJECT_ROOT:=$(cd -P "${HERE}/.." && pwd)}"
PY="${PROJECT_ROOT}/miniconda3/envs/phylo/bin/python"

GENOMES="${TREE_DIR}/genomes"
SPEC="${TREE_DIR}/TREE_SPEC.json"

[ -d "$GENOMES" ] || { echo "  no genomes/ directory in ${TREE_DIR}" >&2; exit 2; }
if [ ! -f "$SPEC" ]; then
    cat >&2 <<EOF

  No TREE_SPEC.json in ${TREE_DIR}

  Every tree must declare what it contains before it can be built. Create it:

    {
      "title":  "Bee/wasp-associated Pseudonocardiaceae",
      "scope":  "family",
      "taxon":  "Pseudonocardiaceae",
      "cohort": "hymenoptera",
      "outgroup": "OUTGROUP",
      "min_comparators_per_genus": 1
    }

  cohort is one of: hymenoptera | attine | substrate  (governing rule: separate trees)

EOF
    exit 2
fi

# Environment FIRST, then the gate. Preflight's E1/E1b check whether GToTree and its
# dependencies are actually reachable, so gating before sourcing the launcher reports two
# guaranteed FAILs and refuses every build -- a gate that always says no teaches you to
# disable it, which is the same disease as a gate that cries wolf.
source "${HERE}/gtotree_env.sh"

echo "=== gate: ${TREE_DIR} ==="
if ! "$PY" "${HERE}/phylo_preflight.py" "$GENOMES"; then
    cat >&2 <<EOF

  BUILD REFUSED. The staged genomes do not satisfy this tree's own specification.

  Fix the staged set, or fix TREE_SPEC.json if the specification is what is wrong.
  Do not build around this: every FAIL above corresponds to a figure that was
  published wrong at least once.

EOF
    exit 1
fi

gtotree_preflight || exit 1

cd "$TREE_DIR"
ls genomes/*.fna > genome_list.txt
echo "=== building $(wc -l < genome_list.txt | tr -d ' ') genomes ==="
# BUILD_TREE_JOBS / BUILD_TREE_THREADS: CPU tunables (default 4/4 = prior hardcoded behavior).
# Added after 2026-09-01, when two tree builds in parallel chats shared one machine and "use less
# cpu cores" required editing this sanctioned script (GToTree -j was overridable via "$@", IQ-TREE
# -T was not). Now: BUILD_TREE_JOBS=2 BUILD_TREE_THREADS=2 tools/build_tree.sh <tree_dir>
GToTree -f genome_list.txt -H "${GToTree_HMM_dir}/Actinobacteria.hmm" -N -j "${BUILD_TREE_JOBS:-4}" -o gtotree "$@"

# --- IQ-TREE, in the same script, to completion --------------------------------------------
# WHY THIS IS HERE: running IQ-TREE as a separate hand-typed step invited a foreground timeout
# that killed it MID-BOOTSTRAP and left a valid-looking treefile (right tip count, ends with ;)
# with NO support values -- which then passed postflight P3 only as a WARN and was nearly
# shipped. An 18-taxon tree took 11m52s; a 6m40s tool timeout is not enough. Fold the tree step
# in so the whole build is ONE tracked background task (invoke build_tree.sh with run_in_background)
# and a partial ML tree can never masquerade as a finished one.
ALN="gtotree/Aligned_SCGs.faa"
[ -s "$ALN" ] || { echo "  no alignment produced -- GToTree failed" >&2; exit 1; }
OG="$(grep '^>' "$ALN" | sed 's/^>//' | grep -i OUTGROUP | head -1)"
[ -n "$OG" ] || { echo "  no *_OUTGROUP sequence in the alignment -- cannot root" >&2; exit 1; }
echo "=== IQ-TREE (LG+F+G4, 1000 UFBoot + 1000 SH-aLRT), outgroup ${OG} ==="
iqtree -s "$ALN" -m LG+F+G4 -B 1000 -alrt 1000 -T "${BUILD_TREE_THREADS:-4}" -o "$OG" --prefix iqtree -redo
# A completed run writes both the treefile and the consensus tree; the .contree is the marker
# that the bootstrap actually finished. Refuse to call the build done without it.
if [ ! -s iqtree.contree ]; then
    echo "  IQ-TREE did not finish the bootstrap (no iqtree.contree) -- tree has NO support." >&2
    echo "  Do NOT render or publish iqtree.treefile; re-run to completion." >&2
    exit 1
fi
echo "=== tree complete: iqtree.treefile (with support), iqtree.contree ==="
