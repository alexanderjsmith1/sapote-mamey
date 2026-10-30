# Catalog and copy a private project

Record where your packages live, check their manifest hashes, and copy the
registered packages into one private archive. You need existing packages under
a project folder and the installed bundle. This example uses one run, `EXAMPLE`.

## Register the package

From the program folder:

```bash
python tools/project_catalog.py register \
  --project-root runs/EXAMPLE --package runs/EXAMPLE/package
python tools/project_catalog.py verify --project-root runs/EXAMPLE
```

Replace the example paths with your project and package. The package must be
inside the chosen project root and have a `manifest.json` containing its strain ID.
Registration writes `project_outputs/project_catalog.json` under that root.
Older projects can keep an existing `lab_quest_outputs/` location.

Verification prints the registered paths and entry count. Expect one entry for
this example. Running it against a new root can create an empty catalog, so check
the count instead of treating exit 0 as a complete inventory. Verification checks
manifest hashes; use the [package validator](reader/03_READ_RESULTS.md) to check
package contents. Registering the same path again replaces its saved manifest hash.

<a id="optional-portfolio-configuration"></a>

## Include a portfolio registry (optional)

An existing portfolio config can add a project registry to the archive. This is
separate from the extraction privacy profile and evidence TSV described in
[portable privacy and evidence](PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md).

To include an existing `config/portfolio.json` and its registry in the archive,
save their binding before exporting. The config path is relative to the project
root:

```bash
python tools/validate_portfolio_config.py \
  --project-root runs/EXAMPLE --config config/portfolio.json --write-binding
```

The config uses `sapote_project_portfolio_v1` and names an existing
`sapote_project_registry_v1` JSON file inside the project root.
`--write-binding` saves the hashes in
`project_outputs/portfolio_binding.json`, which tells the exporter to include the
config and registry. Omit the flag for a check that only prints JSON. Saving again replaces the earlier binding;
keep any receipt you need.
Do not edit the config or registry while the command reads and hashes them.

The registry checks declared IDs and relationships. It records source paths and
hash strings without opening every cited source or resolving the full material
lineage. Check those inputs before relying on a recorded result. An AVAILABLE
assay inventory can contain NOT_TESTED, NOT_RETURNED or UNBOUND entries; read each
result state, material, condition and target alongside the count.

For the detailed field rules, see [the registry reader](../mamey/project_registry.py)
and [portfolio binding code](../mamey/portfolio_config.py). A failed binding can
print a traceback; keep it with the input files so the failing field can be found.


## Export and test the archive

Choose a new ZIP filename outside the project root:

```bash
python tools/project_catalog.py export-private \
  --project-root runs/EXAMPLE --out EXAMPLE-private.zip
python tools/project_catalog.py import-private \
  --project-root restored-EXAMPLE --input EXAMPLE-private.zip
```

The import destination must be empty or absent. A successful import prints the
archive hash, catalog hash, package paths and entry count. Compare them with the
exported project before using the imported files. Test the copy before sending it.

The archive contains **every registered package**, including extra files inside
those package folders. It also includes the catalog and, when configured, the
portfolio binding and its named config/registry. It does not follow a registry's
links to outside evidence. Review the included files and transfer those missing
inputs separately when needed.

This is a private archive with no redaction step. Review every included file before
sharing and send the ZIP's SHA-256 separately through a trusted channel.

The exporter refuses an existing output file, package symlinks, stale hashes and
absolute-location strings in manifests. Keep project files unchanged during
export. If a location is refused, preserve the original manifest and resolve
relocation before trying again. Export also needs a filesystem that supports
hard links for its final write.

The importer checks archive integrity, safe member paths, file hashes and the
catalog's package bindings. On failure, keep the error and use a new empty
destination after correcting the cause. See
[project data locations](PROJECT_DATA_HOME.md) for keeping source data separate
from these copied outputs. For one package's standard transfer ZIP, use the
[package transfer guide](FILES_STORAGE_AND_HANDOFF.md).


<a id="register-and-verify-package-locations"></a>
<a id="export-a-private-archive"></a>
<a id="import-into-an-empty-root"></a>
<a id="portfolio-bindings-have-a-separate-schema"></a>
<a id="project-registry-validation-and-receipt-limits"></a>
<a id="binding-inputs-writes-and-recovery"></a>
