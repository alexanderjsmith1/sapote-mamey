# Compact Thesis Handoff

`tools/build_thesis_handoff.py` packages selected deep reports, locus maps, report receipts, and optional activity decision trees under portable relative paths. It emits an index, a gap and claim-ceiling ledger, checksums, a deterministic ZIP, and a receipt after CRC validation.

The index must provide the complete exact identity for every locus. Receipt identity must match all four components. Missing artifacts, absolute paths, traversal outside the configured input root, duplicate loci, missing gaps, and missing claim ceilings fail before the output directory is created.

```bash
python tools/build_thesis_handoff.py --index-tsv handoff.tsv \
  --input-root project_outputs --output-dir thesis_handoff
```

The handoff is evidence packaging only. It does not imply integration, release, product identity, expression, activity, or owner acceptance.
