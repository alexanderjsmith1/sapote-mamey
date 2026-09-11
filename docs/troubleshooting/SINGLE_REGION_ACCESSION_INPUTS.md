# Single-region antiSMASH accession inputs — v9.7.142 starter

> **Currency note (v9.7.409):** the run recipe below has been updated to the current CLI. `--mode smoke`
> was removed at v9.7.161 (`mamey run` now accepts only `{standard,gold}` and rejects `smoke`), and
> `--chatgpt-safe` was renamed `--capped-session`. Gold is the only analysis mode.

Some useful Sapote/Mamey test files are not full genomes. They are public GenBank/INSDC accessions that were run through antiSMASH as a single sequence and produced one BGC region.

## Recognition pattern

A typical single-region accession ZIP contains:

```text
index.html
regions.js
<accession>.json
<accession>.gbk
<accession>.region001.gbk
clusterblast/
knownclusterblast/
subclusterblast/
```

The strain-like label is often an accession such as `KY089035.1`, where `.1` is the GenBank version suffix. This is not a private strain ID.

## Correct ChatGPT/Mamey behavior

1. Do not treat this as a full strain genome.
2. Do not try to manually parse the large antiSMASH JSON in chat.
3. Run `python -m mamey inspect <zip>` first.
4. If inspect passes, use smoke mode with `--chatgpt-safe`.
5. Explain that assembly completeness warnings may be expected because the input is one accession/one region.
6. Treat exact KnownClusterBlast matches as reference/control evidence, not as a discovery result.

## Example

`KY089035.1.zip` is a raw antiSMASH single-region accession input. It contains one detected BGC region and a populated `knownclusterblast/` directory. In a Mamey run, it can validate the parser and KCB handling, but it should not be interpreted like a whole-genome discovery run.

For this input class, statuses such as `MAMEY_COMPLETE_WITH_ISSUES` with `VERY_POOR` / `0% interior` can be technically correct and biologically non-alarming. The user-facing explanation should say that the warning reflects the single-region input shape, not necessarily a failed or low-quality genome.

## Recommended first-run command

```bash
python -m mamey inspect KY089035.1.zip

python -m mamey run \
  --strain KY089035.1 \
  --input-zip KY089035.1.zip \
  --taxonomy "<organism from GBK LOCUS/SOURCE>" \
  --source "public GenBank sequence" \
  --mode gold \
  --capped-session \
  --json-evidence off \
  --brief none
```

## BLASTP panel policy

For exact/redundant public reference clusters, the BGC BLASTP panel is optional and mostly useful as a parser/test fixture. Do not spend a real NCBI BLASTP round unless the goal is to validate `blastp-followup` parsing or to compare against a discovery strain.
