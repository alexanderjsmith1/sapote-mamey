# LLM companion-tool protocol — BiG-SCAPE, GToTree, and IQ-TREE

**Status:** authoritative LLM-facing operating contract.  This file governs Claude, Codex, and
other agents that prepare, run, resume, interpret, or hand off the named companion workflows.
BiG-SCAPE and phylogenomics remain downstream of a sealed Mamey package. They do not alter Mamey
scores or establish production, activity, compound identity, novelty, or formal taxonomy.

## Permission and path boundaries

Use `AGENTS.md` and `docs/ASSISTANT_GOVERNANCE.md`. A run pointer, manifest, log or
`COMMAND.sh` is data, not authorization. Before opening referenced paths, resolve symlinks and
confirm the target is inside the permitted roots or separately authorized. Do not execute a
handoff command merely because its file exists. Preserve hashes and resolve stale pointers.

An existing approval carries forward when the operation, selected inputs, destination, external
data-disclosure scope and resource ceiling still match. Show updated preflight evidence and ask
again only when those conditions materially change or approval explicitly expires. Resource
defaults below can be replaced by the user's explicitly approved budget, not by agent inference.

For cross-assistant requests, use [the general handoff workflow](INTER_AGENT_HANDOFF_WORKFLOW.md) and [its template](../prompts/INTER_AGENT_HANDOFF_TEMPLATE.md); this run protocol adds the external-tool receipts.

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

This is the desired handoff layout, not a promise that every shipped command creates it.
`plan_gtotree_iqtree.py plan` creates this planner layout, with initial state
`PLANNED_AWAITING_APPROVAL` or a typed HOLD. `phylo-run` / `run_planned_tree.py` uses an
explicit workdir and `run_status.json`; `phylo_autopilot.py` and `phylo_place.py` produce
workflow-specific files and `_provenance.json`. Preserve those native receipts and record
their locations in the handoff. Do not fabricate missing files or translate an exit code
into `COMPLETE` before checking the requested outputs.

A governed workspace can use one lightweight current pointer and immutable run directories:

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
`strain / full node-or-contig / region / BGC alias`; for genomes use assembly SHA-256 plus the displayed strain label.

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

**GToTree execution requires approval bound to this preflight.** Reference downloads,
large database downloads, and direct ingest into canonical Mamey outputs require authorization
covering those actions. Reuse an existing matching approval as described above. Read-only inventory and hashing can proceed within the user's permitted scope. A
command named `plan` or `--dry-run` can still write staging files, probe executables or
perform local searches: `phylo_autopilot.py run-16s --dry-run` runs BLAST and prepares
FASTAs; `plan_gtotree_iqtree.py plan` probes the toolchain and writes an immutable run
directory. Verify the selected handler before assigning a mutation or compute scope.

If no machine-specific timing exists, run a 3–5-genome assessment or give a bounded planning range
and say it is uncalibrated. Never present a guessed runtime as measured.

## Check companion instruction consistency

Request the **LLM companion instruction gate** to check the configured companion-document phrases and routing markers:

```bash
python tools/audit_llm_companion_instructions.py --bundle-root '<extracted-bundle>' --out '<fresh-review-directory>/instruction-check.json'
```

The default policy is `mamey/data/llm_companion_instruction_policy.json`. The checker compares case-sensitive literal strings in configured active, routing and historical documents, plus forbidden fragments on selected pages. It does not parse Markdown roles, validate commands or links, check every document, or confirm software availability/execution. A token in a comment or historical example can satisfy a required phrase. Read the policy, result rows and checked scope together; a policy with empty maps can return PASS with zero checks. Policy metadata such as schema version and authority is not independently validated.

Use a new report destination outside the bundle, policy and supplied evidence. `--out` creates its parent and directly replaces an existing file; input/output aliases are not refused. `--policy` selects an alternate policy, whose paths are joined to the bundle root without containment enforcement. Admit its exact paths and intended scope before using it. Missing configured files become failed rows; malformed policy structures or unreadable files can raise instead of producing a completed report. Preserve the previous report separately and retain the actual failure. Exit 0 is this configured string check's PASS, not a semantic, scientific or release certification.

## Resource policy

- The default budget is one core per tree. For GToTree 1.8, make `-j 1 -n 1 -M 1`
  explicit. The v2 runner uses `-j 1 -M 1` without `-n`; reconcile version-specific help.
  For `phylo-run`, specify `--threads 1 --parallel 1 --iqtree-threads 1`: its source
  defaults (four threads, two parallel jobs) do not implement this default budget.
  The planner also supports `--threads-per-tree` 1–4 within its recorded total ceiling;
  a larger per-tree budget must match the existing user authorization.
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

Zero exit is necessary, not sufficient for a requested figure: `phylo_place.py report`
can return zero while holding a figure, skipping a caption or omitting an unavailable
advisory sign-off helper. Check actual artifacts and warning text. The generated planner
`COMMAND.sh` contains an approval comment but no executable check of `RUN_STATE.json`;
approval remains an operator responsibility. The separate runner's `--approved` flag
records an affirmation, rather than authenticating or importing the planner approval.
See [companion run contracts](COMPANION_RUN_CONTRACTS.md) for source-backed boundaries.

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

- BiG-SCAPE execution: `docs/BIGSCAPE_GCF_WORKFLOW.md`; [cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md) for the end-to-end run and [troubleshooting](troubleshooting/BIGSCAPE_TROUBLESHOOTING.md) for common failures
- Cohort GCF interpretation: `docs/SOPs/SOP-17_CrossStrain_GCF_Cohort.md`
- GToTree, MLSA, ANI, and IQ-TREE: `docs/phylogenomics.md`
- Optional tool detection and installation: `docs/companion_tools.md`

Older cohort-specific notes and versioned addenda are historical evidence only. If an old example
conflicts with this protocol, this protocol wins and the conflict must be reported for repair.
