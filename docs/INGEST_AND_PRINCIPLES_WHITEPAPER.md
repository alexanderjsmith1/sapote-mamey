# Ingest, and the principles behind it

**A white paper on how Sapote–Mamey keeps judgment trustworthy**

*Bundle v9.7.319 · engine Mamey 1.9.111 · working draft, natural voice — formality pass pending*

---

## The one-sentence version

**Ingest is the moment a piece of judgment stops being a thing Claude said in a chat and becomes a thing the pipeline can prove it has.** Everything else in this document is the machinery that makes that transition safe.

---

## 1. The problem ingest solves

A Mode B card is an act of judgment. Claude reads the evidence — the gene grid, the KCB anchor, the boundary status — and writes an interpretation. That interpretation is the valuable part of the whole pipeline. Mamey (the engine) produces facts; Sapote (the judgment layer) produces the reading of those facts. The reading is where the science is.

The problem: a reading typed into a chat is **ephemeral and unverifiable**. The chat window scrolls away. A different session has no memory of it. Nobody downstream can point to it and say "this card exists, it covers this BGC, and it passed the structure contract." If the card lives only in chat, then three things are true and all three are bad:

1. It is lost the moment the session ends.
2. There is no record that the BGC was ever judged — so a later session can't tell "done" from "never touched," and silent omissions creep in.
3. There is no gate between "Claude wrote something" and "the pipeline believes it" — so a thin card, a wrong-scaffold card, or a card for a BGC that doesn't exist can slip through on the strength of looking finished.

Ingest exists to make all three false. It is the **front door to the durable judgment store**, and it is a **fail-closed gate** on the way in.

## 2. What ingest actually is

Concretely, `mamey ingest-receipts` (and its single-card sibling `--card`) does four things, in order, and refuses to do the fourth if the first three don't hold:

- **Resolves the BGC** from the card's `<!-- MODE B: <BGC_ID> | strain: ... | session: ... -->` header, falling back to the filename. An unresolvable card is reported `UNRESOLVED_BGC`, not guessed at.
- **Checks the BGC is real** — it must be in the strain's judgment register. An unknown BGC is *skipped and reported*, never invented. (`mode_b_receipt.py`: "an unknown `bgc_id` … is reported and skipped rather than silently invented.")
- **Runs the structure gate** — the card is linted against the canonical §1–§30 contract (`modeb_corrective_full30_v1`) with the BGC's real triage row as context. ERROR-severity findings **refuse the write**.
- **Only then persists**: writes the per-BGC `.md` into the store, flips the register entry, and (with `--master`) reconciles the workbook index.

Two properties make it safe to run without babysitting it:

- **Fail-closed.** The default is refusal. A structurally-invalid card is `SKIPPED_STRUCTURE_INVALID`; an unknown BGC is `SKIPPED_UNKNOWN`; an empty file is `NO_CONTENT`. You have to pass `--force-structure` to override, and the override is recorded.
- **Idempotent.** Re-ingesting the same card is a no-op. `--auto-detect` at session start can safely sweep the whole judgment directory for orphan cards from a prior session without double-counting or clobbering.

That is the whole trick: **the store only ever contains cards that resolved to a real BGC and passed the contract.** The register's completion count is therefore trustworthy by construction — if it says 2/59, then two cards exist, cover real BGCs, and are structurally complete. Nobody has to take Claude's word for it.

## 3. Why ingest is the *authoritative* gate — not `verify-modeb`

This is the principle that bit me in this very session, and it's worth stating plainly because it's counterintuitive.

There are two gates that look like they do the same job. They do not.

- `verify-modeb <card>` is the **authoring aid**. Run it while writing to check structure + depth floors.
- `ingest-receipts` runs the **enforcement gate**. It supplies the BGC's triage context and enforces the *conditional* sections (§21–§27, §29) as ERRORs.

The gap between them is real and documented (v9.7.152). `verify-modeb`, even given `--bgc`, can treat a required conditional section as a WARN. Ingest, using `_bgc_context_from_triage`, enforces it as an ERROR. **A card can pass `verify-modeb` and be refused by ingest.**

That is not a bug to route around — it's the safety margin. `verify-modeb` says "this looks structurally fine." Ingest says "this is actually complete *for this BGC's class and context*, and I will not persist it otherwise." The lesson, which is now my standing loop: **author → ingest → fix what ingest rejects → re-ingest.** Treating `verify-modeb`'s green as final is how you end up with a store full of cards missing the exact sections that matter for that BGC.

## 4. The firebreak lineage: why a *structure* gate on ingest at all

Ingest didn't grow a structure gate for fun. It's a firebreak against a specific, recurring failure (ISSUES §13.1).

A chat's memory of the *old* §1–§20 Mode B scaffold survives even when the current docs are correct. A session that reaches for that scaffold from memory will author twenty-section cards that are silently wrong — missing §28 (provenance ledger), §30 (decision tree), and every conditional section. Doc fixes alone didn't close this: you can't fix a chat's memory by editing a file it won't re-read.

So the fix was structural. The structure gate now validates *every* card against the canonical §1–§30 contract before persistence, through *any* ingest path (`ingest_one_card`, `auto_detect_ingest`, `ingest_receipt`). Legacy-scaffold cards are refused by default. And `emit-modeb-template` pairs with the gate from the other side: it hands you a structurally-valid skeleton, pre-filled with the BGC's real facts, so you author *interpretation* and never author *structure* from memory at all.

This session is a live instance of that firebreak working. I authored BGC011 and it passed `verify-modeb`. Ingest refused it: `MISSING_CONDITIONAL_SECTION §23` — because a MATURATION_GAP was flagged on the lanthipeptide, §23 (Heterologous expression) was required, and I'd dropped it. The gate caught in one command what a careful re-read might have missed. I added §23, re-ingested, RECORDED. That's the firebreak doing exactly its job.

## 5. The principles ingest depends on

Ingest only works because the rest of the pipeline holds itself to a set of standing principles. These aren't decoration — pull any one and ingest's guarantees weaken.

**Verify against the real artifact, not a proxy.** A gate that reads a summary instead of the output file isn't a gate. This session: I read `manifest.json` for the BGC counts, not the run log; I read `AS-XXX_4A2_ClusterBlast_per_gene.csv` for KCB coverage, not the anchor's headline score. Reporting the receipt — 40 interior + 19 edge → corrected 49.5; 1 of 18 hits to the omnipeptin MIBiG entry — beats reporting an adjective like "solid."

**Fail-closed, idempotent, never invent.** The default is refusal; unknowns are skipped and named, not fabricated; re-running is safe. This is what lets `--auto-detect` recover a prior session's orphan cards without fear.

**Order enforcement.** This is the thing code gets for free and prose doesn't (`SAPOTE_WORKFLOW_CONTRACT.md`). A downstream step must not report done while a mandatory upstream step is incomplete. The W0–W10 contract reads the real package artifacts and marks each step PASS/PENDING/BLOCKED with a receipt. Ingest is W4 — it cannot be faked past, because the register it writes is the artifact W7 (compiled report) and W9 (judgment receipt) read.

**Prose-first, and one card before many.** A Mode B card is a written interpretation; tables, FASTAs, char counts, and PDFs are supporting artifacts, not acceptance evidence (the artifact-drift policy). And one BGC must pass the gate before scaling to all of them. I authored BGC018, gated it, ingested it, and *only then* moved to BGC011 — proving the loop on one card of each architecture class before treating the remaining 57 as a batch.

**No silent omission.** Every BGC is accounted for — judged, tiered, or explicitly archived — never quietly dropped. The register makes this auditable: 57 PENDING is a visible fact, not a gap you discover later. Full Analysis Mode is the standing override against "this one didn't seem important, so I skipped it."

**Claim-safety, always.** Capacity, not production: "biosynthetic capacity consistent with," never "produces." KCB and BLASTp are *similarity, not identity*. Bioactivity is *extract-level only* — never pinned to a BGC without fractionation, and no strain is ever called antifungal- or antibacterial-negative. This session gave two clean illustrations: BGC018's omnipeptin anchor is a single-gene coincidental hit (discarded), and BGC011's top KCB hit is yatakemycin — a DNA-alkylator, class-discordant with the lanthipeptide call, so discarded in favor of the same-genus *S. espanaensis* corroboration. A high KCB score is not the compound.

**Provenance banding.** Every claim is tagged observed / computed / inferred / assumed, and every homology statement is banded to its source — store-backed vs. reconstructed vs. corpus. The §28 ledger makes this per-card and explicit. The honest band matters more than the length: this session the package carried a BLASTp *panel*, but it was staged query FASTAs (`MANUAL_BLASTP_OPTIONAL`), not results — so §4 authored from antiSMASH Pfam with an explicit "staged, not run" band, and fabricated zero hits.

**Cite by node·region; reconcile numbering across sources.** Every BGC is cited with its assembly locator, and IDs are reconciled before authoring so collisions surface. This session flagged, up front, that the antiSMASH-8 run yields 59 raw BGCs against the old v7.x run's 34 — a different detection version, so the numbering does not map 1:1 and any cross-reference to old card numbers must be reconciled first.

**Retract cleanly.** When new evidence overturns something you said, retract it in plain language and move on — no dressing it up. This session I flagged the RG-GMCI rescue lines as a possible wrong-contig bug, checked the authoritative CSV, and retracted: the data was correct (proper NODE contigs), the `NZ_CP…` value was a legitimate reference-genome field, and the real issue was a much smaller provenance-clarity nit in one summary line. "I'm retracting X — the artifact shows Y" is a feature, not an embarrassment.

## 6. This session as a worked example

Every principle above earned its place in the last hour of AS-XXX work. The mapping, with receipts:

| Principle | What happened | Receipt |
|---|---|---|
| Verify real artifact | Read manifest, not log, for counts | 59 raw · 40 int / 19 edge · corrected 49.5 · MODERATE (67.8%) |
| Verify real artifact | Read ClusterBlast CSV for KCB coverage | omnipeptin: 1 of 18 hits to MIBiG entry |
| Reconcile numbering | Flagged antiSMASH-version BGC-count shift | 34 (v7.x) → 59 (antiSMASH 8.0.4), no 1:1 map |
| Retract cleanly | Downgraded "wrong-contig bug" to a summary-line nit | `contig_a`/`contig_b` correct in ranked_pairs.csv |
| emit-template first | Every card started from the pre-filled skeleton | 59 templates emitted; conditional sections auto-selected |
| Prose-first, one-before-many | Proved the loop on BGC018 before scaling | gate PASS → RECORDED, then BGC011 |
| ingest > verify-modeb | ingest caught a conditional §verify-modeb missed | BGC011: `MISSING_CONDITIONAL_SECTION §23` |
| Claim-safety (KCB) | Discarded two discordant/coincidental anchors | omnipeptin (single-gene), yatakemycin (class-discordant) |
| Provenance banding | §4 authored from Pfam, panel banded "staged, not run" | zero fabricated BLASTp hits |
| No silent omission | Register shows honest state | 2/59 COMPLETE, 57 PENDING, judgment_status IN_PROGRESS |

## 7. Where ingest sits in the whole set

Ingest is **W4** in the canonical W0–W10 Sapote workflow contract:

- **W0** sealed Mamey package (`mamey validate` → MAMEY_COMPLETE)
- **W1** first-pass scans + triage board
- **W2** lead boards (AB/AF)
- **W3** §1–§30 templates emitted (`emit-modeb-template --batch`)
- **W4** *Mode B cards authored **and** verified* → **this is where ingest persists them, register goes COMPLETE**
- **W5** BGC Guides (conditional)
- **W6** narrative set (Lay Guide / Ecology / Ferm Card)
- **W7** compiled report (`compile-report --strict`, zero open slots)
- **W8** 13-item deliverable suite (`check_deliverable_suite.py`)
- **W9** judgment receipt (manifest no longer `JUDGMENT_PENDING`)
- **W10** session close + exactly-8 next paths

The point of the ordering: W7, W8, and W9 read the register that W4 writes. So a compiled report can't claim completeness the register doesn't back, and the judgment receipt can't flip `JUDGMENT_PENDING` off while cards are still PENDING. **Ingest is load-bearing for every gate downstream of it.** That's why it fails closed.

## 8. What this buys you

The whole apparatus — ingest, the structure gate, the emit-template pairing, the standing principles — exists to make one claim honest: **when the register says a strain's judgment is done, it is actually done, to contract, for every BGC, and you can prove it without re-reading the chat.**

That's the difference between an AI that *helps you write* Mode B cards and a pipeline you can *cite in a methods section*. The first is a convenience. The second is reproducible science — a reviewer can `git checkout` the version, re-run the gates, and get the same answer. Ingest is the hinge the second one turns on.

---

*Grounding: `docs/SAPOTE_WORKFLOW_CONTRACT.md` (W0–W10), `docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md` §13.1 (BGC033 firebreak), `mamey/mode_b_receipt.py` + `mamey/judgment_store.py` (fail-closed/idempotent ingest), `mamey/modeb_structure_gate.py` (§1–§30 gate), `docs/WISE_WORKFLOW_DOCTRINE.md`, `docs/FULL_MODEB_30_SECTION_CONTRACT_v97150.md`. Worked example: AS-XXX (Saccharothrix sp., moss), this session, bundle v9.7.319.*
