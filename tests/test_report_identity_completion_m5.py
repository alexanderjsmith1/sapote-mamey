"""Synthetic exact report identity and complete ledger controls; no PDF build."""
import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mamey import compile_report as cr
from mamey import markdown_pdf as mp

STRAIN='SYNTHETIC_REFERENCE'
FULL='ctg1_fixture_segment.1'
LABEL=STRAIN+' / '+FULL+' / region001 / BGC001'
FIELDS=['Strain','Contig','Node_ID','antiSMASH_Region','Region','BGC_ID']+[f'Synthetic_field_{i}' for i in range(37)]
assert len(FIELDS)==43


def row():
    result=dict(zip(FIELDS,[STRAIN,FULL,'ctg1','region001','1','BGC001']+[f'VALUE_{i}' for i in range(37)]))
    result['Synthetic_field_0']='q'*1250
    return result


def package(tmp_path):
    pkg=tmp_path/'package';pkg.mkdir()
    manifest={'strain_id':STRAIN,'bgcs':[{'contig':FULL,'node_id':'ctg1','antismash_region':'region001','bgc_id':'BGC001'}]}
    (pkg/'manifest.json').write_text(json.dumps(manifest))
    (pkg/'manifest_short.json').write_text(json.dumps({'strain_id':STRAIN}))
    for name in ('unrelated_name_2_inventory.csv','unrelated_name_4_triage_board.csv'):
        with (pkg/name).open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=FIELDS);writer.writeheader();writer.writerow(row())
    return pkg


def test_native_short_join_key_does_not_replace_full_display_identity(tmp_path):
    pkg=package(tmp_path);ctx=cr._report_identity_context(pkg)
    assert ctx['status']=='BOUND_PACKAGE_IDENTITY'
    assert cr._node_label(row(),ctx)==LABEL
    assert cr._node_label(row()).startswith('REPORT_IDENTITY_HOLD[PACKAGE_CONTEXT_UNAVAILABLE]')
    assert LABEL in cr._node_label(row())


@pytest.mark.parametrize('field,value',[
    ('Node_ID','ctg2'),('Contig','ctg2_fixture_segment.1'),('antiSMASH_Region','region002'),
    ('BGC_ID','BGC002'),('Strain','SYNTHETIC_REFERENCE_OTHER'),('Region','2'),
    ('Full_Node_ID','SYNTHETIC_CONFLICTING_CONTIG'),('Exact_locus','FORGED_DISPLAY'),
    ('Report_locus_identity','FORGED_DISPLAY')])
def test_stale_or_conflicting_row_components_hold(tmp_path,field,value):
    pkg=package(tmp_path);changed=row();changed[field]=value
    assert cr._node_label(changed,cr._report_identity_context(pkg)).startswith('REPORT_IDENTITY_HOLD')


def test_row_alias_alone_is_not_identity(tmp_path):
    pkg=package(tmp_path)
    assert cr._node_label({'BGC_ID':'BGC001'},cr._report_identity_context(pkg)).startswith('REPORT_IDENTITY_HOLD')


@pytest.mark.parametrize('mutation',['strain','inventory','ambiguous','duplicate_header','duplicate_manifest_key','missing_manifest'])
def test_actual_package_sources_must_agree(tmp_path,mutation):
    pkg=package(tmp_path)
    if mutation=='strain':(pkg/'manifest_short.json').write_text(json.dumps({'strain_id':'SYNTHETIC_REFERENCE_OTHER'}))
    elif mutation=='inventory':
        p=pkg/'unrelated_name_2_inventory.csv';p.write_text(p.read_text().replace(FULL,'ctg2_fixture_segment.1'))
    elif mutation=='ambiguous':(pkg/'second_2_inventory.csv').write_bytes((pkg/'unrelated_name_2_inventory.csv').read_bytes())
    elif mutation=='duplicate_header':
        p=pkg/'unrelated_name_2_inventory.csv';p.write_text(p.read_text().replace('Strain,','Strain,Strain,',1))
    elif mutation=='duplicate_manifest_key':(pkg/'manifest.json').write_text('{"strain_id":"SYNTHETIC_REFERENCE","strain_id":"OTHER","bgcs":[]}')
    else:(pkg/'manifest.json').unlink()
    ctx=cr._report_identity_context(pkg);assert ctx['status']=='REPORT_IDENTITY_HOLD'
    assert cr._node_label(row(),ctx).startswith('REPORT_IDENTITY_HOLD')


def test_manifest_inventory_physical_conflict_is_not_unique_alias_repaired(tmp_path):
    pkg=package(tmp_path);p=pkg/'manifest.json';m=json.loads(p.read_text())
    m['bgcs'].append({**m['bgcs'][0],'bgc_id':'BGC002'});p.write_text(json.dumps(m))
    assert cr._report_identity_context(pkg)['status']=='REPORT_IDENTITY_HOLD'


def test_report_triage_retains_every_original_field_and_adds_admitted_label(tmp_path):
    pkg=package(tmp_path);text=cr._triage_board(pkg)
    rows=[mp._table_cells(line) for line in text.splitlines() if line.startswith('|')]
    assert rows[0]==['Report_locus_identity',*FIELDS]
    assert rows[2]==[LABEL,*[row()[name] for name in FIELDS]]
    assert len(rows[2])==44


def capture_table(monkeypatch):
    captured={}
    class CapturedTable:
        def __init__(self,data,**kw):captured['data']=data;captured['options']=kw
        def setStyle(self,style):captured['style']=style
    monkeypatch.setattr(mp,'Table',CapturedTable)
    monkeypatch.setattr(mp,'P',lambda text,*args,**kwargs:text)
    return captured


def test_all_43_original_ledger_fields_and_continuations_repeat_complete_identity(tmp_path,monkeypatch):
    pkg=package(tmp_path);ctx=cr._report_identity_context(pkg);captured=capture_table(monkeypatch)
    r=row();mp.md_table([FIELDS,[r[k] for k in FIELDS]],identity_context=ctx)
    ledger=captured['data'][1:]
    assert all(x[0]=='1: '+LABEL for x in ledger)
    for field in FIELDS:
        pieces=[value for _,name,value in ledger if name==field or name.startswith(field+' (continued ')]
        assert ''.join(pieces)==r[field]
    assert [x[1] for x in ledger if x[1].startswith('Synthetic_field_0')]==[
        'Synthetic_field_0','Synthetic_field_0 (continued 2)','Synthetic_field_0 (continued 3)']


@pytest.mark.parametrize('forgery',['generated_column','typed_component','duplicate_header','no_context'])
def test_wide_ledger_cannot_trust_forged_display_or_stale_fields(tmp_path,monkeypatch,forgery):
    pkg=package(tmp_path);ctx=cr._report_identity_context(pkg);r=row();fields=list(FIELDS)
    if forgery=='generated_column':fields.insert(0,'Report_locus_identity');r['Report_locus_identity']='FORGED_DISPLAY'
    elif forgery=='typed_component':r['antiSMASH_Region']='region002';r['Region']='2'
    elif forgery=='duplicate_header':fields.insert(0,'Contig')
    else:ctx=None
    captured=capture_table(monkeypatch);mp.md_table([fields,[r[k] for k in fields]],identity_context=ctx)
    assert all('REPORT_IDENTITY_HOLD' in x[0] for x in captured['data'][1:])
    assert all('FORGED_DISPLAY' not in x[0] for x in captured['data'][1:])


def test_generic_wide_table_stays_generic(monkeypatch):
    captured=capture_table(monkeypatch);fields=['Name']+[f'Column{i}' for i in range(8)]
    mp.md_table([fields,['generic_record']+['value']*8])
    assert all(r[0]=='1: generic_record' for r in captured['data'][1:])
    assert 'REPORT_IDENTITY_HOLD' not in str(captured['data'])


def test_parse_propagates_explicit_context_to_table(tmp_path,monkeypatch):
    pkg=package(tmp_path);ctx=cr._report_identity_context(pkg);calls=[]
    monkeypatch.setattr(mp,'md_table',lambda rows,**kw:calls.append((rows,kw)) or mp.Spacer(1,1))
    mp.parse('| A | B |\n|---|---|\n| x | y |',identity_context=ctx)
    assert len(calls)==1 and calls[0][1]['identity_context'] is ctx


def test_legacy_pdf_main_uses_only_explicit_identity_package(monkeypatch):
    calls=[];monkeypatch.setattr(mp,'render',lambda *a,**kw:calls.append((a,kw)))
    monkeypatch.delenv('MAMEY_REPORT_IDENTITY_PACKAGE',raising=False)
    mp.main(['input.md','output.pdf']);assert calls[-1][1]['identity_package'] is None
    monkeypatch.setenv('MAMEY_REPORT_IDENTITY_PACKAGE','explicit_package')
    mp.main(['input.md','output.pdf']);assert calls[-1][1]['identity_package']=='explicit_package'


def test_filename_only_blast_link_stays_held_despite_unique_inventory_alias(tmp_path):
    pkg=package(tmp_path);store=pkg/'blastp_nr';store.mkdir()
    (store/'BGC001_top10.csv').write_text('hit_rank,pct_identity,pct_positives,subject_def\n1,70,80,SYNTHETIC_REFERENCE_SUBJECT\n')
    text=cr._blastp_from_channel_stores(pkg)
    assert 'REPORT_IDENTITY_HOLD[BLAST_SOURCE_LINK_UNBOUND]' in text
    assert LABEL not in text and 'BGC001' in text and '70%' in text and '80%' in text


def test_blast_summary_alias_fields_do_not_become_admitted_query_binding(tmp_path):
    pkg=package(tmp_path);p=pkg/'BLASTP_BGC_summary.csv'
    p.write_text('bgc_id,top_titles,best_pct_identity,best_query_coverage\nBGC001,SYNTHETIC_REFERENCE_SUBJECT,70,80\n')
    text=cr._blastp_summary(pkg)
    assert 'REPORT_IDENTITY_HOLD[BLAST_SOURCE_LINK_UNBOUND]' in text and LABEL not in text
    assert 'BGC001' in text and '70' in text and '80' in text


def test_authored_body_is_not_rewritten_or_filename_admitted(tmp_path,monkeypatch):
    pkg=package(tmp_path);p=pkg/'authored.md';body='## BGC001 — original authored body\n\nSYNTHETIC_REFERENCE text.';p.write_text(body)
    register=pkg/'register.json';register.write_text('{}')
    monkeypatch.setattr(cr.js,'_register_path',lambda package:register)
    monkeypatch.setattr(cr.js,'list_complete_bgcs',lambda package:['BGC001'])
    monkeypatch.setattr(cr.js,'_mode_b_path',lambda package,bid:p)
    text=cr._mode_b_cards(pkg)
    assert body in text and 'AUTHORED_CARD_LINK_UNVERIFIED' in text and LABEL not in text



def test_compile_pdf_passes_actual_package_explicitly_not_inherited_guess(tmp_path,monkeypatch):
    import subprocess
    pkg=package(tmp_path);calls=[]
    monkeypatch.setenv('MAMEY_REPORT_IDENTITY_PACKAGE','UNTRUSTED_INHERITED_PATH')
    monkeypatch.setattr(cr,'_prepare_publication_artwork',lambda md,package,profile:(md,{}))
    monkeypatch.setattr(subprocess,'run',lambda argv,**kw:calls.append((argv,kw)) or SimpleNamespace(returncode=1,stderr='synthetic refusal',stdout=''))
    result=cr._render_compiled_pdf('synthetic Markdown',tmp_path/'out.pdf',pkg)
    assert result['status']=='RENDER_FAILED' and len(calls)==1
    assert calls[0][1]['env']['MAMEY_REPORT_IDENTITY_PACKAGE']==str(pkg.resolve())
    assert calls[0][1]['cwd']==str(pkg)


def test_render_loads_actual_explicit_package_context_without_building_pdf(tmp_path,monkeypatch):
    pkg=package(tmp_path);md=tmp_path/'arbitrary_filename.md';md.write_text('# Synthetic report\n')
    seen={}
    monkeypatch.setattr(mp,'FONTS_EMBEDDED',True)
    monkeypatch.setattr(mp,'parse',lambda text,base_dir,**kw:seen.update(kw) or [])
    monkeypatch.setattr(mp,'_footer_line',lambda:'SYNTHETIC_RENDERER')
    class NoPdf:
        def __init__(self,*args,**kw):pass
        def build(self,*args,**kw):pass
    monkeypatch.setattr(mp,'SimpleDocTemplate',NoPdf)
    mp.render(md,tmp_path/'not_created.pdf',identity_package=pkg)
    assert seen['identity_context']['status']=='BOUND_PACKAGE_IDENTITY'
    assert LABEL in seen['identity_context']['identities']
    assert not (tmp_path/'not_created.pdf').exists()


@pytest.mark.parametrize("kind", ["inventory", "triage", "ledger"])
def test_duplicate_optional_identity_synonyms_cannot_be_collapsed(tmp_path, monkeypatch, kind):
    pkg = package(tmp_path)
    ctx = cr._report_identity_context(pkg)
    fields = [*FIELDS, "Full_Node_ID", "Full_Node_ID"]
    values = [row()[key] for key in FIELDS] + ["CONFLICTING_LOCATOR", FULL]
    if kind == "ledger":
        captured = capture_table(monkeypatch)
        mp.md_table([fields, values], identity_context=ctx)
        assert all("DUPLICATE_IDENTITY_HEADER" in r[0] for r in captured["data"][1:])
    else:
        name = "unrelated_name_2_inventory.csv" if kind == "inventory" else "unrelated_name_4_triage_board.csv"
        with (pkg / name).open("w", newline="") as stream:
            writer = csv.writer(stream); writer.writerow(fields); writer.writerow(values)
        if kind == "inventory":
            assert cr._report_identity_context(pkg)["status"] == "REPORT_IDENTITY_HOLD"
        else:
            _, rows = cr._triage_rows(pkg)
            assert "DUPLICATE_IDENTITY_HEADER" in cr._node_label(rows[0], ctx)
            assert "DUPLICATE_IDENTITY_HEADER" in cr._triage_board(pkg)
