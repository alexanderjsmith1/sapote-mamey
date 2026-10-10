# GitHub Hygiene Checklist

Use this checklist before an explicitly authorized public push. Completing checklist items does not authorize a push, versioned cut or release. Review the actual [release manifest](../RELEASE_MANIFEST.md) and [privacy-tier controls](CUSTOM_PRIVACY_TIERS.md) before any public action.

- [ ] Repository name and README use **Sapote-Mamey Bundle**.
- [ ] Mamey described as the executable BGC-analysis module inside Sapote.
- [ ] No real strain FASTA, antiSMASH ZIPs, generated reports, workbooks, or private outputs are committed.
- [ ] `.gitignore` excludes run outputs, large biological data, and archives.
- [ ] `LICENSE`, `LICENSE-DOCS.txt`, and `CITATION.cff` are reviewed for final public metadata.
- [ ] Package profiles are documented in `docs/PACKAGE_PROFILES.md`.
- [ ] BGC crosswalk outputs are present in package manifests/workbooks/CSVs.
- [ ] FLR/VLR literature mode definitions are documented.
- [ ] HMMER/DIAMOND/manual BLASTP missingness is explicit, not silently blank.
- [ ] Tests pass from a clean checkout.

## What these checks establish

`.gitignore` does not remove already tracked files and is not a disclosure audit.

### License-grant presence checker

Request `tools/check_license_docs.py` for the supported path declarations in the adjacent bundle's `LICENSE-DOCS.txt`:

```bash
python tools/check_license_docs.py
```

The tool uses the root containing its own script, rather than the working directory, and has no parsed input-root, report-output or alternate-license option. It reads the grant file without rewriting it. A missing grant file returns 2; recognized declarations with missing targets return 1; no recorded missing target returns 0 and prints PASS. Read/decode and unexpected traversal errors can instead interrupt the command before that summary (`tools/check_license_docs.py:16–17,30–66`).

Recognition is line-based: comment lines are removed, then an entire stripped line must match a literal dotted filename or a simple `directory/*.extension` pattern using the limited ASCII path characters in the regex. Other lines are silently ignored, including backtick-wrapped paths, recursive `**` globs, `?` patterns and filenames with spaces. A grant file with no recognized declarations can print PASS with zero grants. Compare the intended declaration list with the reported recognized count and independently account for unsupported syntax; do not change authored grant wording merely to clear this checker (`:26–49`).

Literal targets must satisfy `is_file`; each directory-glob declaration only needs one immediate matching entry, without requiring that entry to be a regular file. A directory named `example.md` can satisfy `*.md`, and one match does not prove an intended complete population shipped. The accepted path grammar also admits parent components, while file predicates follow symlinks; target presence alone does not establish a contained shipped bundle member. Bind the exact intended regular files, resolved locations and source hashes separately (`:51–58`).

This helper does not read the README optional-tool license table, external-tool inventory, executable/database notices or upstream license text. Its PASS therefore supplies no evidence that those entries are current, complete or compatible with redistribution. Preserve their version-specific source notices and review them through their actual owners. No license metadata or upstream declaration should be rewritten as a consequence of this presence check alone.

There is no persisted roster/hash receipt. Save the actual script/root identity, grant-file hash, recognized/skipped declarations, diagnostics and exit status in a fresh disjoint receipt. Treat a missing/error/interrupted run as incomplete, even if an older saved PASS exists.

### Dependency-name synchronization

Dependency-name sync (`tools/check_requirements_pyproject_sync.py:28–52`) verifies core package names are active in `requirements.txt`, not matching bounds, optional extras or the installed environment. `requirements.txt` includes figure dependencies beyond the core; it is not an exact minimal-core lockfile.

Keep the actual `tools/release_denylist.txt` private and follow [its current consumer contract](CUSTOM_PRIVACY_TIERS.md). The supplied commented example is not an active term list: the cut script skips blank lines but does not skip comments. Content scrub and filename matching differ; this is not a general binary/asset de-identification guarantee. `tools/test_synthetic_ids.txt` is a sanctioned mixed test-token allowlist with historical comments; listed tokens are not proof of synthetic origin or permission to disclose real data. Current source-disclosure policy owns admission (`tools/public_release_audit.py:455–478`; `tools/make_public_tier.sh:276–288,368–398`).

A passing selected test set does not establish full-suite coverage, runtime scientific results or release acceptance. Preserve skipped/failed states and exact source revision. `tests/fixtures/figure_page_text_known_sites.txt` is a shrinking known-exception backlog for tested matplotlib save sites, not a list of cleared figure wording; its ratchet excludes hand-written SVG, R and tests that did not run (`tests/figure_page_text_ratchet.py:1–19,28–57,83–100`).
