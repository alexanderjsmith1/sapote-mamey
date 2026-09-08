from pathlib import Path


def test_standalone_docs_present():
    required = [
        'docs/standalone/MAMEY_STANDALONE_CHATGPT_README.md',
        'docs/standalone/RUN_MAMEY_IN_CHATGPT.md',
        'docs/standalone/CHATGPT_BATCH_PROTOCOL.md',
        # v9.7.101 (P12): the live ChatGPT contract is CHATGPT_START_HERE.md; the
        # superseded MAMEY_V1.9.3/1.9.6 launch prompts were retired (paste-by-mistake
        # footgun). The contract intent is preserved by pinning the live entry doc.
        'CHATGPT_START_HERE.md',
        'scripts/chatgpt_make_batch_summary.py',
    ]
    for rel in required:
        assert Path(rel).exists(), rel


def test_version_current():
    """Engine version must be consistent between mamey/__init__.py and pyproject.toml.
    Not pinned to a specific version — use sync_version.py for that."""
    from mamey import __version__
    pyproject = Path('pyproject.toml').read_text(encoding='utf-8')
    assert f'version = "{__version__}"' in pyproject, \
        f"mamey.__version__ ({__version__}) not found in pyproject.toml — version drift"


def test_chatgpt_limitations_are_explicit():
    text = Path('docs/standalone/MAMEY_STANDALONE_CHATGPT_README.md').read_text(encoding='utf-8')
    assert 'cannot assume BLAST, HMMER, antiSMASH' in text
    assert 'MAMEY_COMPLETE' in text
    assert 'batch' in text.lower()
