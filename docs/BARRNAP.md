# Barrnap — optional external rRNA workflow

Barrnap is mentioned in the [fungal workflow](PHYLO_FUNGAL_WORKFLOW.md), [fungal wiki](../wiki/Fungal-Phylogenetics.md), [field notes](../wiki/Troubleshooting-Field-Notes.md) and [GToTree guide](GTOTREE_WORKFLOW.md). It is an optional external tool, separate from Mamey's core pip installation.

The shipped `tools/marker_candidate_search.py` prints a Barrnap-based rRNA plan; it does not execute Barrnap or complete sequence extraction. Its plan includes an unquoted supplied assembly path and a follow-on extraction comment: review quoting, selected version and expected output files before using it. `tools/comparator_select.py` has a separate BLASTn-seeded route explicitly described as not requiring Barrnap. Barrnap is therefore not a universal prerequisite for every bacterial or phylogenetic workflow.

## Version and environment check

Use the selected executable's `barrnap --version` and `barrnap --help`, and the [upstream installation instructions](https://github.com/tseemann/barrnap). Record executable/version, environment, database path/version/hash, input hash and selected model in the work order. No install, database download or Barrnap run was performed here.

The upstream executable lists kingdoms `bac`, `arc`, `fun`; older guidance here used `euk`. Match flags and dependencies to the actual installed release; do not paste historical flags into another version. See [upstream executable source](https://github.com/tseemann/barrnap/blob/master/bin/barrnap). This source snapshot is not proof of which version is installed locally.

Choose a fresh working destination and retain source evidence in place. GFF annotations and extracted marker sequences are different artifacts: bind each output to the exact assembly, sequence/coordinates, executable and database. A planned command, missing database or empty/failed output is not an admitted marker or negative biological result. Follow the selected tree workflow's separate reference, alignment and acceptance gates.
