# Deliverable Instruction — TEMPLATE (Sapote–Mamey)

Paste one filled copy of this block to request a deliverable. It is self-contained: it states what to build, from
which banked data, in what format, under which claim-safety guards, and how to hand the result back. Keep it
deterministic where a tool exists; only ask the Sapote (LLM) layer to judge where judgment is actually needed.

> **Deliv_ID:** `DLV-XXX` · **Version:** v1.0 · **Owner chat:** [which chat] · **Priority:** HIGH / MED / LOW

### 1. Goal (one line)
[What this deliverable is and why, in a single sentence.]

### 2. Type
[ Figure | BGC Atlas (HTML) | Table (xlsx sheet) | Report (md) | Card ]

### 3. Inputs — banked data only (do not re-scan packages)
- **Primary bank(s):** `merged_cohort/bgc_data.json` (+ `bgc_markers.json`, `tfbs_coupling.json`,
  `modeb_verdicts.csv`, `strains.json` as needed)
- **Filter:** [e.g. product tag == `azoxy-crosslink`; or strain == `AS-XXX`; or modeb_class == Class-A]
- **Params:** [strictness note, count convention, thresholds]

The merged banks are already populated — skip `build_deep_data` / `build_bgc_markers` (they re-scan packages and
are slow).

### 4. Method
- If a tool exists, name it and give the command (deterministic, reproducible):
  `python tools/<script>.py --banked-dir merged_cohort [flags] --out <path>`
- Only then the Sapote judgment step, if any: [what the LLM layer decides — e.g. lead ordering, caption prose].
  State the judgment scope narrowly.

### 5. Output spec
- **Filename:** `[exact_name_with_version].[ext]` (PRIVATE if it contains AS strains)
- **Format / dimensions:** [panels, columns, px/figure size, HTML sections]
- **Encoding conventions:** colour by confidence tier — Confirmed / Predicted-functional / KCB-anchored /
  Candidate-novel (no anchor). Label loci as `Strain / Region · class · KCB anchor · edge-status`.
- **Caption / legend:** [what the caption must state, including the claim-safety line.]

### 6. Claim-safety guards (must hold in the output)
- KCB = similarity anchor, **not identity**. `azoxy-crosslink`, `~enediyne`, `~halogenase` are antiSMASH
  **E-signals**, not structures.
- Use only typed strain-specific bioactivity metadata; otherwise state `NOT_SUPPLIED` without naming an assay target.
- AS verdicts are `[EG]` (offline) unless verified-literature-upgraded — tag accordingly.
- Corrected BGC count = Interior + ½·Edge + ¼·Full-contig.
- AS strains are unpublished → any deliverable containing them is **PRIVATE** (no public release / GitHub /
  Zenodo) — PRIVATE.

### 7. Acceptance checklist
- [ ] Built only from banked data (no package re-scan)
- [ ] Every locus carries strain / region / class / KCB anchor / edge-status
- [ ] Tier colouring applied; legend present
- [ ] Claim-safety line in caption; E-signals flagged
- [ ] PRIVATE marked if AS strains present
- [ ] Filename + version correct; reports back to the HIVE board row

### 8. Hand-back
Return the file + a 2–3 line note (what it shows, any caveats). Update HIVE `Board` row `[HB-xxx]` status →
DONE and drop the output path in `Output_Location`.

---

## Standard encodings (apply across deliverables)

**Confidence-tier palette** (use consistently in figures/atlases/tables):

| tier | meaning | colour |
|---|---|---|
| Confirmed | Mode B CONFIRM, verified-literature-upgraded | `#2E7D32` green |
| Predicted-functional | intact core + self-resistance/SARP, offline `[EG]` | `#2E86AB` blue |
| KCB-anchored | named KCB/MIBiG similarity anchor only | `#E59866` amber |
| Candidate-novel | no anchor (UNRESOLVED / dark) | `#7F8C8D` grey |

**Locus label format:** `SID####/REGION · <class> · ~<KCB anchor> · <edge-status>`
(e.g. `SID-XXX/region003 · transAT-PKS · ~cycloheximide · Interior`). The `~` marks KCB as a similarity anchor.

**Verdict tags:** `[EG]` = offline antiSMASH/extraction-grade; `[VL]` = verified-literature-upgraded;
`[DROP]`/`[DOWNGRADE]` as in `modeb_verdicts.csv`.
