from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import os
import shutil
from pathlib import Path
from typing import Any


def _atomic_write_text(path: Path, text: str, encoding: str = 'utf-8') -> None:
    """AUDIT_374: tmp-sibling + os.replace, so a crash mid-write never leaves a
    truncated package-transparency deliverable on disk (matches mamey/packaging.py's helper)."""
    tmp = str(path) + '.tmp'
    try:
        with open(tmp, 'w', encoding=encoding) as fh:
            fh.write(text)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, str(path))

STATUS_GLOSSARY = {
    'COMPLETE_NATIVE': 'Filled from Mamey/antiSMASH extraction evidence.',
    'COMPLETE_USER_METADATA': 'Filled from user-supplied metadata.',
    'COMPLETE_EXTERNAL_EVIDENCE': 'Filled from provided HMMER/DIAMOND/BLAST or other evidence.',
    'COMPLETE_INFERRED_LOW_CONFIDENCE': 'Filled by conservative inference; review before claims.',
    'NEEDS_ANTISMASH_OUTPUT': 'Needs antiSMASH output ZIP/folder; assembled FASTA alone is not enough.',
    'NEEDS_PROTEIN_FASTA': 'Needs protein FASTA before HMMER/DIAMOND evidence can be generated.',
    'NEEDS_HMMER_DOMTBLOUT': 'Needs HMMER hmmscan --domtblout structured output.',
    'NEEDS_DIAMOND_TSV': 'Needs DIAMOND BLASTP-like TSV output.',
    'MANUAL_BLASTP_OPTIONAL': 'Optional NCBI BLASTP spot-check for top proteins only.',
    'LOW_CONFIDENCE_REVIEW': 'Evidence exists but requires review before claims.',
    'UNRESOLVED_METADATA': 'Metadata not supplied; do not infer.',
    'NOT_APPLICABLE': 'Field does not apply to this strain/BGC/class.',
    'DEFER_SERVER_R2': 'Flagged for future server-assisted Release 2 workflow.',
}
STATUS_CODES = set(STATUS_GLOSSARY)

HEADERS = [
    'worksheet', 'cell_or_field', 'data_label', 'current_value', 'status_code',
    'derived_from', 'source_file', 'source_parser', 'evidence_type', 'confidence',
    'why_missing_if_blank', 'how_to_fill', 'release_handling', 'notes_for_llm'
]

WORKLIST_HEADERS = [
    'priority', 'status_code', 'worksheet', 'cell_or_field', 'data_label',
    'blocking_for_claims', 'how_to_fill', 'release_handling', 'notes_for_llm'
]


def _exists(package_dir: Path, name: str) -> bool:
    return (package_dir / name).exists()


def build_cell_provenance(run: Any, package_dir: str | Path) -> list[dict[str, str]]:
    """Return a transparent per-field provenance table for standalone packages.

    The goal is not to enumerate every literal Excel coordinate. It enumerates the
    major workbook/report fields and every external-evidence field where silent
    blanks would otherwise occur. LLMs and users can read this table to understand
    where data came from and what to do next.
    """
    package_dir = Path(package_dir)
    strain = getattr(run.context, 'strain_id', 'STRAIN')
    rows: list[dict[str, str]] = []
    bgcs = list(getattr(run, 'bgcs', []) or [])

    def add(**kwargs: str) -> None:
        row = {h: '' for h in HEADERS}
        row.update({k: str(v) for k, v in kwargs.items()})
        sc = row.get('status_code', '')
        assert not sc or sc in STATUS_CODES, f"unknown status_code: {sc!r}"
        rows.append(row)

    # Package-level provenance.
    add(worksheet='Intake', cell_or_field='strain_id', data_label='Strain ID',
        current_value=strain, status_code='COMPLETE_USER_METADATA',
        derived_from='CLI argument or ZIP stem', source_file=f'{strain}_1_intake.json',
        source_parser='mamey.cli', evidence_type='metadata', confidence='high',
        how_to_fill='Supply --strain or use clear ZIP filename.', release_handling='Release 1 standalone',
        notes_for_llm='Strain identifiers are user/project metadata; do not rewrite them without user instruction.')
    add(worksheet='Intake', cell_or_field='taxonomy', data_label='Taxonomy',
        current_value=getattr(run.context, 'taxonomy', ''), status_code='COMPLETE_USER_METADATA' if getattr(run.context, 'taxonomy', '') not in {'not verified', ''} else 'UNRESOLVED_METADATA',
        derived_from='User metadata or CLI default', source_file=f'{strain}_1_intake.json',
        source_parser='mamey.cli', evidence_type='metadata', confidence='user-supplied or unresolved',
        why_missing_if_blank='Taxonomy was not supplied or not verified.', how_to_fill='Ask user for taxonomy or add taxonomic classifier output.',
        release_handling='Release 1 manual metadata', notes_for_llm='Do not infer exact species from BGC content.')
    add(worksheet='Intake', cell_or_field='source', data_label='Isolation source',
        current_value=getattr(run.context, 'source', ''), status_code='COMPLETE_USER_METADATA' if getattr(run.context, 'source', '') not in {'not supplied', ''} else 'UNRESOLVED_METADATA',
        derived_from='User metadata or CLI default', source_file=f'{strain}_1_intake.json',
        source_parser='mamey.cli', evidence_type='metadata', confidence='user-supplied or unresolved',
        why_missing_if_blank='Source was not supplied.', how_to_fill='Ask user for host/habitat/source metadata.',
        release_handling='Release 1 manual metadata', notes_for_llm='Unresolved host/site/locality should remain unresolved, not guessed.')
    add(worksheet='BGC_Inventory', cell_or_field='all BGC rows', data_label='BGC inventory',
        current_value=f'{len(bgcs)} BGCs', status_code='COMPLETE_NATIVE' if bgcs else 'NEEDS_ANTISMASH_OUTPUT',
        derived_from='antiSMASH region GenBank files', source_file=f'{strain}_2_inventory.csv',
        source_parser='mamey.parsers.parse_bgcs_from_zip', evidence_type='antiSMASH', confidence='high if region GBKs parsed',
        why_missing_if_blank='No antiSMASH region GenBank records were parsed.', how_to_fill='Provide antiSMASH output ZIP/folder with region*.gbk files.',
        release_handling='Release 1 primary evidence', notes_for_llm='BGC numbering is immutable once written; do not renumber downstream.')
    add(worksheet='Triage', cell_or_field='auto_rank', data_label='Auto triage board',
        current_value='written' if _exists(package_dir, f'{strain}_4_triage_board.csv') else '',
        status_code='COMPLETE_NATIVE' if _exists(package_dir, f'{strain}_4_triage_board.csv') else 'NEEDS_ANTISMASH_OUTPUT',
        derived_from='BGC products, boundaries, evidence scores', source_file=f'{strain}_4_triage_board.csv',
        source_parser='mamey.scoring.triage_bgcs', evidence_type='Mamey extraction', confidence='screening only',
        how_to_fill='Run Mamey on antiSMASH output ZIP.', release_handling='Release 1 screening evidence',
        notes_for_llm='Auto rank is not final biological judgment; Sapote/Mode B review is still required.')

    # External-evidence fields that will often be missing in standalone packages.
    external_rows = [
        ('Protein_Evidence', 'protein_fasta', 'Protein FASTA available', 'NEEDS_PROTEIN_FASTA', 'protein sequences', 'STRAIN_proteins.faa', 'protein FASTA extractor or gene caller', 'protein FASTA', 'Generate proteins from antiSMASH GenBank translations or local gene calling.'),
        ('HMMER', 'hmmscan_domtblout', 'HMMER marker/cassette hits', 'NEEDS_HMMER_DOMTBLOUT', 'HMMER profile scan', 'STRAIN_hmmscan.domtblout', 'HMMER domtblout parser', 'HMMER', 'Run hmmscan --domtblout against protein FASTA and Mamey marker HMMs.'),
        ('DIAMOND', 'diamond_hits_tsv', 'Fast BLASTP-like homolog hits', 'NEEDS_DIAMOND_TSV', 'DIAMOND blastp output', 'STRAIN_diamond_hits.tsv', 'DIAMOND TSV parser', 'DIAMOND', 'Run DIAMOND blastp against selected reference protein database.'),
        ('Manual_BLASTP', 'manual_blastp_top_leads', 'Manual NCBI BLASTP top-lead checks', 'MANUAL_BLASTP_OPTIONAL', 'manual NCBI web BLASTP', 'manual_blastp_notes.tsv', 'human review', 'manual BLASTP', 'Use only for a small number of top proteins, not 10,000-query bulk annotation.'),
    ]
    for worksheet, field, label, status, derived, src, parser, evtype, fill in external_rows:
        add(worksheet=worksheet, cell_or_field=field, data_label=label, current_value='',
            status_code=status, derived_from=derived, source_file=src, source_parser=parser,
            evidence_type=evtype, confidence='not evaluated', why_missing_if_blank=f'{src} not present in package.',
            how_to_fill=fill, release_handling='Release 1 optional evidence / Release 2 automation candidate',
            notes_for_llm='Leave blank cells flagged; do not synthesize missing external evidence.')

    # Per-BGC rows: product/native complete + external evidence pending/review fields.
    for bgc in bgcs:
        products = '; '.join(getattr(bgc, 'products', []) or [])
        boundary = getattr(bgc, 'edge_status', '')
        bgc_id = getattr(bgc, 'bgc_id', 'BGC')
        add(worksheet='BGC_Inventory', cell_or_field=f'{bgc_id}.products', data_label='antiSMASH product class',
            current_value=products, status_code='COMPLETE_NATIVE' if products else 'LOW_CONFIDENCE_REVIEW',
            derived_from='antiSMASH product annotation', source_file=f'{strain}_2_inventory.csv',
            source_parser='mamey.parsers.parse_bgcs_from_zip', evidence_type='antiSMASH', confidence='antiSMASH-derived',
            why_missing_if_blank='antiSMASH product class absent or unparsable.', how_to_fill='Review region GenBank/JSON or rerun antiSMASH.',
            release_handling='Release 1 primary evidence', notes_for_llm='Use product class as a starting point, not a compound identity claim.')
        add(worksheet='BGC_Inventory', cell_or_field=f'{bgc_id}.boundary', data_label='BGC boundary status',
            current_value=boundary, status_code='COMPLETE_NATIVE', derived_from='contig coordinate comparison',
            source_file=f'{strain}_2_inventory.csv', source_parser='mamey.parsers/assembly', evidence_type='assembly', confidence='high',
            how_to_fill='Provided by antiSMASH coordinates and contig lengths.', release_handling='Release 1 primary evidence',
            notes_for_llm='Edge or full-contig BGCs must carry fragmentation caveats.')
        add(worksheet='External_Evidence', cell_or_field=f'{bgc_id}.HMM_markers', data_label='Per-BGC HMM marker hits',
            current_value='', status_code='NEEDS_HMMER_DOMTBLOUT', derived_from='HMMER domtblout',
            source_file='STRAIN_hmmscan.domtblout', source_parser='HMMER domtblout parser', evidence_type='HMMER', confidence='not evaluated',
            why_missing_if_blank='HMMER domtblout was not packaged.', how_to_fill='Generate protein FASTA; run hmmscan --domtblout; import domtblout.',
            release_handling='Release 1 optional evidence / Release 2 automation candidate', notes_for_llm='Do not infer HMM evidence from product labels alone.')
        add(worksheet='External_Evidence', cell_or_field=f'{bgc_id}.manual_blastp_top_leads', data_label='Manual BLASTP top-lead spot-check candidates',
            current_value='', status_code='MANUAL_BLASTP_OPTIONAL', derived_from='selected top BGC proteins',
            source_file=f'{strain}_5b_manual_blastp_worklist.csv', source_parser='mamey.crosswalk.candidate_blastp_rows', evidence_type='manual BLASTP', confidence='not evaluated',
            why_missing_if_blank='Manual NCBI/local BLASTP was not run in this extraction package.',
            how_to_fill='Submit only the selected worklist proteins to NCBI BLASTP or run local blastp/DIAMOND; record database, date, accession, percent identity, coverage, e-value, and functional conclusion.',
            release_handling='Release 1 optional evidence / Release 2 automation candidate', notes_for_llm='Manual BLASTP is independent support for selected top proteins, not bulk annotation.')
        add(worksheet='External_Evidence', cell_or_field=f'{bgc_id}.best_homolog', data_label='Per-BGC best homolog support',
            current_value='', status_code='NEEDS_DIAMOND_TSV', derived_from='DIAMOND TSV',
            source_file='STRAIN_diamond_hits.tsv', source_parser='DIAMOND TSV parser', evidence_type='DIAMOND', confidence='not evaluated',
            why_missing_if_blank='DIAMOND TSV was not packaged.', how_to_fill='Run DIAMOND blastp on protein FASTA and import TSV.',
            release_handling='Release 1 optional evidence / Release 2 automation candidate', notes_for_llm='Use DIAMOND for bulk homolog evidence; reserve NCBI BLASTP for top-lead spot checks.')

    return rows


def write_cell_provenance(run: Any, package_dir: str | Path) -> tuple[Path, Path, Path]:
    package_dir = Path(package_dir)
    strain = getattr(run.context, 'strain_id', 'STRAIN')
    rows = build_cell_provenance(run, package_dir)
    csv_path = package_dir / f'{strain}_7_cell_provenance.csv'
    worklist_path = package_dir / f'{strain}_7_missing_data_worklist.csv'
    md_path = package_dir / f'{strain}_7_cell_provenance_README.md'

    import io as _io
    _csv_buf = _io.StringIO()
    w = _SafeDictWriter(_csv_buf, fieldnames=HEADERS)
    w.writeheader()
    w.writerows(rows)
    _atomic_write_text(csv_path, _csv_buf.getvalue())

    action_codes = {'NEEDS_ANTISMASH_OUTPUT', 'NEEDS_PROTEIN_FASTA', 'NEEDS_HMMER_DOMTBLOUT', 'NEEDS_DIAMOND_TSV', 'MANUAL_BLASTP_OPTIONAL', 'LOW_CONFIDENCE_REVIEW', 'UNRESOLVED_METADATA', 'DEFER_SERVER_R2'}
    work_rows = []
    for r in rows:
        if r['status_code'] in action_codes:
            priority = 'A' if r['status_code'] in {'NEEDS_ANTISMASH_OUTPUT', 'NEEDS_PROTEIN_FASTA', 'NEEDS_HMMER_DOMTBLOUT'} else 'B'
            work_rows.append({
                'priority': priority,
                'status_code': r['status_code'],
                'worksheet': r['worksheet'],
                'cell_or_field': r['cell_or_field'],
                'data_label': r['data_label'],
                'blocking_for_claims': 'yes' if r['status_code'] in {'NEEDS_HMMER_DOMTBLOUT', 'NEEDS_DIAMOND_TSV', 'LOW_CONFIDENCE_REVIEW'} else 'context-dependent',
                'how_to_fill': r['how_to_fill'],
                'release_handling': r['release_handling'],
                'notes_for_llm': r['notes_for_llm'],
            })
    _wl_buf = _io.StringIO()
    w = _SafeDictWriter(_wl_buf, fieldnames=WORKLIST_HEADERS)
    w.writeheader()
    w.writerows(work_rows)
    _atomic_write_text(worklist_path, _wl_buf.getvalue())

    md_lines = [
        f'# {strain} Cell Provenance and Missing-Data Worklist', '',
        'This file explains the CSV outputs written by the standalone package transparency layer.', '',
        f'- `{csv_path.name}`: row-wise source/status/workflow table for major workbook and evidence fields.',
        f'- `{worklist_path.name}`: actionable subset of unresolved, low-confidence, or optional-external-evidence fields.', '',
        'Controlled status codes are defined in the package Troubleshooting folder and repo docs.', '',
        'Rule: no silent blanks. Missing values must have a status code and a workflow.'
    ]
    _atomic_write_text(md_path, '\n'.join(md_lines) + '\n')

    _write_troubleshooting_folder(package_dir)
    return csv_path, worklist_path, md_path


def _write_troubleshooting_folder(package_dir: Path) -> None:
    """Write compact troubleshooting docs into each strain package."""
    tdir = package_dir / 'Troubleshooting'
    tdir.mkdir(exist_ok=True)
    _atomic_write_text(
        tdir / 'README_Troubleshooting.md',
        '# Troubleshooting\n\n'
        'This folder makes missing or low-confidence data explicit. Use the cell provenance and missing-data worklist CSV files to decide what evidence is needed next.\n\n'
        'No silent blanks: every missing field should have a status code, reason, and workflow.\n',
    )
    _atomic_write_text(
        tdir / 'Cell_Status_Code_Glossary.md',
        '# Cell Status Code Glossary\n\n' + '\n'.join(f'- **{k}**: {v}' for k, v in STATUS_GLOSSARY.items()) + '\n',
    )
    _atomic_write_text(
        tdir / 'HMMER_Data_Workflow.md',
        '# HMMER Data Workflow\n\nRun `hmmscan --domtblout STRAIN_hmmscan.domtblout mamey_markers.hmm STRAIN_proteins.faa` after generating a protein FASTA. Parse the `domtblout` file, not the large verbose output, when filling workbook evidence cells.\n',
    )
    _atomic_write_text(
        tdir / 'DIAMOND_Data_Workflow.md',
        '# DIAMOND Data Workflow\n\nUse DIAMOND for scalable BLASTP-like homolog annotation of thousands of proteins. Import the tabular TSV output into Mamey/Sapote rather than using remote NCBI BLASTP for bulk searches.\n',
    )
    _atomic_write_text(
        tdir / 'Protein_FASTA_Workflow.md',
        '# Protein FASTA Workflow\n\nAssembled genome FASTA files contain nucleotide contigs. HMMER and DIAMOND require proteins. Acceptable protein sources include antiSMASH GenBank translations, antiSMASH protein export, or local gene-calling/annotation outputs.\n',
    )
