"""v9.7.441 (session 9c5f37d0): build-ref must not stamp a refpkg inside the code bundle.

phylo_place.cmd_build_ref defaults its outdir to `{workspace_root()}/strain_data/_PLACEMENT/...`.
Run from the bundle root with no SAPOTE_WORKSPACE_ROOT, workspace_root() == cwd == the bundle, so
the default resolves INTO the sealed tree (observed: 12.7 MB of RAxML litter). The containment guard
added by refpkg_bundle_containment.diff refuses that, anchored to the tool's OWN bundle
(parents[1]) rather than to bundle markers -- because the workspace root also carries those markers
(the stray root mamey/), which would make a marker-walk guard false-positive on the real tree home.

This test pins the guard PREDICATE in isolation (the guard uses only os.path, so it can be tested
without importing the full phylo_place module, which needs the mafft/raxml env). Drop into tests/.
"""
import os


def _refuses(self_bundle, outdir):
    """Mirror of the guard inserted at phylo_place.py cmd_build_ref (after outdir is resolved)."""
    out_abs = os.path.abspath(outdir)
    return os.path.isfile(os.path.join(self_bundle, "BUILD_STAMP.txt")) and (
        out_abs == self_bundle or out_abs.startswith(self_bundle + os.sep))


def _make_fake_bundle(tmp_path):
    b = tmp_path / "sapote-mamey-v9.7.441-CODE-fake"
    (b / "tools").mkdir(parents=True)
    (b / "BUILD_STAMP.txt").write_text("version=9.7.441\n")
    return str(b)


def test_refuses_write_inside_the_running_bundle(tmp_path):
    b = _make_fake_bundle(tmp_path)
    assert _refuses(b, os.path.join(b, "strain_data/_PLACEMENT/Streptomyces/refpkg")) is True
    assert _refuses(b, b) is True  # the bundle root itself


def test_allows_writes_outside_the_bundle(tmp_path):
    b = _make_fake_bundle(tmp_path)
    # sibling workspace tree home, and an unrelated temp dir
    assert _refuses(b, str(tmp_path / "AS Strain Master/_PLACEMENT/streptomyces/refpkg")) is False
    assert _refuses(b, str(tmp_path / "strain_data/_PLACEMENT/x/refpkg")) is False


def test_no_bundle_stamp_means_no_containment(tmp_path):
    # if the tool is not running from a recognizable bundle, the guard must not fire
    not_a_bundle = str(tmp_path / "somewhere")
    os.makedirs(os.path.join(not_a_bundle, "tools"))
    assert _refuses(not_a_bundle, os.path.join(not_a_bundle, "strain_data/refpkg")) is False


def test_prefix_match_is_path_boundary_safe(tmp_path):
    # a sibling dir sharing a name prefix must NOT be treated as inside the bundle
    b = _make_fake_bundle(tmp_path)
    sibling = b + "-notes/refpkg"        # starts with the bundle string but is a different dir
    assert _refuses(b, sibling) is False
