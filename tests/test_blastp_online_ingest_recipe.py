"""Plan reminders must lead to executable offline imports; no live search."""
import json
import shlex
import subprocess
from pathlib import Path
from types import SimpleNamespace
import openpyxl
import pytest
from mamey import blastp_online
from mamey.cli import build_parser


@pytest.fixture
def local_plan(monkeypatch):
    monkeypatch.setattr('mamey.parsers.extract_cds_features',
                        lambda p: [SimpleNamespace(locus_tag='query001', translation='MKT')])
    def forbidden(*args, **kwargs):
        raise AssertionError('a plan must never submit sequences')
    monkeypatch.setattr(blastp_online, 'run_batches_online', forbidden)


def args(**overrides):
    data=dict(package='software-region.gbk', bgc=None, region=None, crosswalk=None,
              database='nr', evalue='1e-5', batch_size=10, outdir=None,
              submit=False, confirm_public_upload=False, master=None, strain=None)
    data.update(overrides)
    return SimpleNamespace(**data)


def workbook(tmp_path):
    path=tmp_path/'review with spaces'/'master\'s workbook.xlsx'
    path.parent.mkdir()
    wb=openpyxl.Workbook();wb.save(path);wb.close()
    return path


def printed_command(out):
    lines=[line.strip() for line in out.splitlines()
           if ' ingest-blastp ' in line and not line.startswith('[blastp-online]')]
    assert len(lines)==1,out
    return shlex.split(lines[0])


def test_default_does_not_offer_an_incomplete_ingest_command(local_plan,capsys):
    assert blastp_online.blastp_online_command(args())==0
    out=capsys.readouterr().out
    assert 'PLAN ONLY' in out
    assert '--master' in out and '--strain' in out
    assert ' ingest-blastp ' not in out
    assert '<hits.csv>' not in out


def test_complete_recipe_round_trips_explicit_choices(local_plan,tmp_path,capsys):
    master=workbook(tmp_path)
    strain="software fixture'$(not-a-command)"
    assert blastp_online.blastp_online_command(args(master=str(master),strain=strain))==0
    cmd=printed_command(capsys.readouterr().out)
    parsed=build_parser().parse_args(cmd[2:])
    assert parsed.master==str(master.resolve()) and parsed.strain==strain
    assert parsed.hit_table==str(master.parent/'hits.csv')
    assert parsed.package is None
    assert all('<' not in token and '>' not in token for token in cmd)


def test_printed_recipe_imports_software_rows_into_only_the_chosen_workbook(local_plan,tmp_path,capsys):
    master=workbook(tmp_path)
    hits=master.parent/'hits.csv'
    hits.write_text('query001,subject001,90,20,0,0,1,20,1,20,1e-20,100\n')
    assert blastp_online.blastp_online_command(args(master=str(master),strain='software-fixture'))==0
    cmd=printed_command(capsys.readouterr().out)
    result=subprocess.run(cmd,cwd=tmp_path,capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    wb=openpyxl.load_workbook(master,read_only=True)
    rows=list(wb['B5_BLASTp_Hits'].values);wb.close()
    assert len(rows)==2 and 'software-fixture' in rows[1]
    assert hits.read_text().startswith('query001,subject001')


def test_existing_package_context_adds_the_correct_overlay_destination(local_plan,tmp_path,capsys):
    master=workbook(tmp_path);pkg=tmp_path/'review package';pkg.mkdir()
    (pkg/'manifest.json').write_text(json.dumps({'strain_id':'software-fixture'}))
    assert blastp_online.blastp_online_command(args(master=str(master),strain='software-fixture',crosswalk=str(pkg)))==0
    parsed=build_parser().parse_args(printed_command(capsys.readouterr().out)[2:])
    assert parsed.package==str(pkg.resolve())


def test_conflicting_package_strain_does_not_print_an_import_command(local_plan,tmp_path,capsys):
    master=workbook(tmp_path);pkg=tmp_path/'package';pkg.mkdir()
    (pkg/'manifest.json').write_text(json.dumps({'strain_id':'another-fixture'}))
    assert blastp_online.blastp_online_command(args(master=str(master),strain='software-fixture',crosswalk=str(pkg)))==0
    out=capsys.readouterr().out
    assert 'conflicts' in out and ' ingest-blastp ' not in out


def test_planner_parser_accepts_explicit_import_choices():
    ns=build_parser().parse_args(['blastp-online','--package','region.gbk',
                                 '--master','review.xlsx','--strain','software-fixture'])
    assert ns.master=='review.xlsx' and ns.strain=='software-fixture'


@pytest.mark.parametrize('as_csv',[False,True])
def test_saved_package_supplies_its_recorded_strain(local_plan,tmp_path,capsys,as_csv):
    master=workbook(tmp_path);pkg=tmp_path/'package';pkg.mkdir()
    (pkg/'manifest.json').write_text(json.dumps({'strain_id':'software-fixture'}))
    crosswalk=pkg/'fixture_2b_bgc_crosswalk.csv'
    crosswalk.write_text('bgc_id\n')
    selected=crosswalk if as_csv else pkg
    assert blastp_online.blastp_online_command(args(master=str(master),crosswalk=str(selected)))==0
    ns=build_parser().parse_args(printed_command(capsys.readouterr().out)[2:])
    assert ns.strain=='software-fixture' and ns.package==str(pkg.resolve())


@pytest.mark.parametrize('choice',[{'master':'missing.xlsx'},{'strain':'software-fixture'}])
def test_partial_choices_never_print_an_incomplete_command(local_plan,capsys,choice):
    assert blastp_online.blastp_online_command(args(**choice))==0
    assert ' ingest-blastp ' not in capsys.readouterr().out


def test_missing_workbook_never_becomes_a_working_recipe(local_plan,tmp_path,capsys):
    assert blastp_online.blastp_online_command(args(master=str(tmp_path/'missing.xlsx'),strain='software-fixture'))==0
    out=capsys.readouterr().out
    assert 'existing .xlsx workbook' in out and ' ingest-blastp ' not in out


def test_malformed_context_is_reported_not_used(local_plan,tmp_path,capsys):
    master=workbook(tmp_path);pkg=tmp_path/'package';pkg.mkdir()
    (pkg/'manifest.json').write_text('{bad')
    assert blastp_online.blastp_online_command(args(master=str(master),crosswalk=str(pkg)))==0
    out=capsys.readouterr().out
    assert 'manifest is unreadable' in out and ' ingest-blastp ' not in out
