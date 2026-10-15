from mamey.modeb_export import _print_result

def test_explicit_requested_docx_skip_is_not_success():
    result = {"md": "synthetic.md", "docx": {"status": "SKIPPED_NO_DOCX", "path": None, "detail": "dependency unavailable"}}
    assert _print_result(result, require_both=False) == 1

def test_written_single_format_still_succeeds():
    result = {"md": "synthetic.md", "docx": {"status": "WRITTEN", "path": "synthetic.docx", "bytes": 1}}
    assert _print_result(result, require_both=False) == 0
