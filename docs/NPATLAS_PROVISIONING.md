# Set up NP Atlas references

Use existing reference files or make an actinobacterial subset from the
[NP Atlas download](https://www.npatlas.org/download). You need an installed
bundle and either the ready files or the original dataset and its version.
Check the dataset license before use. Run these examples from the bundle folder.

## Use reference files you already have

Point `MAMEY_NPATLAS_DIR` at your reference directory. Recognized filenames are
`all_actinobacteria_npatlas_ref.json` and `bacteria_nonactino_npatlas_ref.json`.
Replace this example path with that directory:

```bash
export MAMEY_NPATLAS_DIR=../npatlas
python tools/npatlas_provision.py doctor
```

Check that `consumer_ready` is true and `consumer_references` lists the intended
files. The named count uses one entry per lowercased name. `provisioned` reports
a separate check for the original download.

The resolver can also load fallback files; check the contributing paths before
using the reference set. `MAMEY_NPATLAS_DIR` takes precedence over the older
`SM_NPATLAS_DIR` setting.

## Make a subset from the original JSON

Download the JSON, then inspect it before filtering. Replace the source path
and dataset version with yours. Use a fresh output path: existing output files
can be replaced.

```bash
python tools/npatlas_provision.py inspect --source ~/Downloads/NPAtlas_download.json
python tools/npatlas_provision.py provision \
  --source ~/Downloads/NPAtlas_download.json \
  --out ../npatlas-new/all_actinobacteria_npatlas_ref.json \
  --dataset-version v2024_09 --phylum Actinobacteria --phylum Actinomycetota
export MAMEY_NPATLAS_DIR=../npatlas-new
python tools/npatlas_provision.py doctor
```

`--source` selects the download; `--out` chooses the new reference file;
`--dataset-version` records the inspected release. The two `--phylum` values
include either name and also enable schema normalization. No extra normalization
flag is needed.

Read the inspection's record count and keys. Arrays and `compounds` wrappers
are detected automatically; another shape needs `--json-root`. A wrong root
can write an empty subset. On normalized records, a genus filter needs
`--genus-field origin_organism.genus` and the chosen `--genus`.

## Check and keep the result

Provisioning prints source/output hashes, sizes, version, filter and
included/excluded counts. Compare those counts with the intended filter.
Selected records stay in memory, so broad filters need more RAM.

Use `--out-receipt` when you want a saved receipt, creating its parent directory
first. A failed receipt write can leave the subset already written; check both
before retrying. The resolver does not verify this receipt for you.

Keep the source, subset and receipt hashes together. [External data](EXTERNAL_DATA.md)
explains the dataset settings.

## Optional structure drawings

RDKit is needed for structure drawings; provisioning runs without it.
The structure renderer reports `RENDERED` for a specific valid SMILES, `HOLD`
for missing, wildcard or invalid SMILES, and `UNAVAILABLE` when RDKit is absent.
Only `RENDERED` supplies SVG. Use the required caption:

> structure of a related characterized reference, not the predicted BGC product
