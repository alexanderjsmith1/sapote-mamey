"""The failure remedy must not offer an ineffective editable-manifest baseline reset."""
from tools import check_module_accretion as gate


def test_unjustified_module_remedy_names_the_changelog_not_write(monkeypatch, capsys):
    monkeypatch.setattr(gate, "current_modules", lambda: ({"mamey/base.py": "base", "mamey/extra.py": "new"}, []))
    monkeypatch.setattr(gate, "manifest_modules", lambda: {"mamey/base.py"})
    monkeypatch.setattr(gate, "newest_changelog_entry", lambda: "# Candidate\n")
    assert gate.check() == 1
    output = capsys.readouterr().out
    assert "Accretion-justified:" in output
    assert "--write" not in output
    assert "deliberate baseline update" not in output
