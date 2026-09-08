"""modeb_template_emitter.py — canonical §1–§48 template emitter.

Produces a fill-in-the-blank Mode B card skeleton for one BGC or for an
entire strain's worth of leads, pre-populated with the BGC-specific facts
already known from the triage board and the package manifest. The chat
fills in interpretive content; section structure is no longer the chat's
responsibility, which is the right division of labour.

This is the "B" half of the W9 firebreak — A (modeb_structure_gate) catches
wrong-scaffold cards at ingest time; B makes the right scaffold the path of
least resistance by emitting it directly. Together they close the
BGC033-pattern failure mode that recurred in v9.7.150 despite documentation.

Public API:
    emit_card_template(pkg, bgc_id, contract=None) -> str
    emit_batch(pkg, contract=None, *, top_n=None, scope="all") -> dict

The batch emitter writes one card per top-N BGC to a `mode_b_templates/`
subdir of the package, ready for the chat to fill in. Per-strain batching
is the canonical workflow — the chat opens the strain, opens the batch
directory, and works through cards in triage-rank order.

W9 / template-emitter (v9.7.150+).
"""
from __future__ import annotations

import csv
import json
import re as _re
from pathlib import Path
from typing import Optional

from .modeb_structure_gate import load_contract, _build_predicates
from .manifest_schema import read_manifest_field


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def _section_floor_for(num: int, facts: dict) -> int:
    """Resolve the depth-gate char floor for section `num`, mirroring
    modeb_structure_gate's own logic so the emitted header comment matches what
    verify-modeb will enforce. Surfaced inline (Rec 8) so authors write to the
    target on the first pass instead of discovering it via a THIN_SECTION fail."""
    try:
        from .modeb_structure_gate import _DEPTH_DEFAULTS, _HEAVY_SECTIONS, _is_large_bgc
    except Exception:
        return 0  # never block emission on a floor-surfacing convenience
    bgc_context = {
        "boundary": facts.get("boundary", ""),
        "length_kb": facts.get("length_kb", 0) if str(facts.get("length_kb", "")).replace(".", "").isdigit() else 0,
        "total_domains": facts.get("total_domains", 0),
    }
    large = _is_large_bgc(bgc_context)
    if num in _HEAVY_SECTIONS:
        key = "heavy_section_min_chars_large" if large else "heavy_section_min_chars_small"
    else:
        key = "section_min_chars_large" if large else "section_min_chars_small"
    return int(_DEPTH_DEFAULTS.get(key, 0))


def _precompute_facts(pc_dir: str, join_locator: str, strain: str = "", bgc_id: str = "") -> dict:
    """Part C: join a BGC's grounded facts from the cohort precompute tables on the assembly_locator
    (Part B key). Cohort tables are the single source; sections pre-fill from these. Non-fatal."""
    import csv as _csv
    from pathlib import Path as _P
    if not join_locator or not _P(pc_dir).is_dir():
        return {}

    def _rows(fn, key="Assembly_Locator"):
        p = _P(pc_dir) / fn
        if not p.is_file():
            return []
        with open(p, encoding="utf-8") as fh:
            return [r for r in _csv.DictReader(fh) if r.get(key) == join_locator]

    f = {}
    arch = _rows("COHORT_domain_architecture_by_bgc.csv")
    if arch:
        f["pc_archetype"] = arch[0].get("architecture_archetype", "")
        f["pc_archetype_note"] = arch[0].get("archetype_note", "")
        f["pc_domain_string"] = arch[0].get("domain_architecture_string", "")
    mod = _rows("COHORT_module_architecture_by_bgc.csv")
    if mod:
        f["pc_module_count"] = mod[0].get("aSModule_count", "")
        f["pc_module_types"] = mod[0].get("module_types", "")
    cc = _rows("COHORT_domain_claim_ceiling_by_bgc.csv")
    if cc:
        f["pc_safe_claims"] = cc[0].get("Safe_domain_claims", "")
        f["pc_unsafe_claims"] = cc[0].get("Unsafe_domain_claims", "")
        f["pc_claim_ceiling"] = cc[0].get("Domain_claim_ceiling", "")
    roles = _rows("COHORT_domain_roles_by_bgc.csv")
    if roles:
        f["pc_roles"] = "; ".join(f"{r.get('domain_role_category','')}×{r.get('count','')}" for r in roles)
    # resistance + nrps substrates key on (strain, bgc_id) — they carry node_region/contig, not the
    # full assembly_locator. Similarity-level throughout.
    if strain and bgc_id:
        pr = _P(pc_dir) / "COHORT_resistance_signals_by_bgc.csv"
        if pr.is_file():
            with open(pr, encoding="utf-8") as fh:
                rz = [r for r in _csv.DictReader(fh)
                      if r.get("strain") == strain and r.get("bgc_id") == bgc_id and r.get("resistance_genes")]
            if rz:
                f["pc_resistance"] = "; ".join(r["resistance_genes"] for r in rz)
        p = _P(pc_dir) / "COHORT_nrps_adomain_substrates.csv"
        if p.is_file():
            with open(p, encoding="utf-8") as fh:
                subs = [r for r in _csv.DictReader(fh)
                        if r.get("strain") == strain and r.get("bgc_id") == bgc_id]
            if subs:
                f["pc_substrates"] = subs  # additive agreement fields preserve predictor conflicts when available
    return f


def emit_card_template(package_dir: str | Path,
                       bgc_id: str,
                       contract: Optional[dict] = None,
                       precompute_dir: Optional[str] = None) -> str:
    """Return a Mode B card template string for one BGC.

    Pre-fills:
      - canonical §1–§48 headings in order (always-required + applicable
        conditional sections; non-applicable conditional sections are
        omitted to keep the chat from authoring "N/A — RiPP-only" boilerplate)
      - §1 Identity and node/region populated from triage row + manifest
      - §3 Boundary and assembly status populated from triage row +
        manifest_short (tier, interior_pct)
      - §8 Comparator/KCB interpretation seeded with the kcb_top hit
      - §18 Figure/locus-map notes seeded with the expected path to the
        locus map SVG (if W5 has emitted one)
      - §28 evidence provenance and publication-reconciliation tables seeded
        as authoring scaffolds; their placeholder states must be replaced from
        reviewed evidence before publication-gate verification
      - Each section gets a one-line authoring prompt as an HTML comment
        the chat replaces with prose

    Never raises on missing data — fields that can't be resolved show as
    "—" and become part of §15 Missing evidence.
    """
    pkg = Path(package_dir)
    if contract is None:
        contract = load_contract()

    facts = _bgc_facts(pkg, bgc_id)
    facts.update(_over_merge_facts(pkg, facts))
    # Part C (v9.7.225): pre-fill grounded facts from the cohort precompute layer, joined on the
    # assembly_locator (Part B key). Cohort tables are the single source so no card re-derives modules,
    # archetype, claim ceiling, or substrates. Non-fatal — absent tables/rows leave the pre-fills as "—".
    if precompute_dir:
        from .package_inspector import _cohort_locator
        _join = _cohort_locator({"Contig": facts.get("contig", ""), "antiSMASH_Region": facts.get("region", "")})
        facts.update(_precompute_facts(precompute_dir, _join,
                                       strain=facts.get("strain_id", ""), bgc_id=facts.get("bgc_id", "")))
    predicates = _build_predicates(facts)

    lines: list[str] = []
    lines.append(_header_block(facts, contract))

    for s in contract["sections"]:
        num = s["number"]
        title = s["title"]
        required = s["required"]
        cond_key = s["condition_key"]

        applies = required != "conditional" or predicates.get(cond_key, False)

        _floor = _section_floor_for(num, facts)
        lines.append(f"## §{num} {title}")
        lines.append(f"<!-- depth floor: {_floor} chars -->")
        lines.append("")
        body = (_section_body(num, facts, s) if applies else
                "**NOT_APPLICABLE (reason required):** Explain why this section does not apply to "
                "this exact locus and distinguish non-applicability from missing/unbound evidence.")
        lines.append(body)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Template emitted by `mamey emit-modeb-template`. "
                 "Fill prose under each heading. Do not rename, reorder, "
                 "or omit headings. Expanded owner-review candidates preserve "
                 "§1–§48 in order. Replace every prompt, including conditional "
                 "sections, with substantive analysis or a reasoned "
                 "NOT_APPLICABLE disposition.*")
    return "\n".join(lines)


def emit_batch(package_dir: str | Path,
               contract: Optional[dict] = None,
               *,
               top_n: Optional[int] = None,
               scope: str = "all",
               precompute_dir: Optional[str] = None,
               out_subdir: str = "mode_b_templates") -> dict:
    """Emit a batch of Mode B card templates for a strain.

    `scope`:
      - "all"     — every BGC in the triage board (default)
      - "top"     — top-N by Corrected_rank (requires top_n)
      - "leads"   — every BGC with Lead_tier_auto in {HIGH, PRIORITY ISO}
      - "pending" — every BGC not yet COMPLETE in the judgment register

    Output:
        <pkg>/mode_b_templates/<BGC_ID>_template.md
        <pkg>/mode_b_templates/_INDEX.md  (a one-screen catalogue)

    Returns:
        {"out": <str>, "emitted": [bgc_id, ...], "skipped": {bgc_id: reason}}

    Never raises. Per-BGC failures degrade gracefully.
    """
    pkg = Path(package_dir)
    out_dir = pkg / out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    if contract is None:
        contract = load_contract()

    triage_rows = _read_triage(pkg)
    if not triage_rows:
        return {"out": str(out_dir), "emitted": [], "skipped": {},
                "skipped_reason": "no triage board CSV found"}

    bgc_ids = _select_scope(pkg, triage_rows, scope, top_n)

    emitted: list[str] = []
    skipped: dict[str, str] = {}
    for bgc_id in bgc_ids:
        try:
            card = emit_card_template(pkg, bgc_id, contract=contract, precompute_dir=precompute_dir)
            # v9.7.374: write to a .tmp sibling then Path.replace() into place, so a process killed
            # mid-write (SIGKILL/OOM/power loss) -- including on a re-run over an out_dir that
            # already carries a valid prior template for this BGC -- cannot truncate a previously
            # valid deliverable to zero/partial bytes.
            _tmpl_path = out_dir / f"{bgc_id}_template.md"
            _tmpl_tmp = _tmpl_path.with_name(_tmpl_path.name + ".tmp")
            _tmpl_tmp.write_text(card, encoding="utf-8")
            _tmpl_tmp.replace(_tmpl_path)
            emitted.append(bgc_id)
        except Exception as e:
            skipped[bgc_id] = f"{type(e).__name__}: {e}"
            continue

    # Index file — gives the chat a single-glance map of the batch
    _write_index(out_dir, pkg, emitted, skipped, scope, top_n)

    return {"out": str(out_dir), "emitted": emitted, "skipped": skipped,
            "skipped_reason": None}


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def _region_number(region_label) -> Optional[int]:
    """`region002` / `region2` / `2` -> 2. None when unparseable."""
    m = _re.search(r"(\d+)", str(region_label or ""))
    return int(m.group(1)) if m else None


def _over_merge_facts(pkg: Path, facts: dict) -> dict:
    """Surface antiSMASH's over-merge signal for THIS BGC's region from Patch G's
    predicted_polymers.csv. Honest-blank ({}) on any absence; never raises.

    v9.7.240 (P1): the match is (contig, region_number), not contig alone. The old
    code compared only the bare contig, so every BGC sharing a contig with an
    over-merged region inherited that region's banner and its protocluster count.

    Measured on the real AS-XXX package (46 regions, engine 1.9.109): 13 templates
    carried an OVER-MERGED banner; only 7 regions are over-merged per the region
    GBKs and per docs/reference/AS-XXX_AS-XXX_over_merge_decomposition.csv. The 7
    wrong banners were BGC008/009/010 (inherited from NODE_1 region001),
    BGC017/018 (from NODE_2 region001), BGC040 (from NODE_6 region002), and a wrong
    count on BGC042 (banner 3, truth 2). A card authored against a false banner
    withholds a single-product claim it is entitled to make.
    """
    import csv as _csv
    node = (facts.get("node") or facts.get("contig") or "")
    if not node:
        return {}
    bare = node.split(".")[0]
    want_region = _region_number(facts.get("region"))
    for name in (f"{_strain_prefix(pkg)}_predicted_polymers.csv", "predicted_polymers.csv"):
        pp = pkg / name
        if not pp.exists():
            continue
        try:
            for r in _csv.DictReader(pp.open(encoding="utf-8")):
                if (r.get("record_id") or "").split(".")[0] != bare:
                    continue
                row_region = _region_number(r.get("region_number"))
                # Region must match. If either side is unparseable, refuse to guess:
                # an un-regioned row cannot be attributed to this BGC.
                if want_region is None or row_region is None or row_region != want_region:
                    continue
                if "YES" in (r.get("over_merge_flag") or ""):
                    return {"over_merge": True,
                            "n_protoclusters": r.get("n_protoclusters") or "?",
                            "candidate_kind": r.get("candidate_kind") or "?"}
        except OSError:
            continue
    # predicted_polymers.csv carries rows only for regions with an NRPS/PKS polymer
    # prediction, so a lanthipeptide+terpene merge has no row there at all. The
    # manifest's protocluster_count (v9.7.240 P2) is authoritative for every region.
    n_pc = facts.get("manifest_protocluster_count")
    if isinstance(n_pc, int) and n_pc >= 2:
        return {"over_merge": True, "n_protoclusters": n_pc, "candidate_kind": "?"}
    return {}


def _header_block(facts: dict, contract: dict) -> str:
    """Top-of-card metadata banner the chat must preserve.

    v9.7.195: also render the contract's `quality_gate` checklist into the header. The authoring bar
    (gene-interplay prose, >=2 alternatives, CSV-free readability, capacity language) lives in the
    contract JSON but was only reachable by independently opening the file and scrolling past the
    sections list — so an authoring chat could fill to its own sense of 'adequate' and only learn the
    card was thin when verify-modeb rejected it. Surfacing the checklist here makes the bar the first
    thing the author reads, so the gate confirms the work instead of discovering it is thin.
    """
    bgc = facts.get("bgc_id") or "?"
    node = facts.get("node") or facts.get("contig") or "?"
    strain = facts.get("strain_id") or "?"
    products = facts.get("products") or "?"
    qg = contract.get("quality_gate") or []
    gate_block = ""
    if qg:
        items = "\n".join(f"> - {q}" for q in qg)
        gate_block = (
            "\n> **AUTHORING BAR — author to THIS before running the gate (do not fill to "
            "'adequate' and let `verify-modeb` catch thin work):**\n"
            f"{items}\n"
            "> Character counts are progress diagnostics only and never scientific acceptance "
            "evidence. Author to the evidence scaffold first; run the gate as confirmation.\n"
        )
    return (
        f"<!-- MODE B TEMPLATE | bgc: {bgc} | node: {node} | "
        f"strain: {strain} | products: {products} | "
        f"contract: {contract.get('schema_version')} -->\n\n"
        f"# Mode B — {strain} / {node} / {facts.get('region') or '?'} / {bgc}\n\n"
        f"*Template emitted from `{contract.get('schema_version')}`. "
        f"expanded owner-review profile includes §1–§48; non-applicable sections "
        f"remain present with a reasoned NOT_APPLICABLE disposition.*\n"
        f"> **Lifecycle:** this is an authoring scaffold, not a publication candidate. "
        f"Populate every placeholder from the frozen evidence packet, save the authored bytes, "
        f"then run the publication gate. A fresh template is expected to retain unresolved "
        f"publication findings.\n"
        f"{gate_block}"
        f"{_over_merge_banner(facts)}"
    )


def _over_merge_banner(facts: dict) -> str:
    if not facts.get("over_merge"):
        return ""
    return (
        f"\n> \u26a0 **OVER-MERGED REGION \u2014 antiSMASH resolved "
        f"{facts.get('n_protoclusters')} protoclusters (candidate_kind: "
        f"{facts.get('candidate_kind')}). This is antiSMASH's own '>=2 BGCs' "
        f"signal: do NOT make a single-product claim. Analyse per protocluster "
        f"(\u00a75/\u00a79/\u00a710); region-level scores/KCB are aggregates "
        f"over multiple systems \u2014 split before any product-family or "
        f"compound statement.**\n"
    )


def _substrate_display(row: dict) -> str:
    """Render additive NRPS predictor fields while remaining compatible with legacy rows."""
    state = str(row.get("prediction_agreement_state") or "").strip()
    consensus = str(row.get("consensus_substrate") or "").strip()
    stachelhaus = str(row.get("stachelhaus_substrate") or row.get("substrate") or "").strip()
    if state == "SUBSTRATE_PREDICTION_CONFLICT":
        return f"**CONFLICT:** consensus {consensus or 'unresolved'}; Stachelhaus {stachelhaus or 'unresolved'}"
    if state == "SUBSTRATE_PREDICTION_CONCORDANT" and consensus:
        return f"{consensus} (consensus and Stachelhaus concordant)"
    if state == "CONSENSUS_ONLY_STACHELHAUS_UNRESOLVED":
        return f"consensus {consensus}; Stachelhaus unresolved"
    if state == "BOTH_SUBSTRATE_PREDICTIONS_UNINFORMATIVE":
        return "unresolved in both predictor streams"
    return stachelhaus or consensus or str(row.get("substrate") or "—")


def _section_body(num: int, facts: dict, sect: dict) -> str:
    """Return the pre-filled body for section `num`. For sections without a
    pre-fill rule, returns a single-line authoring prompt."""
    bgc = facts.get("bgc_id") or "?"
    node = facts.get("node") or facts.get("contig") or "?"

    if num == 1:
        return (f"**BGC:** {bgc}\n"
                f"**Node / contig:** {node}\n"
                f"**antiSMASH region:** {facts.get('region') or '—'}\n"
                f"**Predicted products:** {facts.get('products') or '—'}\n"
                f"**Length:** {facts.get('length_kb') or '—'} kb\n\n"
                f"<!-- Author: 2–3 sentences placing this locus within the "
                f"strain. Always cite BGC + node/contig together (standing rule). -->")

    if num == 2:
        # v9.7.343 surfacing patch: append the engine's already-computed capacity
        # verdicts (Arch_Capacity/Class_Conf + Diagnostic-Rescue). Additive content
        # inside an existing section — no new ## heading, so the structure gate is
        # unaffected (same pattern as the §4 interpretive stubs). Class-level capacity,
        # not identity. Empty string when the engine wrote nothing, keeping cards clean.
        verdict = ""
        try:
            from . import card_verdicts as _cv
            tv = {
                "arch": facts.get("arch", ""), "arch_capacity": facts.get("arch_capacity", ""),
                "class_conf": facts.get("class_conf", ""), "novelty_auto": facts.get("novelty_auto", ""),
                "concordance": facts.get("concordance", ""), "misanchor_flag": facts.get("misanchor_flag", ""),
                "standing_rule": facts.get("standing_rule", ""),
                "primary_metab_flag": facts.get("primary_metab_flag", ""),
            }
            block = _cv.render_block(None, bgc, triage=tv, rescues=facts.get("diagnostic_rescue") or [])
            if block:
                verdict = "\n\n" + block
        except Exception:
            verdict = ""
        return (f"**Lead tier:** {facts.get('lead_tier') or '—'} | "
                f"**Corrected rank:** {facts.get('corrected_rank') or '—'}\n"
                f"**AB score:** {facts.get('ab_score') or '—'} | "
                f"**AF score:** {facts.get('af_score') or '—'} | "
                f"**Novelty:** {facts.get('novelty') or '—'}\n"
                f"**CCTT triggers:** {facts.get('cctt_triggers') or '—'}\n"
                f"{verdict}\n\n"
                f"<!-- Author: 1–2 sentences on why this BGC merits Mode B "
                f"effort vs. the triage queue. -->" + _subsec(facts, bgc, 2))

    if num == 3:
        return (f"**Boundary:** {facts.get('boundary') or '—'} | "
                f"**Assembly locator:** {facts.get('assembly_locator') or '—'}\n"
                f"**Strain assembly tier:** {facts.get('assembly_tier') or '—'} "
                f"({facts.get('interior_pct') or '—'}% interior)\n\n"
                f"<!-- Author: caveats from boundary/assembly status. "
                f"Edge/full-contig get truncation caveats. POOR/VERY_POOR "
                f"add tier note. Per standing rule: edge/FC at POOR tier "
                f"sort by score, not boundary; no Interior-penalty. -->")

    if num == 4:
        gene_rows = facts.get("gene_rows") or []
        gene_table = _render_gene_table(gene_rows, node)
        blastp_matrix = _render_blastp_matrix_scaffold(gene_rows)
        roles_line = (f"**Domain-role census (grounded, from cohort precompute):** {facts.get('pc_roles')}\n\n"
                      if facts.get("pc_roles") else "")
        # v9.7.339: judgment-forward interpretation stubs. These two anchored #### subsections make the
        # card LEAD with a judgment (the gene table is its evidence, not the interpretation) and force a
        # domain-based read of reference-dark/partial cores instead of leaving them as silence. They are
        # additive (no ## heading added/removed/renamed, so the structure gate is unaffected) and are
        # checked by the interpretation gate (tools/modeb_interp_gate.py). Absence-of-homolog is a
        # novelty prior, not proof of a new compound; comparators stay similarity anchors.
        synthesis_stub = (
            "#### ⬛ Interpretive synthesis — read this first\n"
            "<!-- INTERP-GATE anchor: SYNTHESIS. Author a judgment-forward lead (>=350 chars) with FIVE moves: "
            "(1) family call + the per-gene MIBiG convergence TIER (H1..H5/CAUTION/reference-dark; from the "
            "data card / *_3_mibig_convergence.csv), stated as a similarity anchor not identity; (2) how the "
            "core genes cooperate mechanistically (by locus_tag); (3) any second / over-merged capacity; "
            "(4) the leading ALTERNATIVE read (also carried in §9); (5) the ONE experiment that resolves it "
            "(point to §16/§30). This block leads the card; the gene table below is its evidence. -->\n"
            "<!-- Author: replace this comment with the 5-move synthesis. -->\n\n"
            "#### Reference-dark / partial cores — domain-based read\n"
            "<!-- INTERP-GATE anchor: REFDARK. REQUIRED when any ● core lacks a homology hit (DATA REQUEST / "
            "no Swiss-Prot hit) or carries an incomplete/partial module. Interpret such cores from DOMAIN "
            "grammar (KS/AT/ACP/PCP order, module count, sec_met/Pfam), NOT from silence — absence of a "
            "homolog is a novelty prior, not proof of a new compound. If no core is reference-dark, state "
            "'no reference-dark core' in one line. -->\n"
            "<!-- Author: replace this comment with the domain-based read (or the one-line 'none'). -->\n\n")
        return (f"{synthesis_stub}"
                f"{roles_line}"
                f"**Gene table** (observed, from `gene_context.jsonl`):\n\n"
                f"{gene_table}\n\n"
                f"#### Complete named-match, channel-separated table\n\n"
                f"{blastp_matrix}\n\n"
                f"<!-- Author: replace every angle-bracket placeholder from exact-query-bound "
                f"evidence. Keep nr, ClusteredNR, and local Swiss-Prot separate. Bare typed states "
                f"must not be wrapped in backticks. Missing/unreturned/unbound is a workflow state, "
                f"not biological absence. -->\n\n"
                f"**Independent homology channel (REQUIRED for lead cards):** author §4 "
                f"AFTER the BLASTp panel exists. Two routes produce the SAME "
                f"`<BGC>_online_blastp.csv` panel — prefer the offline one to avoid live polling:\n"
                f"  - **token-friendly / offline (preferred when results are in hand):** if NCBI BLAST has "
                f"already been run (a hit-table CSV, optionally the Alignment XML for subject defs), ingest "
                f"it with ZERO network via `mamey ingest-blastp --master <workbook.xlsx> --strain <ID> "
                f"--hit-table <hits.csv> [--xml <aln.xml>] --package <package_dir>` — no RID poll, no "
                f"per-query wait; it writes the same panel + nr overlay.\n"
                f"  - **live:** `mamey blastp-online --package <antismash_gbk> --bgc {bgc}` "
                f"submits to NCBI and polls (~1-2 min/query); use only when no pre-run results exist. "
                # v9.7.246: the specific example that used to sit here — "overturned two of ten on
                # BGC006 (β-lactamase→esterase, phenol-hydroxylase→ferritin)" — is a REAL result, but it
                # belongs to *Amycolatopsis* sp. NPDC004378 (see Wheelhouse/validations/BGC006_online_blastp.csv).
                # Templated into §4 it was emitted verbatim into every card of every strain, asserting a
                # per-gene BLASTp outcome for strains on which no BLASTp had been run. Cite the validation
                # set; never carry another organism's loci into this card.
                f"antiSMASH Pfam calls are a hypothesis, not function — per-gene BLASTp routinely "
                f"overturns some of them (validation set: `Wheelhouse/validations/BGC006_online_blastp.csv`, "
                f"a different strain — do not cite its loci here). For each "
                f"catalytic-core/tailoring/resistance gene, reconcile the antiSMASH call against the "
                f"BLASTp top hit (CONFIRM / REFINE / OVERTURN) and author from the RECONCILED call. "
                f"If the channel is unavailable, band a note: 'domain calls are antiSMASH Pfam, "
                f"unverified' (never fabricate hits). (blastp-online needs biopython — the `bio` "
                f"extra or the sapote-addons stack, which vendors it; without it the command "
                f"fail-closes with an actionable message, not a traceback.)\n\n"
                f"**Third channel — HMM adjudication (REQUIRED for any OVERTURN):** when BLASTp "
                f"disagrees with the antiSMASH call, the domain signature is the tie-breaker. Run "
                f"`mamey hmm-adjudicate <region.gbk> --locus <locus_tag>` and record the verdict "
                f"(SUPPORTS_BLASTP / SUPPORTS_ANTISMASH / AMBIGUOUS / INSUFFICIENT). This is the "
                f"offline, deterministic channel that breaks a BLASTp/antiSMASH tie. HMM also supplies "
                f"the module grammar "
                f"(KS→AT→DH→KR→ACP order + module count) BLASTp cannot resolve, and rescues short/"
                f"orphan genes with no BLASTp hit (RiPP precursors, leader peptides). Channel roles: "
                f"HMM = what the machine IS (intrinsic, offline); BLASTp = whose machine it is most "
                f"like + product novelty (extrinsic, online). Author the reconciled three-channel "
                f"call.\n\n"
                f"<!-- Author: gene-by-gene PROSE interpretation, written FROM the "
                f"table above AND the reconciled BLASTp calls. The table is the observed fact grid "
                f"(locus_tag, coords, strand, aa, domains); the prose is the interpretation — "
                f"reference catalytic-core genes (●) by locus_tag and explain how "
                f"they work together biochemically. §4 stays prose-first for the "
                f"interpretation; the table supplies the evidence, it does not "
                f"replace the walkthrough. -->" + _subsec(facts, bgc, 4))

    if num == 8:
        kcb = facts.get("kcb_top") or "—"
        kcb_score = facts.get("kcb_score") or "—"
        return (f"**KCB top hit:** {kcb} (score: {kcb_score})\n\n"
                f"**Corroboration (REQUIRED before authoring):** state the KCB anchor's "
                f"gene COVERAGE, not just its score — run `mamey kcb-frontpage <antismash_dir>` "
                f"and read the tier. A high score with few matching genes is COINCIDENTAL "
                f"(a sub-module or single-protein hit), NOT cluster identity. Coverage: "
                f"`____ / ____ genes` · tier: `____`\n\n"
                f"<!-- Author: KCB = SIMILARITY, NOT IDENTITY (standing rule). NEVER state a "
                # v9.7.246: was "the BGC006/colibrimycin fix: score 3734" — another strain's BGC id and
                # another run's KCB score, templated into every card. The lesson is portable; the numbers are not.
                f"KCB anchor without its gene coverage — this is the colibrimycin-class fix: a high "
                f"KCB score backed by only a handful of shared genes is NOT the compound. If per-gene "
                f"BLASTp (§4) shows the top hits are uncharacterised genus homologs, the honest "
                f"read is 'conserved in genus, no characterised product match', which is more "
                f"valuable than a weak MIBiG name. If kcb_top is on the permanent-exclusion "
                f"list (saccharide / NAPAA / hglE-KS-PREV-001), DOWNGRADE and explain. -->")

    if num == 13:
        return ("<!-- Author: claim-safe AB/AF discussion. Standing rule: "
                "bioactivity metadata may be absent and remains strain-level context only. "
                "Never call any strain antifungal-negative or antibacterial-"
                "negative — contrast strains by biosynthetic mechanism, not "
                "phenotype. Never pin activity to a specific BGC without "
                "fractionation. -->")

    if num == 14:
        if facts.get("pc_unsafe_claims") or facts.get("pc_claim_ceiling"):
            # Part C: grounded from COHORT_domain_claim_ceiling_by_bgc.csv (domain-safe/unsafe claims).
            return (f"**Domain claim ceiling (grounded, from cohort precompute):** "
                    f"{facts.get('pc_claim_ceiling') or '—'}\n\n"
                    f"**Cannot be claimed (domain-level unsafe):** {facts.get('pc_unsafe_claims') or '—'}\n\n"
                    f"**Supported at capacity level (domain-safe):** {facts.get('pc_safe_claims') or '—'}\n\n"
                    "<!-- Author: expand into prose. Capacity-based language always — 'biosynthetic "
                    "capacity consistent with…' never 'produces'. KCB = similarity, not identity. -->")
        return ("<!-- Author: list what the evidence DOES NOT support. "
                "Capacity-based language always — 'biosynthetic capacity "
                "consistent with…' never 'produces'. KCB = similarity, "
                "not identity. -->")

    if num == 11:
        if facts.get("pc_archetype"):
            # Part C: grounded from COHORT_domain_architecture_by_bgc.csv archetype.
            return (f"**Architecture archetype (grounded, from cohort precompute):** "
                    f"{facts.get('pc_archetype')}"
                    + (f" — {facts.get('pc_archetype_note')}" if facts.get('pc_archetype_note') else "") + "\n\n"
                    "<!-- Author: relate the archetype to a product family at CAPACITY level. Note if the "
                    "antiSMASH product class differs from the domain-grammar archetype (both are hypotheses). -->")
        return ("<!-- Author: product-family hypothesis at capacity level, "
                "grounded in the domain architecture. -->")

    if num == 16:
        subs = facts.get("pc_substrates")
        if subs:
            # Part C: grounded A-domain substrate table from COHORT_nrps_adomain_substrates.csv.
            # Preserve predictor disagreement; neither stream is a monomer-identity claim.
            hdr = ("| locus | domain | substrate prediction | agreement state | confidence | signature |\n"
                   "|---|---|---|---|---|---|\n")
            rows = "\n".join(
                f"| `{s.get('locus_tag','')}` | {s.get('domain','')[:28]} | {_substrate_display(s)} "
                f"| {s.get('prediction_agreement_state') or 'LEGACY_STACHELHAUS_ONLY'} "
                f"| {s.get('confidence','—')} | `{s.get('stachelhaus_signature','')}` |"
                for s in subs)
            return (f"**A-domain substrate predictions (grounded, from cohort precompute — "
                    f"antiSMASH predictor outputs, NOT monomer identity):**\n\n{hdr}{rows}\n\n"
                    "<!-- Author: turn each call into a capacity statement + the BLASTP/HMMER query that "
                    "would test it. A predictor conflict must remain unresolved unless independent evidence "
                    "adjudicates it. Per standing rule: SIGXFSZ note if any protein > 2,500 aa. -->")
        return ("<!-- Author: ordered list of BLASTP/HMMER queries that "
                "would resolve the current uncertainty. Each entry: "
                "[query target] → [hypothesis it tests] → [decision rule]. "
                "Per standing rule: SIGXFSZ note if any protein > 2,500 aa. -->")

    if num == 21:
        subs = facts.get("pc_substrates")
        if subs:
            calls = ", ".join(f"{s.get('locus_tag','')}→{_substrate_display(s)} ({s.get('confidence','?')})" for s in subs)
            return (f"**Monomer/substrate specificity (grounded, antiSMASH prediction level):** {calls}\n\n"
                    "<!-- Author: relate the substrate code to a product-family hypothesis at CAPACITY "
                    "level; never assert monomer identity from a prediction, and retain conflicts. -->")
        return ("<!-- Author (if NRPS/PKS): substrate-specificity code and what it implies "
                "at capacity level. Omit if not applicable. -->")

    if num == 27:
        rz = facts.get("pc_resistance")
        if rz:
            return (f"**Resistance/self-protection signals (grounded, from cohort precompute — "
                    f"similarity-level):** {rz}\n\n"
                    "<!-- Author: interpret as self-resistance capacity (target-based / efflux / "
                    "modification); never a phenotype claim. Cross-check ARTS if available. -->")
        return ("<!-- Author: resistance / self-protection genes and what they imply about the "
                "producer's self-protection capacity. Omit if none. -->")

    if num == 5:
        if facts.get("pc_archetype") or facts.get("pc_module_count"):
            return (f"**Architecture (grounded, from cohort precompute):** archetype "
                    f"{facts.get('pc_archetype') or '—'}; "
                    f"{facts.get('pc_module_count') or '0'} antiSMASH module(s)"
                    + (f" ({facts.get('pc_module_types')})" if facts.get('pc_module_types') else "")
                    + (f"; domain order: {facts.get('pc_domain_string')}" if facts.get('pc_domain_string') else "")
                    + "\n\n#### Committed-step genes\n<!-- exact genes and committed reactions -->\n\n"
                    "#### Reaction-level sequence\n<!-- conditional ordered biochemical model -->\n\n"
                    "#### Minimal-gene-set audit\n<!-- on-contig completeness and off-contig hold -->\n\n"
                    "#### Strongest alternative\n<!-- strongest primary/catabolic/false-positive model -->\n\n"
                    "#### Evidence for the alternative\n<!-- exact evidence -->\n\n"
                    "#### Evidence against the alternative\n<!-- exact evidence -->\n\n"
                    "#### Claim ceiling\n<!-- positive and negative claim ceilings -->\n\n"
                    "<!-- If OVER-MERGED, analyse each protocluster separately; region-level scores are aggregates. -->"
                    + _subsec(facts, bgc, 5))
        return ("#### Committed-step genes\n<!-- exact genes and committed reactions -->\n\n"
                "#### Reaction-level sequence\n<!-- conditional ordered biochemical model -->\n\n"
                "#### Minimal-gene-set audit\n<!-- on-contig completeness and off-contig hold -->\n\n"
                "#### Strongest alternative\n<!-- strongest false-positive model -->\n\n"
                "#### Evidence for the alternative\n<!-- exact evidence -->\n\n"
                "#### Evidence against the alternative\n<!-- exact evidence -->\n\n"
                "#### Claim ceiling\n<!-- positive and negative claim ceilings -->\n"
                + _subsec(facts, bgc, 5))

    if num == 6:
        return ("#### Direct tailoring candidates\n<!-- exact-bound candidates -->\n\n"
                "#### Broad metabolic context\n<!-- explicitly separate non-coupled context -->\n\n"
                "#### Conditional pathway order\n<!-- ordered model with confidence tags -->\n\n"
                "#### Non-diagnostic enzyme families\n<!-- families that cannot establish membership -->\n\n"
                "#### Comparator conflicts\n<!-- reused accessory enzymes and disagreements -->\n\n"
                "#### Coupling evidence\n<!-- what would bind each candidate to the core -->\n\n"
                "#### Discriminating tests\n<!-- genetic, biochemical, or metabolomic tests -->")

    if num == 7:
        rz = facts.get("pc_resistance")
        # v9.7.372 semantic merge (the patch lane): the publication-quality patch introduced the three
        # adjudication scaffolds but dropped two legacy §7 contract elements pinned since Part C —
        # the "grounded, from cohort precompute" provenance marker and the never-a-phenotype
        # discipline sentence. Both are restored INSIDE the new structure; neither contract loses.
        context = (f"**Similarity-level resistance context (grounded, from cohort precompute):** {rz}\n"
                   "<!-- A resistance-gene family hit is a similarity observation, never a phenotype: "
                   "co-location does not establish self-protection, target identity, or activity. -->\n\n"
                   if rz else "")
        return (context +
                "#### Transport adjudication\n<!-- direction, substrate, pathway coupling -->\n\n"
                "#### Resistance adjudication\n<!-- mechanism-specific evidence versus broad family context -->\n\n"
                "#### Regulation adjudication\n<!-- regulator family, operon hypothesis, unmeasured targets -->\n\n"
                "#### No exact-bound evidence versus biological absence\n"
                "<!-- No exact-bound evidence is not biological absence. -->")

    if num == 18:
        # Wire in the W5 locus-map path if it exists; otherwise note absence
        locus = f"locus_maps/{bgc}_locus_map.svg"
        return (f"**Locus map:** `{locus}` (W5; auto-generated at compile time)\n\n"
                f"<!-- Author: callouts in the locus map worth highlighting. "
                f"Gene coordinates, strand orientation, domain bands. -->")

    if num == 28:
        streams = (
            "antiSMASH", "sealed Mamey", "MIBiG", "BiG-SCAPE", "ClusterBlast",
            "RG-GMCI", "chitin", "resistance", "domain rarity", "literature",
            "prevalence", "historical card", "V7 evidence",
            "current channel-separated BLASTp",
        )
        stream_rows = "\n".join(
            f"| {stream} | <ADMITTED / CONTEXT_ONLY / UNBOUND / ABSENT_IN_SCOPE / SUPERSEDED> | <effect> |"
            for stream in streams
        )
        section_rows = "\n".join(
            f"| §{n} | <SUBSTANTIVE / REASONED_NOT_APPLICABLE> | <named evidence> | "
            "<RETAIN / REFINE / WITHDRAW_WITH_REASON / NOT_APPLICABLE> | <reconciliation note> |"
            for n in range(1, 49)
        )
        return ("**Evidence provenance ledger** (claim-by-claim source tracing).\n\n"
                "| Claim | Evidence type | Source |\n"
                "|---|---|---|\n"
                "| Predicted product class | observed | antiSMASH products field |\n"
                "| Boundary status | observed | antiSMASH region span vs. contig length |\n"
                "| KCB top hit | observed | knownclusterblast output |\n"
                f"| Strain assembly tier | computed | interior_pct={facts.get('interior_pct') or '—'} |\n"
                "| <Author: add claims> | observed / computed / inferred / assumed | <source> |\n\n"
                "#### Evidence-stream disposition\n\n"
                "| Stream | State | Effect on interpretation |\n|---|---|---|\n"
                f"{stream_rows}\n\n"
                "#### Historical source-loss reconciliation\n\n"
                "| Source | Disposition | Retained/refined/withdrawn content and reason |\n|---|---|---|\n"
                "| historical card | <RETAIN / REFINE / WITHDRAW_WITH_REASON / NOT_APPLICABLE> | <detail> |\n"
                "| V7 evidence | <RETAIN / REFINE / WITHDRAW_WITH_REASON / NOT_APPLICABLE> | <detail> |\n"
                "| historical locus map | <RETAIN / REFINE / WITHDRAW_WITH_REASON / NOT_APPLICABLE> | <detail> |\n\n"
                "#### Section-by-section completeness and predecessor reconciliation\n\n"
                "| Section | State | Named evidence used | Predecessor disposition | Reconciliation note |\n"
                "|---|---|---|---|---|\n"
                f"{section_rows}\n")

    if num == 30:
        return ("**Experimental decision tree.** Open questions → "
                "experiments → programme consequences.\n\n"
                "<!-- Author: at least 2 branches. Each branch: "
                "Q[i] → E[i] → C[i] (consequence). Standing rule: the next "
                "experiment or analysis must be specific. -->")

    # Generic fallback — bare prompt
    return f"<!-- Author: §{num} {sect['title']}. {sect['condition_human']} -->"


# ---------------------------------------------------------------------------
# Triage / register helpers
# ---------------------------------------------------------------------------

def _gene_rows_for_bgc(pkg: Path, bgc_id: str) -> list[dict]:
    """Load the per-CDS rows for one BGC from the sealed gene_context.jsonl.

    gene_context.jsonl is one JSON object per line, each carrying a bgc_id (or
    grouped by it, depending on the emitter version). Returns the rows for this
    BGC in genomic order (by start coord). Honest-blank ([]) on any absence or
    parse error — never raises. (v9.7.155)
    """
    rows: list[dict] = []
    # canonical sealed source
    for name in (f"{_strain_prefix(pkg)}_gene_context.jsonl", "gene_context.jsonl"):
        gc = pkg / name
        if not gc.exists():
            continue
        try:
            for line in gc.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                # two shapes: {"bgc_id":..., "row":{...}} OR a flat row with bgc_id,
                # OR {"bgc_id":..., <row fields inline>}. Accept all defensively.
                rid = obj.get("bgc_id") or obj.get("BGC_ID")
                if rid != bgc_id:
                    # some emitters write {bgc_id: [rows]} as a single object
                    if isinstance(obj.get(bgc_id), list):
                        rows.extend(obj[bgc_id])
                    continue
                # current engine shape (gene_context.write_gene_context):
                # {"bgc_id": X, "cds": [ {per-CDS row}, ... ]} — one object per BGC.
                # Without this branch the whole wrapper is appended as a single row and
                # every §4 gene table emits "1 CDS · 0 core" with an empty row.
                if isinstance(obj.get("cds"), list):
                    rows.extend(obj["cds"])
                    continue
                row = obj.get("row") if isinstance(obj.get("row"), dict) else obj
                rows.append(row)
        except (OSError, json.JSONDecodeError):
            continue
        if rows:
            break
    # stable genomic order; rows lacking start sort last
    rows.sort(key=lambda r: (r.get("start") is None, r.get("start") or 0))
    return rows


def _strain_prefix(pkg: Path) -> str:
    """Best-effort strain id for the {strain}_gene_context.jsonl filename."""
    ms = pkg / "manifest_short.json"
    if ms.exists():
        try:
            return json.loads(ms.read_text(encoding="utf-8")).get("strain_id", "") or ""
        except (OSError, json.JSONDecodeError):
            pass
    return ""


def _is_core_gene(row: dict) -> bool:
    """Catalytic-core heuristic: antiSMASH gene_kind == 'biosynthetic', or the CDS
    carries a sec_met domain. Observed classification, not inferred chemistry."""
    if (row.get("gene_kind") or "").lower() == "biosynthetic":
        return True
    return bool(row.get("sec_met_domains"))


def _render_gene_table(rows: list[dict], node: str) -> str:
    """Render a claim-safe per-gene table for §4. Node/contig on every row per the
    standing rule. Columns are all observed fields from gene_context.jsonl — no
    inferred function or product-identity claims. Core genes flagged with ●."""
    if not rows:
        return ("*No per-gene rows available for this BGC in `gene_context.jsonl` "
                "(gene table renders when the sealed gene context is present).*")
    header = (
        "| Core | Locus tag | Node / contig | Start–End | Str | aa | "
        "sec_met domains | TTA | antiSMASH product |\n"
        "|:---:|---|---|---|:---:|---:|---|---:|---|"
    )
    out = [header]
    for r in rows:
        lt = r.get("locus_tag") or "—"
        ctg = r.get("contig") or node or "—"
        start = r.get("start")
        end = r.get("end")
        span = f"{start:,}–{end:,}" if isinstance(start, int) and isinstance(end, int) else "—"
        strand = r.get("strand")
        strand_s = "+" if strand in (1, "+", "1") else "−" if strand in (-1, "-", "-1") else "—"
        aa = r.get("aa_length")
        aa_s = str(aa) if isinstance(aa, int) else "—"
        doms = r.get("sec_met_domains") or []
        doms_s = ", ".join(doms) if isinstance(doms, list) and doms else "—"
        tta = r.get("tta_codons")
        tta_s = str(tta) if isinstance(tta, int) and tta else ("0" if tta == 0 else "—")
        prod = (r.get("product") or "").strip() or "—"
        core = "●" if _is_core_gene(r) else ""
        out.append(
            f"| {core} | `{lt}` | {ctg} | {span} | {strand_s} | {aa_s} | "
            f"{doms_s} | {tta_s} | {prod} |"
        )
    n = len(rows)
    n_core = sum(1 for r in rows if _is_core_gene(r))
    out.append("")
    out.append(f"*{n} CDS in locus · {n_core} catalytic-core (● = antiSMASH "
               f"`gene_kind=biosynthetic` or sec_met domain present). "
               f"All fields observed from `gene_context.jsonl`; product column is "
               f"antiSMASH's annotation, not a product-identity claim.*")
    return "\n".join(out)


def _render_blastp_matrix_scaffold(rows: list[dict]) -> str:
    """Render the canonical §4 channel-matrix authoring scaffold.

    This deliberately emits no hit or state claims. The author replaces each
    placeholder only after exact query/protein binding and keeps nr,
    ClusteredNR, and local Swiss-Prot separate. The publication gate is run on
    the saved authored card, never on this unfilled scaffold.
    """
    header = (
        "| Gene | NCBI nr top hit | NCBI nr identity | "
        "NCBI ClusteredNR top hit | ClusteredNR identity | "
        "Local Swiss-Prot top hit | Swiss-Prot identity |\n"
        "|---|---|---|---|---|---|---|"
    )
    if not rows:
        return (header + "\n"
                "| — | WORKFLOW_GAP_ROSTER_UNAVAILABLE | not reported | "
                "WORKFLOW_GAP_ROSTER_UNAVAILABLE | not reported | "
                "WORKFLOW_GAP_ROSTER_UNAVAILABLE | not reported |")
    output = [header]
    for row in rows:
        locus = row.get("locus_tag") or "—"
        output.append(
            f"| `{locus}` | <accession · matched protein · organism · state> | "
            "<identity / aligned length / qcov> | "
            "<accession · matched protein · organism · state> | "
            "<identity / aligned length / qcov> | "
            "<accession · matched protein · organism · state> | "
            "<identity / aligned length / qcov> |"
        )
    return "\n".join(output)


def _bgc_facts(pkg: Path, bgc_id: str) -> dict:
    """Pull every fact the template can pre-fill from package files."""
    facts: dict = {"bgc_id": bgc_id, "strain_id": "?"}

    # manifest_short
    ms_path = pkg / "manifest_short.json"
    if ms_path.exists():
        try:
            ms = json.loads(ms_path.read_text(encoding="utf-8"))
            facts["strain_id"] = ms.get("strain_id", "?")
            facts["assembly_tier"] = read_manifest_field("assembly_tier", manifest_short=ms, default="—")
            facts["interior_pct"] = read_manifest_field("interior_pct", manifest_short=ms, default="—")
        except (OSError, json.JSONDecodeError):
            pass

    # manifest
    man_path = pkg / "manifest.json"
    if man_path.exists():
        try:
            man = json.loads(man_path.read_text(encoding="utf-8"))
            if facts["strain_id"] == "?":
                facts["strain_id"] = man.get("strain_id", "?")
            facts["taxonomy"] = man.get("taxonomy", "—")
            facts["source"] = man.get("source", "—")
            # v9.7.240 (P1 fallback): authoritative per-region protocluster count,
            # written by parsers.py (P2). Used only when predicted_polymers.csv has
            # no row for this region.
            for _b in man.get("bgcs", []):
                if str(_b.get("bgc_id") or "").strip() == bgc_id:
                    _pc = _b.get("protocluster_count")
                    if isinstance(_pc, int):
                        facts["manifest_protocluster_count"] = _pc
                    break
        except (OSError, json.JSONDecodeError):
            pass

    # Triage row for this BGC
    triage_rows = _read_triage(pkg)
    for r in triage_rows:
        if (r.get("BGC_ID") or r.get("bgc_id") or "").strip() == bgc_id:
            facts.update({
                "node":            (r.get("Node_ID") or r.get("Contig")
                                    or r.get("Node") or "—"),
                "contig":          r.get("Contig") or "—",
                "region":          r.get("antiSMASH_Region") or "—",
                "products":        r.get("Products") or "—",
                "boundary":        r.get("Boundary") or "—",
                "assembly_locator": r.get("Assembly_Locator") or "—",
                "length_kb":       r.get("Length_kb") or "—",
                "ab_score":        r.get("AB_auto") or "—",
                "af_score":        r.get("AF_auto") or "—",
                "novelty":         r.get("Novelty_auto") or "—",
                "novelty_auto":    r.get("Novelty_auto") or "",
                "lead_tier":       r.get("Lead_tier_auto") or "—",
                "lead_tier_auto":  r.get("Lead_tier_auto") or "",
                "corrected_rank":  r.get("Corrected_rank") or "—",
                "kcb_top":         r.get("KCB_top") or "",
                "kcb_score":       r.get("KCB_score") or "—",
                "cctt_triggers":   r.get("CCTT_triggers") or "—",
                "standing_rule":   r.get("Standing_rule") or "",
                "umed_gap_flag":   r.get("UMED_gap") or "",
                # v9.7.343 (surfacing patch): the engine's already-computed capacity
                # verdicts, previously never printed on the per-BGC card (the "GENERIC
                # gap"). Class-level CAPACITY reads, not identity — see card_verdicts.py.
                "arch":            r.get("Arch") or "",
                "arch_capacity":   r.get("Arch_Capacity") or "",
                "class_conf":      r.get("Class_Conf") or "",
                "concordance":     r.get("Concordance") or "",
                "misanchor_flag":  r.get("Misanchor_Flag") or "",
                "primary_metab_flag": r.get("Primary_metab_flag") or "",
            })
            break

    # Roll up strain-level high-priority count for §29 predicate
    n_hp = sum(1 for r in triage_rows
               if (r.get("Lead_tier_auto") or "").upper()
               in ("HIGH", "PRIORITY ISO", "PRIORITY_ISO",
                   "HIGH SEQ", "HIGH_SEQ"))
    facts["strain_high_priority_count"] = n_hp

    # v9.7.155: per-CDS gene rows for this BGC, from the sealed gene_context.jsonl
    # (the durable normalized per-gene source: locus_tag, coords, strand, aa_length,
    # product, sec_met_domains, gene_kind, tta_codons). Feeds the §4 gene table that
    # sits alongside the gene-by-gene prose. Observed data — read straight from the
    # sealed file; honest-blank on absence, never raises.
    facts["gene_rows"] = _gene_rows_for_bgc(pkg, bgc_id)

    # v9.7.343 (surfacing patch): the engine's Diagnostic-Rescue split-pathway
    # reconstruction hypotheses this BGC participates in (core or arm), read from the
    # sealed *_4B_Diagnostic_Rescue_Leads.csv. Homology-guided hypotheses only — not a
    # contig join, not an identity claim. Honest-empty when the file/rows are absent.
    try:
        from . import card_verdicts as _cv
        facts["diagnostic_rescue"] = _cv.rescue_for_bgc(pkg, bgc_id)
    except Exception:
        facts["diagnostic_rescue"] = []

    facts["_pkg"] = str(pkg)  # v9.7.344: for gate-safe #### subsections (modeb_subsections)

    return facts


def _subsec(facts: dict, bgc: str, num: int) -> str:
    """v9.7.344: gate-safe #### subsections (catalytic-domain census, per-channel BLASTp,
    gene-based ClusterBlast, Good Guess, genus literature). Defensive: never breaks the card."""
    try:
        from . import modeb_subsections as _ms
        return _ms.render_for_section(facts.get("_pkg", ""), bgc, num)
    except Exception:
        return ""


def _read_triage(pkg: Path) -> list[dict]:
    candidates = sorted(pkg.glob("*_4_triage_board.csv"))
    if not candidates:
        return []
    try:
        with open(candidates[0], newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except (OSError, csv.Error):
        return []


def _select_scope(pkg: Path, triage_rows: list[dict],
                  scope: str, top_n: Optional[int]) -> list[str]:
    if scope == "leads":
        return [(r.get("BGC_ID") or r.get("bgc_id") or "").strip()
                for r in triage_rows
                if (r.get("Lead_tier_auto") or "").upper()
                in ("EXCEPTIONAL", "HIGH", "PRIORITY ISO", "PRIORITY_ISO",
                    "HIGH SEQ", "HIGH_SEQ")]

    if scope == "pending":
        # Pending in register
        strain = (triage_rows[0].get("BGC_ID") or "").split("_")[0] if triage_rows else ""
        # Better — read register directly
        regs = sorted(pkg.glob("*_judgment_register.json"))
        if not regs:
            return [(r.get("BGC_ID") or "").strip() for r in triage_rows]
        try:
            reg = json.loads(regs[0].read_text(encoding="utf-8"))
            bgcs = reg.get("bgcs", {})
            return [bid for bid, entry in bgcs.items()
                    if entry.get("status") != "COMPLETE"]
        except (OSError, json.JSONDecodeError):
            return [(r.get("BGC_ID") or "").strip() for r in triage_rows]

    if scope == "top":
        if top_n is None:
            top_n = 10
        def _rank(r):
            try:
                return float(r.get("Corrected_rank") or r.get("Rank") or 1e9)
            except (TypeError, ValueError):
                return 1e9
        return [(r.get("BGC_ID") or "").strip()
                for r in sorted(triage_rows, key=_rank)[:top_n]]

    # default: all
    return [(r.get("BGC_ID") or r.get("bgc_id") or "").strip()
            for r in triage_rows
            if (r.get("BGC_ID") or r.get("bgc_id"))]


def _write_index(out_dir: Path, pkg: Path, emitted: list[str],
                 skipped: dict[str, str], scope: str,
                 top_n: Optional[int]) -> None:
    triage_rows = {r.get("BGC_ID") or r.get("bgc_id"): r
                   for r in _read_triage(pkg)}
    lines = [f"# Mode B template batch — {pkg.parent.name}",
             "",
             f"Scope: `{scope}`" + (f", top {top_n}" if top_n else ""),
             f"Emitted: {len(emitted)} | Skipped: {len(skipped)}",
             "",
             "## Card index (work in this order)",
             "",
             "| Rank | BGC | Node | Class | Lead | KCB top |",
             "|---|---|---|---|---|---|"]
    for bgc_id in emitted:
        r = triage_rows.get(bgc_id, {})
        node = r.get("Node_ID") or r.get("Contig") or "—"
        lines.append(
            f"| {r.get('Corrected_rank') or '—'} | "
            f"{bgc_id} | {node} | {r.get('Products') or '—'} | "
            f"{r.get('Lead_tier_auto') or '—'} | "
            f"{r.get('KCB_top') or '—'} |"
        )
    if skipped:
        lines.append("")
        lines.append("## Skipped")
        for bid, reason in skipped.items():
            lines.append(f"- {bid}: {reason}")
    _index_path = out_dir / "_INDEX.md"
    _index_tmp = _index_path.with_name(_index_path.name + ".tmp")
    _index_tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _index_tmp.replace(_index_path)


def emit_database_packet_sections(packet, *, packet_locator, manifest_locator):
    """Render a partial section prototype from a source-verified evidence packet."""
    from .modeb_evidence_packet import render_packet_sections
    return render_packet_sections(packet, packet_locator=packet_locator, manifest_locator=manifest_locator)
