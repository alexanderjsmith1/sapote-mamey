# Read release and validation records

This page tells you which file answers which release question. You do not run anything here.

**Which version do I have?** Open the first lines of [RELEASE_MANIFEST](../RELEASE_MANIFEST.md). They give the bundle version, the engine version and the build stamp. The `bundle_version` in [`pyproject.toml`](../pyproject.toml) is the authority if the two ever differ.

**Was it tested?** The manifest records the test counts of the source tree named in its title. Check that the version in that title matches the version you hold. A candidate built by applying patches to an earlier archive can still carry that archive's manifest and test counts, and those counts say nothing about the candidate's bytes. The manifest also does not cover files you edited later. To test your own copy, see [CONTRIBUTING](../CONTRIBUTING.md).

## Where each record lives

| Record | What it tells you | What it does not tell you |
|---|---|---|
| [RELEASE_MANIFEST](../RELEASE_MANIFEST.md) | Version, engine, build stamp, recorded test results | That your edited copy passes, or that a separate seal exists |
| [CHANGELOG](../CHANGELOG.md) | What the maintainers changed, version by version | That every listed version was released |
| [RELEASES_LOG](../RELEASES_LOG.md) | A partial table of logged releases | That an archive was built from a row |
| [CONTRIBUTING](../CONTRIBUTING.md) | How to run the tests and send a change | That the default test run covers every partition |
| [SECURITY](../SECURITY.md) | How to report a security problem | That a private reporting channel is active |
| [Bootstrap file audit](BOOTSTRAP_FILE_AUDIT.md) | Which assistant instruction files exist and what each does | That every assistant finds them on its own |
| [ENGINE_LINEAGE](ENGINE_LINEAGE.md) | History of engine behavior | That new outputs can be pooled with old ones |

A file title, a changelog line or a PASS row in a record does not authorize a release.

## Check an archive you received

1. Open [RELEASE_MANIFEST](../RELEASE_MANIFEST.md). Note the version and the artifact status line.
2. Compute the SHA-256 of the archive file and compare it with the hash in the seal record that came with it. A seal is a separate `SEAL_RECEIPT.json` that holds the archive hash. The manifest is not a seal.
3. If the seal record or the test logs are missing, treat the archive as unchecked. Say so.
4. After you edit any file, the manifest's test results no longer cover it. Keep the original records unchanged. Do not edit a PASS count.

## Generated files

Do not hand-edit generated content. The Bootstrap file audit is generated from `bootstrap_contract.yml`. The test totals in the manifest are written by `tools/gen_release_manifest.py`. Cut mechanics, including its `--fixed-point` mode, are in [CUT_PROTOCOL](../CUT_PROTOCOL.md). `python tools/sync_version.py --check` reports whether the version anchors agree; a missing lineage file gives a warning, not a failure.
