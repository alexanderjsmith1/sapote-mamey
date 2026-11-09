"""The bioassay adapter never replaces an existing receipt or a source table."""
from tests.test_452_bioassay_admitted_observations import _obs, _tool, world  # noqa: F401


def test_best_table_refuses_existing_receipt_and_keeps_it(world):
    mod, out, _ = _obs(world)
    best = world / "best.tsv"
    receipt = world / "best.tsv.receipt.json"
    receipt.write_text("prior receipt\n")
    assert mod.main(["best-table", "--observations", str(out), "--out", str(best)]) == 2
    assert receipt.read_text() == "prior receipt\n"
    assert not best.exists()


def test_observations_refuses_existing_receipt_and_keeps_it(world):
    mod = _tool()
    out = world / "obs_new.tsv"
    receipt = world / "obs_new.tsv.receipt.json"
    receipt.write_text("prior receipt\n")
    assert mod.main(["observations", "--profile", str(world / "profile.json"), "--out", str(out)]) == 2
    assert receipt.read_text() == "prior receipt\n"
    assert not out.exists()


def test_output_may_not_alias_the_observation_receipt(world):
    mod, out, _ = _obs(world)
    before = (world / "obs.tsv.receipt.json").read_text()
    assert mod.main(["best-table", "--observations", str(out), "--out", str(world / "obs.tsv.receipt.json")]) == 2
    assert (world / "obs.tsv.receipt.json").read_text() == before
