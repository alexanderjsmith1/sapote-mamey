"""The §25 §40 §44 §46 §47 cross-source inputs must reach every route that emits Mode B templates.

`emit-modeb-template` took `--cohort-dir`, `--reference-dir`, `--strain-metadata` and
`--bigscape-regions-dir`, but `modeb-round`, `deliverable-queue` and the full50 wrapper emitted with
no sources, so every template from those routes carried the "Source not supplied" holds the pre-fill
exists to remove. Fixtures use AS-XXX.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

from mamey import cli, deliverable_queue, modeb_round
from mamey import modeb_template_emitter as em

ROOT = pathlib.Path(__file__).resolve().parents[1]
FLAGS = ["--cohort-dir", "--reference-dir", "--strain-metadata", "--bigscape-regions-dir",
         "--gap-rescue-dir", "--rescue-verdicts-tsv", "--rescue-gene-adjudication-tsv", "--rescue-locus-inventory"]


def _pkg(tmp_path: pathlib.Path) -> pathlib.Path:
    pkg = tmp_path / "AS-XXX" / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "AS-XXX", "taxonomy": "sp."}))
    (pkg / "manifest_short.json").write_text(json.dumps({"strain_id": "AS-XXX"}))
    (pkg / "AS-XXX_2_inventory.csv").write_text(
        "BGC_ID,Contig,antiSMASH_Region,Products,KCB_top\n"
        "BGC001,NODE_1_length_100_cov_1.0,region001,NRPS,\n")
    (pkg / "AS-XXX_4_triage_board.csv").write_text(
        "BGC_ID,Node_ID,Contig,antiSMASH_Region,Products,Boundary,Assembly_Locator,Length_kb,"
        "Lead_tier_auto,Corrected_rank,KCB_top\n"
        "BGC001,NODE_1,NODE_1_length_100_cov_1.0,region001,NRPS,Interior,x,40,HIGH,1,\n")
    return pkg


def _parse(argv: list[str]):
    return cli.build_parser().parse_args(argv)


def test_every_emitting_subcommand_accepts_the_source_flags(tmp_path):
    for sub in (["emit-modeb-template", "--package", "p"],
                ["modeb-round", "--package", "p"],
                ["deliverable-queue", "--runs-dir", "r", "--out-root", "o"]):
        args = _parse(sub + [FLAGS[0], "c", FLAGS[1], "r", FLAGS[2], "m", FLAGS[3], "b"])
        got = {k: getattr(args, k, None)
               for k in ("cohort_dir", "reference_dir", "strain_metadata", "bigscape_regions_dir")}
        assert got == {"cohort_dir": "c", "reference_dir": "r",
                       "strain_metadata": "m", "bigscape_regions_dir": "b"}, sub


def test_modeb_round_passes_sources_to_the_emitter(tmp_path, monkeypatch):
    pkg = _pkg(tmp_path)
    seen = {}
    real = em.emit_batch

    def spy(*a, **k):
        seen.update(k.get("sources") or {})
        return real(*a, **k)

    monkeypatch.setattr(em, "emit_batch", spy)
    args = _parse(["modeb-round", "--package", str(pkg), "--cohort-dir", str(tmp_path)])
    assert modeb_round.modeb_round_command(args) == 0
    assert seen.get("cohort_dir") == str(tmp_path)


def test_modeb_round_template_is_prefilled_when_sources_are_given(tmp_path):
    pkg = _pkg(tmp_path)
    r = modeb_round.run_round(pkg, top_n=1, sources={"cohort_dir": str(tmp_path)})
    card = pathlib.Path(r["entries"][0]["template"]).read_text()
    s44 = card.split("## §44 ", 1)[1].split("\n## §", 1)[0]
    assert "--cohort-dir" not in s44 and "Numerator" in s44


def test_deliverable_queue_forwards_sources_to_the_cards_step(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(deliverable_queue, "_run", lambda argv, env=None: (calls.append(argv), (0, ""))[1])
    monkeypatch.setattr(deliverable_queue._g, "gate", lambda *a, **k: {"blocked": False, "missing": []})
    monkeypatch.setattr(deliverable_queue, "_auto_ingest", lambda *a, **k: {})
    runs = tmp_path / "runs"
    (runs / "AS-XXX" / "package").mkdir(parents=True)
    deliverable_queue.process_strain("AS-XXX", str(runs), str(tmp_path / "out"),
                                     sources={"cohort_dir": "C", "strain_metadata": "M"})
    cards = [c for c in calls if c and c[0] == "emit-modeb-template"]
    assert cards and cards[0][-4:] == ["--cohort-dir", "C", "--strain-metadata", "M"]


def test_full50_wrapper_forwards_exactly_the_engine_source_flags(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("_full50", ROOT / "tools" / "emit_modeb_template_full50.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert list(mod.SOURCE_FLAGS) == FLAGS == [f for _d, f, _h in em.SOURCE_FLAGS]
    seen = {}
    monkeypatch.setattr(mod, "build", lambda b, py, p, g, source_args=None:
                        (seen.setdefault("a", source_args), ("", {"section_count": 50}))[1])
    (tmp_path / "mamey_run.py").write_text("")
    mod.main(["--package", "p", "--bgc", "BGC001", "--bundle", str(tmp_path),
              "--out", str(tmp_path / "o.md"), "--cohort-dir", "C", "--bigscape-regions-dir", "B"])
    assert seen["a"] == ["--cohort-dir", str(pathlib.Path("C").resolve()),
                         "--bigscape-regions-dir", str(pathlib.Path("B").resolve())]
