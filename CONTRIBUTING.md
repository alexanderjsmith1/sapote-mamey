# Contributing

Thanks for your interest in Sapote-Mamey.

## Ground rules
- **Claim-safety is non-negotiable.** Outputs are class-level hypotheses with judgment deferred;
  never introduce structure/bioactivity claims beyond the evidence, and preserve the mandatory
  claim-safety language in any emitted text.
- **No third-party data or tools in the repo.** External assets (Pfam, BLAST DBs, MIBiG, GTDB,
  genomes) are acquired by the operator under their own licenses — see
  `docs/EXTERNAL_ASSETS_GUIDE.md`. Do not commit databases, HMMs, genomes, or cohort-private data.
- **Generic, portable code.** No personal paths or private cohort identifiers in shipped code or
  docs. Resolve roots from environment variables / configuration, never a hard-coded home.

## Development
- Install editable: `pip install -e '.[all]'` (or `bash bootstrap.sh`).
- Run the public suite: `pytest -m public`. Run the full suite: `pytest tests/ -q`.
- Keep version streams in sync with `tools/sync_version.py`; version-drift tests must stay green.
- New behavior needs a test; scan/scorer changes usually need a paired gate/guard test.

## Pull requests
Keep changes small and attributable. Describe the problem, the fix, and the tests. A maintainer
reviews and merges; releases are cut and signed off separately.
