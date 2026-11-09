# Compare a fungal isolate with references

Use this page to plan where a fungal isolate sits relative to chosen references. It is a checklist, not a runner. The bundle has no one-command fungal pipeline, and this page gives no command lines for ITSx, MUSCLE, trimAl, IQ-TREE, BUSCO or compleasm. Take their commands from each tool's own documentation and record what you ran.

You need a fungal assembly, chosen reference records, the external tools and a resource plan. Use the fungal outgroup registry. The bacterial registry covers different inputs. For green algae and cyanobacteria, see [their separate guide](PHYLO_ALGAL_CYANO_WORKFLOW.md).

## 1. Pick the scale

| Route | Use it for | Tools |
|---|---|---|
| rDNA markers | A quick placement. 18S for family and genus context. ITS within one genus. | ITSx for ITS; Barrnap for 18S and 28S; MUSCLE; trimAl; IQ-TREE |
| Genome orthologs | A heavier check when markers disagree. | BUSCO or compleasm with a lineage such as `ascomycota_odb10`; MUSCLE; trimAl; IQ-TREE |

Rules for rDNA:

- Barrnap's eukaryote model name depends on its version. Run `barrnap --help` and read the model list. See [Barrnap](BARRNAP.md).
- Do not join ITS from divergent genera into one matrix.
- Keep partial calls and the model you used. A model does not guarantee a complete or correct marker.

Rules for orthologs:

- Review identity, duplicates and missing loci before you align and join them.
- BUSCO setup can fail on macOS-arm64. If it does, use Linux.
- Get references with NCBI `datasets` as a separate step.

## 2. Pick references and an outgroup

Open `mamey/data/fungal_outgroup_registry.tsv`. Find the row by `tree_scope` and `ingroup_taxon`. Read its `status`:

- `LOCKED`: decided and verified.
- `CONFIRM`: a real accession, but check that it fits your tree.
- `BANNED`: do not use as an outgroup or an ingroup reference.

A row gives either a marker accession or a genome assembly. Use the kind that matches your route. If a scope has no confirmed pair, leave the choice open.

Pick a sister group outside the ingroup. Record the row, the accession and the record that supports it. Check deposited names as well as assembly statistics. A bracketed taxon name alone is not a reason to exclude a record. Only a BANNED row excludes one.

One representative per genus gives a first placement view. Write down which congeners you left out and why.

### Check your intake file

Copy [the fungal intake example](../examples/phylo_fungal_intake.example.json) to a working file and replace every placeholder. The untouched example is incomplete on purpose and cannot be used for a run. The `fungal_registry.selection` object in it names a `tree_scope`, `ingroup_taxon` and `accession`.

Then run the checker. It reads and hashes your files and changes nothing:

```bash
python tools/phylo_crossgroup_intake.py /absolute/path/to/intake.json \
  --allow-root /absolute/path/to/your/data
```

A missing, ambiguous or BANNED registry selection is an error. A `HOLD` result lists decisions still open. The checker does not pick a row, confirm the organism, or authorize a run. The [algal and cyanobacterial guide](PHYLO_ALGAL_CYANO_WORKFLOW.md) has the matching intake steps for those groups.

## 3. Record evidence at each stage

Before you run any tool, follow the [companion protocol](LLM_COMPANION_TOOL_PROTOCOL.md). Write down the question, input hashes, reference and outgroup rule, tool versions, output folder and resource estimate. Get approval for any tree build.

Keep this evidence for each stage:

1. **Roster.** Source paths, hashes, accession versions, strain labels, roles (query, ingroup, outgroup), exclusions and the registry file hash.
2. **rDNA calls.** Tool and model versions, coordinates, orientation, partial and ambiguous calls, and which source record each marker came from.
3. **Alignments.** The alignment before and after trimming, the parameters, and every removed site or sequence with its reason.
4. **Orthologs.** Lineage and tool versions, per-taxon results and logs, duplicate and missing loci, the occupancy rule and the partition map.
5. **Tree.** Command and version, model, support settings, seed, alignment and tree hashes, rooting reason, and any tip shown differently from the analysis tree.

A technical pass is not scientific sign-off.

## 4. Check the tree

Run the sanity check before you render:

```bash
python tools/tree_sanity_check.py TREE.treefile --outgroup OUTGROUP_TIP_NAME
```

`--outgroup` takes a word or a complete tip name (case-insensitive), and every tip that contains it as a whole word counts as an outgroup tip. Use `--help` for the registry options. The report has one `[outgroup-term]` line per `--outgroup` value, listing the tips it matched. Check that list against the tip you meant.

The check fails with:

- `OUTGROUP_UNMATCHED` when an `--outgroup` value matches no tip. This holds even when another tip carries an `OUTGROUP` tag;
- `NO_OUTGROUP` when no tip is tagged `OUTGROUP` and no `--outgroup` value matches;
- `LONG_TERMINAL` when a tip branch that is not an outgroup is over the length ceiling;
- `DOMINATING_BRANCH` when one branch that is not an outgroup holds more than half the tree depth (`--dominate`).

Outgroup branches are exempt from `LONG_TERMINAL` and `DOMINATING_BRANCH`. A long outgroup is expected, so a pass says nothing about it. The `[outgroup-exempt]` line gives the longest outgroup branch and its share of tree depth. Read it, and review the root and the alignment yourself. A pass is not a check that the tree is rooted where you intended.

If `DOMINATING_BRANCH` fails, report the branch length and its share of tree depth. Check the alignment and outgroup. Do not loosen the check or prune the query to pass it.

`tools/signoff_check.py` is advisory. It can exit 0 while reporting issues, so read its findings.

If you also have an rDNA tree for this isolate, compare it with the genome tree and describe any disagreement. Bacterial ANI thresholds are not a rule for fungal names.

## 5. Recover an interrupted ortholog run

Start the genome again in a new output folder. Keep the failed run and its logs. A compleasm run can write a `miniprot.done` marker before its hmmsearch step finishes. Resuming from that marker can leave a truncated ortholog set. Check the output, not the marker. The compleasm version that behaves this way is not recorded here, so check yours.
