from pathlib import Path


def test_md_to_pdf_does_not_ignore_xelatex_errors():
    txt = Path('tools/md_to_pdf.sh').read_text()
    assert '|| true' not in txt
    assert '-halt-on-error' in txt
    assert 'sapote_md_preflight.py' in txt
