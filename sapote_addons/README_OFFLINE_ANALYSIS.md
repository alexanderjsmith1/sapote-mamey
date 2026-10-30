# Compare proteins between two strains

Compare CDS translations from two antiSMASH ZIPs and get one best-hit row per
query CDS. You need both result ZIPs and an installed comparison backend.
For optional ANI, you also need both whole-genome FASTAs and an installed
`pyskani` or `pyfastani` backend. [Recover the submitted genomes from the
ZIPs](../docs/COMPANION_FILES.md#recover-a-genome-from-an-antismash-zip) if FASTAs are missing.

## Check and install

From the program folder:

```bash
python mamey_run.py doctor
python mamey_run.py compare --help
```

The code ZIP has three bootstrap wheels, not the complete add-on wheel set.
Activate the target environment and supply compatible wheels:

```bash
bash bundle_support/install_sapote_addons.sh wheels
```

The installer resolves offline by default. It pools wheels from the supplied
folder and nearby roots to depth four; same-named files use first-found precedence.
Record their hashes and the environment. `PYTHON` selects the interpreter,
defaulting to `python3`. Outside a virtual environment the script refuses with
status 2; use a virtual environment for normal installation.

Core imports are required and figure imports are best effort. `--online` permits
an index fallback for absent wheels or a missing distribution; choose it only
when network installation is intended. Partial changes are not rolled back,
and temporary logs are removed on exit, so save terminal diagnostics.
DIAMOND and external databases are separate; see [DIAMOND status](DIAMOND_STATUS.md),
[Install](../docs/INSTALL.md) and [bundle-support roles](../bundle_support/README.md).

## Compare the ZIPs

Put your query ZIP at `inputs/EXAMPLE.zip` and the chosen reference ZIP at
`inputs/reference.zip`, or replace those paths:

```bash
python mamey_run.py compare --strain-a inputs/EXAMPLE.zip \
  --strain-b inputs/reference.zip --out reviews/EXAMPLE/comparison
```

A and B are directional: reversing them changes the query set. Use a new output
folder. To include ANI, add `--genome-a` and `--genome-b` with the matching assembly
FASTAs; both are needed. The default alignment thread count is one. Change
`--alignment-threads` only for your resource plan; the Biopython fallback stays serial.

A Mamey package folder cannot replace the ZIP because this command needs GenBank
translations. ZIP parsing prefers non-region GBKs; otherwise it reads region files
with declared offsets. Bare GenBank files are also accepted. Check the CDS roster:
unparseable locations are skipped, compound locations use the longest part for
representative coordinates, and duplicate contig/start/end/strand/locus records
are collapsed before selecting translations.

## Read the output

Open `S5_gene_level_similarity.csv` for the query gene, best reference match,
identity, coverage, call, backend and note. `gemini_summary.json` contains counts,
backend, requested threads and successful ANI output; its name is kept for compatibility.
Use `backend` for the selected path; `diamond_status` is static text.

The fixed calls are **present** at identity ≥70% and query coverage ≥60%,
**divergent_candidate** for a hit below either threshold, and **no_hit** when no
best hit is returned. Interpret no-hit rows with input completeness and backend
warnings. The CLI's `--min-identity` and `--min-coverage` options are currently
ignored by this command. Backend selection is automatic.

ANI appears only when it succeeds. If both FASTAs were supplied but `ani` is
absent from the summary, no ANI result was returned. A missing backend can be
silent even with exit 0; check `pyskani` or `pyfastani` before retrying. The code rounds ANI before
labeling values: strictly between 94% and 96% is boundary/indeterminate; exactly
94% is distinct and exactly 96% same species. These are routing labels to review,
not a substitute for the taxonomic comparison.


## Check identity and failures

Query keys use locus tags or `cds_N`, without contig/region identity. Repeated tags
can collide and share a best-hit result. Check tag uniqueness and bind each
interpreted locus to **strain / full node-or-contig / region / BGC alias**.
Save input hashes separately; the two output files do not contain them.

The output directory is created early, and its CSV and JSON are replaced
individually. A failed refresh can leave mixed old/new outputs or an empty folder.
Keep an accepted earlier result and retry at a fresh destination after fixing the cause.

Invalid thread counts exit 2 before output creation. Missing input, no translated
CDS or no backend exits 1; a completed comparison exits 0 even without ANI or with
all no-hit rows.  A failed DIAMOND route can
also yield zero-hit output, so inspect warnings and each row's backend.
See [resource control](../docs/COMPARE_RESOURCE_CONTROL.md) for CPU/memory details.

<a id="inputs"></a>
<a id="check-and-install-dependencies"></a>
<a id="run-a-comparison"></a>
<a id="outputs"></a>
<a id="current-limitations"></a>
<a id="identity-overwrites-and-recovery"></a>
