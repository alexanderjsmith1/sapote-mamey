# Mode B batches: progress and completion

A **Mode B card** is the write-up of one biosynthetic gene cluster (see the [glossary](../GLOSSARY.md)). This page covers doing many cards in a row: the commands, the progress counters, and how to tell that the work is done. To write one card, start with the [Mode B walkthrough](../MODE_B_USER_WALKTHROUGH.md). The profiles (`full48`, `current50_v2`) are in the [profile matrix](../MODEB_PROFILE_MATRIX.md).

## Commands for each batch

Work on a copy of the package. Pick a batch size that suits you. The size is a scheduling choice and is not an evidence count. For each cluster in the batch, use file names that carry its BGC ID, so one cluster's files never land on another's:

```bash
python mamey_run.py emit-modeb-template --package PKG --bgc BGC_ID --out BGC_ID-template.md
# write the card in a new file, BGC_ID-card.md, keeping the section titles
python mamey_run.py verify-modeb BGC_ID-card.md --package PKG --bgc BGC_ID
python mamey_run.py ingest-receipts --package PKG --card BGC_ID-card.md
```

If you use `current50_v2`, add `--contract current50_v2` to all three commands: `emit-modeb-template`, `verify-modeb` and `ingest-receipts`.

`emit-modeb-template --out` refuses a path that already exists and leaves that file as it was. `--batch` is different: it writes `<package>/mode_b_templates/` and its `_INDEX.md`, and replaces files of the same name there. Move any edits out of that folder before you emit again.

`emit-modeb-template --batch --scope pending` picks the clusters the register lists with a status other than `COMPLETE`. A cluster missing from the register is not picked. If there is no register, or it cannot be read, it falls back to every row of the triage board. The command prints how many templates it emitted and lists any it skipped; compare that with the clusters you expected.

`verify-modeb` checks the card against the profile. Read every ERROR and WARN it prints. `ingest-receipts --card` records one card in the package register. `ingest-receipts --auto-detect` scans `<package>/judgment/` for `*_mode_b.md` files and records only cards that pass its checks. It skips a card whose cluster is not in the register, is already `COMPLETE`, cannot be read, has no content, names a different strain, contig or region, or fails the structure gate, and it prints each skip. Read those lines; a scan does not record every file it finds.

Keep the full identity with each card: **strain / full node-or-contig / region / BGC alias**. Triage rank only sets the order you work in.

## What the progress counters mean

The register is the file `<strain>_judgment_register.json` at the package root, with a `.last-good` backup beside it. Cards and reader notes sit under `judgment/`; the register does not. It holds one row per cluster, with a `status` and a cached `quality_tier` from an older check (`FULL`, `SHALLOW`, `STUB` or `UNKNOWN`).

- A saved card gets `status=COMPLETE` even when its tier is `SHALLOW` or `UNKNOWN`. So `completion_pct` counts saved cards, not verified ones.
- `verify-modeb` is the check that counts. A register row does not record the card's hash, so if you edit a card, run `verify-modeb` again.
- Before you compile a strain delivery, list the clusters you expected and confirm each has a saved card that passed `verify-modeb`. Keep a short ledger of that. The register will not do it for you.

## For scripts

Scripts can call `mamey.judgment_store` directly. See [persisting a card](MODE_B_WRITE.md).

- `batch_status` reports the register's cached state. It adds any registered aliases outside the order you pass in, so its denominator is not a checked roster.
- `record_batch_complete` marks aliases COMPLETE without any card text. Avoid it for real work.
- `compile_ready(package_dir, ranked_bgc_ids)` returns a tuple `(ok, reason)`. Test `ok`; a tuple is always truthy. It reads cached tiers and blocks on a corrupt register. It does not open the cards.

## The older character floors

The older check in `mamey/mode_b_quality_gate.py` wants at least 12,000 characters for ranks 1 to 10, 11,000 for ranks 11 to 25 and 10,000 for the rest. A card under 2,000 characters is a `STUB`. An edge or full-contig cluster with 22 or fewer CDS can use a 2,500 floor. These numbers are a sanity check. Do not pad text to meet them, and do not use them in place of `verify-modeb`.

## If a batch breaks

- Keep the card files, the register and its `.last-good` backup.
- A write of a card, its notes and the register is not one transaction. Repeating a write can add the same reader note twice, so check those files.
- If the register is corrupt, copy it aside and ask before you rebuild it. Do not guess the roster.
- Resume from your ledger, then run `verify-modeb` on the saved cards.
