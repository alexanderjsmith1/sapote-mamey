import json,subprocess,sys
from tools._figure_route_common import ROOT

def test_singleton_and_shared_family_display_counts(tmp_path):
    f=tmp_path/'members.tsv';f.write_text('family\towner\towner_kind\tproducts\nF1\tSYN_A\tisolate\tNRPS\nF1\tSYN_REF\tpublic\tNRPS\nF2\tSYN_A\tisolate\tNRPS\n')
    out=tmp_path/'out'
    subprocess.run([sys.executable,str(ROOT/'tools/family_network_page.py'),'--members',str(f),'--out',str(out),'--cutoff','0.7'],check=True,timeout=120)
    r=json.loads((out/'ROUTE_RECEIPT.json').read_text())
    assert r['singletons_omitted']=={'SYN_A':1} and r['cutoff']==0.7
    assert all(any(x['path'].endswith(e) for x in r['outputs']) for e in ('.png','.pdf','.svg'))
