# Common Failure Recovery Matrix
**Error message → Root cause → Fix (quick lookup)**

**v9.7.149a** | Last updated: 2026-06-29

> **Currency note (v9.7.409):** the recovery commands below have been updated from `--mode smoke` to
> `--mode gold`. `smoke` was removed at v9.7.161 — `mamey run` accepts only `{standard,gold}` and now
> rejects `smoke` with an argparse `invalid choice` error. Gold is the only analysis mode.

---

## Matrix: Error → Cause → Fix

| Error Message | Root Cause | Fix | Time |
|---------------|-----------|-----|------|
| `mamey: command not found` | Mamey not in PATH | `pip install -e . --break-system-packages` in bundle dir | 1 min |
| `ModuleNotFoundError: ijson` | Dependencies not installed | `pip install openpyxl reportlab ijson --break-system-packages` | 1 min |
| `Python 3.9 not supported` | Python too old | Install Python 3.10+: `brew install python@3.11` (macOS) or apt install python3.11 (Linux) | 5 min |
| `antiSMASH ZIP not found` | File path wrong | Use full path: `python -m mamey run ... --input-zip /full/path/antismash.zip` | 1 min |
| `VALIDATION_FAIL` (after Mamey run) | Corrupted or incomplete antiSMASH ZIP | Re-run antiSMASH at web server. Download full ZIP. Re-run Mamey. | 10 min |
| `No region GBK files found` | antiSMASH ZIP is malformed | Check ZIP structure: `unzip -l antismash.zip` should show `regions/`, `json/` folders | 2 min |
| All KCB scores are 0 | Registry not loaded (registry_detector failed) | Run: `python tools/render_bootstrap_contract.py` to regenerate bootstrap | 2 min |
| Assembly tier: VERY_POOR | Genome is fragmented (<20% interior) | Continue normally; add caveat: "Assembly fragmentation limits BGC boundary confidence" | 0 min |
| [HALLUCINATION TRAP] in Mode B | LLM made an over-confident claim | Rewrite claim to match evidence scope. E.g., "produces X" → "biosynthetic capacity consistent with X-class" | 2 min |
| Mode B card incomplete (stops at §8) | LLM timed out mid-response | Continue in new chat with remaining BGCs. Split batches into groups of 3. | 1 min |
| "Tier parity failure" (after release cut) | Tiers fell out of sync during cut | Delete old tier ZIPs. Run `bash tools/release.sh` to re-cut all tiers. Verify with `check_tier_parity.py`. | 5 min |
| SHA256SUMS don't match | ZIP corrupted during download | Re-download the file. Re-compute checksums. | 5 min |
| "Private data in public tier" detected | AS strains included in public release | Run `redact_public_tier.py` before cut. Re-run `make_public_tier.sh`. | 3 min |
| Workbook missing columns | Schema version mismatch | Run `schema_deployed_audit.py` to identify missing columns. Re-run `build_workbook.py` to regenerate. | 5 min |
| "Key collision" during merge | Two strains have same BGC ID | Rename one BGC_ID manually (e.g., BGC_00001 → BGC_00001_alt). Re-merge. | 2 min |
| Figure generation fails silently | matplotlib not installed (optional) | `pip install matplotlib numpy --break-system-packages`. Retry `build_figures.py`. | 2 min |
| `figure_ready/` directory is empty | Export not run | Run: `export_figure_ready.py --workbook workbook.xlsx --outdir figure_ready/` | 1 min |
| ChatGPT timeout mid-Mode B | Session context too large | Reduce batch size. Hand only 3 BGCs at a time instead of 10. | 0 min (next run) |
| "No Python execution available" in ChatGPT | Text-only session (no code interpreter) | Switch to Claude, or run Mamey locally then hand results to text-only ChatGPT for interpretation. | 0 min |
| Claude context window full mid-response | Batch too large for one session | Split into smaller batches (5 BGCs per session). Continue in next session. | 0 min |
| Mode B has wrong BGC ID in header | Mismatch between LLM data and package | Run: `locator_reconciliation.py --card mode_b.md --package package/`. Edit header to match. | 2 min |
| Evidence conservation audit fails | Fields dropped between source and package | Run `evidence_conservation_audit.py`. Check `issue_log.md` for missing fields. Re-run Mamey if critical. | 5 min |
| "Cannot compare fragments across assembly tiers" | Mixing GOOD and POOR assemblies in cohort | Run `build_normalization_matrix.py` to produce assembly-adjusted counts. Use corrected counts for claims. | 3 min |
| Checksum doesn't match after recompute | Legitimate file difference (not corruption) | If file contents match (`diff -q old new`), checksum difference is OK (may be timestamp). | 1 min |

## Quick triage

**Run failed before MAMEY_COMPLETE?** → Check Sections A (install) or B (antiSMASH input).
**Got MAMEY_COMPLETE but output looks wrong?** → Check `issue_log.md` first, then Section C (registry) or D (assembly).
**ChatGPT/Claude issue?** → Section I.
**Release/tier issue?** → Section F.
**Everything else?** → Search by error message in the matrix table above.

---

## Section A: Installation & Dependency Errors

### Error: "mamey: command not found"

```bash
# Check if Mamey is installed
python -c "import mamey; print(mamey.__version__)"

# If import fails, install:
cd sapote-mamey-v9_7_149
pip install -e . --break-system-packages

# Verify:
python -m mamey doctor
```

---

### Error: "ModuleNotFoundError: No module named 'openpyxl'"

```bash
# Direct install
pip install openpyxl reportlab ijson --break-system-packages

# Verify
python -c "import openpyxl, reportlab, ijson; print('✓ All installed')"
```

---

### Error: "Python 3.9 is not supported. Requires 3.10+"

```bash
# Check your Python version
python --version

# If 3.9 or older, upgrade:
# macOS: brew install python@3.11
# Linux: sudo apt install python3.11 (Ubuntu) or yum install python3.11 (RHEL)
# Windows: Download from python.org

# Then use python3.11 explicitly:
python3.11 -m mamey doctor
python3.11 -m mamey run --strain test --input-zip antismash.zip --mode gold
```

---

## Section B: Input & Format Errors

### Error: "antiSMASH ZIP does not exist"

```bash
# Check file path
ls -la antismash.zip
# If not found, download from antiSMASH web server

# Or use full path:
python -m mamey run \
  --strain test \
  --input-zip /data/mamey-local/Downloads/antismash.zip \
  --mode gold
```

---

### Error: "No region GBK files found" or "antiSMASH version not detected"

```bash
# Check ZIP structure
unzip -l antismash.zip | head -20

# Should show:
# antismash_output/
# antismash_output/antismash.json
# antismash_output/regions/region001.gbk
# antismash_output/regions/region002.gbk
# ... (many more regions)

# If this structure is missing, re-run antiSMASH:
# 1. Go to antiSMASH.secondarymetabolites.org
# 2. Upload your genome (FASTA)
# 3. Download "All Files" ZIP (not partial)
```

---

## Section C: Registry & Bootstrap Errors

### Error: "All KCB scores are 0" or "Unknown BGC" in output

```bash
# Check registry detector status
python -m mamey doctor
# Look for: registry_detector✓ (good) or registry_detector— (problem)

# If it says "fallback", regenerate bootstrap:
python tools/render_bootstrap_contract.py

# Then re-run Mamey
python -m mamey run --strain test --input-zip antismash.zip --mode gold
```

---

## Section D: Assembly & Quality Errors

### Warning: "Assembly tier: POOR (40% interior)"

This is **not a failure**—it's a metadata warning. Continue:

```bash
# The package is still valid
python -m mamey validate package
# ✓ Package is valid

# Just add a caveat in Mode B:
# "Given POOR assembly tier (40% interior), edge BGCs may be incomplete.
#  Comparative claims based on interior BGCs only."
```

---

## Section E: Mode B & Interpretation Errors

### Error: "[HALLUCINATION TRAP] in Mode B §2"

```
Detected error:
"This BGC produces natamycin (KCB hit is 45% similar)"

Fix:
Rewrite to: "Biosynthetic capacity consistent with natamycin-class polyenes.
KCB similarity is 45% (moderate); actual compound may differ."
```

---

### Mode B stops mid-card (incomplete §1–§8)

```bash
# Claude/ChatGPT timed out
# Solution: Continue in new chat session

# For next batch:
# → Hand only 3 clusters at a time (not 10)
# → Or reduce context by summarizing data

# Don't discard the partial work; copy it to a document and continue
```

---

## Section F: Release & Deployment Errors

### Error: "Tier parity check failed"

```bash
# All tiers out of sync
python tools/check_tier_parity.py
# Reports: CODE has 5 files, SID-public has 6

# Fix: Re-cut from scratch
rm sapote-mamey-*.zip  # Remove old tier ZIPs
bash tools/release.sh  # Full release pipeline
python tools/check_tier_parity.py  # Verify
# ✓ All tiers in sync
```

---

### Error: "Private data detected in public tier"

```bash
# Before cutting tiers, anonymize:
python tools/redact_public_tier.py \
  --workbook merged_workbook.xlsx \
  --spec redaction.json \
  --output public_workbook.xlsx

# Then cut tiers:
bash tools/make_public_tier.sh

# Verify no leaks:
python tools/audit_public_cut.py --workbook SID-public/workbook.xlsx
```

---

### Error: "SHA256SUMS don't match"

```bash
# File may be corrupted
# Re-download the ZIP file
# Recompute checksums:
sha256sum -c SHA256SUMS.txt

# If still fails, the release copy may be corrupted
# Contact distributor for a fresh download
```

---

## Section G: Data & Merge Errors

### Error: "Workbook missing columns"

```bash
# Check schema
python tools/schema_deployed_audit.py --workbook workbook.xlsx

# It will list missing columns and their sources

# Fix: Re-run workbook build (regenerates all columns)
python tools/build_workbook.py \
  --package-dir runs/strain/package \
  --outdir results
```

---

### Error: "Key collision during merge" (BGC_00001 appears twice)

```bash
# Two strains have same BGC ID
# Fix manually:

# 1. Open the workbook
# 2. Find the duplicate BGC_ID row in strain_B
# 3. Rename it: BGC_00001 → BGC_00001_B or BGC_00001_alt
# 4. Save workbook
# 5. Re-run merge: python tools/hub_merge.py ...
```

---

## Section H: Figure Generation Errors

### Error: "Figures won't render" or matplotlib errors

```bash
# Install optional dependencies
pip install matplotlib numpy --break-system-packages

# Retry figure generation
python tools/build_figures.py --package package/ --outdir figures/
```

---

### Error: "figure_ready/ directory is empty"

```bash
# Data export step was skipped
python tools/export_figure_ready.py \
  --workbook workbook.xlsx \
  --outdir figure_ready/

# Then build figures:
python tools/build_figures.py --csv-dir figure_ready/ --outdir figures/
```

---

## Section I: LLM (ChatGPT/Claude) Errors

### Error: ChatGPT timeout mid-Mode B

```
Symptom: Output cuts off after 1–2 BGCs instead of all 10

Fix (immediate): Save what you got. Start new ChatGPT session with remaining BGCs.

Fix (preventive): Next time, hand only 3 BGCs per session instead of 10.
This gives LLM more time per BGC (fewer timeouts).
```

---

### Error: "No Python execution available" in ChatGPT

```
This means: Text-only ChatGPT session (no code interpreter enabled)

Note: Claude in claude.ai always has code execution available.
      ChatGPT requires ChatGPT Plus/Pro with the code interpreter tool active.

Options:
1. Switch to Claude (code execution always available in claude.ai)
2. Enable code interpreter in ChatGPT (requires Plus/Pro plan)
3. Run Mamey locally yourself, then hand CSV/JSON output to either LLM
   for Mode B interpretation — no Python needed in the LLM session for that step
```

---

### Error: Claude context window fills up mid-session

```
Symptom: Claude cuts off mid-Mode B, or warns context is full

Cause: Large batches of BGC data + prior conversation history exceed the window

Fix: 
• Split into smaller batches — 3–5 BGCs per session instead of 10–20
• Start a new session for the next batch, paste only the relevant data
• Use mamey list-bgcs --json to get compact structured output instead of
  pasting full CSV rows
```

---

### Error: ChatGPT produces wrong BGC IDs or invented data

```
Symptom: Mode B card has BGC IDs, gene names, or scores that don't match
         your actual Mamey output

Cause: ChatGPT generated data from its training rather than your package

Fix:
• Always paste the actual triage board row and workbook data into the prompt
• Do not ask ChatGPT to "estimate" or "suggest" scores — only use real Mamey output
• Run locator_reconciliation.py to verify header fields match the package
```

---

## Diagnosis Flowchart (Text)

```
Something's wrong with my run.
↓
Is it a Mamey run error, a Mode B writing error, or a data error?
├─ Mamey error? → Search "Installation & Dependency Errors" (Section A)
├─ antiSMASH error? → Search "Input & Format Errors" (Section B)
├─ All scores 0? → Search "Registry & Bootstrap Errors" (Section C)
├─ Assembly warning? → Search "Assembly & Quality Errors" (Section D)
├─ Mode B weird claim? → Search "Mode B & Interpretation Errors" (Section E)
├─ Release broken? → Search "Release & Deployment Errors" (Section F)
├─ Data/merge broken? → Search "Data & Merge Errors" (Section G)
├─ Figures broken? → Search "Figure Generation Errors" (Section H)
├─ ChatGPT/Claude broken? → Search "LLM Errors" (Section I)
└─ Still stuck? → Check batch04_gotcha_guide.md for more detailed diagnosis
```

---

## Pro tips

1. **Before you start, install everything:**
   ```bash
   pip install openpyxl reportlab ijson matplotlib numpy --break-system-packages
   ```

2. **After each step, validate:**
   ```bash
   python -m mamey doctor
   python -m mamey validate package
   python -m mamey list-bgcs package
   ```

3. **Keep issue_log.md handy:**
   - Mamey writes it after every run
   - It often tells you exactly what's wrong and how to fix it

4. **When in doubt, re-run:**
   - Mamey is deterministic (safe to re-run)
   - Re-running often clears transient issues

5. **Use staged workflow:**
   - doctor → inspect → run (smoke) → validate → list-bgcs → run (standard)
   - Each step gates the next; catches errors early

