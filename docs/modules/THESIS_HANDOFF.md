# Compact Thesis Handoff

`tools/build_thesis_handoff.py` packages selected deep reports, locus maps, report receipts, and optional activity decision trees under portable relative paths. It emits an index, a gap and claim-ceiling ledger, checksums, a deterministic ZIP, and a receipt after CRC validation.

The index must provide the complete exact identity for every locus. Receipt identity must match all four components. Missing artifacts, absolute paths, traversal outside the configured input root, duplicate loci, missing gaps, and missing claim ceilings fail before the output directory is created.

```bash
python tools/build_thesis_handoff.py --index-tsv handoff.tsv \
  --input-root project_outputs --output-dir thesis_handoff
```

The handoff is evidence packaging only. It does not imply integration, release, product identity, expression, activity, or owner acceptance.

The builder compares the receipt's four-part identity with the index row, but does not compare selected report/map bytes with the receipt's output hashes or validate an optional activity tree's identity. Verify those bindings independently before packaging. The new checksums and ZIP CRC bind copied bytes; they do not establish that the selected artifacts were the receipt-approved generation.

`SHA256SUMS.txt` covers the copied artifacts and the generated index and gap files; it does not hash itself. `HANDOFF_RECEIPT.json` is written after the ZIP, outside it, and records the index input and the ZIP hash.

Use a fresh output root; an existing directory is refused. After initial admission, basename collisions, copy failures or later writes can leave a partial directory. Publication is sequential, with the final handoff receipt written after the ZIP CRC check. Preserve interrupted candidates and choose a new destination after resolving the failure.
