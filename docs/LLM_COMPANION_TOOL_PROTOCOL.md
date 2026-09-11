# LLM companion-tool protocol — BiG-SCAPE, GToTree, and IQ-TREE

**Status:** authoritative LLM-facing operating contract.  This file governs Claude, Codex, and
other agents that prepare, run, resume, interpret, or hand off the named companion workflows.
BiG-SCAPE and phylogenomics remain downstream of a sealed Mamey package. They do not alter Mamey
scores or establish production, activity, compound identity, novelty, or formal taxonomy.

## The first rule: resume before rediscovering

An agent entering an existing workspace must read, in this order:

1. the tool's `CURRENT_RUN.txt` pointer;
2. that run's `RUN_STATE.json` and immutable `RUN_MANIFEST.json`;
3. `HANDOFF.md`, `QA_REPORT.json` (or tool-specific QA receipt), and the tail of the run log;
4. only the paths named by those files.

Do not recursively scan a large user workspace when a verified handoff exists. Do not create a new
run merely because the producing agent was Claude and the consuming agent is Codex, or vice versa.
The filesystem contract, not the chat transcript, is the cross-agent source of truth.

## Required run layout

Each companion workspace has one lightweight current pointer and immutable run directories:

```text
<tool-workspace>/
  CURRENT_RUN.txt
  runs/<run-id>/
    RUN_MANIFEST.json       # immutable inputs, hashes, tool versions, parameters, resource budget
    RUN_STATE.json          # PLANNED | RUNNING | HOLD | FAILED | COMPLETE
    COMMAND.sh              # exact command; no credentials
    EVENTS.jsonl            # append-only transitions and recoveries
    HANDOFF.md              # short, human-readable resume guide
    input_objects/          # content-addressed objects, or links to them
    input_view/             # run-specific links; no duplicate biological data
    references/             # links + checksums + source metadata
    logs/
    outputs/
    qa/
```

Input objects are keyed by SHA-256. A friendly filename is a view, never the identity of an object.
The manifest records original path, archive member when applicable, byte size, SHA-256, strain,
and biological locator. Never join by a bare BGC number. For BGC regions use
`(strain, bgc_id, contig·region)`; for genomes use assembly SHA-256 plus the displayed strain label.

## Mandatory preflight shown to the user

Before an external-tool run, report:

- tool and exact version;
- local versus network inputs;
- item count and total staged bytes;
- reference count and reference-selection rule;
- HMM/Pfam target and checksum;
- requested cores, jobs, threads per job, and maximum concurrent cores;
- expected runtime and disk use, explicitly labelled as a local benchmark or estimate;
- output root and whether the run is new, resumed, or recovered;
- whether any step downloads data or writes into a sealed/canonical package.

**GToTree requires user approval after this preflight and before execution.** Reference downloads,
large database downloads, and any direct ingest into canonical Mamey outputs also require separate
approval. A dry-run inventory, hashing, version probe, or inspection is read-only and may proceed.

If no machine-specific timing exists, run a 3–5-genome assessment or give a bounded planning range
and say it is uncalibrated. Never present a guessed runtime as measured.

## Resource policy

- One GToTree alignment/tree job uses one core: `-j 1 -n 1 -M 1`.
- IQ-TREE uses one thread per tree (`-T 1` or the locally verified equivalent).
- At most four one-core tree jobs may run concurrently. Never assume unused logical CPUs are free.
- BiG-SCAPE defaults to one core for interactive work; two is the balanced option; four is the
  surfaced ceiling. Record the actual setting.
- Do not use detached `setsid`, `nohup`, background `&`, or an unattended parallel fan-out as the
  default LLM recipe. Use the product's persistent-task mechanism or a foreground process with a
  recorded session and regular status updates.
- Do not force-overwrite an existing output directory. A parameter change creates a new run ID.

## Separation of evidence and mutation

Companion output is an additive evidence layer. Default products are portable TSV/JSON, trees,
figures, and an HTML report. Writing GCF annotations into Mode B cards, editing triage boards, or
replacing canonical labels is a separate, explicitly authorized reconciliation step. The original
artifact and its checksum must remain available.

Missing references or absent admissible hits are `NOT_ASSESSED` or `HOLD/REQUEST`, not negative
biology. Keep NCBI, EBI, Swiss-Prot, ClusterBlast, MIBiG, BiG-SCAPE, ANI, and phylogenomic channels
independently attributable.

## Completion gate

A run is `COMPLETE` only after all of the following are recorded:

1. process exit status is zero;
2. exact completed run ID is selected (never blindly use the maximum database ID);
3. the output database/file passes integrity checks;
4. observed input counts match the immutable manifest;
5. membership/leaf denominators and exclusion reasons are reported;
6. portable exports exist and have checksums;
7. the handoff names the exact files a second agent should read;
8. all warnings remain visible.

A failed historical run row may remain in a database. Do not delete it merely to make the history
look clean; exclude it by explicit completed run ID.

## Claim ceilings

- BiG-SCAPE: “assigned to the same run-specific GCF at cutoff X” means domain-architecture
  similarity within that run. It is not compound identity, activity, novelty, or proof of a shared
  biosynthetic product. Family IDs are not portable across databases/runs.
- MIBiG: “shares a family with a characterized reference” is a similarity anchor. `KNOWN` and
  `NOVEL` are prohibited for cohort-only runs. Even with references, use “MIBiG-anchored” and
  “unanchored in this reference panel,” not universal known/novel claims.
- GToTree/IQ-TREE: a tree supports placement within the sampled panel. It does not by itself delimit
  species, prove strain identity, or establish formal taxonomy. Report support, marker retention,
  exclusions, and the sampled references.
- ANI/16S: report identity/aligned fraction and the exact sequences or assemblies compared. Treat
  thresholds as interpretation aids, not automatic naming rules; investigate suspected duplicates
  or contamination before combining records.

## Routing

- BiG-SCAPE execution: `docs/BIGSCAPE_GCF_WORKFLOW.md`
- Cohort GCF interpretation: `docs/SOPs/SOP-17_CrossStrain_GCF_Cohort.md`
- GToTree, MLSA, ANI, and IQ-TREE: `docs/phylogenomics.md`
- Optional tool detection and installation: `docs/companion_tools.md`

Older cohort-specific notes and versioned addenda are historical evidence only. If an old example
conflicts with this protocol, this protocol wins and the conflict must be reported for repair.
