# Strain BiG-SCAPE report and figure labels

`tools/strain_bigscape_report.py` writes one Markdown report for one strain. It reads tables exported from a BiG-SCAPE analysis, not the BiG-SCAPE database. Terms such as GCF, MIBiG and BGC are in the [glossary](GLOSSARY.md).

## What KNOWN and NOVEL mean

> KNOWN and NOVEL are BiG-SCAPE family labels within one run, at one cutoff, on the loaded strains and reference set. KNOWN means the family contains a MIBiG member. NOVEL means it does not (`tools/bigscape_known_novel.py`). "Unique" or "cohort-exclusive" means no other loaded strain is in the family. None of these labels identifies a compound, shows chemical novelty or shows rarity in nature. Always state the run, cutoff and strain count with any number.

## Inputs

`--strain` and `--per-bgc` are required. The other tables are optional. A section appears only if its table is given, the file exists and it has usable rows. A missing optional path is skipped without a message, so check that each section you asked for is in the output. A missing `--per-bgc` file ends in a Python traceback.

No tool in this bundle writes the per-BGC, capacity, family, sharing or uniqueness tables. They are exports from a cohort BiG-SCAPE analysis done outside the bundle. Only the `--integrated` table has a producer here, `tools/antismash_bigscape_join.py` (`--gbk-dir`, `--bigscape-tsv`, `--out`). All tables are tab-separated with a header row. Column names are matched without regard to case.

| Option | Columns the tool reads | What it adds |
|---|---|---|
| `--per-bgc` | `strain`, `locator`, `antismash_class`, `family_status`, `nearest_mibig`, `nearest_distance` | Overview, assembly quality, class table, MIBiG anchors |
| `--antimicrobial` | `strain`, `antifungal_candida_anchors`, `antibacterial_mrsa_anchors`, `siderophore_anchors` | Antimicrobial capacity |
| `--integrated` | `strain`, `locator`, `antismash_domains` | Domain text in the anchor table; Notable BGCs |
| `--novel` | `qualified_family_id`, `run_id`, `normalized_cutoff`, `family_id`, `strains` (comma-separated), `class`, `n_strains`, `assembly_line_architecture` | Families with no MIBiG member |
| `--sharing` | `strain_a`, `strain_b`, `shared_gcf_families` | Biosynthetic neighbours |
| `--uniqueness` | `strain`, `total_family_bgcs`, `unique_bgcs`, `shared_bgcs`, `strain_exclusive_families` | Uniqueness |

Rules that catch people:

- `family_status` must read `KNOWN` for a BGC to count as known. In `nearest_mibig`, put the compound name in parentheses, for example `BGC0000001 (compound name)`. The tool shows the text inside the parentheses.
- `locator` must contain `length_<N>`, as in a contig name like `NODE_1_length_52000_cov_30`. A row without it is left out of the assembly-quality line.
- `--novel` refuses a table whose rows lack the run, cutoff and qualified-family columns, or whose `qualified_family_id` is not in the form `bigscape-gcf:v1/run/1/cutoff/0.3/family/5` with the same run, cutoff and family. It prints a `BIGSCAPE_NAMESPACE_ERROR` line and exits 2.

Build the tables from one run and one cutoff. Do not combine exports by matching a bare family number or a `node.region` string. `--genus` and `--habitat` are labels you type. The report prints them as given.

## Run it

```bash
python tools/strain_bigscape_report.py --strain EXAMPLE \
    --per-bgc per_strain_BGC_annotation.tsv \
    --antimicrobial antimicrobial_capacity_by_strain.tsv \
    --novel novel_antimicrobial_targets.tsv --sharing strain_pair_shared_BGCs.tsv \
    --uniqueness strain_uniqueness.tsv \
    --integrated antismash_bigscape_integrated.tsv \
    --genus Streptomyces --habitat EXAMPLE-host
```

Success prints one line, `wrote EXAMPLE_bigscape_report.md: N BGCs (K known / M novel / U no status), A anchors`, and writes that file to the current folder. Use `--out` to name another path. The parent folder must exist. An existing file with that name is overwritten. When some KNOWN rows give no nearest reference or no distance, the line ends `, R KNOWN without a reference`, and `A` counts only the KNOWN rows that have both. If no `--per-bgc` row matches `--strain`, the tool stops with `no BGCs for EXAMPLE in <file>`.

The report starts with the title and a subtitle line, then has these sections in this order. The first three are always present. The rest appear only when their table gave rows.

1. **Overview:** BGC count, the KNOWN, NOVEL and no-status counts as labeled in `family_status`, and the dominant class. The sentence says the labels are read as given. The tool does not check family membership, the reference set, or the run and cutoff.
2. **Assembly quality — read the counts with this:** contig span and median from the locators, and the count under 15 kb. The median is the middle value, or the mean of the two middle values for an even count. Repeated contigs are not merged. These values do not establish assembly quality.
3. **BGC class distribution:** classes counted at least twice, or containing PKS, NRPS or RiPP. It is not a full census.
4. **Antimicrobial capacity (vs MRSA / Candida targets)** (`--antimicrobial`): antifungal, antibacterial and siderophore anchors. Capacity only.
5. **MIBiG anchors:** the nearest MIBiG cluster named in `nearest_mibig` for each KNOWN BGC, with the distance as given, locator and domain text. Always present. A KNOWN row with a blank reference or a blank distance shows `not given` in that cell, sorts last, and is counted in a line above the table as unresolved. The heading reads distance as a run-specific similarity score: distance 0 does not show identical sequences or the same product.
6. **Notable BGCs (intact assembly lines)** (`--integrated`): rows whose domain text has a PKS core (KS, AT and ACP) or an NRPS core (C, A and PCP). Display rules, not proof of an intact pathway.
7. **Families with no MIBiG member** (`--novel`): families this strain is in that have no MIBiG member in this run.
8. **Biosynthetic neighbours** (`--sharing`): the strains that share the most families.
9. **Uniqueness** (`--uniqueness`): the strain's family-assigned BGC count and how many fall in families no other loaded strain occupies.
10. **Caveats.**

Display is capped at 25 anchor rows, 20 notable rows, 15 family rows and 8 neighbours. Long locators are shortened. Keep the full tables and a `strain / full node-or-contig / region / BGC alias` crosswalk for any single-locus use, because the Markdown does not carry the full identity.

## Wording in the output to read with care

Some generated sentences say more than the evidence does. Treat them as follows.

- A NOVEL family means only that no MIBiG member sits in the same family in this run. It is not a novelty or chemistry claim, and the report says so.
- Strain-unique families are family membership among the loaded strains. A strain-unique BGC can come from a family that the assembly split, and it says nothing about what the strain makes.

## Limits to know before you use the numbers

- The tool has no run or cutoff option and writes no hash receipt. You are responsible for feeding it tables from one run.
- KNOWN and NOVEL count only rows with that status, ignoring case. A blank, held or unknown status is reported separately as "no family status", never as NOVEL.
- A NOVEL family is not evidence that no homolog exists outside the run.
- The report subtitle always says "BiG-SCAPE GCF vs MIBiG 4.0". It is a fixed label, not a check of the reference version you used. Correct it by hand if the run used a different release.
- The "very likely" and "likely" assembly-line labels come from domain words and a 15 kb contig threshold. They are not functional proof.
- An absent section is not a biological negative.

## Figure labels

`tools/bigscape_figure_labels.py` fixes the legend names and colors for BiG-SCAPE figures. Cohort type strains are legended "type strain" (gray). MIBiG clusters are legended "MIBiG reference" (red). Host habitat categories keep their own names. A bare "Reference" label is refused. A figure builder imports `category_of`, `STYLE` and `legend_handles` from the module.

The report only reformats tables. It does not change any clustering or anchoring. Convert the Markdown to Word or PDF yourself if you need a formal copy.
