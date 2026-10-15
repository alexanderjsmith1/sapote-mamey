from tools.check_bgc_naming import scan

def test_generic_folder_file_scope_and_filter_case(tmp_path):
    (tmp_path / "AS-971_BGC001.txt").write_text("data")
    assert scan(str(tmp_path), ["as-971"], None) == 1

def test_missing_requested_root_is_not_a_clean_scan(tmp_path):
    assert scan(str(tmp_path / "missing"), None, None) == 2

def test_conflicting_directory_file_strain_is_held(tmp_path):
    folder = tmp_path / "AS-971"
    folder.mkdir()
    (folder / "AS-972_contig1_region001_BGC001.tsv").write_text("data")
    assert scan(str(folder), None, None) == 1

def test_complete_identity_and_raw_exceptions_still_work(tmp_path):
    (tmp_path / "AS-971_contig1_region001_BGC001.tsv").write_text("data")
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "AS-971_BGC001.tsv").write_text("upstream")
    assert scan(str(tmp_path), None, None) == 0
