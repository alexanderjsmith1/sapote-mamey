# Sapote Module — Lead Detail, Iterative Thinking & Literature Punch-Card Handoff

**Tool:** `tools/build_lead_detail.py`
**Purpose:** drive mechanism-aware Mode B on the nominated antifungal/antibacterial leads and fix the RG-GMCI fragment-rescue interpretation. It also hands off literature questions to an external web-enabled session when Sapote has no network.

---

## 1. The RG-GMCI rescue fix (bug → corrected rule)

**Previous-rule limitation:** comparing shared product-class tokens could reject split-locus candidates when annotations differed. Assess each candidate's bound pair evidence and alternatives independently; differing calls do not themselves prove a real split. The older `good_geometry_references` / `avg_min_identity` fields can be unavailable under selected JSON evidence settings; inspect their actual availability and producer, not a label alone.

**Corrected rule (implemented in `rescue_groups()`):** only `strong_supporting_references` (reference clusters with
strong protein co-membership) decides which pairs count. A pair joins the graph when it has 1 or more. Three other
fields are copied onto each edge. `max_protein_sum` (shared-protein count) and `rggmci_score` only order the edges,
after the strong-reference count. `complete_or_chromosome_references` (support from complete genomes) is recorded
but neither gates nor orders.

The helper then reports **connected components (rescue groups)**, not individual pairs:
- **CLEAN_SPLIT** — a 2-fragment group. The label comes from component size alone: two loci joined by reference-derived pair support. It does not show physical linkage, a single pathway or higher biological confidence; keep both full endpoint identities and treat the join as unresolved until checked.
- **HUB_COMPONENT_NEEDS_SUBRESOLUTION** — a component with three or more fragments. This label follows graph size, not the number of pathways or physical joins. Inspect each shared-reference edge and full endpoint identity separately, retaining alternatives.

Before interpreting rescue status, independently verify the exact selected RG-GMCI file, full endpoint identities, source/run binding and completion state. The helper selects the first matching `*RGGMCI_full.json` and otherwise uses an empty pair list; absent or ambiguous selection is unavailable evidence, not a negative assessment.

No public worked result is bundled. When you report one, write each alias as `<strain> / <contig> / region<NNN> / BGCnnn`, copied from the package.

> **Claim ceiling for rescue:** RG-GMCI nominates homology-guided shared-reference linkage; it is **not** nucleotide-level joining. A rescue group is a *reconstruction hypothesis to confirm by long-read/contig-overlap*, never an asserted merge.

---

## 2. Lead-detail iterative thinking step

For each nominated antifungal/antibacterial lead, work in three passes over the
`tools/build_lead_detail.py` output. The tool does Pass 1. You write Passes 2 and 3.

**Pass 1 — gene inventory (deterministic; the tool).**
The helper reports parsed CDS and heuristic annotation candidates from a resolved region GBK. Verify exact source, full locus identity, parse coverage and annotations independently. Missing or unresolved GBK input holds the inventory; empty lists or zero counts are not biological absence. Rescue membership reflects the selected pair graph, not independently validated linkage.

**Pass 2 — module / role assignment (you).**
Walk the biosynthetic genes in order and assign each a role: loading/extension module (KS-AT-KR…), NRPS module (C-A-PCP), tailoring (P450, MT, halogenase, glycosyltransferase, deoxysugar), resistance/self-protection, export. State what the *captured* module set can and cannot make, and where truncation cuts the assembly line.

**Pass 3 — mechanism hypothesis + literature questions (you).**
From the module roles + KCB anchor, state a claim-safe mechanism hypothesis ("capacity consistent with…"), the single most diagnostic gene/domain to confirm it, and the **literature questions** that would resolve identity/novelty. These questions become the punch-card (§3).

**Iteration trigger:** a reference-associated gene annotation can motivate a source-bound query and literature question. Confirm identity, gene context and alternatives before naming a pathway, compound or mechanism. Any new query or external submission remains subject to the selected task's authorization.

---

## 3. Literature punch-card handoff (external web-enabled session)

When Sapote has no network, literature verification is delegated to a web-enabled session. The flow: **Sapote fills a punch card → the human relays it to the web session → results return to Sapote → Sapote folds them into Pass 3 and the dereplication verdicts**.

Punch-card requirements:
- One block per question, each **self-contained** (the web session has no project context): name the organism, the MIBiG/KCB anchor, the domain/gene evidence, and the exact question.
- Ask for **sourced** answers (DOI/PMID/accession) and a one-line confidence.
- Never ask the web session to make project judgments — only to retrieve facts (is product X real for organism Y; mechanism; closest characterized cluster to this gene/domain set; whether a cluster spans these product types).
- Keep each answer blank explicit so results paste back cleanly.

The deterministic helper writes the selected lead-detail JSON; it does not emit `<STRAIN>_LITERATURE_PUNCHCARD.md`. A punch card is a separate authored output when selected, with source-bound questions and explicit unresolved evidence. Preparing it does not authorize sending it or making external queries.

---

## 4. Wiring

```bash
python tools/build_lead_detail.py --package path/to/package --gbk-dir path/to/region_gbks --leads BGC001,BGC002 --out path/to/fresh-output/lead_detail.json
```

These paths and aliases are illustrative, not evidence for biological loci. Substitute bound inputs and an existing fresh authorized output directory; quote spaces. The parser takes comma-separated BGC IDs, not full-locus selectors. Recover complete identities from the bound manifest before interpretation. An occupied output or an output aliasing a retained input is refused. Without `--out`, the helper targets `lead_detail.json` in the package. Passes 2 and 3 and any literature punch card are separately authored; preparing them does not authorize sending them.
