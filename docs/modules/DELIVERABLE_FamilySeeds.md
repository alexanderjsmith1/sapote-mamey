# DELIVERABLE: Cross-Strain Family Seeds

**What this is.** A convention for labeling each BGC (biosynthetic gene cluster) so clusters from different strains can be compared later. No tool writes a `CrossStrain_Family_Seeds` table. You or an assistant build it by hand. The only real command on this page is `tools/build_gcf_tags.py`, which writes a different thing: product-family tags.

**Purpose.** Give every BGC a comparable seed label. When 3 or more strains carry seeds in the same class, plan a cross-strain family comparison for that class.

The current task and [assistant governance](../ASSISTANT_GOVERNANCE.md) decide what you may do. The thresholds below are conventions. The engine does not enforce them. Terms are in the [glossary](../GLOSSARY.md).

## When to do it

Do this after the BGC inventory for a strain is done. A strain whose inventory has no seed labels is incomplete for cross-strain work.

## Inputs, per BGC

| Field | Used for |
|---|---|
| Strain ID, deposited isolation source, genus, BGC number, product class | The seed label (a display name) |
| Strain, full node or contig, region, BGC alias | The locus identity behind each seed |
| Architecture grade, KCB (KnownClusterBlast) top hit and score | The seed row |
| Diagnostic domains, module signature, TFBS signature, TTA tier | Comparison axes |
| The master workbook's earlier strains | The 3-strain check |

Leave an axis with no value blank and label it (for example `not computed`). Do not impute. Count a class toward the 3-strain threshold only when each strain has a real seed.

## The command that exists

```bash
python tools/build_gcf_tags.py --banked-dir <banked_dir> --workbook <master.xlsx> --out-dir <out_dir>
```

`<banked_dir>` is the cohort bank folder that `tools/ingest_package.py --merge` writes. This tool reads one file from it, `bgc_data.json`, and uses its `bgcs` list: each entry's `sid`, `bgc_id`, `contig`, `region`, `products` and `closest_kcb_product`. Other files in the folder are not read. The default is `cohort` for this tool. `tools/ingest_package.py` defaults to `/data/mamey-local`, so pass `--banked-dir` to both. GCF means gene cluster family. `--ww` is a free-text strain id for the cohort. `--thesaurus` defaults to `resources/gcf_thesaurus.json`. `--workbook` is optional.

What you should see: a line such as `tagged N BGCs -> GCF_Tags.csv` and the file `GCF_Tags.csv` in `<out_dir>`. The tool refuses to run, with exit 2 and `refusing <out_dir>/GCF_Tags.csv`, when that file already exists or names an input. Use a new `<out_dir>` for each run. With `--workbook`, the tool also replaces a sheet named `GCF_Tags` in that workbook, so copy the workbook first. The columns are `strain`, `bgc`, `Predicted_BGC_Class`, `KCB_anchor`, `GCF_Product_Family_Tag`, `match_basis`, `contig`, `region` and `identity_status`. `identity_status` is `COMPLETE` when the bank entry has a strain, contig, region and BGC alias, and `IDENTITY_HOLD` when one is missing (the missing cell is blank). Join on all four; a strain and alias alone can match a different locus after a reassembly.

The tag is anchored on the KCB hit. It states similarity, not product identity. An unresolved anchor gets no family.

To add a new package to the cohort first:

```bash
python tools/ingest_package.py --package <package_dir> --ww <strain_id> --banked-dir <banked_dir> --merge
```

## Seed label format

```text
<Genus>_<Habitat>_<CompoundClass>_<Strain>_BGC<N>
```

Use the deposited isolation source for `<Habitat>`. Example shape: `Genus_Source_Class_ABC-12_BGC001`.

The seed label is a display name. It does not carry the contig or region, so it cannot bind a locus on its own. Keep each seed row's full `strain / full node-or-contig / region / BGC alias` identity beside the label, with the assembly it came from, and hold a seed whose alias maps to more than one locus.

## Threshold

When 3 or more strains carry seeds in the same class, plan a cross-strain family comparison for that class. After every fifth strain, audit the seed table against the master workbook.

## Checklist

- [ ] Every BGC has a seed row with all axes, blanks labeled.
- [ ] Labels follow the format above.
- [ ] You checked the 3-strain threshold against the master.
- [ ] NAPAA is scoring-neutral in the rules registry (`mamey/data/rules_registry.json`): it is neither downgraded nor excluded. Leave it out of cohort family comparisons and do not use it as a family signal. hglE-KS is treated as habitat-nonspecific.
- [ ] Open holds are listed.
