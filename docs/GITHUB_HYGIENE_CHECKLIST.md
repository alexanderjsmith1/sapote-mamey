# GitHub Hygiene Checklist

Before public push:

- [ ] Repository name and README use **Sapote-Mamey Bundle**.
- [ ] Mamey described as the executable BGC-analysis module inside Sapote.
- [ ] No real strain FASTA, antiSMASH ZIPs, generated reports, workbooks, or private outputs are committed.
- [ ] `.gitignore` excludes run outputs, large biological data, and archives.
- [ ] `LICENSE.txt`, `LICENSE-DOCS.txt`, and `CITATION.cff` are reviewed for final public metadata.
- [ ] Package profiles are documented in `docs/PACKAGE_PROFILES.md`.
- [ ] BGC crosswalk outputs are present in package manifests/workbooks/CSVs.
- [ ] FLR/VLR literature mode definitions are documented.
- [ ] HMMER/DIAMOND/manual BLASTP missingness is explicit, not silently blank.
- [ ] Tests pass from a clean checkout.
