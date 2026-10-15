from pathlib import Path


def test_workflow_explains_identity_scope_and_links_shared_guide():
    text = (Path(__file__).resolve().parents[1] / 'docs/PHYLOGENETICS_WORKFLOW.md').read_text()
    assert '### How identity is measured' in text
    assert 'LOCAL_16S_DATABASE.md#how-identity-is-measured' in text
    assert 'pident_raw' in text
    assert 'not an exhaustive alignment guarantee' in text
