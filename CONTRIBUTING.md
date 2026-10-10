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

Work from the actual source root in an isolated virtual environment using Python 3.12 or newer.
Use [INSTALL](docs/INSTALL.md) for optional dependencies and compatible offline wheels.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[all]'
python -m pytest -m public
# Include all configured partitions only within the authorized test/network scope:
python -m pytest tests/ -q --run-slow --run-network
```

`python -m pytest tests/ -q` alone is the default partition: explicitly marked slow/network tests
are skipped by `tests/conftest.py`. Even the configured full partition may skip unavailable external
fixtures/tools; report counts, markers, input hashes and remaining skips rather than claiming live
integration. The conftest deliberately binds test cohort fixtures and overrides MAMEY_OFFICIAL_DATA /
MAMEY_DATA_ROOT for the suite; these tests do not validate the operator’s real registry.

`bash bootstrap.sh` installs pytest and tries editable `.[all]`, then falls back to core if that
fails. It uses PyPI by default; `--wheels <compatible-local-dir>` selects offline resolution. It
prints external-tool installation advice but does not install those binaries. Its one version-sync
smoke test is not the full suite or proof that all extras were installed. Run it from the source
root, select the intended interpreter/venv, and inspect actual installed capabilities.

Keep declared version anchors synchronized through `tools/sync_version.py`; its mutation mode
rewrites selected anchors/generated blocks. `--check` is not a full semantic or release audit.
Do not bump versions or regenerate acceptance evidence merely to prepare a documentation patch.
Behavior changes need meaningful regression coverage; reversible prose/link edits need source and
link verification rather than implementation-mirroring tests.

Reference existing source/fixture evidence in place by path and SHA-256. Stage only changed files;
do not duplicate databases, complete bundles, reports or render assets. Maintain one candidate and
its authoritative index; keep unique evidence and rebuild scripts separate from temporary output.
See [release record scopes](docs/RELEASE_RECORDS_GUIDE.md) before interpreting historical PASS rows.

## Pull requests
Keep changes small and attributable. Describe the problem, the fix, and the tests. A maintainer
reviews and merges; releases are cut and signed off separately.
