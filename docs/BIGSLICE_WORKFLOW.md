# Bound BiG-SLiCE companion workflow

**In short.**

- `tools/bigslice_query.py` is optional. It places your antiSMASH regions against one BiG-SLiCE model (`query`), builds a new model from your regions (`cluster`), or reads finished results back (`read`).
- It runs only after you have reviewed and recorded the exact BiG-SLiCE install, model and resources. Until then it refuses, by design.
- It never changes Mamey scores, boards, cards or packages.
- `query` writes into the model folder you name; every run writes its receipts to a new `--out` folder.
- A family or a nearest-centroid distance is relatedness to that model only. It is not compound identity, activity, production or novelty.
- Most readers do not need this page. Read on only if you are setting up or reviewing a BiG-SLiCE run. The rest is the exact input, admission and output contract.

This optional adapter exports evidence relative to one selected clustering model. It does not change Mamey scores, boards, cards, packages or release decisions. Family membership and nearest-centroid distance do not establish compound identity, activity, production or universal novelty. All attempt receipts are PRIVATE. Tool presence is separate from runtime/model admission and scientific acceptance.

## Compatibility and scope

`tools/bigslice_query.py` implements the explicitly reviewed **CLI-reported BiG-SLiCE 2.0.0 / model schema 1.0.1 / query schema 1.0.1** profile. Unknown installed versions or model profiles refuse. This is an adapter compatibility target; a source review or synthetic test does not certify any laptop's installed tool/model. Upstream sources are linked below; pin actual installed source before native execution. Nothing is installed, downloaded or automatically cloned by this adapter.

Historical query commands ignored `--out` and wrote into `--bigfam-model`. New commands require an explicit writable model/run/profile and source-bound identities. `--bigfam-model` is only a deprecated spelling of `--working-model`, with all new gates still required. Old outputs remain historical. Read no longer recursively selects a first DB or guesses strain/contig from filenames; it requires exact DB/report selection and a fresh export root. Cluster refuses occupied outputs and stale staging. There is no automatic resume/retry or model conversion.

Supported input is a selected, nonempty view of contained antiSMASH `*.regionNNN.gbk` files. The current metadata gate requires one record, exact VERSION/full-contig identity, or the narrowly admitted antiSMASH SPAdes coverage-suffix normalization when LOCUS retains the full contig, one simple bounded `region` feature and one matching region-number qualifier. Unsupported/multiple/complex regions are held, not silently discarded. Unknown topology/date/organism metadata are not inferred or changed. The parsed database region length must equal the bound source feature width. Whole-genome GBKs and alias-only input are not accepted by this route. Distinct accession versions and full NODE coverages remain distinct.

## Inputs and provenance

Supply `--identity-tsv` with these exact columns (extra columns are retained in the immutable manifest):

```
relative_path bytes sha256 strain full_contig region bgc_alias
manifest_path manifest_sha256 inventory_row_sha256
source_zip source_zip_sha256 source_member
```

The actual separator is TAB. `relative_path` is a canonical path under `--input`; source ZIP/member bytes must exactly match that file. The native Mamey `manifest_path` must bind the original ZIP via `input_zip_sha256`, carry `strain_id`, and contain exactly one BGC row with the supplied `inventory_row_sha256`. That row supplies contig, producer-normalized node key, region, alias and exact `source_gbk`; the existing typed native identity validator checks their roles. Row hashes use UTF-8 JSON with sorted keys, separators `(',', ':')`, and `ensure_ascii=True`. Hashes bind bytes/provenance, not biological truth or human authorization. No bare alias, filename substring or shortened NODE token repairs a missing identity. Every input GBK must appear exactly once, and every parsed DB BGC must resolve to one selected source record.

Native `query` and `cluster` require a reviewed `--runtime-manifest`:

```json
{
  "schema": "bigslice-runtime-admission:v1",
  "profile": "bigslice-2.0.0-schema-1.0.1",
  "version": "2.0.0",
  "distribution": {"name": "bigslice", "mode": "installed-distribution", "version": "<separately reviewed exact distribution version>"},
  "review_status": "ADMITTED_BY_OPERATOR",
  "source_pin": "immutable upstream commit/distribution provenance",
  "interpreter_path": "/exact/env/bin/python",
  "interpreter_sha256": "64 lowercase hexadecimal characters",
  "executable_sha256": "64 lowercase hexadecimal characters",
  "source_root": "/exact/installed/bigslice/package",
  "source_files": [
    {"relative_path": "bigslice", "sha256": "64 lowercase hexadecimal characters"}
  ]
}
```

The displayed `source_files` row is an abbreviated schema example, not a complete admitted manifest. Include every regular file in the declared package root, including the entry script and data/query/report schemas, BGC parser and membership implementation. Symlinks escaping that root refuse. `--bigslice` names the actual upstream Python entry script; the pinned interpreter invokes it directly, preserving the declared venv invocation rather than guessing ambient PATH/shebang resolution. The executable, interpreter, runtime manifest, package files and HMM tree are hashed before use and checked afterward. The executed entry's content must equal the declared `source_root/bigslice` content; a separately hashed unrelated script is refused. The actual child interpreter/platform/distribution versions are recorded. Native admission also requires the separately declared exact distribution version to match actual interpreter metadata. A reviewed uninstalled source tree uses `{"name":"bigslice","mode":"source-tree","version":null}` and requires no installed BiG-SLiCE distribution. Neither form proves that all third-party dependencies are source-hashed.

The entry is probed with `--help`, whose argparse banner must contain exactly one `[ Version 2.0.0 ]`. `RUNTIME_PROBE.json` records `UPSTREAM_HELP_BANNER`, argv, log/process hashes, CLI-reported version and separate distribution version. Upstream `--version` rewrites argv and reads entry-adjacent default HMM assets, discarding a custom folder; it is deliberately not used. A help banner of 2.0.0 does not establish a distribution version of 2.0.0: a distribution labeled 2.0.2 can contain that banner and remains held until its exact installed source/distribution/profile is independently reviewed and explicitly admitted. Help still imports upstream dependencies; no native platform compatibility is inferred.

`query` and `read` also require `--model-profile`:

```json
{
  "schema": "bigslice-model-profile:v1",
  "profile": "bigslice-2.0.0-schema-1.0.1",
  "model_sha256": "exact result/data.db SHA256",
  "run_id": 3,
  "normalization": "l2",
  "review_status": "ADMITTED_BY_OPERATOR",
  "provenance": "reference scope/date/inclusion, upstream derivation and compatibility evidence"
}
```

These are operator-supplied review records, not permission tokens or self-authenticating proof. Preserve the actual supporting installation/model receipts. Normalization is explicit; `legacy-unnormalized` additionally requires `--allow-legacy-profile` and the exact matching model descriptor. Cluster uses v2 l2 normalization and threshold 0.4 by default. The conservative adapter requires model run status 7, exactly one clustering/HMM binding and a unique GCF roster. This is stricter than upstream's clustering-ready query allowance. The HMM directory is explicit, inventoried and checked against the selected run's library MD5 identifiers. It must have the compatible upstream layout; a historical download label does not prove compatibility.

## Write and resource boundary

`--out` is always a fresh receipt/export root under explicit `--write-root`; an occupied path is refused without changing its contents. Query also writes into `--working-model`, an existing writable result directory under that permitted root. `--allow-model-write` acknowledges this boundary. Use repeated `--read-only-root` for protected research/source roots; this campaign's research workspace remains read-only. Resolve symlinks before admission. Input, output, model, runtime, HMM and source manifests/archives may not alias mutable destinations. Never silently copy a multi-GB model to make it writable.

The working model is cooperatively locked by `.mamey-bigslice-lease`; an occupied lease refuses and is never automatically broken. Query names default to UUID-bearing tokens. Explicit names allow alphanumeric characters, dots and hyphens, and must be new. A failed upstream report row is preserved; retries require a fresh output/query name. Query report/index/cache paths and all allowed writes are recorded before launch. Existing model DB and cached resource bytes must remain unchanged; new cache/report files are recorded. The adapter never unpickles model caches itself; their provenance must be admitted before the external tool consumes them.

Defaults are one thread (allowed 1–4), serial foreground computation, `nice -n 15`, 3.8 GB observed process-tree RSS stop, 1800 seconds per watched child (runtime identity, help probe and native run each have a separate clock; admission/readback have no overall attempt timeout), at least 2 GB free disk, and a 2 GB filesystem-free-space consumption proxy shared across all attempt phases. The existing watcher samples periodically and stops owned processes; it is not a kernel memory sandbox or exact per-job disk quota. Working model, scratch and exports must share the monitored filesystem. Unrelated filesystem changes can affect the disk proxy. Record actual watcher receipts and cleanup errors. These ceilings are not feasibility measurements: unknown model size/platform/resource estimates hold native admission. Child scratch is placed under the new export root, and no detached background fan-out is used.

## Commands after separately authorized admission

Placeholders below are not executable until exact inputs/runtime/model/resource scope are admitted. Use an output outside the bundle and all canonical packages.

```bash
python tools/bigslice_query.py query \
  --input '<selected-region-view>' --identity-tsv '<bound-crosswalk.tsv>' \
  --working-model '<writable-result-root>' --allow-model-write \
  --model-run-id '<exact-run-id>' --model-profile '<reviewed-model.json>' \
  --program-db-folder '<compatible-HMM-root>' \
  --bigslice '<upstream-python-entry-script>' --runtime-manifest '<reviewed-runtime.json>' \
  --write-root '<permitted-root>' --read-only-root '<research-root>' \
  --out '<fresh-export-root>' --threads 1 --n-ranks 5
```

Cluster uses the same input/crosswalk/runtime/HMM/write/resource arguments with `cluster`, omitting model/run/profile/write-acknowledgment arguments. It creates fresh `input_view/cohort` links and datasets metadata plus an initially nonexistent `native_result` directory; upstream never receives an occupied cluster result. Duplicate staged basenames refuse. No isolation or symbiont classification is invented.

Read query results without executing BiG-SLiCE:

```bash
python tools/bigslice_query.py read \
  --input '<same-selected-region-view>' --identity-tsv '<same-bound-crosswalk.tsv>' \
  --model-db '<working-result>/result/data.db' \
  --model-run-id '<exact-run-id>' --model-profile '<reviewed-model.json>' \
  --reports-db '<working-result>/reports/reports.db' \
  --report-id '<exact-report-id>' --query-name '<exact-name>' \
  --query-db '<working-result>/reports/<exact-report-id>/data.db' \
  --query-receipt '<original-query-export>/SELECTED_RESULT.json' \
  --write-root '<permitted-root>' --out '<fresh-read-export>' --n-ranks 5
```

Query read requires the explicit producer `SELECTED_RESULT.json` with COMPLETE PRIVATE query state and exact result/manifest hash closure. Its model path/hash/run/clustering/HMM/profile/normalization, input identity roster, query DB hash and selected report row/link must match. A different model with coincident integer IDs or a replacement at the original model path refuses. Later unrelated index additions are allowed. Legacy/external queries without this producer provenance stay held; no same-ID inference or unsupported external admission shortcut is provided. Receipt hashes establish artifact consistency, not human authorization.

For clustering readback omit query/report/producer-receipt arguments. Use `--cluster-view` only when DB source paths follow the declared `cohort/<filename>` staging grammar. Otherwise exact absolute original input paths are required. An explicit missing path never causes recursive discovery or database creation. SQLite inputs must be quiescent and checkpointed; nonempty WAL/journal sidecars hold. Connections use `mode=ro` and `query_only`; no `immutable=1` bypass is used.

## Completion and result meaning

Fresh attempts record request, immutable plan, state/events and child logs/resource receipts. A preflight failure may have only request/state/events and no admitted plan; this is FAILED. Exceptions/signals preserve non-complete state and diagnostic files. Occupied outputs and failed historical reports are not deleted.

Upstream zero exit is necessary but insufficient: the reviewed launcher can print failure without propagating its return code. Before launch, the full reports tree is inventoried and existing report files are bound; unindexed numeric destinations are refused without deletion. The newly selected report destination must not have existed before launch. Query must create exactly one new declared report, preserve previous report history, bind exactly the requested run, and produce the selected complete query DB. The reader treats model/query schemas separately, resolves GCF IDs through the selected model clustering, validates one source record per parsed BGC and all requested zero-based ranks, and rejects missing/duplicate/orphan/out-of-scope rows. It exports every requested rank and raw membership value, with explicit input/parsed/membership/exclusion denominators. Nothing falls back to a previous success. Fresh cluster output must retain exactly the requested threshold and the reviewed `birch` method. Its newly produced model is bound before membership readback and checked afterward; a post-scope model mutation refuses.

`bigslice_assignment.tsv` displays **strain / full contig / region / BGC alias**, plus source hash, attempt/report/DB identities, rank/value and a method-specific qualified family tuple. The tuple includes immutable model digest, run, clustering, both GCF IDs, profile and normalization. It is distinct from BiG-SCAPE families. `SELECTED_RESULT.json` binds that export and exact selection; `RUN_STATE.json` is COMPLETE only after readback and unchanged-source checks. A nearest hit is not a threshold-qualified membership claim. Family sizes and agreement scores are omitted until their exact statistical/selection contracts are separately implemented.

Optional `--bigscape-tsv` requires existing portable qualified-family fields. A supplied missing file fails. Without `--bigscape-bridge`, comparison is explicitly held while valid BiG-SLiCE export can complete. Bridge TSV columns are `strain`, `full_contig`, `region`, `bgc_alias`, `qualified_family_id`, `member_locator`; the last field must occur in that family's source membership list. Bridge provenance remains operator-supplied. Only coverage/exclusion counts are reported; no numeric equality of method-specific family IDs or unimplemented concordance statistic is claimed.

Synthetic metadata/fake-child tests validate software contracts only. An eventual public type-strain query needs a separately frozen subset/crosswalk and actually admitted tool/HMM/model/resources. Previous Mamey extraction/figure success does not certify BiG-SLiCE parsing or model coverage. No current native result is implied by this workflow.

Primary upstream references: [README](https://github.com/medema-group/bigslice), [executable](https://github.com/medema-group/bigslice/blob/master/bigslice/bigslice), [model schema](https://github.com/medema-group/bigslice/blob/master/bigslice/modules/data/schema.sql), [query schema](https://github.com/medema-group/bigslice/blob/master/bigslice/modules/data/schema_query_mode.sql), [report schema](https://github.com/medema-group/bigslice/blob/master/bigslice/modules/data/schema_reports_index.sql). These floating links are for orientation; runtime admission requires immutable source/distribution provenance.

Crosswalk and optional bridge TSVs are byte-limited before opening and row-limited while iterating, before unbounded list materialization. The separately reused BiG-SCAPE reader is byte-limited at this adapter boundary; this is not a claim of a streaming allocation bound inside that external reader.
