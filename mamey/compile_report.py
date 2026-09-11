"""compile_report.py — deterministic assembler for the §13 compiled analysis report.

THE PROBLEM
-----------
The compiled report (execution-slice §13) is a 14-section master deliverable. Most of
those sections are mechanical: the cover block is "pull from manifest deterministically",
the triage board is the package's `_4_triage_board.csv` rendered as a table, the Mode B
section is the completed cards concatenated *in full*, the figures section is the PNGs in
the package embedded with captions. Today the LLM stitches all of that by hand — which is
slow, fatigue-prone, and the source of the TOC/page-number disasters §13 documents (a TOC
"53 pages off by the final section").

THE FIX
-------
Invert the workflow. Python assembles the full skeleton in the exact §13 order and fills
every *deterministic* section from disk. The only things left for the judgment layer are
the genuinely generative narrative sections (executive summary, layperson guide, ecological
synthesis, priority deep-dives), which are emitted as clearly-labelled fill-in slots:

    <!-- SAPOTE:executive_summary -->
    *(Sapote: write the executive summary here — 5–10 claim-safe sentences.)*
    <!-- /SAPOTE:executive_summary -->

If a narrative section already exists on disk (e.g. `judgment/<strain>_laypersons_section.md`),
it is inlined instead of left as a slot. So a fully-prepared package compiles to a finished
report with zero LLM time; a partial one compiles to a skeleton with the prose gaps marked.

The output is pandoc-ready Markdown with `toc: true` front-matter, so the TOC and page numbers
are computed by LaTeX at render time — never hand-estimated. Pure read of the package; the
only write is the output file the caller names.

Claim-safety is structural: deterministic sections only restate fields the package already
contains (class capacity, KCB similarity, contig/node citations); no phenotype or identity
language is synthesised here.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import contextlib
import csv
import json
from pathlib import Path
from typing import Any

from . import judgment_store as js
from . import BUNDLE_VERSION as _ACTIVE_BUNDLE_VERSION
from .manifest_schema import (
    read_manifest_field, F_ASSEMBLY_TIER, F_INTERIOR_PCT, F_RAW_BGCS,
    F_CORRECTED_BGCS, F_N50, F_CONTIGS, F_MODE, F_ISSUES,
)
from .figure_policy import FigurePolicyError, PUBLICATION_PROFILES, validate_publication_artwork

# ── SSOT: every openable SAPOTE:<key> slot in a compiled report ────────────────
# MB-02 (v9.7.338): build_report emits SIX SAPOTE markers, but NARRATIVE_SLOTS / write-narrative only
# knew FOUR — `blastp_evidence` and `fermentation` were openable-but-unfillable, so `--strict` was
# unsatisfiable and its remediation ("fill the SAPOTE slots") was wrong for those two. Fix: ONE table
# of every openable marker, each tagged with a `kind`:
#   - "narrative"            → authored via `mamey write-narrative --section <key>` (claim-safety linted).
#   - "deterministic-source" → filled by supplying the source artifact on disk / re-compiling; NOT a
#                              write-narrative section. Carries its own remediation string.
# open_slots(), classify_open_slots(), compile-report --strict, and write_narrative() all consult this.
SLOT_KIND_NARRATIVE = "narrative"
SLOT_KIND_DETERMINISTIC = "deterministic-source"

# key -> dict(kind, heading, filename-template|None, prompt, remediation). Declared in §13 report order,
# narrative slots first (so the derived NARRATIVE_SLOTS view keeps its historical order + shape).
SLOT_REGISTRY: dict[str, dict[str, Any]] = {
    "executive_summary": {
        "kind": SLOT_KIND_NARRATIVE,
        "heading": "2. Executive summary",
        "filename": "{strain}_execsummary_section.md",
        "prompt": ("write 5–10 claim-safe sentences: what the strain is, what the assembly quality "
                   "means for confidence, the top 3–5 leads by class, the single most important action."),
        "remediation": "author it: `mamey write-narrative <pkg> --section executive_summary --file <md>`",
    },
    "layperson_guide": {
        "kind": SLOT_KIND_NARRATIVE,
        "heading": "3. Layperson guide",
        "filename": "{strain}_laypersons_section.md",
        "prompt": "plain English for a PI who does not know antiSMASH; must stand alone.",
        "remediation": "author it: `mamey write-narrative <pkg> --section layperson_guide --file <md>`",
    },
    "ecological_synthesis": {
        "kind": SLOT_KIND_NARRATIVE,
        "heading": "7. Cross-strain and ecological synthesis",
        "filename": "{strain}_ecology_section.md",
        "prompt": "what this strain contributes to the cohort; mechanism not phenotype, capacity not activity.",
        "remediation": "author it: `mamey write-narrative <pkg> --section ecological_synthesis --file <md>`",
    },
    "priority_deep_dives": {
        "kind": SLOT_KIND_NARRATIVE,
        "heading": "8. Priority lead deep-dives",
        "filename": "{strain}_deepdives_section.md",
        "prompt": "one synthesised narrative per top 3–5 BGC (NOT a copy of the Mode B card).",
        "remediation": "author it: `mamey write-narrative <pkg> --section priority_deep_dives --file <md>`",
    },
    "blastp_evidence": {
        "kind": SLOT_KIND_DETERMINISTIC,
        "heading": "10. BLASTP evidence summary",
        "filename": None,
        "prompt": "",
        "remediation": ("NOT a write-narrative section — run the BLASTP rounds and re-compile so the "
                        "evidence store (`BLASTP_BGC_summary[_all_rounds].csv`) is present in the "
                        "package, or fill this deterministic slot manually."),
    },
    "fermentation": {
        "kind": SLOT_KIND_DETERMINISTIC,
        # AUDIT_374: was "{strain}_fermentation.md" / "judgment/<strain>_fermentation.md" in
        # both this field and the remediation string below — the WRONG filename. The function that
        # actually inlines this section, _ferm_section() -> judgment_store._fermentation_path(),
        # reads "{strain}_fermentation_section.md" (matching judgment_store.py's own module
        # docstring and every doc reference: docs/modules/MODE_B_WRITE.md,
        # docs/reference/03_Plumbing_Reference.md, docs/user_guides/comprehensive_glossary.md).
        # An author who followed this printed remediation text literally had their real authored
        # fermentation guidance silently ignored — _ferm_section() never found it at the wrong
        # path, fell back to the generic deterministic draft, and gave no warning either way.
        "heading": "11. Fermentation and wet-lab guidance",
        "filename": "{strain}_fermentation_section.md",
        "prompt": "",
        "remediation": ("NOT a write-narrative section — author `judgment/<strain>_fermentation_section.md` "
                        "(media, additives, timepoints, extraction, detection); it is inlined from disk."),
    },
}

# Backward-compatible view: the narrative-writable slots as (heading, filename, prompt), in report
# order. Other modules import NARRATIVE_SLOTS / STRICT_NARRATIVE_KEYS — keep their shape stable.
NARRATIVE_SLOTS = {
    k: (v["heading"], v["filename"], v["prompt"])
    for k, v in SLOT_REGISTRY.items() if v["kind"] == SLOT_KIND_NARRATIVE
}

# Public alias for the narrative section keys that `compile-report --strict`
# requires to be present on disk. Single source of truth — other modules
# (e.g. session_resume's strict-runnable probe, the new write-narrative
# subcommand) import from here to stay in sync. (W3 + W1-F5, v9.7.149c.)
STRICT_NARRATIVE_KEYS = tuple(NARRATIVE_SLOTS.keys())


def classify_open_slots(markdown: str) -> list[dict]:
    """Every still-open SAPOTE slot in an assembled report with its kind + remediation (SSOT:
    SLOT_REGISTRY). Lets --strict emit per-kind guidance instead of a blanket 'fill the slots'."""
    out = []
    for key in open_slots(markdown):
        meta = SLOT_REGISTRY.get(key)
        if meta is None:
            out.append({"key": key, "kind": "unknown",
                        "remediation": "unknown SAPOTE slot key — not registered in SLOT_REGISTRY."})
        else:
            out.append({"key": key, "kind": meta["kind"], "remediation": meta["remediation"]})
    return out


def narrative_filename(key: str, strain: str) -> str:
    """Return the on-disk filename for a narrative section key, or '' if
    the key has no disk-backed slot.

    Used by `mamey write-narrative` and by session_resume's strict-runnable
    probe to resolve `judgment/<filename>` without re-encoding the mapping.
    """
    if key not in NARRATIVE_SLOTS:
        return ""
    _, fname_tmpl, _ = NARRATIVE_SLOTS[key]
    if not fname_tmpl:
        return ""
    return fname_tmpl.format(strain=strain)


# ── manifest read (mirrors explain / session_resume) ───────────────────────────

def _read_manifests(pkg: Path) -> dict[str, Any]:
    ms, man = {}, {}
    manifest_read_status = "RECORDED"
    if (pkg / "manifest_short.json").exists():
        try:
            ms = json.loads((pkg / "manifest_short.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
            ms = {}
            manifest_read_status = f"INVALID_MANIFEST_SHORT: {type(exc).__name__}"
    if (pkg / "manifest.json").exists():
        try:
            man = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
            man = {}
            manifest_read_status = f"INVALID_MANIFEST: {type(exc).__name__}"
    return {
        "manifest_read_status": manifest_read_status,
        "strain_id": ms.get("strain_id") or man.get("strain_id") or pkg.parent.name,
        "taxonomy": man.get("taxonomy") or "not verified",
        "source": man.get("source") or "not supplied",
        # v9.7.160: via canonical accessor. It knows manifest_short wins, then the
        # nested manifest.json["assembly"] location (the v9.7.156 vintage-package fallback
        # for n50/contigs is now built into read_manifest_field, not hand-rolled here).
        "assembly_tier": read_manifest_field(F_ASSEMBLY_TIER, manifest=man, manifest_short=ms, default="unknown"),
        "interior_pct": read_manifest_field(F_INTERIOR_PCT, manifest=man, manifest_short=ms),
        "raw_bgcs": read_manifest_field(F_RAW_BGCS, manifest=man, manifest_short=ms, default="?"),
        "corrected_bgcs": read_manifest_field(F_CORRECTED_BGCS, manifest=man, manifest_short=ms, default="?"),
        "n50": read_manifest_field(F_N50, manifest=man, manifest_short=ms, default="?"),
        "contigs": read_manifest_field(F_CONTIGS, manifest=man, manifest_short=ms, default="?"),
        # v9.7.153 (Part-2 Finding 6): legacy manifests predating the bundle_version
        # field rendered a bare "?" with no indication that this package is correct,
        # not broken — just old. Fall back to the bundle that's actually doing the
        # compiling, labelled so it's clearly the renderer's version, not the
        # original run's, when the two may differ.
        "bundle_version": man.get("bundle_version") or f"{_ACTIVE_BUNDLE_VERSION} (compiler; not recorded at run time)",
        "release": (man.get("release") or "").upper(),
        "mamey_version": ms.get("mamey_version") or "?",
        "mode": read_manifest_field(F_MODE, manifest=man, manifest_short=ms, default="?"),
        # BCHERRY-374 (rebased to .375b): run-level red flags (CONTAMINATION_SUSPECT,
        # RECORD_LIMIT_TRUNCATION, MULTIBATCH, OVER_MERGE_CANDIDATES, …) — deterministic engine
        # findings on manifest.json; previously never read, so the compiled report carried zero
        # indication a run had them even when its assembly is contamination-suspect or truncated.
        "issues": read_manifest_field(F_ISSUES, manifest=man, manifest_short=ms, default=[]) or [],
    }


def _triage_rows(pkg: Path) -> tuple[list[str], list[dict]]:
    csvp = next(pkg.glob("*_4_triage_board.csv"), None) or next(pkg.glob("*triage_board.csv"), None)
    if not csvp:
        return [], []
    with csvp.open(newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        rows = list(rd)
        return (rd.fieldnames or []), rows


def _node_label(row: dict) -> str:
    """§15: every BGC reference carries node + region, never bare.
    Tolerant of the several column spellings the CSV may use."""
    bid = row.get("BGC_ID") or row.get("bgc_id") or "?"
    node = (row.get("Node_ID") or row.get("contig/NODE") or row.get("Contig")
            or row.get("node") or "").strip()
    region = (row.get("antiSMASH_Region") or row.get("region") or "").strip()
    if node and region:
        return f"{bid} ({node} · {region})"
    if node:
        return f"{bid} ({node})"
    return bid  # honest: no node available rather than a fabricated one


# ── deterministic §12: wet-lab decision matrix derived from triage columns ──────

# Standing-rule / primary-metabolism classes are excluded by the user's conventions
# (saccharide; NAPAA; hglE-KS-PREV-001; NI-siderophore; NRP-metallophore). Mirrored here so the
# matrix is rule-driven. BH-007/BH-007b (mamey/data/rules_registry.json): NI-SIDEROPHORE and
# NRP-METALLOPHORE are permanent, lead_blocking downgrade rules with the same "never surfaced as
# a discovery lead" intent as SACCHARIDE, but their standing_rule_flag strings
# ("NI-siderophore-exclusion" / "NRP-metallophore-exclusion", mamey/scoring.py::_RULE_FLAG) were
# never added to this tuple, so a BGC the scorer already dropped from the corrected lead order
# (empty Corrected_rank) still renders HIGH SEQ / isolation-candidate in the wet-lab matrix.
# Live-reproduced on a real AS-XXX gold-mode run: BGC007 and BGC009 (both
# Standing_rule=NI-siderophore-exclusion, Corrected_rank empty) rendered "HIGH SEQ" instead of
# "EXCL" in AS-XXX_compiled_report.md §12.
_EXCL_TOKENS = ("saccharide", "napaa", "hgle-ks-prev", "ni-siderophore", "nrp-metallophore", "primary")


def _decision_for(row: dict) -> tuple[str, str]:
    """Return (action, rationale) for one triage row, derived deterministically.
    Vocabulary per §13.12: PRIORITY ISO / HIGH SEQ / MEDIUM ACT / LOW / EXCL, with
    UNRESOLVED reserved for malformed numeric source values that cannot safely be scored."""
    standing = (row.get("Standing_rule") or row.get("Downgrade") or "").strip().lower()
    primary = (row.get("Primary_metab_flag") or "").strip().lower()
    # v9.7.377 (AUDIT audit): scoring.py leaves Corrected_rank BLANK for every one of its
    # three lead-exclusion reasons (standing_rule_flag, primary_metabolism_flag, OR
    # mobile_element_flag — scoring.py:737's three-flag gate), but only the first two are
    # detectable here by text-matching Standing_rule/Primary_metab_flag. A mobile-element-only
    # exclusion leaves BOTH those columns empty, so without this check the row fell through to
    # the rank-tier branches below, where the `row.get("Rank")` fallback (the RAW, PRE-EXCLUSION
    # rank, always populated 1..N for every row regardless of exclusion) could resurrect an
    # engine-excluded BGC as high as PRIORITY ISO — silently contradicting the exclusion
    # scoring.py already made (live-reproduced: Standing_rule="", Primary_metab_flag="",
    # Corrected_rank="", Rank="1", AB_auto=0.95 -> pre-fix returned PRIORITY ISO). A
    # present-but-blank Corrected_rank is itself the authoritative, already-available signal for
    # all three reasons — no new column is needed (unlike the sibling tranche5 figure-layer fix,
    # which had to plumb mobile_element_flag through verdicts.json because the figure bundle had
    # no equivalent column at all). A genuinely legacy package predating this column (key ABSENT
    # from the row, not merely blank) still falls back to the pre-existing Rank behaviour below.
    corrected_rank_col_present = "Corrected_rank" in row
    corrected_rank_value = row.get("Corrected_rank")
    corrected_rank_blank = (corrected_rank_col_present
                            and (corrected_rank_value is None
                                 or (isinstance(corrected_rank_value, str)
                                     and not corrected_rank_value.strip())))
    if any(tok in standing for tok in _EXCL_TOKENS) or primary in ("1", "true", "yes") or corrected_rank_blank:
        return "EXCL", (f"standing-rule / primary-metabolism / mobile-element exclusion "
                        f"({standing or primary or 'engine-excluded (corrected_rank blank)'})")
    novelty = (row.get("Novelty_auto") or row.get("novelty_auto") or "").strip().upper()
    tier = (row.get("Lead_tier_auto") or "").strip().upper()
    def _f(k):
        raw = row.get(k)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return 0.0, False
        try:
            return float(raw), False
        except (TypeError, ValueError):
            return 0.0, True
    (ab, ab_invalid), (af, af_invalid) = _f("AB_auto"), _f("AF_auto")
    invalid_fields = [name for name, invalid in (
        ("AB_auto", ab_invalid), ("AF_auto", af_invalid),
    ) if invalid]
    if invalid_fields:
        return "UNRESOLVED", f"invalid numeric triage field(s): {', '.join(invalid_fields)}"
    score = max(ab, af)
    # rank-aware top leads get isolation priority
    rank_raw = row.get("Corrected_rank") or row.get("Rank")
    try:
        crank = int(rank_raw) if rank_raw not in (None, "") else 999
    except (TypeError, ValueError):
        return "UNRESOLVED", "invalid numeric triage field: Corrected_rank/Rank"
    if crank <= 3 and score >= 0.8:
        return "PRIORITY ISO", f"top-rank lead (rank {crank}), strong score {score:.2f}"
    if crank <= 3 and novelty == "HIGH" and score >= 0.5:
        return "PRIORITY ISO", f"top-rank novel lead (rank {crank}), novelty HIGH, score {score:.2f}"
    if novelty == "HIGH" or score >= 0.7:
        return "HIGH SEQ", f"high-novelty/score (score {score:.2f}, novelty {novelty or 'n/a'})"
    if score >= 0.4:
        return "MEDIUM ACT", f"moderate signal (score {score:.2f})"
    return "LOW", f"low signal (score {score:.2f})"


def _decision_matrix(pkg: Path) -> str:
    fields, rows = _triage_rows(pkg)
    if not rows:
        return "# 12. Wet-lab decision matrix\n\n*(triage board CSV not found in package)*\n"
    out = ["# 12. Wet-lab decision matrix\n",
           "*Derived deterministically from the triage board (rank, score, novelty, standing rule).*\n",
           "| BGC (node · region) | Action | Dereplicate | Rationale |",
           "|---|---|---|---|"]
    for r in rows:
        action, why = _decision_for(r)
        # dereplicate flag: a named KCB hit means a known scaffold to dereplicate against
        kcb = (r.get("KCB_top") or r.get("kcb_top") or "").strip()
        derep = "yes" if kcb and kcb.lower() not in ("none", "") else "no"
        out.append(f"| {_node_label(r)} | {action} | {derep} | {why} |")
    return "\n".join(out) + "\n"


# ── deterministic §10: BLASTP evidence summary from the evidence store ──────────

def _find_blastp_summary(pkg: Path) -> Path | None:
    """Locate the BGC-level BLASTP summary CSV the evidence store writes.
    Prefers the cumulative all-rounds table; falls back to a per-round one."""
    candidates = list(pkg.rglob("BLASTP_BGC_summary_all_rounds.csv")) \
        or list(pkg.rglob("BLASTP_BGC_summary.csv"))
    return candidates[0] if candidates else None


def _blastp_from_channel_stores(pkg: Path) -> str:
    """v9.7.344: fill the BLASTP-evidence slot deterministically from the package's INTERNAL,
    unmixed channel stores (blastp_nr/blastp_clustered_nr/blastp_swissprot/blastp_ebi). Shows best
    %identity AND %positives per channel — never conflated. Similarity, not identity."""
    stores = [("blastp_nr", "nr"), ("blastp_clustered_nr", "clustered_nr"),
              ("blastp_cluster_nr", "clustered_nr"),
              ("blastp_swissprot", "swissprot"), ("blastp_ebi", "ebi")]
    present = [(pkg / d, lab) for d, lab in stores if (pkg / d).is_dir()]
    if not present:
        return ""
    # per BGC: best rank-1 %id/%pos + nearest title, per channel
    by_bgc: dict[str, dict] = {}
    read_failures: dict[str, int] = {}
    for sdir, lab in present:
        for f in sorted(sdir.glob("*_top10.csv")):
            bgc = f.name.split("_top10")[0]
            try:
                with f.open(newline="", encoding="utf-8") as handle:
                    reader = csv.DictReader(handle)
                    required = {"hit_rank", "pct_identity", "pct_positives"}
                    if required - set(reader.fieldnames or []):
                        raise ValueError("missing required BLASTP columns")
                    rows = [r for r in reader if str(r.get("hit_rank", "")).strip() == "1"]
                for row in rows:
                    float(row.get("pct_identity"))
                    float(row.get("pct_positives"))
            except (OSError, UnicodeDecodeError, csv.Error, ValueError, TypeError):
                read_failures[lab] = read_failures.get(lab, 0) + 1
                continue
            if not rows:
                continue
            def _f(r, k):
                return float(r[k])
            best = max(rows, key=lambda r: _f(r, "pct_identity"))
            # Canonical store is enumerated before the legacy spelling and wins
            # when a transition package happens to carry both.
            by_bgc.setdefault(bgc, {}).setdefault(lab, (
                _f(best, "pct_identity"), _f(best, "pct_positives"),
                (best.get("subject_def", "") or "")[:38]))
    if not by_bgc and not read_failures:
        return ""
    out = ["# 10. BLASTP evidence summary\n",
           "*Per-BGC BLASTP from the package's internal, unmixed channel stores. Best rank-1 hit per "
           "channel; **%ID and %positives shown separately** (similarity, not identity; per-gene top-10 "
           "with both metrics are in `blastp_nr/`, `blastp_clustered_nr/`, `blastp_swissprot/`).*\n",
           "| BGC | channel | best %ID | best %pos | nearest subject |",
           "|---|---|--:|--:|---|"]
    if read_failures:
        detail = ", ".join(f"{channel}={count}" for channel, count in sorted(read_failures.items()))
        out.insert(2, f"**BLASTP_CHANNEL_INPUT_INVALID:** unreadable top-10 table count by channel: {detail}. "
                      "These files were not interpreted as no-hit evidence.\n")
    for bgc in sorted(by_bgc, key=lambda b: int("".join(ch for ch in b if ch.isdigit()) or 0)):
        for lab, (pid, pos, title) in by_bgc[bgc].items():
            out.append(f"| {bgc} | {lab} | {pid:.0f}% | {pos:.0f}% | {_md_cell(title)} |")
    return "\n".join(out) + "\n"


def _md_cell(text) -> str:
    """v9.7.410 hostile audit: BLAST subject titles are external text and the classic NCBI form
    carries pipes (`gi|123|ref|WP_…`). Unescaped, one such title split the compiled report's
    evidence table into extra columns and shifted every later cell under the wrong header."""
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def _blastp_summary(pkg: Path) -> str:
    csvp = _find_blastp_summary(pkg)
    if not csvp:
        # v9.7.344: before declaring the slot open, try the internal channel stores.
        from_stores = _blastp_from_channel_stores(pkg)
        if from_stores:
            return from_stores
        return ("# 10. BLASTP evidence summary\n\n"
                "<!-- SAPOTE:blastp_evidence -->\n"
                "*(No BLASTP evidence store in package. If BLASTP rounds were run, point "
                "compile-report at the store, or fill this slot manually.)*\n"
                "<!-- /SAPOTE:blastp_evidence -->\n")
    with csvp.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return "# 10. BLASTP evidence summary\n\n*(BLASTP summary table is empty)*\n"
    out = ["# 10. BLASTP evidence summary\n",
           "*Class-defining BGC-level BLASTP evidence (similarity, not identity).*\n",
           "| BGC | Top titles | Best %ID | Coverage | Claim level | Next action |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        bid = r.get("bgc_id", "?")
        out.append(
            f"| {bid} | {_md_cell((r.get('top_titles','') or '')[:60])} | "
            f"{r.get('best_pct_identity','')} | {r.get('best_query_coverage','')} | "
            f"{r.get('current_claim_level','')} | {_md_cell((r.get('recommended_next_action','') or '')[:50])} |")
    return "\n".join(out) + "\n"


def _slot(key: str, strain: str, pkg: Path) -> str:
    heading, fname, prompt = NARRATIVE_SLOTS[key]
    body = None
    if fname:
        # F2 (v9.7.149c): use read-only variant so a probe doesn't create
        # an empty judgment/ directory in a package that has none.
        p = js._judgment_dir_read(pkg) / fname.format(strain=strain)
        if p.exists():
            body = p.read_text(encoding="utf-8").strip()
    if body:
        return f"# {heading}\n\n{body}\n"
    return (f"# {heading}\n\n"
            f"<!-- SAPOTE:{key} -->\n"
            f"*(Sapote: {prompt})*\n"
            f"<!-- /SAPOTE:{key} -->\n")


# ── section builders (deterministic) ───────────────────────────────────────────

def _cover(m: dict) -> str:
    tag = f"  ·  **{m['release']}**" if m["release"] in ("PRIVATE", "MERGED-PRIVATE") else ""
    manifest_status = m.get("manifest_read_status", "RECORDED")
    manifest_note = (f"\n\n*Manifest input status: {manifest_status}; report fields use typed fallbacks.*"
                     if manifest_status != "RECORDED" else "")
    return (f"# {m['strain_id']} — Compiled Analysis Report\n\n"
            f"*{m['taxonomy']}* · {m['source']}{tag}\n\n"
            f"Assembly: {m['assembly_tier']}"
            + (f" ({m['interior_pct']}% interior)" if m['interior_pct'] is not None else "")
            + f" · {m['raw_bgcs']} raw / {m['corrected_bgcs']} corrected BGCs · "
            f"Mamey v{m['mamey_version']} · bundle {m['bundle_version']}\n"
            + manifest_note)


def _assembly_table(m: dict) -> str:
    out = ("# 4. Assembly and strain summary\n\n"
           "| Field | Value |\n|---|---|\n"
           f"| Taxonomy | {m['taxonomy']} |\n"
           f"| Source (host / location) | {m['source']} |\n"
           f"| Assembly tier | {m['assembly_tier']}"
           + (f" ({m['interior_pct']}% interior)" if m['interior_pct'] is not None else "") + " |\n"
           f"| Raw / corrected BGCs | {m['raw_bgcs']} / {m['corrected_bgcs']} |\n"
           f"| N50 | {m['n50']} |\n"
           f"| Contigs | {m['contigs']} |\n"
           f"| Analysis mode | {m['mode']} |\n")
    issues = m.get("issues") or []
    if issues:
        out += ("\n**Run-level issues** (deterministic engine flags, not interpretation — carry "
                "these into any caption or sign-off note before presenting figures/tables below):\n\n")
        for issue in issues:
            if str(issue).startswith("[CLAIM-SAFETY REFUSAL] auto-emitted compiled report WITHHELD:"):
                # Keep the historical refusal visible without importing its rejected
                # prose into a newly assembled report. Original diagnostics are immutable.
                out += ("- A previous automatic compiled report was withheld by the claim-language "
                        "check. Its original diagnostic remains in the source package's "
                        "`manifest.json` issues field; this report is checked afresh.\n")
            else:
                out += f"- {issue}\n"
    return out


def _triage_board(pkg: Path) -> str:
    fields, rows = _triage_rows(pkg)
    if not rows:
        return "# 5. Triage board\n\n*(triage board CSV not found in package)*\n"
    # render every BGC, no omissions; preserve CSV column order
    head = "| " + " | ".join(fields) + " |\n"
    sep = "|" + "|".join("---" for _ in fields) + "|\n"
    body = "".join("| " + " | ".join(str(r.get(c, "")) for c in fields) + " |\n" for r in rows)
    return f"# 5. Triage board (all BGCs)\n\n{head}{sep}{body}"


def _figures(pkg: Path, generate: bool = True, preflight_note: str = "") -> str:
    # N3 (v9.7.149c): walk both *.png and *.svg so locus_maps/*.svg from W5
    # are picked up alongside raster figures. The markdown image syntax
    # `![alt](path.svg)` is valid for pandoc → LaTeX (PDF) and for HTML.
    pngs = sorted([p for p in pkg.rglob("*.png")])
    svgs = sorted([p for p in pkg.rglob("*.svg")])
    figs = pngs + svgs
    note = preflight_note
    if not figs and generate:
        # §13 Step 1/2: try to populate figures from already-extracted CSVs before giving up.
        # Best-effort and non-blocking — figure generation needs matplotlib; if it isn't
        # available the report still assembles, with an honest note (mirrors the engine's
        # own GOLD_FIGURES_SKIPPED behaviour).
        made = _try_generate_figures(pkg)
        pngs = sorted([p for p in pkg.rglob("*.png")])
        svgs = sorted([p for p in pkg.rglob("*.svg")])
        figs = pngs + svgs
        if not figs:
            if made == "ERROR":
                # AUDIT_374: made=="ERROR" means cohort_figures.generate() itself
                # raised (a real bug — bad CSV schema, KeyError, etc.), NOT an absent
                # dependency or missing source CSV. Say so; the blanket message below was
                # actively misleading a reader into chasing the wrong root cause.
                note += ("\n*(Figure generation raised an error — this looks like a real bug, "
                         "not a missing dependency or missing source CSV. Check the "
                         "compile-report run log for the traceback, then re-run "
                         "`mamey render-figures` / `cohort-figures` directly to reproduce.)*\n")
            else:
                note += ("\n*(No figures could be generated — matplotlib unavailable or no figure "
                         "source CSVs in package. Run `mamey render-figures` / `cohort-figures`, "
                         "or `tools/build_first_pass_scans.py`, then re-compile.)*\n")
        elif made:
            note += f"\n*(Figures generated at compile time: {made}.)*\n"
    if not figs:
        return "# 6. Figures\n" + (note or "\n*(no figures in package)*\n")
    out = ["# 6. Figures\n"]
    for p in figs:
        rel = p.relative_to(pkg)
        out.append(f"![{rel.stem}]({rel})\n\n*Figure: {rel.stem.replace('_',' ')}.*\n")
    return "\n".join(out) + note


def _try_generate_figures(pkg: Path) -> str:
    """Attempt §13 Step-1 per-strain figures from the triage CSV. Returns a short
    description of what was made, or '' on any failure. Never raises."""
    try:
        from . import cohort_figures  # noqa: F401  (import guard: matplotlib present?)
    except Exception:
        return ""
    try:
        # runs_dir is two levels up from package (same relation the engine uses)
        runs_dir = pkg.parent.parent
        strain = _read_manifests(pkg)["strain_id"]
        from .cohort_figures import generate as _gen
        res = _gen(runs_dir=str(runs_dir), out=str(pkg / "compile_figures"), strains=[strain])
        n = (res or {}).get("figures", 0)
        return f"{n} figure(s)" if n else ""
    except Exception as exc:
        # AUDIT_374: this used to swallow ANY exception — including a genuine bug in
        # cohort_figures.generate() (bad CSV schema, KeyError, etc.), not just an absent
        # dependency — and the caller's fallback note then asserted a specific, false cause
        # ("matplotlib unavailable or no figure source CSVs"). Surface the real exception to
        # stderr (never blocking; the report still assembles) and tell the caller this was a
        # crash, not an absence, via the "ERROR" sentinel so §6 can say so honestly.
        import sys, traceback
        emit(f"  WARNING: figure generation crashed ({type(exc).__name__}: {exc}) — "
              f"§6 will flag this as an error rather than 'no figures available'.",
              file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return "ERROR"


def _mode_b_cards(pkg: Path) -> str:
    complete = js.list_complete_bgcs(pkg) if js._register_path(pkg).exists() else []
    out = ["# 9. Complete Mode B cards\n"]
    if not complete:
        out.append("*(no completed Mode B cards in the register)*\n")
        return "\n".join(out)
    for bid in complete:
        card = js._mode_b_path(pkg, bid)
        if card.exists():
            out.append("\n---\n")
            out.append(card.read_text(encoding="utf-8").strip() + "\n")
        else:
            out.append(f"\n---\n\n*(card file missing for {bid} — register says COMPLETE; investigate)*\n")
    return "\n".join(out)


def _fermentation_draft(pkg: Path) -> str:
    """v9.7.344: deterministic bench/fermentation DRAFT from genus + dominant product classes, so the
    slot fills to a usable starting point (the author refines it). Guidance only — no result claim."""
    # dominant non-housekeeping classes from the triage board
    tb = next(iter(pkg.glob("*_4_triage_board.csv")), None)
    classes: list[str] = []
    source_notes: list[str] = []
    if tb:
        try:
            import collections
            c = collections.Counter()
            for r in csv.DictReader(tb.open(newline="", encoding="utf-8")):
                for p in (r.get("Products", "") or "").replace(",", ";").split(";"):
                    p = p.strip().lower()
                    if p and p not in ("terpene", "ectoine", "other", "saccharide", "carotenoid",
                                       "hopene", "arylpolyene", "melanin", "napaa", "betalactone"):
                        c[p] += 1
            classes = [k for k, _ in c.most_common(6)]
        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            source_notes.append(f"TRIAGE_INPUT_INVALID:{type(exc).__name__}")
    genus = ""
    try:
        from . import modeb_subsections as _ms
        genus = _ms._genus_of(pkg)
    except Exception as exc:
        source_notes.append(f"GENUS_INPUT_INVALID:{type(exc).__name__}")
    class_notes = []
    joined = " ".join(classes)
    if "ripp" in joined or "lanthipeptide" in joined or "lassopeptide" in joined:
        class_notes.append("RiPP/lanthipeptide capacity → screen for post-translationally modified "
                           "peptides (MS for dehydration/lanthionine/azoline mass shifts); precursor "
                           "peptides may need targeted induction.")
    if "nrps" in joined or "pks" in joined:
        class_notes.append("NRPS/PKS capacity → LC-MS/MS of organic extracts; consider elicitors "
                           "(rare earths, subinhibitory antibiotics) to switch on silent clusters.")
    if "siderophore" in joined or "metallophore" in joined:
        class_notes.append("Siderophore/metallophore capacity → run an iron-limited condition to "
                           "de-repress; use a CAS assay as a follow-up test of candidate fractions. No assay result is inferred.")
    return "\n".join([
        "# 11. Fermentation and wet-lab guidance",
        "",
        "*Deterministic starting-point draft (genus + class based). Author refines per top-priority "
        "BGC. Guidance only — not a result or activity claim.*",
        "",
        f"**Genus:** {genus or 'actinomycete (unresolved)'} · **dominant specialised classes:** "
        f"{', '.join(classes) or '—'}",
        *([f"**Source status:** {', '.join(source_notes)}; fallbacks are unresolved, not observed absence."]
          if source_notes else []),
        "",
        "**Baseline production screen (actinomycete):**",
        "- Media panel: ISP2, R5/R5A, SFM/MS, and one oatmeal/soy medium; 28–30 °C, 200–250 rpm, 5–10 days.",
        "- Small-scale (25–50 mL) time-course, sampling on days 3/5/7/10 for a production window.",
        "- Extraction: whole-broth EtOAc (and n-butanol for polar/peptidic classes); XAD-16 resin for "
        "secreted metabolites.",
        "- Detection: LC-HRMS on extracts; parallel bioassay-guided fractionation against the strain's "
        "measured phenotype (antifungal-first for Candida+ strains).",
        "",
        "**Class-specific notes:**",
        *([f"- {n}" for n in class_notes] if class_notes else ["- (add per top BGC once leads are chosen)"]),
    ]) + "\n"


def _ferm_section(pkg: Path) -> str:
    p = js._fermentation_path(pkg)
    if p.exists():
        return "# 11. Fermentation and wet-lab guidance\n\n" + p.read_text(encoding="utf-8").strip() + "\n"
    # v9.7.344: fill with a deterministic draft rather than leaving the slot open.
    draft = _fermentation_draft(pkg)
    if draft:
        return draft
    return ("# 11. Fermentation and wet-lab guidance\n\n"
            "<!-- SAPOTE:fermentation -->\n"
            "*(Sapote: per top-priority BGC — media, additives, timepoints, extraction, detection.)*\n"
            "<!-- /SAPOTE:fermentation -->\n")


def _simple_slot(num_title: str, prompt: str) -> str:
    return f"# {num_title}\n\n*(Sapote: {prompt})*\n"


# ── top-level assembler ────────────────────────────────────────────────────────

# ── reader-facing front matter (May-27 parity; deterministic, no judgment) ─────

def _key_findings(pkg: Path, m: dict) -> str:
    """Deterministic KEY FINDINGS banner: top leads by KCB score, low/zero-KCB novelty count, and
    assembly posture. Format-only, grounded in the triage CSV; claim-safe (capacity, not identity).

    Standing-rule / primary-metabolism exclusions (saccharide; NAPAA; hglE-KS-PREV-001) are
    filtered out before ranking, mirroring `_decision_for()`'s `_EXCL_TOKENS` policy for the same
    triage rows (§12 wet-lab decision matrix) — those classes are permanently excluded from
    "discovery lead" status by `mamey/data/rules_registry.json` and must not headline the report's
    one always-populated, reader-facing narrative section."""
    _, rows = _triage_rows(pkg)
    if not rows:
        return "# Key findings\n\n*(triage table unavailable)*\n"
    def _excluded(r):
        standing = (r.get("Standing_rule") or r.get("Downgrade") or "").strip().lower()
        primary = (r.get("Primary_metab_flag") or "").strip().lower()
        # v9.7.377 (AUDIT audit): mirror _decision_for()'s corrected_rank-blank signal (see
        # its comment) — a mobile-element-only exclusion leaves Standing_rule/Primary_metab_flag
        # both empty, so without this check an engine-excluded BGC could headline this
        # always-populated Key Findings banner (live-reproduced: a BGC with Corrected_rank="" but
        # the package's highest KCB_score surfaced as the #1 key finding pre-fix).
        corrected_rank_blank = "Corrected_rank" in r and not (r.get("Corrected_rank") or "").strip()
        return (any(tok in standing for tok in _EXCL_TOKENS) or primary in ("1", "true", "yes")
                or corrected_rank_blank)
    def _score(r):
        raw = r.get("KCB_score")
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
    eligible = [r for r in rows if not _excluded(r)] or rows  # fail-safe: never emit an empty banner
    out = ["# Key findings\n"]
    for r in sorted(eligible, key=lambda row: (_score(row) is not None, _score(row) or 0.0),
                    reverse=True)[:5]:
        kcb = (r.get("KCB_top") or "").strip() or "no KCB hit"
        prod = (r.get("Products") or "").strip()
        out.append(f"- **{_node_label(r)}** — {prod}; nearest MIBiG "
                   f"neighbour by protein similarity (KCB): {kcb}. Capacity consistent with this "
                   f"class; product identity requires isolation.")
    invalid_scores = sum(1 for r in rows if _score(r) is None)
    if invalid_scores:
        out.append(f"- **KCB_SCORE_INPUT_INVALID: {invalid_scores} row(s)** — missing or malformed "
                   "KCB scores remain unresolved and were not counted as measured zero.")
    nnov = sum(1 for r in rows if _score(r) == 0.0)
    if nnov:
        out.append(f"- **{nnov} low/zero-KCB BGC(s)** — no protein-level MIBiG comparator; highest "
                   f"discovery value and priority for targeted BLASTp / isolation.")
    ip = m.get("interior_pct")
    out.append(f"- **Assembly {m.get('assembly_tier', '?')}**"
               + (f" ({ip}% interior)" if ip is not None else "")
               + f" · {m.get('raw_bgcs')} raw / {m.get('corrected_bgcs')} corrected BGCs. Bioactivity "
                 f"is extract-level; no activity is pinned to a single BGC without fractionation.")
    return "\n".join(out) + "\n"


def _described_toc() -> str:
    """Reader-facing described table of contents (section + one-line purpose), mirroring the May-27
    compilation front matter. Complements the pandoc auto-TOC, which lists headings without context."""
    secs = [
        ("2. Executive summary", "what the strain is, confidence, top leads, the next action"),
        ("3. Layperson guide", "plain-English overview for a non-specialist"),
        ("4. Assembly and strain summary", "genome/assembly stats and BGC counts"),
        ("5. Triage board", "every BGC ranked by priority with class and KCB anchor"),
        ("6. Figures", "landscape, composition, per-BGC locus maps, cohort panels"),
        ("7. Cross-strain and ecological synthesis", "biosynthetic capacity in ecological context"),
        ("8. Priority lead deep-dives", "synthesised narrative for the top leads"),
        ("9. Complete Mode B cards", "full per-BGC interpretation for completed BGCs"),
        ("10. BLASTP evidence summary", "protein-similarity evidence, if an evidence store is present"),
        ("11. Fermentation and wet-lab guidance", "media, additives, timepoints, extraction, detection"),
        ("12. Wet-lab decision matrix", "per-BGC sequence / activate / isolate / dereplicate scores"),
        ("13. Outstanding work and next actions", "ordered by speed and impact"),
        ("14. Methods and claim-safety note", "pipeline, claim ceilings, citation format"),
    ]
    return "# Contents\n\n" + "\n".join(f"- **{s}** — {d}" for s, d in secs) + "\n"


def build_report(package_dir: str | Path, generate_figures: bool = True,
                 toc_depth: int = 1) -> str:
    """Assemble the full §13 report as pandoc-ready Markdown. Pure read except for
    optional figure generation (best-effort; never blocks).

    `toc_depth` controls the depth of the pandoc TOC. Default is 1
    (top-level sections only) — at 2, every BGC Mode B card heading gets
    a TOC entry, producing a 3-page TOC for a 51-BGC strain. Override via
    `mamey compile-report --toc-depth N`. (W3 Gap 3, v9.7.149c.)
    """
    pkg = Path(package_dir).resolve()
    m = _read_manifests(pkg)
    strain = m["strain_id"]

    # W5 (v9.7.149c): generate locus maps from the sealed gene_by_gene CSV
    # before assembling, so the report's §6 figure section and §8 deep-dives
    # can reference them. Respect generate_figures=False: the mandatory
    # compiled-report gate uses that mode during `mamey run`, including when
    # the caller explicitly selected `--locus-maps off`.
    locus_map_note = ""
    if generate_figures:
        try:
            from . import locus_map as _locus_map
            _locus_map.render_for_compile_report(pkg, top_n=5)
        except Exception as exc:
            # Strictly non-blocking: a locus_map exception must not block the
            # compiled report. Skipped BGCs surface in the per-BGC §8 sub-blocks.
            locus_map_note = (f"\n*(LOCUS_MAP_RENDER_INVALID: {type(exc).__name__}; "
                              "compiled report continues without treating the failure as absence.)*\n")

    front = ("---\n"
             f'title: "{strain} Analysis Report"\n'
             "toc: true\n"
             f"toc-depth: {int(toc_depth)}\n"
             "---\n")

    parts = [
        front,
        _cover(m),
        _key_findings(pkg, m),
        _described_toc(),
        _slot("executive_summary", strain, pkg),
        _slot("layperson_guide", strain, pkg),
        _assembly_table(m),
        _triage_board(pkg),
        _figures(pkg, generate=generate_figures, preflight_note=locus_map_note),
        _slot("ecological_synthesis", strain, pkg),
        _slot("priority_deep_dives", strain, pkg),
        _mode_b_cards(pkg),
        _blastp_summary(pkg),          # §10 — deterministic from evidence store
        _ferm_section(pkg),
        _decision_matrix(pkg),         # §12 — deterministic from triage CSV
        _simple_slot("13. Outstanding work and next actions",
                     "numbered list ordered by speed/impact: immediate, bioinformatic, wet lab."),
        ("# 14. Methods and claim-safety note\n\n"
         f"Pipeline: Sapote–Mamey bundle {m['bundle_version']}, engine Mamey v{m['mamey_version']}. "
         "All interpretations are claim-safe and capacity-based ('biosynthetic capacity consistent with…'), "
         "never compound-identity claims. KnownClusterBlast hits are **similarity, not identity**. "
         "Bioactivity metadata is optional extract-level, strain-level context; no activity is pinned to a specific BGC "
         "without fractionation. Citations for antiSMASH and MIBiG in PNAS format.\n"),
    ]
    # join with a blank line; each section already ends in a newline.
    return "\n".join(p.rstrip() + "\n" for p in parts)


def open_slots(markdown: str) -> list[str]:
    """Return the list of still-unfilled SAPOTE slot keys in an assembled report.
    Lets a caller (or a gate) report exactly what narrative work remains."""
    import re
    return re.findall(r"<!-- SAPOTE:([a-z_]+) -->", markdown)


# ── write-narrative (W3 Gap 1, v9.7.149c) ──────────────────────────────────────

def write_narrative(package_dir: str | Path, section_key: str,
                    content: str, *, force: bool = False) -> dict:
    """Validate + write a narrative section to `judgment/<strain>_<section>.md`.

    Runs the package claim-safety linter against `content`; refuses (returns
    a dict with `status: "REFUSED"`) on any finding unless `force=True`.

    Returns:
        {"status": "WRITTEN"|"REFUSED"|"UNKNOWN_SECTION",
         "path": <str|None>, "findings": [<str>...], "section": <key>}

    Never raises. The caller (CLI or another module) decides exit behaviour.
    """
    from . import judgment_store as js
    from . import claim_safety_gate as csg

    # MB-02: consult the SSOT. An unknown key is UNKNOWN_SECTION; a real slot that is
    # deterministic-source (blastp_evidence / fermentation) is NOT_NARRATIVE — it is filled by
    # supplying data on disk, not by write-narrative — with its own remediation string.
    meta = SLOT_REGISTRY.get(section_key)
    if meta is None:
        return {"status": "UNKNOWN_SECTION", "path": None, "findings": [],
                "section": section_key,
                "valid_sections": list(NARRATIVE_SLOTS.keys())}
    if meta["kind"] != SLOT_KIND_NARRATIVE:
        return {"status": "NOT_NARRATIVE", "path": None, "findings": [],
                "section": section_key, "kind": meta["kind"],
                "remediation": meta["remediation"],
                "valid_sections": list(NARRATIVE_SLOTS.keys())}

    pkg = Path(package_dir).resolve()
    strain = _read_manifests(pkg)["strain_id"]
    fname = narrative_filename(section_key, strain)

    # v9.7.409 (CLAUDE narrative-gates): claim-safety findings are a HARD refusal that `force`
    # CANNOT bypass. `csg.lint_text()` returns ONLY claim-safety overclaim findings (product-identity,
    # anchor-as-identity, bioactivity-phenotype) — there are no cosmetic/quality warnings in this
    # channel — so the previous `and not force` made `--force` a silent claim-safety bypass: it shipped
    # an overclaiming narrative into judgment/<strain>_<section>.md with the finding only echoed to
    # stderr and no marker in the written file. `force` is retained for API/CLI compatibility (it may
    # still override any future non-claim-safety warning) but it is now decoupled from the claim-safety
    # gate: any claim-safety finding refuses the write. Revise to capacity-based language instead.
    findings = csg.lint_text(content or "")
    if findings:
        return {"status": "REFUSED", "path": None,
                "findings": findings, "section": section_key}

    # Resolve write path via the write variant so judgment/ is created here,
    # not silently elsewhere (F2 contract).
    out = js._judgment_dir_write(pkg) / fname
    _otmp = out.with_name(out.name + ".tmp")  # OUT-P06: atomic — no truncated narrative on a mid-write crash
    _otmp.write_text(content, encoding="utf-8")
    _otmp.replace(out)

    return {"status": "WRITTEN", "path": str(out),
            "findings": findings,  # always [] — a WRITTEN section has passed the claim-safety gate
            "section": section_key}


def write_narrative_command(args) -> int:
    """CLI entry: `mamey write-narrative <pkg> --section <key> --file <input.md>`."""
    import sys
    pkg = Path(args.package_dir).resolve()
    if not pkg.is_dir():
        emit(f"ERROR: not a directory: {pkg}", file=sys.stderr)
        return 1
    in_path = Path(args.file)
    if not in_path.exists():
        emit(f"ERROR: input file not found: {in_path}", file=sys.stderr)
        return 1
    try:
        content = in_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        emit(f"ERROR: cannot read {in_path}: {e}", file=sys.stderr)
        return 1

    res = write_narrative(pkg, args.section, content,
                          force=getattr(args, "force", False))

    if res["status"] == "UNKNOWN_SECTION":
        emit(f"ERROR: unknown section '{args.section}'. "
              f"Valid: {', '.join(res['valid_sections'])}", file=sys.stderr)
        return 2
    if res["status"] == "NOT_NARRATIVE":
        emit(f"ERROR: '{args.section}' is a {res['kind']} slot, not a write-narrative section.\n"
              f"  {res['remediation']}\n"
              f"  write-narrative sections: {', '.join(res['valid_sections'])}", file=sys.stderr)
        return 2
    if res["status"] == "REFUSED":
        emit(f"REFUSED: claim-safety linter raised {len(res['findings'])} "
              f"finding(s) for section '{args.section}':", file=sys.stderr)
        for f in res["findings"]:
            emit(f"  - {f}", file=sys.stderr)
        # v9.7.409 (CLAUDE narrative-gates): a claim-safety finding is not force-writable. The only
        # remedy is to revise the text — --force no longer ships an overclaiming narrative.
        emit("Revise the text to use capacity-based language "
              "('biosynthetic capacity consistent with…'); a claim-safety finding cannot be "
              "overridden with --force.", file=sys.stderr)
        return 3
    emit(f"wrote narrative section '{args.section}' → {res['path']}")
    return 0


# ── CLI ────────────────────────────────────────────────────────────────────────

def _svg_to_pdf(src: "Path", dst: "Path") -> bool:
    """Convert live SVG to vector PDF without passing through a screen raster."""
    import shutil, subprocess
    from pathlib import Path as _P
    src, dst = _P(src), _P(dst)
    try:
        import cairosvg
        cairosvg.svg2pdf(url=str(src), write_to=str(dst))
        return dst.exists() and dst.stat().st_size > 0
    except Exception:
        pass
    for conv in (["rsvg-convert", "-f", "pdf", "-o", str(dst), str(src)],
                 ["inkscape", str(src), "--export-type=pdf", f"--export-filename={dst}"]):
        if shutil.which(conv[0]):
            try:
                subprocess.run(conv, capture_output=True, timeout=120, check=True)
                if dst.exists() and dst.stat().st_size > 0:
                    return True
            except Exception:
                continue
    return False


def _svg_to_png(src: "Path", dst: "Path", *, output_width: int | None = None) -> bool:
    """Fallback SVG rasterization at an explicit publication-native pixel width."""
    import shutil, subprocess
    from pathlib import Path as _P
    src, dst = _P(src), _P(dst)
    width = int(output_width or 2160)
    with contextlib.suppress(Exception):
        import cairosvg
        cairosvg.svg2png(url=str(src), write_to=str(dst), output_width=width)
        return dst.exists() and dst.stat().st_size > 0
    for conv in (["rsvg-convert", "-w", str(width), "-o", str(dst), str(src)],
                 ["inkscape", str(src), "--export-type=png", f"--export-width={width}",
                  f"--export-filename={dst}"]):
        if shutil.which(conv[0]):
            try:
                subprocess.run(conv, capture_output=True, timeout=120, check=True)
                if dst.exists() and dst.stat().st_size > 0:
                    return True
            except Exception:
                continue
    return False


def _prepare_publication_artwork(md: str, pkg: "Path", *, profile: str = "DOUBLE_COLUMN") -> tuple[str, dict]:
    """Preserve vectors and refuse publication-inadequate raster references before PDF work."""
    import math, re
    pkg = Path(pkg).resolve()
    gated, dropped, vector_preserved, raster_fallbacks, checked = [], 0, 0, 0, []
    minimum_width = math.ceil(
        PUBLICATION_PROFILES[profile]["width_in"]
        * PUBLICATION_PROFILES[profile]["minimum_raster_dpi"]
    )
    for line in md.splitlines(keepends=True):
        match = re.search(r"!\[[^]]*\]\(([^)]+)\)", line)
        if not match:
            gated.append(line)
            continue
        target = match.group(1)
        source = (pkg / target).resolve()
        try:
            source.relative_to(pkg)
        except ValueError as exc:
            raise FigurePolicyError("FIGURE_ARTWORK_ROOT_ESCAPE", target) from exc
        if not source.exists():
            dropped += 1
            continue
        suffix = source.suffix.casefold()
        if suffix == ".svg":
            checked.append(validate_publication_artwork(source, profile=profile))
            vector_rel = target + ".vector.pdf"
            vector_path = pkg / vector_rel
            if _svg_to_pdf(source, vector_path):
                gated.append(line.replace(target, vector_rel))
                vector_preserved += 1
                continue
            raster_rel = target + ".publication.png"
            raster_path = pkg / raster_rel
            if not _svg_to_png(source, raster_path, output_width=minimum_width):
                raise FigurePolicyError(
                    "FIGURE_VECTOR_EMBED_UNAVAILABLE",
                    f"no vector converter or publication-resolution raster fallback for {target}",
                )
            checked.append(validate_publication_artwork(raster_path, profile=profile))
            gated.append(line.replace(target, raster_rel))
            raster_fallbacks += 1
            continue
        if suffix == ".png":
            checked.append(validate_publication_artwork(source, profile=profile))
            gated.append(line)
            continue
        dropped += 1
    return "".join(gated), {
        "profile": profile,
        "checked_figures": len(checked),
        "dropped_figures": dropped,
        "vector_preserved": vector_preserved,
        "publication_raster_fallbacks": raster_fallbacks,
        "artwork_receipts": checked,
    }


def _verify_compiled_pdf_artwork(out_pdf: "Path", quality: dict) -> dict:
    """Fail closed if embedded vector text/fonts or raster effective DPI cannot be verified."""
    import shutil, subprocess
    vector_expected = quality.get("vector_preserved", 0) > 0
    raster_expected = any(
        row.get("artwork_type") == "RASTER_PNG"
        for row in quality.get("artwork_receipts", [])
    )
    receipt = {"status": "PASS", "vector_fonts": "NOT_APPLICABLE",
               "live_text_probe": "NOT_APPLICABLE", "minimum_embedded_raster_dpi": "NOT_APPLICABLE"}
    if vector_expected:
        for executable in ("pdffonts", "pdftotext"):
            if shutil.which(executable) is None:
                raise FigurePolicyError(
                    "FIGURE_EMBED_FONT_QA_UNAVAILABLE", f"{executable} is required for vector-text PDF QA"
                )
        fonts = subprocess.run(["pdffonts", str(out_pdf)], capture_output=True, text=True,
                               timeout=120, check=True).stdout.splitlines()[2:]
        if not fonts or not all(len(line.split()) > 3 and line.split()[3].casefold() == "yes" for line in fonts if line.strip()):
            raise FigurePolicyError(
                "FIGURE_EMBED_FONT_NOT_EMBEDDED", "compiled PDF contains a non-embedded font"
            )
        extracted = subprocess.run(["pdftotext", str(out_pdf), "-"], capture_output=True,
                                   text=True, timeout=120, check=True).stdout
        probes = [probe for row in quality.get("artwork_receipts", [])
                  for probe in row.get("live_text_probes", [])]
        if probes and not any(probe in extracted for probe in probes):
            raise FigurePolicyError(
                "FIGURE_EMBED_LIVE_TEXT_NOT_VERIFIED",
                "no validated artwork text probe survived PDF embedding",
            )
        receipt["vector_fonts"] = "EMBEDDED"
        receipt["live_text_probe"] = "VERIFIED" if probes else "NO_NONTRIVIAL_PROBE"
    if raster_expected:
        if shutil.which("pdfimages") is None:
            raise FigurePolicyError(
                "FIGURE_EMBED_RASTER_QA_UNAVAILABLE", "pdfimages is required for embedded-raster DPI QA"
            )
        listing = subprocess.run(["pdfimages", "-list", str(out_pdf)], capture_output=True,
                                 text=True, timeout=120, check=True).stdout.splitlines()[2:]
        dpi = []
        for line in listing:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    dpi.append(min(float(parts[-4]), float(parts[-3])))
                except ValueError:
                    continue
        if not dpi or min(dpi) < 300:
            raise FigurePolicyError(
                "FIGURE_EMBED_EFFECTIVE_DPI_INSUFFICIENT",
                f"embedded raster minimum is {min(dpi) if dpi else 'unavailable'} dpi; requires 300",
            )
        receipt["minimum_embedded_raster_dpi"] = min(dpi)
    return receipt


def _render_compiled_pdf(md: str, out_pdf: "Path", pkg: "Path") -> dict:
    """Boss-Ready / Compiled Master PDF (menu Special / monolith §15.8) via the SANCTIONED renderer
    tools/md_to_pdf.sh (Markdown -> pandoc -> xelatex, with the wide-table preflight). This does NOT
    hand-roll a renderer; it drives the documented "correct PDF path". Non-blocking — returns a status
    dict, never raises into the build, never affects the markdown.

    Two compile-report-side adjustments let the sanctioned tool succeed on a package:
      (1) figure references are publication-gated at 7.2 inches. Live-text SVG is converted to a
          vector PDF; only when vector conversion is unavailable may a native 300-DPI PNG fallback
          be made. Existing low-resolution PNGs are refused rather than enlarged;
      (2) md_to_pdf.sh is run with cwd = package dir so the report's relative image paths
          (gold_figures/…, locus_maps/…) resolve for xelatex.
    A PDF-derived screenshot is never a source-artwork substitute."""
    import shutil, subprocess
    pkg = Path(pkg)
    script = Path(__file__).resolve().parents[1] / "tools" / "md_to_pdf.sh"
    if not script.exists():
        return {"status": "SKIPPED_NO_RENDERER", "path": None, "detail": f"{script} absent"}
    if shutil.which("pandoc") is None or shutil.which("xelatex") is None:
        return {"status": "SKIPPED_NO_TOOLCHAIN", "path": None,
                "detail": "pandoc/xelatex not on PATH — the sanctioned PDF path requires both"}
    try:
        gated_md, quality = _prepare_publication_artwork(md, pkg, profile="DOUBLE_COLUMN")
    except FigurePolicyError as exc:
        return {"status": "FIGURE_QUALITY_REFUSED", "path": None,
                "code": exc.code, "detail": exc.detail}
    render_md = out_pdf.with_suffix(".render.md")
    render_md.write_text(gated_md, encoding="utf-8")
    try:  # cwd=pkg so relative figure paths (gold_figures/…, locus_maps/…) resolve
        # cwd=pkg changes the working dir, so relative render_md/out_pdf would not resolve
        # inside the script (this was the RENDER_FAILED / FileNotFoundError on *.render.md).
        r = subprocess.run(["bash", str(script), str(render_md.resolve()), str(out_pdf.resolve()), "boss"],
                           cwd=str(pkg), capture_output=True, text=True, timeout=600)
    except Exception as e:
        return {"status": "ERROR", "path": None, "detail": str(e)}
    if r.returncode == 0 and out_pdf.exists():
        try:
            embedded_qa = _verify_compiled_pdf_artwork(out_pdf, quality)
        except (FigurePolicyError, subprocess.SubprocessError, OSError) as exc:
            with contextlib.suppress(OSError):
                out_pdf.unlink()
            return {"status": "FIGURE_EMBED_QA_REFUSED", "path": None,
                    "code": getattr(exc, "code", type(exc).__name__), "detail": str(exc),
                    "figure_quality": quality}
        return {"status": "WRITTEN", "path": str(out_pdf),
                "dropped_figs": quality["dropped_figures"],
                "converted_figs": quality["vector_preserved"] + quality["publication_raster_fallbacks"],
                "figure_quality": quality,
                "embedded_pdf_qa": embedded_qa,
                "engine": "md_to_pdf.sh (colorful reportlab, pandoc+xelatex fallback)"}
    return {"status": "RENDER_FAILED", "path": None,
            "detail": (r.stderr or r.stdout or "").strip()[-400:]}


def compile_report_command(args) -> int:
    import sys
    pkg = Path(args.package_dir).resolve()
    if not pkg.is_dir():
        emit(f"ERROR: not a directory: {pkg}", file=sys.stderr)
        return 1
    # v9.7.409 (BC hostile audit H14): the compiled report was built from packages whose manifest identity
    # had been swapped and whose triage board had been deleted — `gate_validation.json` still said PASS from
    # seal time. A reader that authors a deliverable must check the package it reads, at read time, for
    # TAMPER evidence: identity binding, manifest parse, and checksum mismatches/missing files (excluding the
    # report artifacts this command itself rewrites). File-presence and RG-GMCI gates are NOT consulted here:
    # partial fixture packages and pre-seal trees legitimately lack them and the existing contract allows
    # compiling those.
    from .validate import validate_package as _validate_now
    _v = _validate_now(pkg)
    _tamper = []
    if str(_v.get("identity_binding", "PASS")).upper().startswith(("FAIL", "ERROR")):
        _tamper.append(f"identity_binding ({_v.get('identity_binding_detail', '')})")
    if str(_v.get("manifest_parse", "PASS")).upper().startswith("FAIL"):
        _tamper.append("manifest_parse")
    _cs = [e for e in (_v.get("checksum_errors") or []) if "compiled_report" not in str(e) and "provenance" not in str(e)]
    # a package that never carried checksums_sha256.txt (fixtures, pre-seal trees) is unverifiable, not tampered
    if (pkg / "checksums_sha256.txt").is_file() and str(_v.get("checksum_integrity", "PASS")).upper() == "FAIL" and _cs:
        _tamper.append("checksum_integrity: " + "; ".join(str(e) for e in _cs[:3]))
    if _tamper:
        raise SystemExit("compile-report: REFUSED — package shows tamper evidence at read time (" + " | ".join(_tamper) + f"); run `mamey validate {pkg}` and repair before compiling a report")
    # v9.7.344 BLASTp-completeness HARD gate: BLASTp ingestion is a MANDATORY step before the
    # compiled report. If ingestable BLASTp is available on disk but not ingested, REFUSE (exit 3)
    # with the exact ingest command — unless --blastp-waiver "<reason>" is given (recorded to
    # manifest provenance; the report ships BLASTP-INCOMPLETE by attestation).
    from . import blastp_gate as _bpg
    _strain = _read_manifests(pkg).get("strain_id", "") or ""
    _bp = _bpg.gate(pkg, _strain, waiver=getattr(args, "blastp_waiver", None))
    if _bp["blocked"]:
        emit(_bp["message"], file=sys.stderr)
        return 3
    if _bp["waived"]:
        emit(f"  {_bp['message']}", file=sys.stderr)
    md = build_report(pkg, generate_figures=not getattr(args, "no_figures", False),
                      toc_depth=int(getattr(args, "toc_depth", 1)))
    out = Path(args.out) if getattr(args, "out", None) else (pkg / f"{_read_manifests(pkg)['strain_id']}_compiled_report.md")
    slots = open_slots(md)
    # MB-03 (v9.7.338): run claim-safety over the report's OWN assembled text at compile time. CS-01
    # otherwise only bites at seal, so a freshly compiled report could ship an overclaim un-scanned.
    from . import claim_safety_gate as csg
    cs_findings = csg.lint_text(md)
    if getattr(args, "strict", False) and slots:
        # compile gate: do not ship a master report with unfilled slots. Per-kind remediation (MB-02):
        # narrative slots are write-narrative sections; deterministic slots need the source artifact.
        emit(f"STRICT: report NOT written — {len(slots)} unfilled slot(s): "
              f"{', '.join(slots)}", file=sys.stderr)
        for it in classify_open_slots(md):
            emit(f"  - {it['key']} [{it['kind']}]: {it['remediation']}", file=sys.stderr)
        return 2
    if cs_findings:
        # v9.7.409 (CLAUDE narrative-gates): claim-safety findings in the ASSEMBLED report now BLOCK
        # by default (write nothing, exit 3). Previously they were warning-only unless --strict, so a
        # freshly compiled master report carrying a product-identity / bioactivity overclaim shipped to
        # disk by default with only a stderr warning. This compile-time scan (MB-03) is the report
        # boundary's backstop for authored narrative injected from judgment/ — it must be a GATE, not a
        # note. Escape hatch: --allow-claim-safety-warnings restores the old warn-and-ship behaviour for
        # a deliberate, explicitly-attested draft; --strict continues to block and is NOT overridable by
        # that flag (a strict compile never ships past claim-safety findings).
        emit(f"  claim-safety: {len(cs_findings)} possible product-identity overclaim(s) in the "
              f"assembled report:", file=sys.stderr)
        for f in cs_findings:
            emit(f"    - {f}", file=sys.stderr)
        strict = getattr(args, "strict", False)
        allow_warn = getattr(args, "allow_claim_safety_warnings", False)
        if strict or not allow_warn:
            emit("claim-safety: report NOT written — resolve the findings above "
                  "(capacity-based language: 'biosynthetic capacity consistent with…'), or pass "
                  "--allow-claim-safety-warnings to ship a draft past them "
                  "(not honoured under --strict).", file=sys.stderr)
            return 3
        emit("  (--allow-claim-safety-warnings: report written past the claim-safety findings above "
              "— draft only, explicitly attested.)", file=sys.stderr)
    _otmp = out.with_name(out.name + ".tmp")  # OUT-P06: atomic — no truncated report on a mid-write crash
    _otmp.write_text(md, encoding="utf-8")
    _otmp.replace(out)
    emit(f"compiled report → {out}")
    if slots:
        emit(f"  {len(slots)} narrative slot(s) still to fill: {', '.join(slots)}")
    else:
        emit("  all narrative sections present — report is complete.")
    if getattr(args, "pdf", False):
        if slots and not getattr(args, "allow_unfilled_pdf", False):
            # v9.7.405 (WAC-01375 item 7 / BUG-06): a missing evidence stream is a WORKFLOW gap,
            # not a biological no-hit, and the message now says how to close it instead of only
            # naming the override. Nothing here fills or fabricates a sequence-evidence slot.
            emit(f"  PDF NOT rendered — {len(slots)} narrative slot(s) unfilled "
                  f"({', '.join(slots)}). A Boss-Ready PDF must not ship with empty judgment slots.\n"
                  f"  How to close them:\n"
                  f"    - narrative/judgment slots: `python mamey_run.py write-narrative --package <pkg> --section <slot>`\n"
                  f"    - BLASTp evidence slots: ingest a LOCAL result bound to the exact protein + locus —\n"
                  f"      `python mamey_run.py ingest-blastp --master <master.xlsx> --strain <id> --hit-table <HitTable.csv> --package <pkg>`; a slot left empty\n"
                  f"      means 'stream not run', never 'no hit' (see docs/BLASTP_NOVELTY_WORKFLOW.md)\n"
                  f"    - to record an explicit UNRESOLVED gap instead: `python mamey_run.py workflow --package <pkg>`\n"
                  f"  `--allow-unfilled-pdf` is a DRAFT-ONLY override: the PDF it renders carries empty judgment\n"
                  f"  slots and must not be presented as a finished deliverable.",
                  file=sys.stderr)
            return 0
        pdf_out = out.with_suffix(".pdf")
        res = _render_compiled_pdf(md, pdf_out, pkg)
        if res["status"] == "WRITTEN":
            drop = res.get("dropped_figs", 0)
            extra = f" ({drop} svg/absent figure ref(s) dropped)" if drop else ""
            emit(f"  compiled master PDF → {pdf_out}  [{res.get('engine', '')}]{extra}")
        else:
            emit(f"  PDF not written ({res['status']}: {res.get('detail', '')}) — "
                  f"markdown is unaffected", file=sys.stderr)
            return 1  # CLI-02: a requested --pdf render that failed must exit non-zero
    return 0
