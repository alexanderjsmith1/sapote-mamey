from pathlib import Path


def test_public_naming_and_literature_docs_exist():
    for rel in [
        'docs/PROJECT_NAMING.md',
        'docs/LITERATURE_REVIEW_MODES.md',
        'docs/PACKAGE_PROFILES.md',
        'docs/GITHUB_HYGIENE_CHECKLIST.md',
    ]:
        assert Path(rel).exists(), rel
    readme = Path('README.md').read_text(encoding='utf-8')
    assert 'Sapote-Mamey' in readme  # normalized single-hyphen in v9.3
    assert 'Mamey is the executable BGC-analysis module' in readme
    lit = Path('docs/LITERATURE_REVIEW_MODES.md').read_text(encoding='utf-8')
    assert 'FLR -- Focused Literature Review' in lit
    assert 'VLR -- Verified Literature Review' in lit


def test_crosswalk_contract_in_code():
    models = Path('mamey/models.py').read_text(encoding='utf-8')
    cli = Path('mamey/cli.py').read_text(encoding='utf-8')
    workbook = Path('mamey/workbook.py').read_text(encoding='utf-8')
    assert 'user_label' in models
    assert 'crosswalk_dict' in models
    assert '_2b_bgc_crosswalk.csv' in cli
    assert 'BGC_Crosswalk' in workbook


def test_external_evidence_status_contract():
    ext = Path('mamey/external_adapters.py').read_text(encoding='utf-8')
    cell = Path('mamey/cell_provenance.py').read_text(encoding='utf-8')
    assert 'COMPLETED_SOURCE_DERIVED' in ext
    assert 'NEEDS_HMMER_DOMTBLOUT' in ext
    assert 'MANUAL_BLASTP_OPTIONAL' in ext
    assert 'manual_blastp_top_leads' in cell
    assert 'candidate_blastp_rows' in Path('mamey/crosswalk.py').read_text(encoding='utf-8')
