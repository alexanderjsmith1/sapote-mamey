# SOP-09 — C7 Public Workbook / Redaction Safety

This SOP was reserved as an outline and never written. No single page holds a public-workbook
disclosure review. Use these pages together:

- [Public-workbook audit limits](../CUSTOM_PRIVACY_TIERS.md#public-workbook-audit-limits): what
  `tools/audit_public_cut.py` checks in a workbook, and what it does not read.
- [Public release guide](../PUBLIC_RELEASE_GUIDE.md): what ships with the code release and how
  tiers are derived. It covers the code archive, not workbook cells.
- [Strain privacy profiles](../PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md).

The workbook audit reads cached cell values. Review formulas, sheet names, comments, hyperlinks,
document properties and images yourself. Keep the private source workbook unchanged and work on a
copy. A `CLEAN` audit result or a privacy-profile label is not release approval. This page stays so the SOP number keeps pointing somewhere.
