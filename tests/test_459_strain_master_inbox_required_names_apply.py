"""The INBOX_REQUIRED refusal names the last step by its command, `apply` (it said `import`)."""
import re

import pytest

from mamey import cli
from mamey import strain_master as sm


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    monkeypatch.delenv("SAPOTE_STRAIN_MASTER", raising=False)


def _refusal(tmp_path):
    master = tmp_path / "M"
    sm.init_master(str(master), name="Test master")
    src = tmp_path / "ani.tsv"
    src.write_text("strain\tani\nAS-970\t95.1\n")
    with pytest.raises(sm.StrainMasterError) as exc:
        sm.store(str(src), "03 Genomes/ANI", "x", master=str(master))
    return str(exc.value), master, src


def test_refusal_names_apply_not_import(tmp_path):
    text, _, _ = _refusal(tmp_path)
    assert text.startswith("INBOX_REQUIRED")
    assert "`apply`" in text
    assert "import" not in text


def test_every_step_the_message_names_is_a_strain_master_action(tmp_path):
    text, _, _ = _refusal(tmp_path)
    sub = next(a for a in cli.build_parser()._actions if a.dest == "command")
    actions = set(next(a for a in sub.choices["strain-master"]._actions if a.dest == "action").choices)
    named = set(re.findall(r"`(?:strain-master )?([a-z]+)`", text))
    assert {"submit", "verify", "apply"} <= named
    assert named <= actions


def test_cli_prints_the_same_wording(tmp_path, capsys):
    _, master, src = _refusal(tmp_path)
    assert cli.main(["strain-master", "store", "--master", str(master), "--target", "03 Genomes/ANI",
                     "--what", "x", str(src)]) == 2
    out = capsys.readouterr().out
    assert "INBOX_REQUIRED" in out and "`apply`" in out
