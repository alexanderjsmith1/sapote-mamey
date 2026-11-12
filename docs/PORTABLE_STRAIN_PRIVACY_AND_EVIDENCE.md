# Set strain access and track assay records

A privacy profile says which strains are public and which are private. An evidence
registry lists your materials (extracts and fractions) and the assays run on them.
You need your strain names, your access decisions and a source record for each
material or assay.

The two files below are separate. `run` takes the profile. The registry is only
checked and kept for your records.

## Privacy profile

Make new folders for your files and copy the examples into them. Do this once. From
the program folder:

```bash
mkdir privacy evidence && \
cp -n examples/privacy/strain_privacy_profile.example.json privacy/strain_privacy_profile.json && \
cp -n examples/privacy/strain_evidence_registry.example.tsv evidence/strain_evidence_registry.tsv
```

`mkdir` without `-p` stops with `File exists` when either folder is already there, and
the copies then do not run. That protects a profile or registry you have already edited.
`cp -n` also refuses to replace an existing file. If you see `File exists`, keep your
files and skip this step; copy an example to a new name only if you want a fresh start.
The first folder may have been created before `mkdir` encountered the existing second
folder. Inspect both paths before retrying, and use fresh names when needed.

Open `privacy/strain_privacy_profile.json` and replace the example strain names and
tier names with yours. A tier with `"public_export": true` is `PUBLIC`. Every other
tier is `PRIVATE`. The default tier must be non-public, so a strain you do not list
stays private. The registry in the next section uses the same strain and tier names:
each row's `strain_id` and `privacy_tier` must match the profile, or the check fails
with `privacy_tier does not match exact/default profile tier`. A strain the profile does
not list takes the default tier.

Add the profile to your `run` command from the [first run](reader/01_FIRST_RUN.md):

```bash
python mamey_run.py run --strain EXAMPLE --input-zip ~/Downloads/EXAMPLE.zip \
  --privacy-profile privacy/strain_privacy_profile.json
```

The profile decides the release label. The `--strain` value must equal a profile
`strain_id` to take that strain's tier. If you add `--release PUBLIC` to a private tier,
the override is refused. The run prints `[release] PUBLIC override refused by the supplied privacy
authority; tagged PRIVATE.`, records the reason `public_override_refused_by_profile`
in the `release_decision` block of the package's `manifest.json`, and still finishes.
`--release PRIVATE` always wins. The label does not remove anything from the files.

## Evidence registry

Edit `evidence/strain_evidence_registry.tsv`. Replace the example `strain_id` and `privacy_tier` values with the strain and tier names from your profile.

- A material row names an extract or fraction. Set `material_level` to
  `crude_extract`, `flash_fraction` or `hplc_fraction`.
- `parent_material_id` links a material to the one it came from. A fraction needs a
  parent that is not the root.
- An assay row names the panel and target tested on one material. The material must
  belong to the same strain. Set `replicate_state` to what actually happened.
- `RESULTS_BOUND` records your assertion that a result exists at `source_locator`.
  The check does not open the locator, so a missing file or a wrong row still passes.
  Open the source and match it to the row before you rely on it; until then treat the
  result as unverified. The check's JSON says `source_locator_check: NOT_OPENED` and
  counts these rows in `results_bound_record_count`.

Check both files:

```bash
python tools/validate_portfolio_registry.py \
  --privacy-profile privacy/strain_privacy_profile.json \
  --evidence-registry evidence/strain_evidence_registry.tsv
```

With the example files, it prints JSON that ends with `"status": "PASS"` for the
profile and for `evidence`, and exits `0`. A problem prints the failing check and
exits nonzero.

The check covers required fields, unique IDs, allowed state words, parent links,
profile tiers, and material-to-strain agreement. It rejects parent cycles and
parents from another strain. It does not open each `source_locator`, and it does not
check the words used in `replicate_state`. Check both yourself before you rely on a
recorded result.

## A project registry is a different file

`run` also has `--project-registry`, for a `sapote_project_registry_v1` file. `run`
records it in the manifest but it does not set the release label. Giving both
`--project-registry` and `--privacy-profile` stops with `PRIVACY_AUTHORITY_CONFLICT`.
Pick one. To archive a project registry, see the
[project catalog](PROJECT_CATALOG.md).

## Before you publish

The profile sets the package's access label. Publishing still needs the release
checks in the [public release guide](PUBLIC_RELEASE_GUIDE.md) and your own decision.
The registry does not load measurements into a genome run.

The profile and the release guide do not check a workbook for leaked private data. For a public workbook, run the separate [workbook disclosure audit](CUSTOM_PRIVACY_TIERS.md#public-workbook-audit-limits) and review what it does not read, such as formulas, comments and document properties, by hand.
