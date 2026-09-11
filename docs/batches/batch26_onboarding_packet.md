# Onboarding Packet
**What you need to know in your first week with Sapote–Mamey**

**v9.7.149a** | Last updated: 2026-06-29

---

## Welcome

You've joined a project using Sapote–Mamey — a two-layer genome-mining pipeline for actinomycete natural-product discovery. This packet gets you from zero to your first real strain analysis in one week.

Don't try to read everything at once. Follow the reading order below. The pipeline rewards incremental understanding — you can produce useful results on day one with minimal background.

---

## What the pipeline does (30-second version)

1. You give it an antiSMASH output ZIP (DNA sequence → gene clusters already detected)
2. Mamey (Python) extracts, scores, and ranks all the gene clusters
3. You (or Claude) write detailed interpretations of the best ones
4. Result: a ranked list of the most interesting potential natural products, with evidence-grounded analysis of each

---

## Week 1 reading order

### Day 1 (30 min): Get running

1. `batch03_new_user_5min_runbook.md` — Get Mamey installed and running on a test genome
2. Run `python -m mamey doctor` — confirm your environment is set up
3. Run `python -m mamey run` on any antiSMASH ZIP — see what output looks like

### Day 2 (1 hour): Understand the output

1. `batch08_workflow_accessibility_rewrite.md` — The full pipeline in plain English (Sections 1–4)
2. Open the triage board CSV (`[strain]_4_triage_board.csv`) in Excel — explore the columns
3. Open the workbook (`[strain]_5_workbook.xlsx`) — explore the E1_BGC_Summary sheet

### Day 3 (1 hour): Understand the concepts

1. `batch07_glossary_plain_language_pass.md` — KCB, CCTT, UMED, CGAD, assembly tier at 3 levels
2. `batch20_claim_safety_field_manual.md` — The claim-safety rules (important: know these before writing anything)
3. Key rule to internalize: "biosynthetic capacity consistent with [class]" — never "produces [compound]"

### Day 4 (2 hours): Write your first Mode B card

1. Pick a top BGC from your triage board
2. Read `batch10_modeb_output_contract_plain_english.md`
3. Paste the BGC data into Claude: triage board row + workbook row + locus map image
4. Ask Claude: "Please write §1–§8 Mode B for this cluster"
5. Review the output against the floors in `batch16_modeb_interpretive_floor.md`

### Day 5 (1 hour): Learn what can go wrong

1. `batch04_gotcha_guide.md` — Skim the error lookup table; know where to come when things break
2. `batch23_common_mistakes_extended.md` — Read mistakes 1, 6, and the bonus (sealing packages)
3. Ask any question you have about the output you've produced

---

## Key vocabulary to know before your first meeting

| Term | Plain English |
|------|--------------|
| **BGC** | Biosynthetic gene cluster — a block of DNA encoding one chemical-making pathway |
| **antiSMASH** | The web tool that finds BGCs in a genome. Input: genome FASTA. Output: ZIP file. |
| **Mamey** | The Python engine that processes the antiSMASH ZIP and produces scores/ranks |
| **Sapote** | The LLM interpretation layer — where Claude writes the detailed analysis |
| **KCB** | Known Cluster Blast — how similar a cluster is to known compounds (similarity, NOT identity) |
| **Mode B** | The detailed written analysis of one BGC (8–20 sections, ~2 pages) |
| **Triage board** | The ranked list of all BGCs (sorted by antibacterial or antifungal score) |
| **Corrected BGC count** | Interior × 1 + Edge × 0.5 + Full-contig × 0.25 — accounts for assembly fragmentation |
| **Assembly tier** | GOOD (≥70% interior) / MODERATE / POOR / VERY_POOR — quality of the genome assembly |
| **Extract-level bioactivity** | Default assumption: all strains assumed active against MRSA + *Candida* at extract level |

---

## Key rules to know before writing anything

These five rules underpin everything:

1. **Capacity, not production.** "Biosynthetic capacity consistent with X" — never "produces X." KCB = similarity, never identity.

2. **No negative activity claims.** Never call a strain "antifungal-negative" or "antibacterial-negative." Absent data ≠ absent activity.

3. **BGC locator mandatory.** Every BGC in every document must carry its contig and region: `BGC007 (NODE_1_length_406707 · region001)`.

4. **Standing exclusions.** NAPAA, hglE-KS-PREV-001, and saccharide BGCs are excluded from cross-strain comparisons. (You'll encounter these when you read multi-strain reports.)

5. **AS strains are private.** Any data from AS-prefixed strains requires PI clearance before public use or external sharing.

---

## Tools you'll use most

| Command | When |
|---------|------|
| `python -m mamey doctor` | First thing in any session — confirms your environment |
| `python -m mamey run ...` | Running the extraction engine on a new strain |
| `python -m mamey validate package/` | After a run — confirms the output is complete |
| `python -m mamey list-bgcs package/ --top 5` | Quick look at the top BGCs |
| `python -m mamey explain package/` | Narrative overview of what's in a package |
| `python -m mamey inspect antismash.zip` | Before running — checks the input ZIP |

---

## Common first questions

**Q: What's an antiSMASH ZIP and where do I get one?**
A: Run your genome through antiSMASH at [antismash.secondarymetabolites.org](https://antismash.secondarymetabolites.org), then download "All Files." That's your input.

**Q: How do I know if my run worked?**
A: Look for `✓ MAMEY_COMPLETE` in the output. Then run `mamey validate` to confirm the package is complete.

**Q: What does "MAMEY_COMPLETE_WITH_ISSUES" mean?**
A: You got results, but something was imperfect. Check `issue_log.md` in the package. Usually minor; your analysis can proceed.

**Q: Do I need Claude to use Mamey?**
A: No. Mamey runs completely without Claude. Claude (Sapote layer) is for writing the Mode B interpretations afterward — you can also write those yourself if you have the domain expertise.

**Q: What's the difference between a BGC and a compound?**
A: A BGC is the DNA sequence encoding the machinery to potentially make a compound. The compound is the actual molecule. Mamey tells you about BGCs; what compound (if any) gets made requires wet-lab work to confirm.

**Q: Can I run multiple strains at once?**
A: Yes, but limit to 2–3 per session to avoid timeouts (especially in ChatGPT). Claude can handle more.

---

## Your PI and project context

- **Lab:** 
- **PI:** the Developer or User
- **Project focus:** Natural product discovery from bee, wasp, moss, and attine ant-associated actinomycetes; primary targets MRSA and *Candida*
- **Your strains:** AS-prefix strains are private to the lab; SID-prefix strains are from published datasets (Chevrette et al. 2019 insect-microbiome cohort)

For questions about specific strains, BGC findings, or access to private data: ask the PI or senior lab members.

---

## Where to get help

| Situation | Go to |
|-----------|-------|
| Something broke | `batch04_gotcha_guide.md` |
| Need to find a specific tool | `batch01_tools_discoverability_map.md` |
| Need to find a specific doc | `batch06_doc_navigation_guide.md` |
| Confused about a concept | `batch07_glossary_plain_language_pass.md` |
| Writing Mode B and unsure | `batch10_modeb_output_contract_plain_english.md` + `batch16_modeb_interpretive_floor.md` |
| Command not working | `batch04_gotcha_guide.md` § quick-reference error table |

---

## See also

- **5-minute runbook:** `batch03_new_user_5min_runbook.md`
- **Workflow guide:** `batch08_workflow_accessibility_rewrite.md`
- **Full reference manual:** `docs/GUIDE/01_User_Manual.md`
- **Session start protocol:** `batch26_session_handoff_protocol.md`
