# Single-region antiSMASH accession inputs

Some useful Sapote/Mamey test files are not full genomes. They are public GenBank/INSDC accessions that were run through antiSMASH as a single sequence and produced one BGC region. The bundle does not ship an example ZIP; `<accession>.zip` below is a placeholder for one you download or build.

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

`inspect` reports the input shape `raw antiSMASH single-region accession run`, and prints a single-region note, only when the filtered names contain exactly one lowercase-suffix `.gbk` path containing `region`, an `index.html` or `index.htm` filename, `regions.js`, a JSON filename and a path containing `clusterblast` (including KnownClusterBlast or SubClusterBlast names), after recognized macOS cruft filtering. Otherwise a one-region ZIP is reported as `raw antiSMASH region run`, with no note. The shape comes from file names, not from the sequence's source.

The strain-like label is often an accession such as `<accession>.1`, where `.1` is the GenBank version suffix.

## What to do with this input

1. Do not infer full-genome coverage from a one-region input. Check the actual assembly and supplied record scope.
2. Do not try to manually parse the large antiSMASH JSON in chat.
3. Run `python mamey_run.py inspect path/to/EXAMPLE.zip` first, substituting the actual path and quoting spaces.
4. Treat `inspect` as a filename/marker preview, then reconcile the actual input records and identity before an authorized gold run. Start from the run command it prints. It does not certify parse success or completeness. `--capped-session` reduces selected work but imposes no wall-clock limit and does not itself disable optional reference completion.
5. Inspect the parsed boundary counts, issue records and validation state before explaining assembly or completion warnings.
6. Retain the KnownClusterBlast metric and comparator identity. Even an exact reported match is similarity evidence; it does not establish the role of the input, production or a biological discovery.

## What the warnings mean

A single-region input can produce boundary-based warnings such as `VERY_POOR` / `0% interior`. Inspect the actual parsed boundary counts, validation and issue records to identify their causes. `MAMEY_COMPLETE_WITH_ISSUES` also depends on issues or validator state. These metrics do not by themselves assess the completeness or quality of the source genome. Retain the run's actual success, failure and evidence-coverage records; one successful fixture run does not validate all parser or KCB behavior.

## Recommended first-run command

```bash
python mamey_run.py inspect path/to/EXAMPLE.zip

python mamey_run.py run \
  --strain EXAMPLE \
  --input-zip path/to/EXAMPLE.zip \
  --taxonomy "unknown" \
  --source "not verified" \
  --outdir reviews/fresh-accession-run \
  --mode gold \
  --release PRIVATE \
  --capped-session \
  --reference-completion off
```

Run from the selected bundle root with its compatible Python environment. `EXAMPLE`, the paths and unknown metadata above are illustrative: substitute a safe explicit ID (review the `inspect` suggestion), bound input, fresh output root and verified metadata, quoting spaces. Retain explicit unknowns where not established. The `inspect` suggestion and `--strain auto` often agree, but `inspect` can shorten or sanitize an archive-derived name that auto returns unchanged; verify the resolved identity rather than assuming equivalence. An accession label can be retained with a warning when the archive supplies no organism-based identity. The command `inspect` prints also passes `--release PRIVATE`, `--json-evidence off` and `--brief none`; keep or change the release setting as your privacy profile requires. Record the resulting strain ID rather than assuming it equals the ZIP stem.

To keep an accession as the output label on purpose, replace the illustrative `--strain EXAMPLE` with the actual accession and add `--allow-accession-strain-id` and record that decision. The run then keeps the accession as the output identity: the run folder, package and manifest are all named after it. `--taxonomy` is recorded as metadata and never renames the strain. Without the flag, an explicit accession label is refused when the archive names an organism. The internal accession remains a sequence locator.

`run --json-evidence` defaults to `bounded`; `--capped-session` forces `off` for the main JSON walker. A separate record pass still reads eligible, readable JSON for KCB percent and other record evidence; inspect its status for held, absent or unreadable inputs. The explicit `--reference-completion off` above is a separate choice, not an effect of the capped flag.

This recipe consumes an existing antiSMASH ZIP. `run --accession` does not download or preprocess a genome; it is an unsupported placeholder when no `--input-zip` is supplied.

## BLASTP panel policy

For exact/redundant public reference clusters, the BGC BLASTP panel is optional and mostly useful as a parser/test fixture. Do not spend a real NCBI BLASTP round unless the goal is to validate `blastp-followup` parsing or to compare against a discovery strain.
