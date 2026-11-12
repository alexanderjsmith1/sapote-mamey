# Catalog and copy a private project

Record where your packages live, check their manifest hashes, and copy the
registered packages into one private archive. You need existing packages under
a project folder and the installed bundle. This example uses one run, `EXAMPLE`.

## Register the package

Three things to know before you run the examples:

- `register` on a path that is already listed replaces its saved manifest hash.
- `verify` on a root with no catalog can create an empty catalog. Check the entry count.
- `export-private` has no redaction step. The archive holds every registered
  package in full.

From the program folder:

```bash
python tools/project_catalog.py register \
  --project-root runs/EXAMPLE --package runs/EXAMPLE/package
python tools/project_catalog.py verify --project-root runs/EXAMPLE
```

Replace the example paths with your project and package. The package must be
inside the chosen project root and have a `manifest.json` containing its strain ID.
Registration writes `project_outputs/project_catalog.json` under that root.

Verification prints the registered paths and entry count. Expect one entry for
this example. Running it against a new root can create an empty catalog, so check
the count instead of treating exit 0 as a complete inventory. Verification checks
manifest hashes; use the [package validator](reader/03_READ_RESULTS.md) to check
package contents.

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

A sample registry is `examples/project_registry.example.json`. Copy it and replace its
example names. A failed binding can print a traceback; keep it with the input files
so the failing field can be found.


## Export and test the archive

**Read this first.** `export-private` refuses a package straight from the
[first run](reader/01_FIRST_RUN.md). The run writes the full path of your input
ZIP into `manifest.json` (`input_zip`), and the exporter refuses any manifest
that holds an absolute path. The refusal reads:

```text
ValueError: private handoff refuses package package: manifest.input_zip contains an absolute locator.
```

The bundle has no command that removes the path. `register` and `verify` work
on such a package. To send the package itself, use the standard transfer ZIP in
the [package transfer guide](FILES_STORAGE_AND_HANDOFF.md). That ZIP retains the
package contents, including absolute paths; review those contents and recipient
access before sharing. It does not redact paths or create a multi-package private
export. Verify the source ZIP hash and use a fresh destination: standard handoff
replaces an existing destination and does not compare the source ZIP hash against
the manifest.

The export and import commands below work once the package manifest holds no
absolute path. That means changing `manifest.json`, so the package is no longer
the sealed original. If you do it, do it on a copy, run `validate` again, and
run `register` again, because the saved manifest hash goes stale.

Choose a new ZIP filename outside the project root:

```bash
python tools/project_catalog.py export-private \
  --project-root runs/EXAMPLE --out EXAMPLE-private.zip
python tools/project_catalog.py import-private \
  --project-root restored-EXAMPLE --input EXAMPLE-private.zip
```

A successful export prints the archive path and nothing else.

The import destination must be empty or absent. The importer opens and checks
the ZIP before it creates anything. It then unpacks to a staging folder beside
the destination and checks the catalog (and portfolio binding, if present)
there. A staged tree that passes is moved into place in one rename. If the
destination gained files in the meantime, the rename is refused and nothing is
copied into it. A refusal the importer can catch removes its staging folder and
any parent folders it created; an absent destination stays absent. A killed
process can leave a `mamey_project_import_*` staging folder beside the
destination. A successful import prints the archive hash, catalog hash, package paths and entry count. Compare them with the
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
export. Export also needs a filesystem that supports
hard links for its final write.

The importer checks archive integrity, safe member paths, file hashes, the
catalog's package bindings and, when present, the portfolio binding hashes. All
of these run on the staged tree before the move. On failure, keep the error and use a new empty
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
