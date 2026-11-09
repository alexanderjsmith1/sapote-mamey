# Dominated diagnostic report

A class call is the pipeline's label for what kind of cluster a region is, such
as lanthipeptide or NRPS. Some class calls rest on one domain hit. Read this page
only if such a hit is weak and you want to know whether a stronger domain on the
same gene overshadows it. Most runs do not
need it. The report is report-only: it changes no hit, score or class call.

## Where it is

Every `run` writes it into `<strain>_AntiSMASH_Evidence_Parse.json` in the
package folder, under the key `dominated_diagnostics`. Open that file and search
for the key.

## What it flags

A domain hit is a match of a gene's protein to a protein-family model (HMM). It
carries two numbers. The bitscore measures how well the protein fits the model;
higher is better. The E-value is the number of matches this good expected by
chance; smaller is stronger, so `1e-40` is far stronger than `1e-05`.

A tier-1 diagnostic is a domain the pipeline treats as strong evidence for a
cluster class, such as `YcaO`, `Radical_SAM` or `AMP-binding`. The fixed list is
`_TIER1_DOMAIN_NAMES` in `mamey/antismash_evidence.py`.

A tier-1 hit is flagged when both conditions hold for hits that carry the same locus tag in the same
region ("same gene" below means that tag match; the diagnostic does not check that a repeated tag
names one source CDS):

- Its bitscore is 30 or less.
- A different domain on that gene has a significance at least 20 orders of
  magnitude stronger. The code compares -log10(E-value). The other E-value must
  be about 1e-20 times smaller than the weak hit's E-value.

Missing, zero, non-finite and malformed E-values cannot be assessed, so they are
skipped. Unrecognized or ambiguous TIGRFAM region locations are not used as
competing evidence.

## Fields

| Field | Meaning |
|---|---|
| `status` | Always `CALIBRATION_REQUIRED`. The thresholds are not validated. This is not an error. |
| `thresholds` | `max_bitscore` (30.0) and `min_evalue_orders` (20.0). |
| `flags` | A list. Empty when nothing was flagged. |
| `scope` | A fixed sentence: same-gene parsed hits only, nothing else changed. |

Each entry in `flags` has:

| Field | Meaning |
|---|---|
| `flag` | `DOMINATED_DIAGNOSTIC`. |
| `region_key` | The region the gene sits in. |
| `locus_tag` | The gene. |
| `diagnostic_domain`, `diagnostic_bitscore`, `diagnostic_evalue` | The weak tier-1 hit. |
| `competing_domain`, `competing_evalue` | The strongest rival on that gene. |
| `evalue_orders_gap` | The gap in -log10(E-value) between the two. |

## Example

```json
"dominated_diagnostics": {
  "status": "CALIBRATION_REQUIRED",
  "thresholds": {"max_bitscore": 30.0, "min_evalue_orders": 20.0},
  "flags": [{
    "flag": "DOMINATED_DIAGNOSTIC",
    "region_key": "contig_1_region001",
    "locus_tag": "ABC12_00345",
    "diagnostic_domain": "Radical_SAM", "diagnostic_bitscore": 24.1,
    "diagnostic_evalue": "1e-05",
    "competing_domain": "Pfam_housekeeping_domain", "competing_evalue": "1e-40",
    "evalue_orders_gap": 35.0
  }],
  "scope": "Same-CDS parsed hits only; ..."
}
```

This entry says the gene's weak `Radical_SAM` hit is far weaker than another
domain on the same gene. The names above are invented for illustration.

## What to do with a flag

Look at that gene by hand before you trust the class call it supports. A flag is
a prompt to look, not a finding about function. Different HMM families have
different score ranges, so their E-values are not directly comparable.

An empty `flags` list does not show the hit is real. It means no flag was emitted from the hits the
diagnostic could assess. A tier-1 hit with no locus tag, a missing, negative or non-finite bitscore,
or an E-value it cannot assess is skipped, not counted as a tested negative,
and the list does not record that it was skipped. When the source evidence was unavailable, no hit was
assessed. If two different genes share a locus tag, hits from both are compared as one gene;
check tag uniqueness before reading a flag as same-gene competition.
