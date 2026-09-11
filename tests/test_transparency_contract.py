from pathlib import Path


def test_troubleshooting_docs_present():
    required = [
        'docs/troubleshooting/README_TROUBLESHOOTING.md',
        'docs/troubleshooting/CELL_STATUS_CODE_GLOSSARY.md',
        'docs/troubleshooting/HMMER_DATA_WORKFLOW.md',
        'docs/troubleshooting/DIAMOND_DATA_WORKFLOW.md',
        'docs/troubleshooting/PROTEIN_FASTA_WORKFLOW.md',
        'templates/Cell_Provenance_Template.csv',
        'mamey/cell_provenance.py',
    ]
    for rel in required:
        assert Path(rel).exists(), rel


def test_cell_provenance_status_codes_documented():
    text = Path('docs/troubleshooting/CELL_STATUS_CODE_GLOSSARY.md').read_text(encoding='utf-8')
    for code in ['NEEDS_PROTEIN_FASTA', 'NEEDS_HMMER_DOMTBLOUT', 'NEEDS_DIAMOND_TSV', 'MANUAL_BLASTP_OPTIONAL', 'DEFER_SERVER_R2']:
        assert code in text


def test_cli_writes_cell_provenance_call():
    text = Path('mamey/cli.py').read_text(encoding='utf-8')
    assert 'write_cell_provenance(run, package_dir)' in text
