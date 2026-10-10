# Current optional scanner data provisioning

This CODE bundle retains selector/provenance records rather than a bundled scanner HMM. Exact reconstruction of the historical 35-model artifact remains held for missing unambiguous source-release/archive hash evidence. The current source-bound builder can produce a separately receipted new-source artifact; it does not prove the old model bytes or scanner results were recovered. Read [the scanner manifest boundary](reference/SCANNER_PFAM_MANIFEST.md) and [external asset guide](EXTERNAL_ASSETS_GUIDE.md) first.

The original download/grep recipe below is retained as historical evidence, **not the current provisioning recipe**. It fetches a mutable current_release source, indexes it, derives selectors from Markdown prose and directly overwrites an output beneath the bundle. Use the dedicated reviewed selector file/preset and fresh external output paths instead. Do not automatically download/index/press data or create Wheelhouse directories while reading a guide.

## Current producer and prerequisites

For an authorized new-source build, bind the operator-provided Pfam-A HMM path/hash and release receipt, the exact 35/148 selector list path/hash, separately provisioned HMMER `hmmfetch`/`hmmpress` identity, and a reviewed new destination outside accepted source evidence. From the bundle root, use this optional command template only within the selected build scope:

```bash
python3 tools/build_scanner_hmm.py --source /ABSOLUTE/PATH/TO/Pfam-A.hmm --preset 35 --out /ABSOLUTE/PATH/TO/new-scanner.hmm
```

Preset 148 is a different selector set. The builder refuses existing model/index/receipt targets, validates one exact fetched versioned accession per selector, requires all four press indices, checks unchanged source/list hashes and emits `COMPLETE_NEW_SOURCE_BUILD` plus output hashes. It reads operator source and selector files, not the historical source_pins JSON. Nonreplacing hardlinks publish outputs sequentially with rollback of its own published paths on caught publication error; interrupted publication still needs inspection. Source: `tools/build_scanner_hmm.py:31–92`. Do not loosen selector versions or substitute a current-release model merely to make a fetch succeed; incompatible source/selector combinations remain held until a reviewed new binding is defined.

## Distinct evidence channels

antiSMASH fullhmmer annotations and a separately generated scanner/domtblout result have different source/model/query/coordinate/threshold provenance. They are not automatically equivalent to the historical 35-model subset, and cannot silently fill pending HMMER workbook cells. The main extraction CLI has no general domtblout import; `mamey/cell_provenance.py:117–147` emits NEEDS_HMMER_DOMTBLOUT placeholders. Use [HMMER integration limits](troubleshooting/HMMER_DATA_WORKFLOW.md) and the owning consumer's exact contract, keeping unrun/missing/unbound states explicit.

Model-data license terms, HMMER software license, selector-file provenance and any service access conditions are separate records. An old data-license label or large-file omission is not proof of current acquisition/redistribution permission. Keep exact upstream release/license and applicable source receipt with the supplied model; no legal or biological acceptance is implied by builder completion. No data download, HMM indexing/build/search, install or fixture run was performed here.

## Historical provenance and old recipe — preserved below

# Public-release data — provenance and optional HMM rebuild

The public release does **not** bundle the Pfam HMM (`Wheelhouse/hmm/scanner_pfam.hmm`); acquire it per `docs/EXTERNAL_ASSETS_GUIDE.md`. Pfam is
CC0, but it is **not bundled** here — you provision it yourself (see `docs/EXTERNAL_ASSETS_GUIDE.md`). This document is
kept only as **provenance** and a **rebuild recipe**: you do not need to fetch anything. Rebuild the
HMM from a newer Pfam-A only if you want to; the engine also runs without it (regex fallback).

## `Wheelhouse/hmm/scanner_pfam.hmm` (~4 MB) — curated Pfam HMM set

This is the 35 Pfam families the v0.3 scanner registry gates on, extracted from Pfam-A with each
family's curated gathering cutoff. The family list, the versioned accessions and the reference SHA-256 are in
`docs/reference/SCANNER_PFAM_MANIFEST.md`. That file was restored from v9.7.338, because the `Wheelhouse/hmm/` folder
that held it is no longer shipped.

**Exact reconstruction is held.** The restored manifest preserves versioned accessions and
an output hash, but its historical “v3.3” source description supplies neither an unambiguous
Pfam release archive locator nor a source-archive SHA-256. Those missing receipts must be
recovered and independently checked before claiming an exact rebuild. Do not infer the
source release from family versions or substitute `current_release`.

The following is an optional **new-source build**, not an exact-reconstruction recipe
(requires HMMER's `hmmfetch` / `hmmpress`):

```bash
# 1. Fetch a new Pfam-A source and index it. Record its resolved release and archive hash.
#    This mutable current_release URL does not reproduce the historical artifact.
mkdir -p Wheelhouse/hmm
curl -O https://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.hmm.gz
gunzip Pfam-A.hmm.gz
hmmfetch --index Pfam-A.hmm

# 2. Pull the 35 accessions listed in SCANNER_PFAM_MANIFEST.md into scanner_pfam.hmm
#    (accession list, one per line, e.g. PF00155.28 PF00202.28 ... PF04738.19)
grep -oE 'PF[0-9]{5}\.[0-9]+' docs/reference/SCANNER_PFAM_MANIFEST.md \
  | while read acc; do hmmfetch Pfam-A.hmm "$acc"; done > Wheelhouse/hmm/scanner_pfam.hmm

# 3. Press for pyhmmer/hmmscan and verify
hmmpress Wheelhouse/hmm/scanner_pfam.hmm
sha256sum Wheelhouse/hmm/scanner_pfam.hmm   # record as a new artifact; do not expect the old hash
```

A rebuild from `current_release` is a **new version**, not a copy. Its accessions can change version, `hmmfetch`
may not find the pinned accessions, and its hash will differ from the manifest. Record the new source release,
the accession list actually fetched and the new SHA-256 as a new receipt, then review compatibility. Do not
compare it to the old hash as if it were the same artifact.

If you already run antiSMASH with `--fullhmmer`, its genome-wide Pfam output is an equivalent evidence
source and you can skip building this file (see `docs/troubleshooting/HMMER_DATA_WORKFLOW.md`).

## Provenance and rebuild rationale

The HMM is static reference data (Pfam models plus curated gathering cutoffs), not source. It is NOT bundled; it belongs in
operator-provisioned because it is large; it is not bundled here (see `docs/EXTERNAL_ASSETS_GUIDE.md`). The recipe above
supports a separately versioned build from a newer Pfam-A source, with a new receipt and output hash.
The old manifest hash identifies the historical subset only; exact recovery remains held until the
missing source receipt is recovered. The teicoplanin MIBiG fixtures that
an earlier release stripped were retired in v9.7.270 in favour of the small public Micromonospora humida
fixture (`tests/fixtures/micromonospora_humida_JAFEUC01.zip`), which also ships in every tier — so there
is nothing to download to complete a checkout.
