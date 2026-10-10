# Source and generated-repository contribution boundary

This file is a repository-extra template. `build_rggmci_package.py` creates a standalone source package from copied/lifted engine source plus templates and writes `src/rggmci/PROVENANCE.json`. `make_repo_candidate.py` then adds repository extras, substitutes version placeholders in citation/changelog templates, copies a small fixture and executes an engine probe to generate expected JSON and an engine-parity test. These are separate producers; the test named below is not present in the template or a plain standalone build (`build_rggmci_package.py:176–193`; `make_repo_candidate.py:90–130`).

Source fixes should be made in their owning bundle/template paths and reviewed with exact provenance. `PROVENANCE.json` hashes selected copied/lifted engine source; it does not hash every template, repository extra, dependency or model/database. A consistent source label/test fixture is not a full release or scientific-validation receipt. The parity test compares one fixture's records and output against engine-produced expectations; scientific independence and broader compatibility remain unverified.

The repository candidate builder refuses a nonempty nongit destination. For a nonempty Git checkout it stages a new candidate, then deletes every target child except `.git` and moves replacement files in (`make_repo_candidate.py:68–88`). This can remove untracked/local evidence and interrupt midway; it is not a read-only sync or automatic contribution step. Preserve accepted evidence in place and use a reviewed fresh candidate when regeneration is authorized. Candidate generation is a separate action; preserve the source checkout and local evidence before a maintainer runs it.

## Retained contribution note — unchanged below

# Contributing

This repository is built from Sapote-Mamey by `build_rggmci_package.py`. The scorer (`core.py`) and the
lifted helpers (`_parsers.py`, `_ids.py`, `_blastp_io.py`) are copies of Sapote-Mamey source. Don't edit them
here: a change made here would be lost on the next build and would make this package disagree with the
engine. Report problems in them as issues; fixes go into Sapote-Mamey and reach this repository on the next
build.

The reader, grouping, BLASTp round trip, command line, tests and docs are package-only and can be changed
here, with a matching change to the templates in Sapote-Mamey.

`tests/test_example_matches_engine.py` pins the package to the engine's own output on the public example, so
any drift fails the tests.
