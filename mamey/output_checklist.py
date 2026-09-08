from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path
from typing import Any


def _scan_lookup(run: Any) -> dict[str, tuple[str, str]]:
    scans = {}
    try:
        raw = run.scan_status.get('scans', []) if isinstance(run.scan_status, dict) else []
        for name, status, note in raw:
            scans[str(name)] = (str(status), str(note))
    except Exception:
        pass
    return scans


def _status(condition: bool, partial: bool = False) -> str:
    if condition:
        return 'COMPLETE'
    if partial:
        return 'PARTIAL'
    return 'PENDING'


def build_output_checklist(run: Any, package_dir: str | Path) -> list[dict[str, str]]:
    """Build a user-facing status checklist for the Mamey/Sapote output suite.

    The checklist is deliberately evidence-oriented: every row reports the expected
    output, current status, and the file or scan result that supports that status.
    It is safe to write during the extraction phase and makes downstream Sapote
    judgment/report progress visible instead of hidden in the final package.
    """
    package_dir = Path(package_dir)
    strain = getattr(run.context, 'strain_id', 'STRAIN')
    bgcs = list(getattr(run, 'bgcs', []) or [])
    raw_n = len(bgcs)
    scan = _scan_lookup(run)
    ss = getattr(run, 'source_scans', None)

    def exists(name: str) -> bool:
        return (package_dir / name).exists()

    def scan_row(name: str, label: str) -> dict[str, str]:
        st, note = scan.get(name, ('PENDING', 'not run or not recorded'))
        return {
            'Phase': 'Source scans',
            'Output_or_task': label,
            'Expected_artifact_or_evidence': f'{strain}_3_scan_states.json / manifest.json source_scans.{name}',
            'Status': 'COMPLETE' if st in {'PASS', 'NULL'} else st,
            'Progress': st,
            'Evidence': note,
            'Next_action': 'Use in Sapote judgment; confirm with external tools before manuscript claims.' if st in {'PASS', 'NULL'} else 'Run or repair scan.',
        }

    rows: list[dict[str, str]] = []
    rows.extend([
        {'Phase': 'Run setup', 'Output_or_task': 'Intake metadata locked', 'Expected_artifact_or_evidence': f'{strain}_1_intake.json', 'Status': _status(exists(f'{strain}_1_intake.json')), 'Progress': f'{raw_n} BGC IDs locked', 'Evidence': f'{strain}_1_intake.json', 'Next_action': 'Carry unresolved host/site metadata as unresolved, not guessed.'},
        {'Phase': 'Extraction', 'Output_or_task': 'BGC inventory table', 'Expected_artifact_or_evidence': f'{strain}_2_inventory.csv', 'Status': _status(exists(f'{strain}_2_inventory.csv') and raw_n > 0), 'Progress': f'{raw_n}/{raw_n} BGCs', 'Evidence': f'{strain}_2_inventory.csv', 'Next_action': 'Use inventory as immutable BGC numbering reference.'},
        {'Phase': 'Extraction', 'Output_or_task': 'Auto triage board', 'Expected_artifact_or_evidence': f'{strain}_4_triage_board.csv', 'Status': _status(exists(f'{strain}_4_triage_board.csv')), 'Progress': 'ranked auto board written' if exists(f'{strain}_4_triage_board.csv') else 'not written', 'Evidence': f'{strain}_4_triage_board.csv', 'Next_action': 'Do not use auto rank alone; follow with Sapote judgment.'},
        {'Phase': 'Workbook', 'Output_or_task': 'Per-strain workbook', 'Expected_artifact_or_evidence': f'{strain}_5_workbook.xlsx', 'Status': _status(exists(f'{strain}_5_workbook.xlsx')), 'Progress': 'written' if exists(f'{strain}_5_workbook.xlsx') else 'missing', 'Evidence': f'{strain}_5_workbook.xlsx', 'Next_action': 'Populate judgment/write-back layer after Sapote pass.'},
        {'Phase': 'Packaging', 'Output_or_task': 'Manifest and checksums', 'Expected_artifact_or_evidence': 'manifest.json; checksums_sha256.txt', 'Status': _status(exists('manifest.json') and exists('checksums_sha256.txt')), 'Progress': 'sealed package' if exists('manifest.json') and exists('checksums_sha256.txt') else 'not sealed', 'Evidence': 'manifest.json; checksums_sha256.txt', 'Next_action': 'Regenerate after every artifact addition.'},
        {'Phase': 'Deliverable', 'Output_or_task': 'Deterministic strain brief (extraction-layer)', 'Expected_artifact_or_evidence': f'{strain}_8_strain_brief.pdf; {strain}_8a_fig_landscape.png(+_data.csv)', 'Status': 'COMPLETE (extraction-layer)' if exists(f'{strain}_8_strain_brief.pdf') else 'SKIPPED', 'Progress': 'rendered from manifest + triage' if exists(f'{strain}_8_strain_brief.pdf') else 'not rendered (--brief none or render skipped)', 'Evidence': f'{strain}_8_strain_brief.pdf', 'Next_action': 'Human-readable summary of extracted capacity; Sapote-layer deliverables below remain pending.'},
        {'Phase': 'Deliverable', 'Output_or_task': 'Deterministic Sapote figures (DAPR scatter, AB/AF ranked, claim-safety funnel)', 'Expected_artifact_or_evidence': f'{strain}_8c_fig_dapr_scatter.png; {strain}_8d_fig_ab_ranked.png; {strain}_8e_fig_af_ranked.png; {strain}_8f_fig_funnel.png (each +_data.csv)', 'Status': 'COMPLETE (extraction-layer)' if exists(f'{strain}_8d_fig_ab_ranked.png') else 'SKIPPED', 'Progress': 'rendered from triage + manifest' if exists(f'{strain}_8d_fig_ab_ranked.png') else 'not rendered (--brief none or render skipped)', 'Evidence': f'{strain}_8d_fig_ab_ranked.png', 'Next_action': 'Data-only priority figures; capacity-level, KCB=similarity. Reference-overlay + cross-strain class matrix are cohort-level (see figure overlay spec).'},
    ])
    for name, label in [
        ('KCB_sweep', 'KnownClusterBlast sweep'),
        ('FLBR', 'fragment/linkage rescue scan'),
        ('CCTT', 'cassette / trigger scan'),
        ('CGAD', 'glycosylation arm scan'),
        ('UMED', 'RiPP maturation/gap scan'),
        ('EFLS', 'edge-fragment linkage scan'),
        ('resistance', 'self-resistance / transporter scan'),
        ('bldA_TTA', 'bldA/TTA codon scan'),
        ('TFBS', 'regulatory motif scan'),
    ]:
        rows.append(scan_row(name, label))

    # Source-scan subtasks visible even when generated inside manifest rather than as standalone files.
    if ss is not None:
        extra = [
            ('chitinase', 'chitinase / fungal-interaction scan'),
            ('regulators', 'regulator family scan'),
            ('transporters', 'transporter family scan'),
            ('cassettes', 'cassette registry scan'),
            ('wetlab_rows', 'wet-lab detection guide rows'),
            ('qs_signals', 'QS/NAPAA routing'),
            ('glycosylation_arms', 'glycosylation arm candidates'),
            ('per_bgc_dss', 'per-BGC DSS evidence'),
        ]
        for key, label in extra:
            val = getattr(ss, key, None) if not isinstance(ss, dict) else ss.get(key)
            present = bool(val)
            rows.append({
                'Phase': 'Source scans',
                'Output_or_task': label,
                'Expected_artifact_or_evidence': f'manifest.json source_scans.{key}',
                'Status': _status(present),
                'Progress': (val.get('status', 'SOURCE_DERIVED') if isinstance(val, dict) else 'SOURCE_DERIVED') if present else 'missing',
                'Evidence': f'manifest.json:{key}' if present else 'not present',
                'Next_action': 'Use as source-derived evidence; verify before manuscript use.' if present else 'Add/repair scan.',
            })

    rows.extend([
        {'Phase': 'Sapote judgment', 'Output_or_task': 'Full Mode B status for every BGC', 'Expected_artifact_or_evidence': 'External Sapote judgment workbook/ledger', 'Status': 'JUDGMENT_PENDING', 'Progress': f'{raw_n}/{raw_n} depth-floor assignments ready for judgment', 'Evidence': 'gate_validation.json gold_completeness=JUDGMENT_PENDING', 'Next_action': 'Load manifest.json into Sapote/LLM judgment layer and write per-BGC interpretations.'},
        {'Phase': 'Sapote reporting', 'Output_or_task': 'Technical report PDF', 'Expected_artifact_or_evidence': f'{strain}_Mamey_Sapote_Technical_Report.pdf', 'Status': 'REQUIRED', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote full-run profile (Modules 1–20)', 'Next_action': 'Run full project-wide delivery trigger in Sapote; compile Mode B + DAPR + Ecology into technical report.'},
        {'Phase': 'Sapote reporting', 'Output_or_task': 'DAPR dual-track priority table', 'Expected_artifact_or_evidence': f'{strain}_DAPR_AB_AF_Priority.md', 'Status': 'REQUIRED', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote Module 17 (DAPR)', 'Next_action': 'Run DAPR module after triage board is complete.'},
        {'Phase': 'Sapote reporting', 'Output_or_task': 'Fermentation/Induction/Extraction Plan', 'Expected_artifact_or_evidence': f'{strain}_Fermentation_Induction_Plan.md', 'Status': 'REQUIRED', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote Module 18 + wetlab_rows from manifest', 'Next_action': 'Run Module 18 after DAPR; derive from bldA tier + TFBS + wetlab_rows.'},
        {'Phase': 'Sapote reporting', 'Output_or_task': 'Layperson ranked guide', 'Expected_artifact_or_evidence': f'{strain}_Layperson_Ranked_BGC_Guide.md', 'Status': 'REQUIRED', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote Module 19', 'Next_action': 'Generate after Mode B and DAPR are complete; use plain-English translation rules from Module 19.'},
        {'Phase': 'Sapote reporting', 'Output_or_task': 'Compound Detection and Isolation Bench Guide', 'Expected_artifact_or_evidence': f'{strain}_Compound_Detection_Isolation_Bench_Guide.md', 'Status': 'REQUIRED', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote Module 20 + DAPR top leads', 'Next_action': 'Generate for top-2 AB + top-2 AF leads; all mandatory fields from Module 20 template must be present.'},
    ])
    return rows


def write_output_checklist(run: Any, package_dir: str | Path) -> tuple[Path, Path]:
    package_dir = Path(package_dir)
    strain = getattr(run.context, 'strain_id', 'STRAIN')
    rows = build_output_checklist(run, package_dir)
    # P01: judgment pointer row — direct the user to full Sapote Mode B instead of stopping here.
    try:
        import json as _json
        af = package_dir / f'{strain}_ANALYSIS_FORWARD.md'
        if af.exists():
            _man = _json.loads((package_dir / 'manifest.json').read_text(encoding="utf-8"))
            _n = (_man.get('bgc_counts') or {}).get('raw', 0)
            _judged = bool(_man.get('top_bgc_targets')) or bool(_man.get('wet_lab_priorities'))
            rows.append({
                'Phase': 'Judgment',
                'Output_or_task': 'Full Sapote Mode B (\u00a71\u2013\u00a78) judgment',
                'Expected_artifact_or_evidence': f'{strain}_ANALYSIS_FORWARD.md',
                'Status': 'COMPLETE' if _judged else 'PENDING',
                'Progress': f'{_n}/{_n}' if _judged else f'0/{_n} BGCs',
                'Evidence': f'{strain}_ANALYSIS_FORWARD.md',
                'Next_action': '\u2014' if _judged else f'Run full Sapote analysis on {strain}',
            })
    except Exception:
        pass
    csv_path = package_dir / f'{strain}_6_output_checklist.csv'
    md_path = package_dir / f'{strain}_6_output_checklist.md'
    headers = ['Phase', 'Output_or_task', 'Expected_artifact_or_evidence', 'Status', 'Progress', 'Evidence', 'Next_action']
    # v9.7.371 fix: was a direct write. cli.py calls this right before regenerating the final
    # manifest/checksums so the checklist itself is tracked -- an interrupted write here would
    # seal a truncated checklist file as if it were valid (the checksum step never sees the
    # half-written state to catch it). Same tmp-sibling+replace pattern as packaging.py.
    _csv_tmp = csv_path.with_name(csv_path.name + '.tmp')
    with _csv_tmp.open('w', newline='', encoding='utf-8') as f:
        w = _SafeDictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
    _csv_tmp.replace(csv_path)
    lines = [f'# {strain} Output Progress Checklist', '', '| Phase | Output / task | Status | Progress | Next action |', '|---|---|---:|---|---|']
    for r in rows:
        lines.append(f"| {r['Phase']} | {r['Output_or_task']} | {r['Status']} | {r['Progress']} | {r['Next_action']} |")
    _md_tmp = md_path.with_name(md_path.name + '.tmp')
    _md_tmp.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    _md_tmp.replace(md_path)
    return csv_path, md_path
