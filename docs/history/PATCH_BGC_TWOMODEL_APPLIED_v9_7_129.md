# Patch applied — BGC two-model decomposition (v9.7.129)

Applied from PATCH_BGC_TWOMODEL_instructions(1).md.

Changes:
- CREATE mamey/bgc_decomp.py
- CREATE tests/test_bgc_decomp.py
- MODIFY mamey/diagnostic_rescue.py parse_cb blast_score
- MODIFY mamey/cli.py import bgc_decomp
- MODIFY mamey/cli.py triage header Two_Model_Flag
- MODIFY mamey/cli.py decomp placeholder
- MODIFY mamey/cli.py triage row Two_Model_Flag cell
- MODIFY mamey/cli.py write 4B decomp after all-BGC gene table
- MODIFY mamey/__init__.py bundle version 9.7.129
- MODIFY pyproject.toml bundle_version 9.7.129
- MODIFY TAG bundle version/patch note

Implementation note: the two-model CSV and triage-board Two_Model_Flag are populated after the all-BGC gene-by-gene table is written, because the fitter requires per-CDS sec_met_domain rows.
