import importlib.util
import os
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from tools import gecco_cohort_report as gcr
helper_spec=importlib.util.spec_from_file_location('existing_gecco_tests',ROOT/'tests/test_457_gecco_cohort_report.py')
helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper);helper.gcr=gcr

@pytest.mark.parametrize('name_map,expected',[
 (None,'PF00109 (Pfam name not supplied) x2; PF02801 (Pfam name not supplied)'),
 ('accession\tname\nPF00109\tketoacyl-synt\n','PF00109 (ketoacyl-synt) x2; PF02801 (Pfam name not found in supplied mapping)'),
 ('accession\tname\nPF00109\t  \nPF02801\tKetoacyl-synt_C\n','PF00109 (Pfam name not found in supplied mapping) x2; PF02801 (Ketoacyl-synt_C)'),
])
def test_missing_names_do_not_claim_release_absence(tmp_path,name_map,expected):
 helper.kit(tmp_path);args=['--genomes',str(tmp_path/'genomes.tsv'),'--out',str(tmp_path/'out'),'--no-figures']
 if name_map is not None:
  names=tmp_path/'test_names.tsv';names.write_text(name_map);args+=['--pfam-names',str(names)]
 assert gcr.main(args)==0;assert helper.calls(tmp_path)['c1']['pfam_domains']==expected
 assert 'not in the supplied Pfam release' not in (tmp_path/'out/gecco_calls.tsv').read_text()

def test_versioned_accession_preserved_and_lookup_uses_base_name(tmp_path):
 helper.kit(tmp_path)
 clusters=tmp_path/'S-1.clusters.tsv';clusters.write_text(clusters.read_text().replace('PF00109','PF00109.25'))
 names=tmp_path/'test_names.tsv';names.write_text('accession\tname\nPF00109\tknown\n')
 args=['--genomes',str(tmp_path/'genomes.tsv'),'--out',str(tmp_path/'out'),'--pfam-names',str(names),'--no-figures']
 assert gcr.main(args)==0
 assert helper.calls(tmp_path)['c1']['pfam_domains']=='PF00109.25 (known) x2; PF02801 (Pfam name not found in supplied mapping)'
