"""Commands that read an existing package refuse a path that is not a folder, before they run.

guide used to create <path>/guide/ and exit 0; resume printed "All BGCs complete" for a missing
path; fingerprint, seal-package and report-card crashed with a FileNotFoundError traceback.
"""
import pytest

from mamey import cli


@pytest.mark.parametrize("argv", [
    ["resume", "{p}"],
    ["guide", "--package", "{p}"],
    ["fingerprint", "{p}"],
    ["seal-package", "{p}"],
    ["report-card", "--package", "{p}"],
])
def test_missing_package_is_refused_before_dispatch(tmp_path, capsys, argv):
    missing = tmp_path / "no_such_package"
    args = [a.format(p=missing) for a in argv]
    assert cli.main(args) == 2
    captured = capsys.readouterr()
    assert "not a package directory" in captured.err
    assert "Traceback" not in captured.err
    assert "All BGCs complete" not in captured.out
    assert not missing.exists()


def test_every_listed_command_names_a_real_argument():
    parser = cli.build_parser()
    choices = next(a for a in parser._actions if getattr(a, "dest", "") == "command").choices
    for command, attr in cli._PACKAGE_PATH_COMMANDS.items():
        assert command in choices, command
        assert attr in {a.dest for a in choices[command]._actions}, (command, attr)
