"""The dependency banner no longer calls the no-ijson fallback "TXT-only".

Without ijson the main JSON walker is off, but KnownClusterBlast TXT files and the separate
record pass still read the JSON, so "TXT-only" misstated which evidence a run used.
"""
import inspect

from mamey import cli


def test_banner_names_the_main_walker_not_txt_only(monkeypatch):
    from mamey import antismash_evidence as ae
    monkeypatch.setattr(ae, "_HAVE_IJSON", False)
    banner = cli._dependency_banner()
    assert "TXT-only" not in banner
    assert "main JSON walker off" in banner
    assert "record pass still reads JSON files up to 80 MB" in banner


def test_no_user_visible_txt_only_string_left_in_cli():
    source = inspect.getsource(cli)
    assert '"ijson\\u2717 bounded\\u2192TXT-only' not in source
