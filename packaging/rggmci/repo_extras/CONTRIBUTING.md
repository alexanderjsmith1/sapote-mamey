# Contributing

This repository is built from the Sapote-Mamey pipeline. Don't edit its files here: the next build replaces them,
and a change made here would make this package disagree with the pipeline. Open an issue instead. Fixes go into
Sapote-Mamey and reach this repository on the next build.

## Where each file comes from

- The scorer (`core.py`) and most modules are copies of Sapote-Mamey source. `groups.py` is
  `mamey/rescue_groups.py` under another name.
- The underscore modules (`_parsers.py`, `_ids.py`, `_blastp_io.py`, `_gene_context.py` and the others) hold
  functions lifted out of larger Sapote-Mamey modules.
- The reader, the command line and the BLASTp round trip are package templates in Sapote-Mamey's
  `packaging/rggmci/templates/`. The CI, citation, changelog and this file are in `packaging/rggmci/repo_extras/`.
- `build_rggmci_package.py` builds the package and writes `src/rggmci/PROVENANCE.json`, with the SHA-256 of
  every engine source file it copied. `make_repo_candidate.py` adds the repository files and the example.

## The pipeline and this package agree

The Sapote-Mamey pipeline runs the same scorer, from the same source. With the same ZIP, strain label and databases,
both should give the same pairs, scores and confidences. The JSON's `wrapper_context` holds only what
differs between the two: file paths, the distribution name, provenance and where the contig sequences were read from.

`tests/test_example_matches_engine.py` checks the scorer itself, below the command line. When the repository is
built, the pipeline reads the bundled example's regions and scores them, and saves both. The test makes the
package's region reader and scorer reproduce them exactly. It doesn't run the `rggmci` command, the optional
databases or any other genome, so a disagreement elsewhere is worth an issue.
