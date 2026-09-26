"""`sapote_hooks.py install --apply --bundle` never silently replaces a hook that differs.

The installer used to copy every manifest hook over `.claude/hooks/<file>` with no check and no
backup, so reinstalling from a bundle could put an older rule back over the one a workspace runs.
It now refuses, before writing anything, unless `--overwrite` is given; with it, each differing
hook is backed up first. `project_root` is pinned to tmp_path, so no real `.claude/` is touched.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = "sapote_session_start.sh"


def _setup(monkeypatch, tmp_path, local_text):
    spec = importlib.util.spec_from_file_location("sapote_hooks_install_v97443", ROOT / "sapote_hooks" / "sapote_hooks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    project = tmp_path / "project"
    (project / ".claude" / "hooks").mkdir(parents=True)
    (project / ".claude" / "settings.json").write_text(json.dumps({"hooks": {}}))
    if local_text is not None:
        (project / ".claude" / "hooks" / HOOK).write_text(local_text)
    bundle = tmp_path / "bundle_hooks"
    bundle.mkdir()
    (bundle / HOOK).write_text("#!/bin/sh\necho bundle\n")
    monkeypatch.setattr(mod, "project_root", lambda: str(project))
    monkeypatch.setattr(mod, "load_manifest", lambda: [{"hook": HOOK}, {"hook": "INLINE"}])
    return mod, project, bundle


def test_differing_hook_refuses_and_writes_nothing(monkeypatch, tmp_path):
    mod, project, bundle = _setup(monkeypatch, tmp_path, "#!/bin/sh\necho local rule\n")
    with pytest.raises(SystemExit) as exc:
        mod.main(["install", "--apply", "--bundle", str(bundle)])
    assert "INSTALL_REFUSED" in str(exc.value) and HOOK in str(exc.value)
    assert (project / ".claude" / "hooks" / HOOK).read_text() == "#!/bin/sh\necho local rule\n"
    assert sorted(p.name for p in (project / ".claude").iterdir()) == ["hooks", "settings.json"]


def test_overwrite_backs_up_first(monkeypatch, tmp_path):
    mod, project, bundle = _setup(monkeypatch, tmp_path, "#!/bin/sh\necho local rule\n")
    mod.main(["install", "--apply", "--overwrite", "--bundle", str(bundle)])
    assert (project / ".claude" / "hooks" / HOOK).read_text() == "#!/bin/sh\necho bundle\n"
    backups = list((project / ".claude" / "hook_backups").rglob(HOOK))
    assert len(backups) == 1 and backups[0].read_text() == "#!/bin/sh\necho local rule\n"


@pytest.mark.parametrize("local", [None, "#!/bin/sh\necho bundle\n"])
def test_absent_or_identical_hook_installs_without_the_flag(monkeypatch, tmp_path, local):
    mod, project, bundle = _setup(monkeypatch, tmp_path, local)
    mod.main(["install", "--apply", "--bundle", str(bundle)])
    assert (project / ".claude" / "hooks" / HOOK).read_text() == "#!/bin/sh\necho bundle\n"
    assert not (project / ".claude" / "hook_backups").exists()
