from tools.sapote_md_preflight import preflight_markdown


def test_boss_preflight_routes_wide_tables():
    md = '''# Report\n\n| a | b | c | d | e | f | g |\n|---|---|---|---|---|---|---|\n| 1 | 2 | 3 | 4 | 5 | 6 | 7 |\n\nDone.\n'''
    safe, appendix, findings = preflight_markdown(md, profile='boss', max_cols=6)
    assert 'Table routed to appendix/workbook' in safe
    assert '| a | b | c | d | e | f | g |' not in safe
    assert '| a | b | c | d | e | f | g |' in appendix
    assert any(f['type'] == 'wide_table_routed' for f in findings)


def test_technical_preflight_keeps_table():
    md = '''# Report\n\n| a | b | c | d | e | f | g |\n|---|---|---|---|---|---|---|\n| 1 | 2 | 3 | 4 | 5 | 6 | 7 |\n'''
    safe, appendix, findings = preflight_markdown(md, profile='technical', max_cols=6)
    assert '| a | b | c | d | e | f | g |' in safe
