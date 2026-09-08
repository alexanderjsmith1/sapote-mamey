# Single-strain quickstart

Most `build_*` tools take `--banked-dir` (a cohort bank), so one strain is run as a "cohort of
one." This bundle does **not** fetch accessions or run antiSMASH — you supply an antiSMASH output
zip you produced yourself.

As of build -k, `build_modeb_deepdive.py` **errors** (instead of emitting placeholder `?` cards) if
you neither pass `--targets` nor provide `cohort/modeb_verdicts.csv` — see step 5.

## Steps
1. Deterministic extraction (gold mode):
   ```
   python mamey_run.py run --strain <ID> --input-zip <antismash_out.zip> --mode gold --outdir work/<ID>
   ```
   Produces `records.json` / `verdicts.json` with the JUDGMENT_PENDING fields.
(`run --help` for `--taxonomy` / `--source` / typed `--bioactivity-json` / `--json-evidence`; omitted bioactivity is `NOT_SUPPLIED`.)

2. Validate the package (flags per `validate --help`):
   ```
   python mamey_run.py validate --package work/<ID>
   ```
   Expect `file_presence PASS` / `rggmci_gate PASS`.

3. Seed a bank of one and ingest:
   ```
   mkdir -p cohort
   python tools/ingest_package.py --package work/<ID> --banked-dir cohort
   ```
   Writes `bgc_data.json` / `deep_data.json` / `gene_data.json` into `cohort/`.

4. Run cohort-dir build tools against the one-strain bank (see each tool's `--help`), e.g.:
   ```
   python tools/build_figures.py --banked-dir cohort --out fig/
   ```

5. Mode B deep dives — supply targets explicitly:
   ```
   python tools/build_modeb_deepdive.py --banked-dir cohort --targets <ID>:BGC04,<ID>:BGC13 --out ModeB_<ID>.md
   ```
   Or run the Mode B verdict step to produce `cohort/modeb_verdicts.csv`, then omit `--targets`.

## Next: cross-strain / cohort GCF analysis
Once you have several strains ingested into a bank, the per-strain BGCs can be clustered across the
cohort into gene cluster families (GCFs) with BiG-SCAPE and read back into the Mamey locator space.
Driver: `tools/bigscape_pipeline.py`; full walkthrough in `docs/SOPs/SOP-17_CrossStrain_GCF_Cohort.md`
(and `docs/BIGSCAPE_GCF_WORKFLOW.md`). Families join back on `strain:node.region`, so single-strain
work here feeds the cohort layer directly.

## Cautions
- Cohort-local layers (product-class matrices, pan-genome families) are degenerate at N=1 — read
  them as single-strain, not cohort statistics; recompute after any real merge.
- Unpublished AS-### strains must never enter a public cut (hard guard). Keep single-strain work on
  an AS strain in the private/MERGED scaffold.
