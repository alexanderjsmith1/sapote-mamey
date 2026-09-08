# Sapote-Mamey Workflow Guide
**Version:** v9.4

---

## Two execution paths

| Path | When to use | Where documented |
|---|---|---|
| **Python CLI (recommended)** | You have Python installed locally; processing any number of strains | This guide + README quickstart |
| **ChatGPT standalone** | No local Python; ChatGPT-only environment | `docs/standalone/` |

**The Python CLI has no session-size limit and requires no API access.** If you can run `python mamey_run.py --help`, use this path.

---

## Path 1 — Python CLI (primary, recommended)

### Architecture

The pipeline has three tiers:

| Tier | Where it runs | What it needs | What it produces |
|---|---|---|---|
| **Mamey** (Tier 1) | Your machine (Python CLI) | antiSMASH output ZIPs | Sealed JSON/CSV packages per strain |
| **Sapote-slim** (Tier 2) | Claude (Project) | Mamey packages | Scored workbook, triage, hallucination flags |
| **Sapote full** (Tier 3) | Claude (Project) | Tier 1+2 outputs | Mode B reports, ecology, cross-strain synthesis |

### Step 1 — Run antiSMASH on your genomes

Standard antiSMASH v8+ run. Keep the output ZIP for each strain. No parameter changes needed.

### Step 2 — Run Mamey locally

```bash
# Single strain
python mamey_run.py run \
  --strain AS-XXX \
  --input-zip AS-XXX_antismash.zip \
  --taxonomy "Streptomyces sp." \
  --source "bee-associated" \
  --mode gold

# Batch (up to 3 per call)
python mamey_run.py run \
  --strains AS-XXX.zip AS-XXX.zip AS-XXX.zip \
  --master project_master.xlsx \
  --taxonomy "Streptomyces sp.|Streptomyces sp.|Streptomyces sp." \
  --source "bee-associated|soil|soil" \
  --mode gold
```

Process completes in seconds to minutes depending on genome size. No session limit.

### Step 3 — Validate

```bash
python mamey_run.py validate runs/AS-XXX/package
```

Expect `MAMEY_COMPLETE`. If any scan shows `FAIL`, check `issue_log.md` in the package.

### Step 4 — Upload to Claude (Sapote)

Upload `manifest.json` (the authoritative handoff object) from the package directory to your Claude Project that has `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md` loaded.

Claude does not need the original antiSMASH ZIP — only the Mamey package.

### Step 5 — Request full analysis

```
Run sapote_standard on AS-XXX. Mamey package: AS-XXX_manifest.json.
```

Or with the full-delivery profile:

```
Load Mamey output for AS-XXX. Run full project-wide delivery.
```

---

## Path 2 — ChatGPT standalone

For users without a local Python environment. ChatGPT executes the Mamey Python code directly inside the session. See `docs/standalone/` for the full ChatGPT-specific guides, including:

- `docs/standalone/MAMEY_STANDALONE_CHATGPT_README.md` — what works and what is limited
- `docs/standalone/RUN_MAMEY_IN_CHATGPT.md` — step-by-step execution guide
- `docs/standalone/CHATGPT_BATCH_PROTOCOL.md` — batching protocol (4–6 strains per session)

**Key constraint:** ChatGPT can process approximately 4–6 antiSMASH ZIPs per session due to context window limits. Save the checkpoint CSV and per-strain packages before ending each session.

---

## Status meanings

| Status | Meaning | Action |
|---|---|---|
| `MAMEY_COMPLETE` | All scans finished. Ready for Claude. | Upload to Claude. |
| `MAMEY_DEFERRED` | Not yet processed (ChatGPT session budget). | Upload in next session. |
| `MAMEY_FAILED` | A scan failed. See `notes`. | Fix and re-upload this strain only. |
| `MAMEY_SKIPPED` | Excluded by user instruction. | No action. |

**Legacy note:** Packages from before v1.9.7 may show `PASS_EXTRACTION_JUDGMENT_PENDING`. Treat as `MAMEY_COMPLETE`.

---

## What never needs to be re-uploaded

Once a strain has `MAMEY_COMPLETE` status and its package is saved locally, the original antiSMASH ZIP is never needed again. The sealed package contains everything Claude needs for all downstream analysis.

---

## Frequently asked questions

**Q: Can I start Claude analysis before all strains are processed?**
A: Yes. Claude accumulates strains into the master workbook incrementally.

**Q: My ChatGPT session ran out of context mid-batch. Is the work lost?**
A: Only if you did not save the checkpoint CSV. Re-upload only deferred/failed strains.

**Q: How do I check RGGMCI is complete?**
A: Run `mamey_run.py validate` and check `rggmci_pairs_total > 0`.

---

*· 2026*
*github.com/alexanderjsmith1/sapote-mamey*
