"""Functional annotations share actual intake and survive every analytical pair view.

Fixtures are N-only source metadata; no proteins, live searches or biological truth claims.
"""
import copy
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest
from mamey import parsers, rggmci as rg

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"functional_rescue_class", "a_core_fraction", "b_core_fraction", "a_functional_roles",
          "b_functional_roles", "modular_continuation", "a_assembly_line_cds", "b_assembly_line_cds",
          "a_release_cds", "b_release_cds"}
EXPECTED = dict(functional_rescue_class="COMPLEMENTARY", a_core_fraction=1.0, b_core_fraction=0.0,
                a_functional_roles="core", b_functional_roles="regulatory",
                modular_continuation="MODULAR_CONTINUATION", a_assembly_line_cds=1, b_assembly_line_cds=1,
                a_release_cds=0, b_release_cds=1)


def source_archive(path, *, whole=False, missing=False):
    """Two full contig identities, identical local region number, declared global frame."""
    def record(cid, *, region, side):
        off = 0 if region else 100
        lines = [f"LOCUS       {cid:<16}{120 if region else 240:>12} bp    DNA     linear   BCT 01-JAN-2000",
                 "DEFINITION  Synthetic annotation metadata; no biological sequence.",
                 f"ACCESSION   {cid.split('.')[0]}", f"VERSION     {cid}"]
        if region: lines += ["COMMENT     Orig. start :: 100", "            Orig. end :: 220"]
        lines += ["FEATURES             Location/Qualifiers"]
        if region:
            lines += ["     region          1..120", '                     /product="other"',
                      '                     /contig_edge="True"']
        if not missing:
            lines += [f"     CDS             {6 + off}..{35 + off}", f'                     /locus_tag="SYNTH_GENE_{side}"',
                      '                     /product="metadata annotation"',
                      f'                     /gene_kind="{"biosynthetic" if side == 1 else "regulatory"}"',
                      f"     aSDomain        {6 + off}..{20 + off}", f'                     /locus_tag="SYNTH_GENE_{side}"',
                      f'                     /aSDomain="{"Condensation" if side == 1 else "ACP"}"']
            if side == 2:
                lines += [f"     aSDomain        {21 + off}..{35 + off}",
                          f'                     /locus_tag="SYNTH_GENE_{side}"',
                          '                     /aSDomain="Thioesterase"']
        lines += ["ORIGIN"] + [f"{i + 1:9d} " + "n" * 60 for i in range(0, 120 if region else 240, 60)] + ["//", ""]
        return "\n".join(lines)
    with zipfile.ZipFile(path, "x") as archive:
        for side in (1, 2):
            cid = f"SYNTH_FULL_{side}.1"
            archive.writestr(f"{cid}.region001.gbk", record(cid, region=True, side=side))
            if whole: archive.writestr(f"{cid}.gbk", record(cid, region=False, side=side))
    return path


def scored_pairs(path, bgcs, **options):
    a, b = bgcs
    pair = dict(pair=f"{a.bgc_id}+{b.bgc_id}", bgc_a=a.bgc_id, bgc_b=b.bgc_id,
                contig_a=a.contig, contig_b=b.contig, edge_a="Edge", edge_b="Edge",
                products_a="other", products_b="other", rggmci_score=9,
                rggmci_confidence="MODERATE_RG_GMCI_CANDIDATE")
    # Independent dictionaries must remain coherent even after JSON/deepcopy boundaries.
    return dict(ranked_pairs=[pair], split_candidates=[copy.deepcopy(pair)], related_locus_pairs=[],
                reference_completion={"completion_tier": "OFF"})


def projection(pair):
    assert FIELDS <= pair.keys()
    return {key: pair[key] for key in FIELDS}


@pytest.mark.parametrize("whole", [False, True], ids=["region_offset", "whole_record_preference"])
def test_actual_feature_extraction_matches_literal_native_context_contract(tmp_path, monkeypatch, whole):
    path = source_archive(tmp_path / "metadata.zip", whole=whole)
    monkeypatch.setattr(rg, "run_rggmci", scored_pairs)
    result = rg.run_archive(path, reference_completion="off", label="SYNTH_DECLARED_INPUT")
    assert [x.start for x in parsers.extract_cds_features(path)] == [106, 106]
    assert result["functional_context"]["n_cds"] == 2
    assert result["functional_context"]["n_bgcs_with_cds"] == 2
    assert result["functional_profiles"]["BGC001"] == dict(core=1, tailoring=0, transport=0, regulatory=0,
                                                          other=0, has_core=True, roles_present=["core"])
    assert result["modular_profiles"] == {"BGC001": {"assembly_line_cds": 1, "release_cds": 0},
                                          "BGC002": {"assembly_line_cds": 1, "release_cds": 1}}
    for view in ("ranked_pairs", "split_candidates"):
        pair = result[view][0]
        assert projection(pair) == EXPECTED
        assert pair["identity_a"] == "SYNTH_DECLARED_INPUT / SYNTH_FULL_1.1 / region001 / BGC001"
        assert pair["identity_b"] == "SYNTH_DECLARED_INPUT / SYNTH_FULL_2.1 / region001 / BGC002"
    serialized = json.loads(rg.canonical_artifacts(result, name="synthetic")["synthetic.json"])
    assert projection(serialized["split_candidates"][0]) == EXPECTED
    rows = list(csv.DictReader(io.StringIO(rg.canonical_artifacts(result, name="synthetic")["synthetic_pairs.tsv"].decode()), delimiter="\t"))
    assert rows[0]["functional_rescue_class"] == "COMPLEMENTARY"
    assert rows[0]["b_release_cds"] == "1"


def test_missing_context_is_complete_unknown_not_silent_missing_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(rg, "run_rggmci", scored_pairs)
    result = rg.run_archive(source_archive(tmp_path / "metadata.zip", missing=True), reference_completion="off")
    expected = dict(functional_rescue_class="UNKNOWN_NO_PROFILE", a_core_fraction=None, b_core_fraction=None,
                    a_functional_roles="", b_functional_roles="", modular_continuation="UNKNOWN_NO_PROFILE",
                    a_assembly_line_cds="", b_assembly_line_cds="", a_release_cds="", b_release_cds="")
    assert result["functional_profiles"] == result["modular_profiles"] == {}
    assert result["functional_context"]["n_cds"] == 0
    for view in ("ranked_pairs", "split_candidates"): assert projection(result[view][0]) == expected


@pytest.mark.parametrize("failure", ["typed_refusal", "unexpected"])
def test_context_failure_propagates_before_scoring(tmp_path, monkeypatch, failure):
    path = source_archive(tmp_path / "metadata.zip")
    error = parsers.GbkSizeGuardRefusal("synthetic.gbk", "controlled refusal") if failure == "typed_refusal" else RuntimeError("controlled context failure")
    def fail(*args): raise error
    monkeypatch.setattr(rg, "extract_cds_features", fail)
    monkeypatch.setattr(rg, "run_rggmci", lambda *a, **k: pytest.fail("must not score partial context"))
    with pytest.raises(type(error)) as caught: rg.run_archive(path, reference_completion="off")
    assert caught.value is error


def test_input_mutation_during_new_context_reads_refuses(tmp_path, monkeypatch):
    path = source_archive(tmp_path / "metadata.zip")
    original = rg.extract_domain_features
    def mutate(path):
        value = original(path)
        with zipfile.ZipFile(path, "a") as archive: archive.writestr("changed.txt", "metadata")
        return value
    monkeypatch.setattr(rg, "extract_domain_features", mutate)
    monkeypatch.setattr(rg, "run_rggmci", scored_pairs)
    with pytest.raises(ValueError, match="INPUT_CHANGED"): rg.run_archive(path, reference_completion="off")


def test_split_only_candidate_not_in_ranked_head_is_annotated(tmp_path, monkeypatch):
    def split_only(*args, **kwargs):
        value = scored_pairs(*args, **kwargs)
        value["ranked_pairs"] = []
        return value
    monkeypatch.setattr(rg, "run_rggmci", split_only)
    result = rg.run_archive(source_archive(tmp_path / "metadata.zip"), reference_completion="off")
    assert result["ranked_pairs"] == []
    assert projection(result["split_candidates"][0]) == EXPECTED
    assert " / SYNTH_FULL_2.1 / region001 / BGC002" in result["split_candidates"][0]["identity_b"]


@pytest.mark.parametrize("bad", ["contig", "alias"])
def test_split_only_identity_conflict_refuses(tmp_path, monkeypatch, bad):
    def conflict(*args, **kwargs):
        result = scored_pairs(*args, **kwargs)
        result["split_candidates"][0]["contig_a" if bad == "contig" else "bgc_a"] = "shortened_or_unbound"
        return result
    monkeypatch.setattr(rg, "run_rggmci", conflict)
    with pytest.raises(ValueError, match="PAIR_IDENTITY_CONFLICT"):
        rg.run_archive(source_archive(tmp_path / "metadata.zip"), reference_completion="off")


@pytest.fixture(scope="module")
def functional_generated(tmp_path_factory):
    target = tmp_path_factory.mktemp("functional_generated") / "pkg"
    process = subprocess.run([sys.executable, str(ROOT / "packaging/rggmci/build_rggmci_package.py"),
                              "--bundle", str(ROOT), "--out", str(target)], capture_output=True, text=True)
    assert process.returncode == 0, process.stdout + process.stderr
    return target


@pytest.mark.parametrize("without_bio", [False, True], ids=["available", "builtin"])
def test_generated_actual_intake_full_projection_and_all_exports_match(functional_generated, tmp_path, monkeypatch, without_bio):
    path = source_archive(tmp_path / "metadata.zip")
    monkeypatch.setattr(rg, "run_rggmci", scored_pairs)
    expected = rg.run_archive(path, reference_completion="off", label="SYNTH_DECLARED_INPUT")
    script = '''
import copy,json,sys
if sys.argv[2]=='builtin':sys.modules['Bio']=None
from rggmci import run,core

def scored(path,bgcs,**options):
 a,b=bgcs
 pair=dict(pair=f'{a.bgc_id}+{b.bgc_id}',bgc_a=a.bgc_id,bgc_b=b.bgc_id,contig_a=a.contig,contig_b=b.contig,
           edge_a='Edge',edge_b='Edge',products_a='other',products_b='other',rggmci_score=9,
           rggmci_confidence='MODERATE_RG_GMCI_CANDIDATE')
 return dict(ranked_pairs=[pair],split_candidates=[copy.deepcopy(pair)],related_locus_pairs=[],reference_completion={'completion_tier':'OFF'})
core.run_rggmci=scored
result=run(sys.argv[1],reference_completion='off',label='SYNTH_DECLARED_INPUT')
result.pop('wrapper_context')
print(json.dumps({'result':result,'artifacts':{k:v.decode() for k,v in core.canonical_artifacts(result,name='same').items()}},sort_keys=True))
'''
    env = dict(os.environ, PYTHONPATH=str(functional_generated / "src"), PYTHONDONTWRITEBYTECODE="1")
    process = subprocess.run([sys.executable, "-c", script, str(path), "builtin" if without_bio else "available"], cwd=tmp_path,
                             env=env, capture_output=True, text=True)
    assert process.returncode == 0, process.stdout + process.stderr
    expected.pop("wrapper_context")
    got = json.loads(process.stdout)
    assert got["result"] == json.loads(json.dumps(expected))
    assert got["artifacts"] == {k: v.decode() for k, v in rg.canonical_artifacts(expected, name="same").items()}
    assert projection(got["result"]["ranked_pairs"][0]) == EXPECTED
    assert projection(got["result"]["split_candidates"][0]) == EXPECTED
