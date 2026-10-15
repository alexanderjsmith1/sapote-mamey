"""Real R rendering and stamps for every C02 layout with synthetic isolate IDs."""
import shutil
import csv
import importlib.util
from pathlib import Path
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1];TOOL=ROOT/'tools/genus_composition_figures.py'
spec=importlib.util.spec_from_file_location('composition',TOOL);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
@pytest.mark.parametrize('layout,groups,palette',[
 ('bee',['Bumblebees','Honeybees','Other bees','Wasps'],None),
 ('moss',['Bryophytes','Lichens','Mushrooms'],'moss'),
 ('attine',['Atta','Acromyrmex'],'attine')])
@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_every_layout(tmp_path,layout,groups,palette):
 roster=tmp_path/'isolates.tsv';rows=[dict(strain=f'SYN-{971+i}',group=g,genus='Streptomyces' if i%2==0 else 'Nocardia') for i,g in enumerate(groups)]
 module.write_tsv(roster,['strain','group','genus'],rows)
 argv=['--isolates',str(roster),'--out',str(tmp_path/'render'),'--layout',layout,'--groups',*groups]
 if palette:argv+=['--palette-set',palette]
 assert module.main(argv)==0
 for ext in ('.png','.pdf'):assert b'Sapote-Mamey genus_composition_figures' in (tmp_path/'render'/('C02_genus_composition'+ext)).read_bytes()
 with (tmp_path/'render/C02_genus_composition_numbers.tsv').open() as f:numbers=list(csv.DictReader(f,delimiter='\t'))
 assert sum(int(r['n']) for r in numbers)==len(groups)
 assert all(int(r['group_n'])==1 for r in numbers)
 assert all(int(n['n'])==sum(r['group']==n['group'] and r['genus']==n['genus'] for r in rows) for n in numbers)
 with pytest.raises(FileExistsError):module.main(argv)
@pytest.mark.parametrize('rows',[[dict(strain='SYN-971',group='Group A',genus='Nocardia')]*2,[dict(strain='SYN-971',group='',genus='Nocardia')],[]])
def test_roster_refusals(tmp_path,rows):
 p=tmp_path/'bad.tsv';module.write_tsv(p,['strain','group','genus'],rows)
 with pytest.raises(ValueError):module.read_roster(p)
def test_help():assert subprocess.run([sys.executable,str(TOOL),'--help'],capture_output=True).returncode==0
def test_genus_colours_only_from_palette():
 assert 'PAL<-setNames(pal$colour,pal$genus)' in module.R_SCRIPT
 assert '"Streptomyces": "#' not in TOOL.read_text()
