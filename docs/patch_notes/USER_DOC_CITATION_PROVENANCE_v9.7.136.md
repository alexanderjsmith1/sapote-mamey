# User-Doc Citation Provenance Patch — v9.7.136

Adds a compact provenance/status block to current user-facing docs before four-tier release.

The block records:

- antiSMASH 8.0 method/database provenance: DOI `10.1093/nar/gkaf334`;
- MIBiG 4.0 reference-database provenance: DOI `10.1093/nar/gkae1115`;
- `PASS_STRUCTURE` as structural validation, not literature truth verification;
- `operator_supplied` and `citation_needed` meanings;
- `Literature_Search_WorkOrder.md/json` as a search handoff, not a verified fact;
- `interpretation_scope` as the current reader-facing compact scope field, without reintroducing the legacy field name into current user docs.

This patch is documentation-only and does not alter scoring or package runtime behavior.
