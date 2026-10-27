# GitHub Hygiene Checklist

Use this checklist before an explicitly authorized public push. Completing the list does not approve a push; the owner does. Review the actual [release manifest](../RELEASE_MANIFEST.md) and [privacy-tier controls](CUSTOM_PRIVACY_TIERS.md) before any public action.

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

## Notes on the checks

- `.gitignore` does not remove files already tracked, and it is not a disclosure audit.
- `python tools/check_license_docs.py` checks that every file granted in `LICENSE-DOCS.txt` ships. It reads only whole lines that are a plain filename or a `directory/*.ext` pattern. Other lines (backticks, `**`, spaces) are skipped without warning, so compare the reported grant count with the file. Exit 0 is PASS; 1 means a granted file is missing or no grant was recognized; 2 means `LICENSE-DOCS.txt` is missing. A `dir/*.md` grant passes if any one entry matches. It does not check the README tool-license table or upstream licenses.
- `python tools/check_requirements_pyproject_sync.py` checks that every core dependency name in `pyproject.toml` appears in `requirements.txt`. It does not compare version bounds or extras.
- Keep `tools/release_denylist.txt` private; see [privacy tiers](CUSTOM_PRIVACY_TIERS.md). The cut script skips blank lines and lines that start with `#`.
- `tools/test_synthetic_ids.txt` is an allowlist of test tokens, not proof that a token is synthetic.
- A passing selected test set is not the full suite. `tests/fixtures/figure_page_text_known_sites.txt` lists known figure-text exceptions still to clear; it does not cover SVG, R or tests that did not run.
