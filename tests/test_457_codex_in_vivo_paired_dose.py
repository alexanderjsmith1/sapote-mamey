import json,subprocess,sys
from tools._figure_route_common import ROOT

def test_missing_high_dose_refuses_without_figure(tmp_path):
    f=tmp_path/'raw.tsv';f.write_text('isolate\tgenus_16s\tdose\tneg_log_cfu\tin_bee_wasp_figure\nSYN_A\tNocardia\tlow\t-1\tyes\n')
    out=tmp_path/'out'
    result=subprocess.run([sys.executable,str(ROOT/'tools/in_vivo_paired_dose.py'),'--data',str(f),'--out',str(out)],capture_output=True,text=True)
    assert result.returncode!=0 and not out.exists()

def test_values_do_not_change_to_activity_calls(tmp_path):
    f=tmp_path/'raw.tsv';f.write_text('isolate\tgenus_16s\tdose\tneg_log_cfu\tin_bee_wasp_figure\nSYN_A\tNocardia\tlow\t-0.2\tyes\nSYN_A\tNocardia\thigh\t-1.2\tyes\n')
    out=tmp_path/'out'
    subprocess.run([sys.executable,str(ROOT/'tools/in_vivo_paired_dose.py'),'--data',str(f),'--out',str(out)],check=True,timeout=120)
    r=json.loads((out/'ROUTE_RECEIPT.json').read_text())
    assert r['target_organism']=='not inferred' and r['visual_qa']=='NOT_PERFORMED'
    assert f.read_text().endswith('-1.2\tyes\n')
