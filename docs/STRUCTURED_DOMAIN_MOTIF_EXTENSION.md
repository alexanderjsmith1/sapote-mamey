# Structured-domain/motif sidecar: source and receipt boundary

This Markdown companion explains the unchanged `STRUCTURED_DOMAIN_MOTIF_EXTENSION.html` candidate. It indexes pinned saved Mamey exports, not original antiSMASH JSON or new scientific analysis. Raw row hashes prove byte binding only; full source/locus/gene/protein binding does not validate biochemical function, product, activity, novelty or scientific acceptance.

`mamey/structured_domain_motif_extension.py:19–44,55–130` checks export hash/schema/table counts and consumed-file checksums. Missing input or checksum conflict is held; a file not listed in package checksums can be hash-captured rather than a full package-checksum pass. Source archive/manifest/geometry/roster/protein holds stay typed. Empty exported tables are `EXPORTED_EMPTY_NOT_BIOLOGICAL_ABSENCE`. Unsupported motifs/predictions stay sidecar-only; do not promote them into compatible domain evidence just because they are indexed.

## Publication and resume

CLI requires inventory pin, source root, base pin, output, allowed root and receipt. Inventory paths and package names are validated through the shared source owner. Output DB containment is checked before opening; an existing DB requires `--resume`. Base bytes are checked before and after build. Resume binds base hash and normalized inventory content, rechecks completed partition files/verified archives, and can return `RESUME_COMPLETE_OUTPUT_UNCHANGED` (`:135–194,270–297`). This does not independently certify the sidecar code/runtime or a historical scientific decision.

Bounds are128 inventory packages,64MiB per export/sidecar and100,000 observations per package. The900-second timer is checked **between partitions**, not a hard timeout within one package. Commits occur per package; budget/parse/output failure can retain a partial DB with committed partitions. Final integrity/foreign-key checks are assertions, not a complete scientific validator. Preserve partial output and the original input inventory; use governed resume with unchanged pins rather than deleting evidence to bypass a hold.

The receipt root is checked **after DB build**, and the receipt is directly written afterward. A bad receipt path/write failure can leave a built DB without a published receipt. JSON progress lines may appear before a final refusal; process exit2 is `REFUSED_OR_CHECKPOINT_REQUIRED`, not empty-output assurance. DB and receipt are not one transaction. The returned DB hash/size is useful but the receipt lacks its own hash and full code/parameter pin. Record actual process status, DB, receipt, source inventory, code and parameter hashes separately; do not treat “all saved packages” as the whole project's scientifically accepted cohort.

## Reader and full-identity constraints

The inspection callback needs both already-open, caller-pinned native SQLite connections in read-only transactions. It rechecks file hashes, exact50 section number/profile hash/requirement parity, limits1–500 and bounded result size (`:196–267`). It provides no generic CLI dispatch: parent shared-reader integration is separate. Raw rows additionally need an explicit package root and verified export/raw-row hashes.

A gene-first evidence index requires a complete locus and compatible domain observations with gene hash/hold checks. Preserve strain / full node-or-contig / region / BGC alias. Pagination is over source rows, not guaranteed genes or a complete locus inventory. `READ_ONLY_CANDIDATE_INSPECTION` explicitly records scientific admission `NOT_PERFORMED`. Section parity does not validate a current50 authored card or approve any scientific claim. Record sidecar builds, callback execution, dataset changes and rendering as separate actions with their own receipts.
