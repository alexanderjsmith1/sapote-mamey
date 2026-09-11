"""v9.7.192 — authored-output verification: read the FINISHED deliverable, not the skeleton.

Two reported failures motivate this module:
  1. A guide's quality gate ran on the rebuilt SKELETON, so a green "guide gate: OK" was reported
     over an EMPTY template. `verify-guide` reads the authored .md instead (see bgc_guide.
     verify_authored_guide).
  2. A hand-built 5-section docx was titled "Mode B Card" and shipped though it had none of the
     §1–§48 structure. `verify-modeb` runs the real `lint_card` (structure + strict depth) on the
     authored file, and `guard_deliverable_name` refuses to let a NO_HEADINGS card be *named* Mode B.

These close the gap where the appearance of rigor (a green check) diverged from actual rigor (a
check that read the work).
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

from collections import Counter, defaultdict
import json
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .bgc_guide import verify_authored_guide
from .modeb_structure_gate import lint_card

# a deliverable whose filename claims to be a Mode B card
_MODEB_NAME_RE = re.compile(r"mode[\s_\-]?b", re.IGNORECASE)

VERIFY_REPORT_SCHEMA_VERSION = "sapote.modeb.verify-report.v1"
VERIFY_REPORT_AUTHORITY_CEILING = (
    "Mechanical and evidence-accounting verification only. A pass does not confer "
    "scientific correctness, owner acceptance, integration, shelf promotion, "
    "release approval, or publication approval."
)

def grouped_verify_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group exact findings by severity and code without discarding instances."""
    counts: Counter[tuple[str, str]] = Counter()
    sections: dict[tuple[str, str], set[int]] = defaultdict(set)
    for finding in findings:
        severity = str(finding.get("severity") or "UNKNOWN").upper()
        code = str(finding.get("code") or "UNSPECIFIED")
        key = (severity, code)
        counts[key] += 1
        section = finding.get("section")
        if isinstance(section, int):
            sections[key].add(section)
    return [
        {"severity": severity, "code": code, "count": counts[(severity, code)],
         "sections": sorted(sections[(severity, code)])}
        for severity, code in sorted(counts)
    ]


def build_verify_report(*, card_name: str, profile: str, exit_code: int,
                        findings: list[dict[str, Any]], independent_roster_bound: bool,
                        package_core_denominator_bound: bool) -> dict[str, Any]:
    """Build a stable receipt with both finding-instance and category counts."""
    normalized = [
        {"severity": str(f.get("severity") or "UNKNOWN").upper(),
         "code": str(f.get("code") or "UNSPECIFIED"), "section": f.get("section"),
         "message": str(f.get("message") or "")}
        for f in findings
    ]
    categories = grouped_verify_findings(normalized)
    return {
        "schema_version": VERIFY_REPORT_SCHEMA_VERSION,
        "card_name": card_name,
        "profile": profile,
        "status": "PASS" if exit_code == 0 else "FAIL",
        "exit_code": exit_code,
        "authority_ceiling": VERIFY_REPORT_AUTHORITY_CEILING,
        "independent_roster_bound": independent_roster_bound,
        "package_core_denominator_bound": package_core_denominator_bound,
        "coverage_verified": package_core_denominator_bound,
        "error_instances": sum(f["severity"] == "ERROR" for f in normalized),
        "warning_instances": sum(f["severity"] == "WARN" for f in normalized),
        "finding_categories": len(categories),
        "category_summary": categories,
        "findings": normalized,
    }


def write_verify_report(path: str | Path, report: dict[str, Any]) -> None:
    """Write a deterministic JSON receipt atomically."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)


def compact_verify_summary_lines(findings: list[dict[str, Any]]) -> list[str]:
    """Return deterministic human-readable grouped diagnostic lines."""
    lines = []
    for row in grouped_verify_findings(findings):
        section_text = ",".join(f"§{n}" for n in row["sections"]) or "n/a"
        lines.append(f"{row['severity']}: {row['code']} x{row['count']} (sections: {section_text})")
    return lines


_CONTEXT_FINDINGS_KEY = "_verification_context_findings"


def _record_context_finding(ctx: dict[str, Any], *, code: str, source: Path,
                            role: str) -> None:
    """Attach a path-safe, structured failure for a present but unusable context source."""
    finding = {
        "severity": "ERROR",
        "code": code,
        "section": None,
        "message": (
            f"Package {role} `{source.name}` is present but cannot supply trustworthy "
            "verification context. Repair or replace the package artifact before verification."
        ),
    }
    findings = ctx.setdefault(_CONTEXT_FINDINGS_KEY, [])
    if finding not in findings:
        findings.append(finding)


def _read_context_csv(ctx: dict[str, Any], source: Path, *, role: str,
                      required_columns: tuple[tuple[str, ...], ...]) -> list[dict[str, str]] | None:
    """Read a present verification CSV strictly; optional absence is handled by the caller."""
    import csv

    try:
        with open(source, encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or ())
            if not fields or any(not fields.intersection(aliases) for aliases in required_columns):
                raise ValueError("required context columns absent")
            rows = list(reader)
            if any(None in row or any(value is None for value in row.values()) for row in rows):
                raise ValueError("row width differs from header width")
            return rows
    except OSError:
        _record_context_finding(
            ctx, code="VERIFICATION_CONTEXT_UNREADABLE", source=source, role=role)
    except (UnicodeError, csv.Error, ValueError):
        _record_context_finding(
            ctx, code="VERIFICATION_CONTEXT_MALFORMED", source=source, role=role)
    return None


def _read_context_json(ctx: dict[str, Any], source: Path, *, role: str) -> dict | None:
    """Read a present verification JSON object without turning corruption into absence."""
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("top-level JSON value is not an object")
        return value
    except OSError:
        _record_context_finding(
            ctx, code="VERIFICATION_CONTEXT_UNREADABLE", source=source, role=role)
    except (UnicodeError, json.JSONDecodeError, ValueError):
        _record_context_finding(
            ctx, code="VERIFICATION_CONTEXT_MALFORMED", source=source, role=role)
    return None


def _read_context_jsonl(ctx: dict[str, Any], source: Path, *, role: str) -> list[dict] | None:
    """Read current gene-context JSONL strictly while admitting its optional header row."""
    try:
        rows = []
        for line in source.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("JSONL row is not an object")
            if "bgc_id" not in row:
                if "schema_version" in row:
                    continue
                raise ValueError("JSONL data row lacks bgc_id")
            if not isinstance(row.get("cds"), list):
                raise ValueError("JSONL BGC row lacks a CDS list")
            rows.append(row)
        return rows
    except OSError:
        _record_context_finding(
            ctx, code="VERIFICATION_CONTEXT_UNREADABLE", source=source, role=role)
    except (UnicodeError, json.JSONDecodeError, ValueError):
        _record_context_finding(
            ctx, code="VERIFICATION_CONTEXT_MALFORMED", source=source, role=role)
    return None


def _manifest_bgc_rows(ctx: dict[str, Any], manifest: dict, source: Path) -> list[dict] | None:
    """Return a validated manifest BGC inventory, preserving an absent optional list."""
    rows = manifest.get("bgcs", [])
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        _record_context_finding(
            ctx, code="VERIFICATION_CONTEXT_MALFORMED", source=source,
            role="package manifest BGC inventory")
        return None
    return rows


def _bgc_context_from_package(package: str | None, bgc: str | None, _cross: bool = True) -> dict | None:
    """Best-effort BGC context for lint_card's conditional predicates (§21/§22/§24 for RiPP, §9/§10,
    novelty). Reads the sealed manifest/gene table if available; returns None if nothing found (then
    lint_card treats conditional sections as optional WARN, not ERROR).

    `_cross` guards the sibling merge with `_bgc_context_from_triage`; see A-03 note there. A
    top-level call (`_cross=True`) merges triage once and calls it with `_cross=False` so it does
    not cross back — breaking the unbounded mutual recursion the two "one ctx, both doors" merges
    otherwise formed."""
    if not package or not bgc:
        return None
    pkg = Path(package)
    ctx: dict[str, Any] = {"bgc_id": bgc}
    # v9.7.229: evidence-presence — does the strain have a BLASTp panel? If so, §4 must carry the
    # reconciled per-gene closest-match table (drives the EVIDENCE_GAP WARN in the depth gate).
    # v9.7.246: the strain's own locus_tag universe, so PHANTOM_LOCUS can tell a real gene from a
    # locus templated in from another organism's session. Read from the sealed CDS table; silent if absent.
    loci = set()
    for _cds in list(pkg.glob("*_cds_table.csv")) + list(pkg.glob("cds_table.csv")):
        _cds_rows = _read_context_csv(
            ctx, _cds, role="CDS table",
            required_columns=(("locus_tag", "Locus_Tag"),),
        )
        for _r in _cds_rows or ():
            _lt = (_r.get("locus_tag") or _r.get("Locus_Tag") or "").strip()
            if _lt:
                loci.add(_lt)
    if loci:
        ctx["known_loci"] = loci
    try:
        ctx["has_blastp_panel"] = (pkg / "bgc_blastp_panel").is_dir() or bool(
            next(pkg.glob("*_manual_blastp_worklist.csv"), None)) or bool(
            next(pkg.glob("*blastp*results*.csv"), None))
    except OSError:
        ctx["has_blastp_panel"] = False
        _record_context_finding(
            ctx, code="VERIFICATION_CONTEXT_UNREADABLE", source=pkg,
            role="BLASTp panel discovery")
    # B1 (v9.7.256): per-BGC membership so LOCUS_BGC_MISMATCH can tell a real gene cited under the
    # WRONG BGC (AS-XXX ctg12_71 -> BGC010, leaked as BGC006). Map every locus_tag to its home BGC
    # from the gene-by-gene table; silent if the table is absent.
    gt2 = next(pkg.glob("*_gene_by_gene_all_bgcs.csv"), None)
    _gene_rows = (_read_context_csv(
        ctx, gt2, role="gene-by-gene table",
        required_columns=(("locus_tag", "Locus_Tag"), ("bgc_id", "BGC_ID")),
    ) if gt2 else None)
    if _gene_rows is not None:
            # v9.7.373b (Codex roster-membership correction): a boundary CDS can legitimately
            # belong to TWO adjacent/overlapping BGC region records that share it. The prior
            # last-write dict `home[lt] = bg` silently dropped such a gene from the earlier BGC's
            # roster (Codex census: 8 per-BGC undercounts across 6 packages, e.g. AS-XXX/BGC031
            # loses ctg37_25). Preserve membership as a one-to-many relation instead.
            membership: dict[str, set[str]] = {}   # bgc_id -> set[locus_tag] (authoritative)
            homes: dict[str, set[str]] = {}         # locus_tag -> set[bgc_id] (for the mismatch guard)
            for _r in _gene_rows:
                _lt = (_r.get("locus_tag") or _r.get("Locus_Tag") or "").strip()
                _bg = (_r.get("bgc_id") or _r.get("BGC_ID") or "").strip()
                if _lt and _bg:
                    membership.setdefault(_bg, set()).add(_lt)
                    homes.setdefault(_lt, set()).add(_bg)
            if homes:
                # ctx["locus_home"] stays locus_tag -> home, but a gene with >1 declared home now
                # carries the SET of homes. The mismatch guard (modeb_structure_gate) accepts a set
                # or a legacy single-string home, so older verifier contexts still work.
                ctx["locus_home"] = {lt: (bgs if len(bgs) > 1 else next(iter(bgs)))
                                     for lt, bgs in homes.items()}
                # v9.7.373 (roster wiring, B2): the .372 matrix gate
                # (_section4_complete_blastp_matrix_findings) reads the authoritative per-BGC
                # locus-tag roster from ctx["known_locus_tags"], but no production caller ever set
                # that key — the context builder only set the strain-wide ctx["known_loci"], so a
                # finished card verified with --package/--bgc always hit BLASTP_MATRIX_ROSTER_UNBOUND.
                # Bind the exact per-BGC roster from DIRECT membership rows for the requested BGC
                # (never from a last-write single-home dict). Includes declared boundary-context CDS
                # (verified on a real per-BGC roster with declared boundary-context CDS).
                _roster = membership.get(bgc, set())
                if _roster:
                    ctx["known_locus_tags"] = sorted(_roster)
    # B1 (v9.7.256): which BGCs actually have a panel, so PANEL_ABSENT_CLAIM can flag a per-gene
    # BLASTp *result* asserted for a BGC on which no panel was run. Silent (key absent) if no panel
    # inventory is discoverable — a whole-strain has_blastp_panel flag is too coarse for this.
    try:
        panels: set[str] = set()
        pd = pkg / "bgc_blastp_panel"
        _man = next(pd.glob("*_BGC_BLASTP_PANEL_selection_manifest.csv"), None) if pd.is_dir() else None
        if _man is None:
            _man = next(pkg.glob("*_manual_blastp_worklist.csv"), None)
        _panel_rows = (_read_context_csv(
            ctx, _man, role="BLASTp panel selection manifest",
            required_columns=(("bgc_id", "BGC_ID"),),
        ) if _man is not None else None)
        for _r in _panel_rows or ():
            _bg = (_r.get("bgc_id") or _r.get("BGC_ID") or "").strip()
            if _bg:
                panels.add(_bg)
        # any per-BGC result CSVs (e.g. BGC042_online_blastp.csv) also count as a present panel
        import re as _re2
        results: set[str] = set()   # B1 (v9.7.264): BGCs with an actual results artifact, not just a selection
        for _p in list(pkg.glob("**/*blastp*.csv")):
            _m = _re2.search(r"(BGC\d{3})", _p.name)
            if _m:
                panels.add(_m.group(1))
                if _p.name.endswith("_online_blastp.csv"):
                    results.add(_m.group(1))   # a returned-alignments artifact, specifically
        if panels or (pd.is_dir()):
            ctx["panels_present"] = panels   # present-but-empty is a valid "no panels" signal
        # B1 (v9.7.264): distinguish "panel selected" from "panel actually run". Only when a results
        # directory is present (some BGC was run) can we tell an unrun selected BGC from one whose
        # results simply aren't shipped — so the results-tracked signal gates the stricter check.
        _rdir = pkg / "blastp_online"
        if _rdir.is_dir() and any(_rdir.glob("*_online_blastp.csv")):
            ctx["blastp_results_present"] = results
    except OSError:
        _record_context_finding(
            ctx, code="VERIFICATION_CONTEXT_UNREADABLE", source=pkg,
            role="BLASTp panel inventory discovery")
    # products / class hints from the gene table (drives is_ripp)
    if _gene_rows is not None:
            n_core = 0
            for row in _gene_rows:
                if str(row.get("bgc_id", "")).strip() != str(bgc).strip():
                    continue
                if "products" not in ctx:  # first matching row sets products / is_ripp / boundary
                    prod = (row.get("bgc_products") or "").lower()
                    ctx["products"] = prod
                    ctx["is_ripp"] = any(t in prod for t in
                                         ("ripp", "lanthipeptide", "lassopeptide", "thiopeptide",
                                          "lap", "sactipeptide", "lanthidin", "microviridin", "bottromycin"))
                    ctx["boundary"] = (row.get("edge_status") or row.get("boundary_flag") or "").strip()
                # item 5 (v9.7.323): count rule-based core genes across ALL rows so §4_BLASTP_COVERAGE
                # can use the package core count as its denominator (catches a §4 that OMITS cores, not
                # just under-covers listed ones). Same "core biosynthetic" signal bgc_guide._role_of keys on.
                # MODEB-GATE-P01 (v9.7.331): the gene_function_inference "core biosynthetic" label is
                # sparse in cohort packages (AS-XXX: 4 core rows over 12 BGCs; AS-XXX/BGC016: 0), so
                # n_core collapsed to 0 for most cards and §4 coverage self-downgraded to
                # COVERAGE_UNVERIFIED — the gate never actually verified §4. The antiSMASH gene_kind,
                # carried in product_qualifier, marks EVERY rule-based core with a leading
                # "biosynthetic (rule-based-clusters)" token (the supporting "-additional" form has a
                # hyphen, so a plain-space substring test excludes it). Also honour the template's ●
                # core mark. Accept any of these so the real core count reaches the gate.
                fn = (row.get("gene_function_inference") or "").lower()
                pq = (row.get("product_qualifier") or "").lower()
                is_core = ("core biosynthetic" in fn or fn.strip() == "core"
                           or "biosynthetic (rule-based-clusters)" in pq
                           or "●" in fn or "●" in pq)
                if is_core:
                    n_core += 1
            if n_core:
                ctx["n_core_genes"] = n_core
    # B1 (v9.7.203): §24 novelty must use the SAME two-branch formula as ingest-receipts, or a HIGH-novelty
    # card can pass `verify-modeb --package` yet fail `ingest-receipts`. Supply the triage context
    # (kcb_top + Novelty_auto) — which is what modeb_structure_gate's `(not kcb_top) or novelty=="HIGH"`
    # reads — and do NOT pre-set novel_or_no_mibig here (my .202 single-branch `not kcb` missed the HIGH arm).
    try:
        from .mode_b_receipt import _bgc_context_from_triage
        # _cross=False: the triage builder must not merge this package ctx back in, or
        # the two doors recurse without bound (A-03). When we are already the nested
        # call (_cross False), skip the triage read entirely — tctx stays empty.
        tctx = _bgc_context_from_triage(pkg, str(bgc), _cross=False) if _cross else {}
        # W7 (v9.7.370, the patch lane, INDIGO2-lane inheritance): ONE ctx source, both doors.
        # The triage builder (_bgc_context_from_triage) is the canonical Mode-B context.
        # This door previously merged a hand-kept WHITELIST of its keys — kcb/novelty
        # at v9.7.203, +4 extension-predicate inputs at v9.7.369 — so every NEW
        # triage-ctx key silently re-opened the two-door divergence the W4 closing
        # report measured in both directions (cards recorded while verify failed
        # them; cards blocked at one door that the other passed silently). Merge ALL
        # triage keys; authored package-derived values keep precedence (`k not in
        # ctx`), so door symmetry holds BY CONSTRUCTION for every future key and the
        # whitelist is retired. Extra raw triage-row columns (Products, ranks, …)
        # are inert to _build_predicates, which reads named keys only.
        for k, v in tctx.items():
            if k not in ctx:
                ctx[k] = v
    except Exception:
        _record_context_finding(
            ctx, code="VERIFICATION_CONTEXT_MERGE_FAILED", source=pkg,
            role="triage context merge")
    man = pkg / "manifest.json"
    _manifest = (_read_context_json(ctx, man, role="package manifest") if man.exists() else None)
    _manifest_rows = (_manifest_bgc_rows(ctx, _manifest, man)
                      if _manifest is not None else None)
    if not any(k in ctx for k in ("kcb_top", "KCB_top")) and _manifest is not None:
        # fallback: no triage row available — derive from the sealed manifest kcb_top (single-branch)
        if _manifest_rows is not None:
            for b in _manifest_rows:
                if str(b.get("bgc_id") or "").strip() == str(bgc).strip():
                    ctx.setdefault("novel_or_no_mibig", not str(b.get("kcb_top") or "").strip())
                    break
    # v9.7.233 readiness-lint inputs: per-gene conservation (novelty check),
    # per-gene TTA + CDS count + protocluster + edge (fact-binding check).
    if _manifest is not None and _manifest_rows is not None:
        try:
            m = _manifest
            # Conservation source precedence: ingested nr BLASTp (broadest reference — all
            # of GenBank) OVER ClusterBlast (narrow curated set). This matters: ClusterBlast's
            # BGC043 median is 62% (distant Streptomyces hits) while nr is ~100% to
            # Micromonospora — using ClusterBlast alone would let the novelty over-claim pass.
            from .genome_explore import _conservation_observation
            observation = _conservation_observation(pkg, m, str(bgc))
            ctx["conservation_source"] = observation["source"]
            ctx["conservation_source_status"] = observation["status"]
            if observation["invalid_source"]:
                ctx["conservation_invalid_source"] = observation["invalid_source"]
            if observation["median_id"] is not None:
                ctx["conservation_median_id"] = observation["median_id"]
                ctx["conservation_n_genes"] = observation["n_genes"]
                ctx["multispecies_hits"] = observation["multispecies_hits"]
            # v9.7.240: the per-BGC median is only interpretable against the genome-wide background.
            # When a near-relative is deposited in nr, rank-1 identity saturates (AS-XXX: background
            # 95.4%, all 36 BGCs 92-99%) and an absolute >=90% floor flags every cluster. Carry the
            # background so a novelty verdict is never read without its reference point.
            from .genome_explore import _conservation_background_observation as _cbg
            _background = _cbg(pkg)
            _bg = _background["median_id"]
            _bgn = _background["n_genes"]
            ctx["conservation_background_status"] = _background["status"]
            if _background["invalid_source"]:
                ctx["conservation_background_invalid_source"] = _background["invalid_source"]
            if _bg is not None:
                ctx["conservation_background_id"] = round(_bg, 1)
                ctx["conservation_background_n"] = _bgn
                ctx["conservation_saturated"] = _bg >= 90.0
            for b in _manifest_rows:
                if str(b.get("bgc_id") or "").strip() == str(bgc).strip():
                    # v9.7.240 (P2): protocluster_count is the antiSMASH `protocluster`
                    # feature count. single_protocluster_count counts /kind="single"
                    # cand_clusters; they are different numbers (AS-XXX BGC041: 3 vs 1).
                    # Aliasing them made modeb_structure_gate raise FACT_MISMATCH against
                    # cards stating the correct count, and pass cards stating 1.
                    # Read the real field; stay silent when an older package lacks it.
                    if b.get("protocluster_count") is not None:
                        ctx["protocluster_count"] = b.get("protocluster_count")
                    if b.get("edge_status"):
                        ctx["edge_status"] = b.get("edge_status")
                    break
        except OSError:
            _record_context_finding(
                ctx, code="VERIFICATION_CONTEXT_UNREADABLE", source=man,
                role="package conservation context")
        except (AttributeError, TypeError, KeyError, ValueError):
            _record_context_finding(
                ctx, code="VERIFICATION_CONTEXT_MALFORMED", source=man,
                role="package conservation context")
    # per-gene TTA + CDS count from gene_context.jsonl
    try:
        gc = next(pkg.glob("*gene_context.jsonl"), None)
    except OSError:
        gc = None
        _record_context_finding(
            ctx, code="VERIFICATION_CONTEXT_UNREADABLE", source=pkg,
            role="gene-context discovery")
    if gc:
        for r in _read_context_jsonl(ctx, gc, role="gene context") or ():
            if str(r.get("bgc_id") or "").strip() == str(bgc).strip():
                cds = r.get("cds", [])
                if any(not isinstance(g, dict) for g in cds):
                    _record_context_finding(
                        ctx, code="VERIFICATION_CONTEXT_MALFORMED", source=gc,
                        role="gene context")
                    break
                ctx["cds_count"] = len(cds)
                ctx["tta_by_gene"] = {
                    str(g["locus_tag"]).lower(): g.get("tta_codons", 0)
                    for g in cds if g.get("locus_tag")
                }
                break
    return ctx


def guard_deliverable_name(path: str | Path, *, bgc_context: dict | None = None,
                           strict_depth: bool = True) -> tuple[bool, list[str]]:
    """Refuse to let a file be *named* a Mode B card unless it passes lint_card.

    Returns (allowed, reasons). If the filename does not claim to be Mode B, always allowed.
    If it does, the file must exist and pass lint_card (no NO_HEADINGS_DETECTED / EMPTY_CARD /
    structural ERROR; strict depth by default). This is the structural block on the reported
    failure: a 5-section hand-built doc titled "Mode B Card" cannot pass NO_HEADINGS_DETECTED.
    """
    p = Path(path)
    if not _MODEB_NAME_RE.search(p.name):
        return True, []  # not claiming to be Mode B — nothing to guard
    if not p.exists():
        return False, [f"named a Mode B deliverable but file not found: {p}"]
    md = p.read_text(encoding="utf-8", errors="replace")
    findings = lint_card(md, bgc_context=bgc_context, check_depth=True, strict_depth=strict_depth, check_claim_safety=True, check_evidence_presence=True)
    errs = [f for f in findings if f.get("severity") == "ERROR"]
    if errs:
        reasons = [f"{f.get('code')}: {f.get('message')}" for f in errs]
        return False, [f"'{p.name}' is named a Mode B card but fails lint_card:"] + reasons
    return True, []


# --------------------------------------------------------------------------- CLI
def verify_guide_command(args) -> int:
    ok, errors, warnings = verify_authored_guide(args.file, audience=getattr(args, "audience", "both"))
    label = Path(args.file).name
    if ok:
        emit(f"[verify-guide] {label}: OK — authored ({len(warnings)} warning(s))")
        for w in warnings:
            emit(f"        WARN: {w}")
        return 0
    emit(f"[verify-guide] {label}: FAIL — {len(errors)} error(s). This reads the AUTHORED file, "
          f"not the skeleton; a blank template fails here by design.")
    for e in errors:
        emit(f"        ERROR: {e}")
    for w in warnings:
        emit(f"        WARN: {w}")
    return 1


# v9.7.324+ (F-cov, reconciled with the other chat's AS-XXX BGC054 finding): verify-modeb reports
# OK on a CARD-ONLY run (no --package/--bgc), but §4_BLASTP_COVERAGE then scores completeness against
# the card's OWN core rows — with bgc_context=None the denominator collapses to n_card_cores, so a
# thin §4 that lists reconciled BLASTp verdicts for the few rows it shows passes clean (BGC054 shipped
# 3 core rows and sailed through all three gates). The pure gate keeps that card-only behaviour by
# design (locked by test_modeb_core_denominator_v9_7_323); the hole is that verify-modeb *certifies*
# coverage it never actually checked. Fix: when §4 asserts reconciled per-gene BLASTp verdicts but no
# authoritative package core count reached the gate, surface a COVERAGE_UNVERIFIED WARN and mark the
# summary line, so a bare OK can't be mistaken for "coverage verified."
_S4_VERDICT_RE = re.compile(r"\b(?:CONFIRM|REFINE|OVERTURN)\b")


def _coverage_unverified_reason(card_md: str, ctx: "dict | None") -> "str | None":
    """WARN reason when §4 makes reconciled per-gene BLASTp claims but verify-modeb had no
    authoritative package rule-based core count to judge §4 completeness against — i.e. a card-only
    run, or a --package/--bgc that yielded no core count (wrong --bgc, missing gene table). Returns
    None when there is no reconciled §4 claim to certify, or when the real denominator was available
    (item 5's §4_BLASTP_COVERAGE then really ran). Pure/testable; does not change the gate itself."""
    from .modeb_structure_gate import extract_section_bodies
    s4 = extract_section_bodies(card_md).get(4, "")
    if not s4 or not _S4_VERDICT_RE.search(s4):
        return None  # §4 asserts no CONFIRM/REFINE/OVERTURN -> no completeness claim to check
    if (ctx or {}).get("n_core_genes") or (ctx or {}).get("core_gene_count"):
        return None  # authoritative core count present -> §4_BLASTP_COVERAGE (item 5) really ran
    return ("§4 asserts reconciled per-gene BLASTp verdicts, but verify-modeb had no package "
            "rule-based core count to judge §4 completeness against — coverage was scored against the "
            "card's OWN rows, which cannot detect a thin or omitted grid. Re-run "
            "`verify-modeb --package <sealed package> --bgc <BGCid>` so §4_BLASTP_COVERAGE gates "
            "against the real rule-based core count (item 5).")


def verify_modeb_command(args) -> int:
    p = Path(args.file)
    label = p.name
    if not p.exists():
        emit(f"[verify-modeb] {label}: FAIL — file not found")
        report_path = getattr(args, "report_json", None)
        if report_path:
            report = build_verify_report(
                card_name=label, profile="unresolved", exit_code=1,
                findings=[{"severity": "ERROR", "code": "FILE_NOT_FOUND", "section": None,
                           "message": f"Authored card file not found: {label}"}],
                independent_roster_bound=False, package_core_denominator_bound=False,
            )
            write_verify_report(report_path, report)
        return 1
    md = p.read_text(encoding="utf-8", errors="replace")
    ctx = _bgc_context_from_package(getattr(args, "package", None), getattr(args, "bgc", None))
    strict = not getattr(args, "no_strict_depth", False)
    # B1 (v9.7.373): the publication (§§1–48) gate is profile-triggered. A card that declares the
    # strict finished profile — FINISHED_FULL48_CURRENT_EVIDENCE, or the grandfathered legacy alias
    # FINISHED_CURRENT_EVIDENCE (ratified vocabulary 2026-08-21) — is asserting it meets the
    # publication contract, so verify-modeb holds it to that contract and supplies the authoritative
    # per-BGC roster (from the BREAK-1 ctx["known_locus_tags"]) to the roster check. Draft / candidate
    # cards (no finished token) keep the existing structure+depth path unchanged. This mirrors the
    # matrix gate, which already self-triggers on the same finished token.
    _finished_profile = ("FINISHED_FULL48_CURRENT_EVIDENCE" in md) or ("FINISHED_CURRENT_EVIDENCE" in md)
    _substantive_quality_v2 = bool(getattr(args, "substantive_quality_v2", False))
    _semantic_sections_v3 = bool(getattr(args, "semantic_sections_v3", False))
    _semantic_comparators_v4 = bool(getattr(args, "semantic_comparators_v4", False))
    _semantic_sections_v5 = bool(getattr(args, "semantic_sections_v5", False))
    _semantic_decision_chains_v6 = bool(getattr(args, "semantic_decision_chains_v6", False))
    _semantic_claim_models_v7 = bool(getattr(args, "semantic_claim_models_v7", False))
    _inventory_reconciliation_v8 = bool(getattr(args, "inventory_reconciliation_v8", False))
    _selection_process_v9 = bool(getattr(args, "selection_process_v9", False))
    _figure_spec_v10 = bool(getattr(args, "figure_spec_v10", False))
    _reconciliation_specificity_v11 = bool(
        getattr(args, "reconciliation_specificity_v11", False))
    findings = list((ctx or {}).get(_CONTEXT_FINDINGS_KEY, [])) + lint_card(md, bgc_context=ctx, check_depth=True, strict_depth=strict, check_class_content=True, check_claim_safety=True, check_evidence_presence=True,
                         check_publication_quality=_finished_profile,
                         check_substantive_quality_v2=(_finished_profile and _substantive_quality_v2),
                         check_semantic_sections_v3=(_finished_profile and _semantic_sections_v3),
                         check_semantic_comparators_v4=(_finished_profile and _semantic_comparators_v4),
                         check_semantic_sections_v5=(_finished_profile and _semantic_sections_v5),
                         check_semantic_decision_chains_v6=(_finished_profile and _semantic_decision_chains_v6),
                         check_semantic_claim_models_v7=(_finished_profile and _semantic_claim_models_v7),
                         check_inventory_reconciliation_v8=(_finished_profile and _inventory_reconciliation_v8),
                         check_selection_process_v9=(_finished_profile and _selection_process_v9),
                         check_figure_spec_v10=(_finished_profile and _figure_spec_v10),
                         check_reconciliation_specificity_v11=(
                             _finished_profile and _reconciliation_specificity_v11),
                         canonical_loci=((ctx or {}).get("known_locus_tags") if _finished_profile else None))
    if _substantive_quality_v2 and not _finished_profile:
        findings.append({
            "severity": "ERROR",
            "code": "SUBSTANTIVE_QUALITY_V2_REQUIRES_FINISHED_PROFILE",
            "section": None,
            "expected": "FINISHED_FULL48_CURRENT_EVIDENCE profile token",
            "found": "finished profile token absent",
            "message": (
                "--substantive-quality-v2 is a finished-card review gate. "
                "Declare FINISHED_FULL48_CURRENT_EVIDENCE only after all other "
                "finished-card requirements are actually met."
            ),
        })
    if _semantic_sections_v3 and not _finished_profile:
        findings.append({
            "severity": "ERROR",
            "code": "SEMANTIC_SECTIONS_V3_REQUIRES_FINISHED_PROFILE",
            "section": None,
            "expected": "FINISHED_FULL48_CURRENT_EVIDENCE profile token",
            "found": "finished profile token absent",
            "message": (
                "--semantic-sections-v3 is a finished-card review gate. "
                "Declare FINISHED_FULL48_CURRENT_EVIDENCE only after all other "
                "finished-card requirements are actually met."
            ),
        })
    if _semantic_comparators_v4 and not _finished_profile:
        findings.append({
            "severity": "ERROR",
            "code": "SEMANTIC_COMPARATORS_V4_REQUIRES_FINISHED_PROFILE",
            "section": None,
            "expected": "FINISHED_FULL48_CURRENT_EVIDENCE profile token",
            "found": "finished profile token absent",
            "message": (
                "--semantic-comparators-v4 is a finished-card review gate. "
                "Declare FINISHED_FULL48_CURRENT_EVIDENCE only after all other "
                "finished-card requirements are actually met."
            ),
        })
    if _semantic_sections_v5 and not _finished_profile:
        findings.append({
            "severity": "ERROR",
            "code": "SEMANTIC_SECTIONS_V5_REQUIRES_FINISHED_PROFILE",
            "section": None,
            "expected": "FINISHED_FULL48_CURRENT_EVIDENCE profile token",
            "found": "finished profile token absent",
            "message": (
                "--semantic-sections-v5 is a finished-card review gate. "
                "Declare FINISHED_FULL48_CURRENT_EVIDENCE only after all other "
                "finished-card requirements are actually met."
            ),
        })
    if _semantic_decision_chains_v6 and not _finished_profile:
        findings.append({
            "severity": "ERROR",
            "code": "SEMANTIC_DECISION_CHAINS_V6_REQUIRES_FINISHED_PROFILE",
            "section": None,
            "expected": "FINISHED_FULL48_CURRENT_EVIDENCE profile token",
            "found": "finished profile token absent",
            "message": (
                "--semantic-decision-chains-v6 is a finished-card review gate. "
                "Declare FINISHED_FULL48_CURRENT_EVIDENCE only after all other "
                "finished-card requirements are actually met."
            ),
        })
    if _semantic_claim_models_v7 and not _finished_profile:
        findings.append({
            "severity": "ERROR",
            "code": "SEMANTIC_CLAIM_MODELS_V7_REQUIRES_FINISHED_PROFILE",
            "section": None,
            "expected": "FINISHED_FULL48_CURRENT_EVIDENCE profile token",
            "found": "finished profile token absent",
            "message": "--semantic-claim-models-v7 is a finished-card review gate.",
        })
    if _inventory_reconciliation_v8 and not _finished_profile:
        findings.append({
            "severity": "ERROR",
            "code": "INVENTORY_RECONCILIATION_V8_REQUIRES_FINISHED_PROFILE",
            "section": None,
            "expected": "FINISHED_FULL48_CURRENT_EVIDENCE profile token",
            "found": "finished profile token absent",
            "message": "--inventory-reconciliation-v8 is a finished-card review gate.",
        })
    if _selection_process_v9 and not _finished_profile:
        findings.append({
            "severity": "ERROR",
            "code": "SELECTION_PROCESS_V9_REQUIRES_FINISHED_PROFILE",
            "section": None,
            "expected": "FINISHED_FULL48_CURRENT_EVIDENCE profile token",
            "found": "finished profile token absent",
            "message": "--selection-process-v9 is a finished-card review gate.",
        })
    if _figure_spec_v10 and not _finished_profile:
        findings.append({
            "severity": "ERROR",
            "code": "FIGURE_SPEC_V10_REQUIRES_FINISHED_PROFILE",
            "section": None,
            "expected": "FINISHED_FULL48_CURRENT_EVIDENCE profile token",
            "found": "finished profile token absent",
            "message": "--figure-spec-v10 is a finished-card review gate.",
        })
    if _reconciliation_specificity_v11 and not _finished_profile:
        findings.append({
            "severity": "ERROR",
            "code": "RECONCILIATION_SPECIFICITY_V11_REQUIRES_FINISHED_PROFILE",
            "section": None,
            "expected": "FINISHED_FULL48_CURRENT_EVIDENCE profile token",
            "found": "finished profile token absent",
            "message": "--reconciliation-specificity-v11 is a finished-card review gate.",
        })
    # MB-04 (v9.7.338): with MB-01's restored §4 signal, BLASTP_ABSENT (no core carries a real
    # per-gene BLASTp %id + reconciliation) is a substantive evidence failure, not a style note — a
    # Pfam-only §4. Promote it to ERROR when an AUTHORITATIVE package rule-based core count reached the
    # gate (i.e. --package/--bgc supplied a real denominator), so verify-modeb can no longer return OK
    # on a Pfam-only §4. The honest DATA_REQUESTED path (the card explicitly requests the missing data)
    # stays WARN; a card-only run with no package core count stays WARN (COVERAGE_UNVERIFIED already
    # flags that it could not be certified).
    _pkg_core_count = bool((ctx or {}).get("n_core_genes") or (ctx or {}).get("core_gene_count"))
    if _pkg_core_count:
        for f in findings:
            if f.get("code") == "BLASTP_ABSENT" and f.get("severity") == "WARN":
                f["severity"] = "ERROR"
    # v9.7.409 B2 (owner ruling 2026-09-04): a card declaring the finished/publication profile asserts
    # it meets the claim-safety contract, so product-identity phrasing is a BLOCKING failure there, not
    # an advisory WARN (an overclaimed finished card verified "OK / exit 0" before this). Draft and
    # candidate cards keep WARN so authors can iterate. Escape hatch: --force (reviewed phrase).
    if _finished_profile and not getattr(args, "force", False):
        for f in findings:
            if f.get("code") in ("CLAIM_SAFETY", "KCB_IDENTITY_RISK") and f.get("severity") == "WARN":  # v9.7.409 (CLAUDE_409/F3 merged): KCB identity risk blocks on the finished profile too
                f["severity"] = "ERROR"
    errs = [f for f in findings if f.get("severity") == "ERROR"]
    warns = [f for f in findings if f.get("severity") == "WARN"]
    cov_gap = _coverage_unverified_reason(md, ctx)
    if cov_gap:
        warns = warns + [{"severity": "WARN", "code": "COVERAGE_UNVERIFIED", "section": 4,
                          "message": cov_gap}]
    # FA4: optional interpretation layer (advisory WARN-severity; never changes PASS/FAIL).
    if getattr(args, "interp", False):
        from .modeb_interp_gate import interp_findings
        warns = warns + interp_findings(md, strict=getattr(args, "interp_strict", False))
    # v9.7.405 (CODEX_390 G5 verifier diagnostics, hand-merged onto the current §1–§48 wording):
    # optional JSON receipt (--report-json) and grouped diagnostic lines (--summary-only).
    all_report_findings = errs + warns
    exit_code = 0 if not errs else 1
    profile_name = "§1\u2013§48 structure + depth"
    if _substantive_quality_v2:
        profile_name += " + substantive quality v2"
    if _semantic_sections_v3:
        profile_name += " + semantic sections v3"
    if _semantic_comparators_v4:
        profile_name += " + semantic comparators v4"
    if _semantic_sections_v5:
        profile_name += " + semantic sections v5"
    if _semantic_decision_chains_v6:
        profile_name += " + semantic decision chains v6"
    if _semantic_claim_models_v7:
        profile_name += " + semantic claim models v7"
    if _inventory_reconciliation_v8:
        profile_name += " + inventory reconciliation v8"
    if _selection_process_v9:
        profile_name += " + selection process v9"
    if _figure_spec_v10:
        profile_name += " + figure specification v10"
    if _reconciliation_specificity_v11:
        profile_name += " + reconciliation specificity v11"
    report_path = getattr(args, "report_json", None)
    if report_path:
        report = build_verify_report(
            card_name=label, profile=profile_name, exit_code=exit_code,
            findings=all_report_findings,
            independent_roster_bound=False,
            package_core_denominator_bound=bool(_pkg_core_count),
        )
        try:
            write_verify_report(report_path, report)
        except OSError as exc:
            sys.stderr.write(f"[verify-modeb] REPORT_WRITE_FAILED: {exc}\n")
            return 2
    summary_only = bool(getattr(args, "summary_only", False))
    if not errs:
        head = "OK" if not cov_gap else "OK (§4 coverage NOT verified — no package core count)"
        emit(f"[verify-modeb] {label}: {head} — {profile_name} ({len(warns)} warning(s))")
        if summary_only:
            for line in compact_verify_summary_lines(warns):
                sys.stdout.write(f"        {line}\n")
        else:
            for w in warns:
                emit(f"        WARN: {w.get('code')}: {w.get('message')}")
        return 0
    emit(f"[verify-modeb] {label}: FAIL — {len(errs)} error(s). A hand-built doc without §1\u2013§48 "
          f"headings fails NO_HEADINGS_DETECTED here; a thin card fails depth.")
    if summary_only:
        for line in compact_verify_summary_lines(all_report_findings):
            sys.stdout.write(f"        {line}\n")
    else:
        for f in errs:
            emit(f"        ERROR: {f.get('code')}: {f.get('message')}")
        for w in warns:
            emit(f"        WARN: {w.get('code')}: {w.get('message')}")
    return 1
