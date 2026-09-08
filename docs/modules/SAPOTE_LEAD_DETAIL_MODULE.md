# Sapote Module — Lead Detail, Iterative Thinking & Literature Punch-Card Handoff

**Status:** new in v9.6.21-patched · pairs with `tools/build_lead_detail.py`
**Purpose:** drive mechanism-aware Mode B on the nominated antifungal/antibacterial leads, fix the RG-GMCI fragment-rescue interpretation, and hand off literature questions to an external web-enabled session (ChatGPT) when Sapote has no network.

---

## 1. The RG-GMCI rescue fix (bug → corrected rule)

**Bug:** the prior rescue interpretation graded a pair on *shared product-class tokens* and discarded pairs whose two fragments carried different product annotations. That systematically **rejected real splits** — a cluster split across contigs has its core on one fragment and its tailoring/sugar/transport genes on another, so the two fragments are *expected* to have different product-class calls. It also leaned on `good_geometry_references` / `avg_min_identity`, which are empty when JSON evidence is `off`.

**Corrected rule (implemented in `rescue_groups()`):** grade rescue strength on the evidence the engine actually populates —
- `strong_supporting_references` (reference clusters with strong protein co-membership),
- `complete_or_chromosome_references` (support from complete genomes),
- `max_protein_sum` (shared-protein count),
- `rggmci_score`.

Then build a graph from pairs with `strong_supporting_references ≥ 1` and report **connected components (rescue groups)**, not individual pairs:
- **CLEAN_SPLIT** — a 2-fragment group → highest-confidence single split cluster.
- **HUB_COMPONENT_NEEDS_SUBRESOLUTION** — a larger component with one or two high-degree hub nodes → likely a *small* number of large fragmented pathways, **not** one cluster and not N clusters. Resolve by the shared-protein edges, not by merging the whole component.

**Worked result (AS-XXX):** 5 groups — one 19-fragment hub component (hubs BGC004 deg 11, BGC014 deg 8; top edge BGC004+BGC014 at 48 shared proteins) and four clean 2-fragment splits (BGC021+BGC032 siderophore; BGC024+BGC027 terpene; BGC006+BGC026 NRPS/lanthipeptide; BGC015+BGC060). The top lead BGC038 correctly returns `NO_STRONG_RESCUE` — it is a complete interior cluster.

> **Claim ceiling for rescue:** RG-GMCI nominates homology-guided shared-reference linkage; it is **not** nucleotide-level joining. A rescue group is a *reconstruction hypothesis to confirm by long-read/contig-overlap*, never an asserted merge.

---

## 2. Lead-detail iterative thinking step

For each nominated antifungal/antibacterial lead, Sapote reasons in three passes over the
`tools/build_lead_detail.py` output. Passes 2–3 are written by the judgment layer.

**Pass 1 — gene inventory (deterministic; the tool).**
Per lead: biosynthetic genes with their domains, tailoring enzymes, **resistance genes in-cluster**, transporter count, regulators, rescue-group membership.

**Pass 2 — module / role assignment (Sapote).**
Walk the biosynthetic genes in order and assign each a role: loading/extension module (KS-AT-KR…), NRPS module (C-A-PCP), tailoring (P450, MT, halogenase, glycosyltransferase, deoxysugar), resistance/self-protection, export. State what the *captured* module set can and cannot make, and where truncation cuts the assembly line.

**Pass 3 — mechanism hypothesis + literature questions (Sapote).**
From the module roles + KCB anchor, state a claim-safe mechanism hypothesis ("capacity consistent with…"), the single most diagnostic gene/domain to confirm it, and the **literature questions** that would resolve identity/novelty — which become the punch-card (§3).

**Iteration trigger:** if Pass 2 reveals a diagnostic gene the KCB anchor does not explain (e.g. `nikJ` in a "nucleoside" region → nikkomycin/chitin-synthase-inhibitor, not the generic anchor), loop back: re-query the lead with that gene as the seed before writing Pass 3.

**Worked examples (AS-XXX):**
- **BGC008 (nucleoside, antifungal):** Pass 1 surfaces `nikJ` (nikkomycin pathway) + `truD` + aminotransferases + a drug-efflux transporter. Pass 2: the nikJ hit reframes the generic "nucleoside" call as a **chitin-synthase-inhibitor** candidate (peptidyl-nucleoside) — ecologically pointed for a bee symbiont vs brood fungi. Pass 3: confirm nikJ identity; lit question on nikkomycin/polyoxin cluster homology.
- **BGC002 (polyene, antifungal):** Pass 1: KS-AT-KR PKS module + NRPS C-A-PCP module + `azdH`/Acyl-CoA-dh + **four efflux transporters**. Pass 2: a PKS-NRPS hybrid with strong export — consistent with a secreted polyene/hybrid antifungal. Pass 3: the four-transporter export cassette is the self-protection story to confirm.
- **BGC038 (saccharide, antibacterial; top lead):** Pass 1: `APH` resistance gene **in-cluster** beside `RmlD` (dTDP-deoxysugar), `MGT`/`Glycos_transf` glycosyltransferases, `PKS_KR`. Pass 2: a glycosylated/aminoglycoside-adjacent antibacterial with co-encoded aminoglycoside self-resistance. Pass 3: the in-cluster APH is the diagnostic; lit question on the *Dactylosporangium* anchor product.

---

## 3. Literature punch-card handoff (external web-enabled session)

When Sapote has no network, literature verification is delegated to a web-enabled session (e.g. ChatGPT). The flow: **Sapote fills a punch card → the human relays it to the web session → results return to Sapote → Sapote folds them into Pass 3 and the dereplication verdicts.**

Punch-card requirements:
- One block per question, each **self-contained** (the web session has no project context): name the organism, the MiBIG/KCB anchor, the domain/gene evidence, and the exact question.
- Ask for **sourced** answers (DOI/PMID/accession) and a one-line confidence.
- Never ask the web session to make project judgments — only to retrieve facts (is product X real for organism Y; mechanism; closest characterized cluster to this gene/domain set; whether a cluster spans these product types).
- Keep each answer blank explicit so results paste back cleanly.

A pre-filled card for the current strain ships as `<STRAIN>_LITERATURE_PUNCHCARD.md`.

---

## 4. Wiring

```
mamey run … --master …            # strain inventory + triage + RGGMCI (unchanged)
python tools/build_lead_detail.py --package <pkg> --gbk-dir <gbks> \
       --leads <nominated leads>   # → lead_detail.json  (Pass 1 + corrected rescue groups)
# Sapote: Pass 2 + Pass 3 over lead_detail.json → Mode B lead cards + punch card
# human relays punch card to web session → results → Sapote dereplication verdicts
```
