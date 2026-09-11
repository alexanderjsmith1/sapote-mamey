# MODE_B_BATCH_RUN — full §1–§10 Mode B in rank-ordered batches (v9.7.112)

## Why batches

A full strain analysis is large: AS-NNN has 64 BGCs, and a full §1–§10 card runs 9k+ chars for a
HIGH-priority cluster — so all-of-AS-NNN is ~640 sections and 2+ hours of generation. That does not
fit one session. The run is **batched**, and batches are **rank-ordered**: the highest-priority BGCs
are analyzed first, so a token-limited session completes the most valuable cards before it stops.

## Run shape

1. **Mamey seal** — run the deterministic engine; produce the sealed package (triage board, RG-GMCI
   pairs, gene context, RGGMCI_HOWTO in START_HERE.md).
2. **Rank order** — take the triage-board rank (1 = highest priority). Assign BGCs to batches in rank
   order: ranks 1..N → batch 1, N+1..2N → batch 2, … Default batch size **N = 8** (parameter — drop
   to 4–6 per session at this depth if a batch is too heavy; nothing hardcodes 8).
3. **Mode B per BGC** — write the full §1–§10 card (see MODE_B_WRITE.md), then call
   `record_mode_b(..., rank=<triage rank>)`. The write-time gate stamps the quality verdict
   (FULL / SHALLOW / STUB + missing sections) into the register. A card that stops short of §9/§10,
   or falls below the priority char floor (HIGH 9k / MID 8k / LOW 6k), is recorded **SHALLOW** — it
   does not silently pass as done.
4. **Per-batch checkpoint** — after each batch, `batch_status(package_dir, ranked_bgc_ids)` prints
   e.g. `AS-NNN: 64 BGCs | 16 FULL / 2 SHALLOW / 0 STUB / 46 not-started`. Re-do any SHALLOW card in
   the same batch before moving on.
5. **Resume (CDSW)** — a new session calls `batch_status` first; the rank-ordered `per_bgc` list shows
   exactly which ranks are done and which is next. No re-explaining needed.
6. **Compile gate** — the compiled master PDF should only build when `compile_ready(package_dir,
   ranked_bgc_ids)` returns True (every BGC FULL §1–§10). A partial run cannot masquerade as a
   finished strain.

## Helpers (mamey.judgment_store)

- `record_mode_b(package_dir, bgc_id, mode_b_md, ..., rank=<int>)` — write a card; returns
  `{"path", "verdict"}`. The verdict tells you immediately if the card is FULL or stopped short.
- `batch_status(package_dir, ranked_bgc_ids)` — rank-ordered progress (counts + per-BGC state).
- `incomplete_cards(package_dir)` — every recorded card that is not FULL (to re-do).
- `compile_ready(package_dir, ranked_bgc_ids)` — `(ok, reason)` compile gate.

## Token-budget discipline

Because batches are rank-ordered, a run that stops early still delivers the top BGCs complete. Prefer
**finishing fewer cards fully** over starting many cards shallow — a SHALLOW card is recorded as not
done and must be redone, so a half-written card is wasted budget. Concise is good; complete is required.

## Fragments

Single-ORF / full-contig fragments (sub-2k chars) are STUB-exempt from the §9/§10 length requirement —
§10(D) RG-GMCI linkage is their key section. Don't pad a fragment to hit a floor; that violates
evidence-conservation.
