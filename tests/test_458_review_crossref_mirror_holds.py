from pathlib import Path
import importlib.util
import os
import zipfile
import pytest
ROOT=Path(os.environ.get('CROSSREF_REVIEW_BASE',Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('crossref_mirror_review',ROOT/'tools/chapter_table_crossrefs.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
CAPTION='Table 5.1. Fixture counts.'
def fixture(tmp_path,kind):
    md=tmp_path/'chapter.md';md.write_text(CAPTION+'\n')
    run='<w:r><w:t>'+CAPTION+'</w:t></w:r>'
    if kind=='field':body='<w:p><w:fldSimple w:instr="SEQ Table">'+run+'</w:fldSimple></w:p>'
    elif kind=='tracked':body='<w:p><w:ins w:id="1">'+run+'</w:ins></w:p>'
    elif kind=='autonumber':body='<w:p><w:pPr><w:numPr/></w:pPr>'+run+'</w:p>'
    else:body='<w:p>'+run+'</w:p>'
    if kind=='parser':body+='<w:p><w:r><w:t>Table S5.G</w:t></w:r></w:p>'
    xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'</w:body></w:document>'
    mirror=tmp_path/'synthetic.docx'
    with zipfile.ZipFile(mirror,'w') as archive:archive.writestr('word/document.xml',xml)
    return {'docx_reader':str(ROOT/'tools/paper_reference_audit.py'),'documents':[{'id':'fixture','scope':'chapter5','path':str(md),'docx_mirrors':[str(mirror)]}]}
@pytest.mark.parametrize('kind,expected',[('field','CACHED_FIELD_TEXT'),('tracked','TRACKED_CHANGES_PRESENT'),('autonumber','UNSUPPORTED_AUTONUMBER'),('parser','TABLE_LABEL_PARSE_HOLD')])
def test_matching_tokens_do_not_clear_explicit_mirror_holds(tmp_path,kind,expected):
    result=tool.audit_manifest(fixture(tmp_path,kind));mirror=result['DOCX_mirrors'][0]
    assert mirror['status']=='TABLE_TOKEN_MULTISET_MATCH'
    assert expected in {x['code'] for x in mirror['native_read_holds']+mirror['parser_holds']}
    assert result['status']=='ACCOUNTED_WITH_HOLDS'

def test_clean_mirror_keeps_accounted_control(tmp_path):
    result=tool.audit_manifest(fixture(tmp_path,'clean'));mirror=result['DOCX_mirrors'][0]
    assert mirror['native_read_holds']==[] and mirror['parser_holds']==[]
    assert result['status']=='ACCOUNTED' and mirror['status']=='TABLE_TOKEN_MULTISET_MATCH'
