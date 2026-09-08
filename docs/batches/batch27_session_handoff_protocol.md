# Session Start and Handoff Protocol
**How to start, run, and close a Sapote–Mamey session properly**

**v9.7.149a** | Source: `SESSION_START_MANIFEST.md`, `docs/CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md` | Last updated: 2026-06-29

---

## Why this matters

Analysis work is lost in two ways: the session ends without committing Mode B cards to the judgment store, or a new session starts without checking what was done before. Both are preventable. This protocol covers both ends.

---

## Session start ritual (CDSW protocol)

At the start of every session:

**Step 1: Search past conversation history**

```
Search for: [strain ID or project context]
```

Use `conversation_search` or `recent_chats` to find prior context. Never restart from scratch if there's prior work. Acknowledge what was found before proceeding.

**Step 2: Read the session manifest**

Read `SESSION_START_MANIFEST.md` at the bundle root — it's the command menu and tells you what the bundle can do in this session.

**Step 3: State the context explicitly**

Before any task, state:
- Which strain(s) are in scope
- What was completed in prior sessions (from search results or user statement)
- What the starting point is now

**Step 4: Offer next paths**

Present 3–6 genuinely different next directions as a plain-text numbered list. Never tappable widgets. Paths should be specific to the current state (strain IDs, BGC IDs, package status, named deliverable) — not generic options.

---

## Mamey staging workflow (use this order)

For every strain, run in this order. Skip-ahead causes issues:

```bash
# 1. Preflight
python -m mamey doctor

# 2. Inspect input
python -m mamey inspect <antismash.zip>

# 3. Capped-session gold run (gold is the only analysis mode; use this first)
python -m mamey run \
  --strain <ID> \
  --display '<Genus species strain ID>' \
  --input-zip <antismash.zip> \
  --outdir runs_<date> \
  --mode gold \
  --release <PUBLIC|PRIVATE> \
  --capped-session --json-evidence off \
  --master runs_<date>/Mamey_Master.xlsx

# 4. Validate
python -m mamey validate runs_<date>/<ID>/package

# 5. List top leads
python -m mamey list-bgcs runs_<date>/<ID>/package --axis ab --top 10
python -m mamey list-bgcs runs_<date>/<ID>/package --axis af --top 10

# 6. Explain (narrative overview)
python -m mamey explain runs_<date>/<ID>/package

# 7. Mode B (deep analysis — after validation)
python -m mamey mode-b --package runs_<date>/<ID>/package --top-n <N> --outdir mode_b/

# 8. Render figures
python -m mamey render-figures --package runs_<date>/<ID>/package

# 9. Ingest Mode B receipts (commit to durable store)
python -m mamey ingest-receipts \
  --package runs_<date>/<ID>/package \
  --receipt mode_b_receipt.json \
  --master runs_<date>/Mamey_Master.xlsx
```

**v9.7.374 correction:** there is no "smoke" mode to deepen from — `--mode smoke` was removed at
v9.7.161 and the capped-session run above already runs gold (the only analysis mode) directly.

---

## The judgment store — why it matters

Mode B cards that live only in a chat window are lost when the session ends.

The judgment store is the durable per-BGC record inside the package. A card is not part of the permanent analysis record until it's been ingested:

```bash
python -m mamey ingest-receipts \
  --package runs/[strain]/package \
  --receipt mode_b_receipt.json \
  --master project_master.xlsx
```

This command:
- Writes each Mode B card as a `.md` file in the judgment store
- Flips the register entry to COMPLETE
- Reconciles the workbook's `E1_Mode_B_Index` from the register

It is **fail-closed** (unknown BGC IDs are skipped, never invented) and **idempotent** (safe to run multiple times).

**This is the single most common way analysis work goes missing: cards written but never ingested.**

---

## Mode B receipt format

The receipt is a JSON file with this structure:

```json
{
  "strain_id": "AS-XXX",
  "session_id": "2026-06-29_session_01",
  "cards": [
    {
      "bgc_id": "BGC_0012",
      "mode_b_md": "# Mode B Card\n\n## §1 — Cluster identification\n...",
      "layperson_paragraph": "Optional plain-language summary...",
      "fermentation_note": "Optional wet-lab note..."
    }
  ]
}
```

Save this file at the end of every Mode B session. Paste back into Claude with the `ingest-receipts` command.

---

## Post-MAMEY_COMPLETE handback (mandatory)

When a package status is `MAMEY_COMPLETE` or `MAMEY_COMPLETE_WITH_ISSUES`, always present these outputs first:

- `OPEN_ME_FIRST.html` (entry point)
- `manifest.json`
- `[strain]_8_strain_brief.pdf`
- `_8a…_8m_fig_*.png` plus companion `_data.csv` files
- `locus_maps/` directory
- `[strain]_5_workbook.xlsx`
- `checksums_sha256.txt`
- `issue_log.md`

A handback without this block is incomplete. Never stop at status.

---

## Session close protocol

Before ending a session:

1. **Check judgment store:** Are all Mode B cards from this session ingested? If not, run `ingest-receipts`.

2. **Check handoff triggers:** Does a ChatGPT task brief need to be produced? (See trigger conditions in `batch25_claude_chatgpt_handoff_protocol.md`)

3. **Offer CDSW next paths:** 3–6 genuinely different directions, plain-text numbered list, grounded in current state.

4. **State what was completed:** "This session completed: [list]. Remaining: [list]. Recommended first step next session: [specific]."

---

## ChatGPT-specific: the 8-path rule

Every ChatGPT handback must include exactly 8 unique next paths. This is stricter than the Claude/Sapote 3–6 range because ChatGPT-tier runners historically under-fill this closer.

Standing first path when any BGC still lacks full §1–§20 Mode B:
> 1. Continue deeper Mode B: run next batch (BGC[list]) to full §1–§20

Paths must span different action types when possible:
- Continue/run deeper
- Deepen one lead
- Compare/cross-strain
- Make figures
- Package/merge
- Patch/debug
- Literature/wet-lab
- Documentation/release

---

## PRIVATE-LARGE-STRAIN timeout guard

> **v9.7.374 correction:** the smoke-first gate described below was removed at **v9.7.160** —
> `cli.py:3037`'s own comment records it: "capped sessions run gold DIRECTLY (the old forced
> smoke-first FATAL is gone)." There is no `--chatgpt-followup`-gated smoke-then-gold sequence to
> follow any more; `--capped-session`/`--chatgpt-followup` are aliases of `--capped-session`/
> `--capped-followup` (`cli.py:4292-4300`) that only cap wall-clock/output budget, not analysis
> depth. See `SESSION_START_MANIFEST.md`'s "capped ChatGPT/Claude sessions" line for the current
> authoritative first-run command.

In a capped ChatGPT/Claude session, run gold directly with `--capped-session --json-evidence off`
(gold is the only analysis mode, so there is nothing to "graduate" to).

This prevents the large-strain timeout failure where a gold run starts before ChatGPT's specific workflow has been re-read.

---

## Stateful session management

Claude has no memory between completions. All relevant state must be supplied in each request:

```
When starting Mode B batch N (where N > 1):
- Tell Claude: "This is batch N of X. Previous batches covered BGC_0001 through BGC_0010. 
  Here is the triage board for remaining clusters: [paste]"
- Paste the relevant manifest/triage data
- Don't assume Claude remembers the previous batch
```

For long multi-session analyses, maintain a `SESSION_LOG.md` in the package noting what was covered in each session. Paste the relevant section at session start.

---

## Quick reference: important session commands

| Command | When |
|---------|------|
| `mamey doctor` | Every session start |
| `mamey inspect <zip>` | Before every new strain run |
| `mamey run --mode gold --capped-session` | First run per strain (gold is the only analysis mode) |
| `mamey validate package/` | After every run |
| `mamey explain package/` | When unsure what a package contains |
| `mamey list-bgcs package/ --top 10` | Triage start |
| `mamey ingest-receipts` | After every Mode B session |
| `mamey render-figures package/` | When figures failed or weren't rendered |

---

## See also

- **Session manifest:** `SESSION_START_MANIFEST.md` (command menu)
- **Handoff protocol:** `batch25_claude_chatgpt_handoff_protocol.md`
- **Post-MAMEY handback rule:** `SESSION_START_MANIFEST.md` § 0.6
- **Gotcha guide:** `batch04_gotcha_guide.md` (when something breaks)
- **Common mistakes:** `batch23_common_mistakes_extended.md` (bonus mistake: not sealing packages)
