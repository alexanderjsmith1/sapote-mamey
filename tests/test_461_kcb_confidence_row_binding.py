"""Confidence labels must stay bound to the HTML row that supplies their anchor."""
from tools.kcb_confidence import extract_kcb_confidence

def row(anchor, confidence=None, label=''):
 cells=(f'<td class="similarity-text">{confidence}</td><td>{label}</td>' if confidence else '<td></td><td></td>')
 return f'<tr data-anchor="#{anchor}"><td>region</td>{cells}</tr>'

def test_blank_row_cannot_take_later_confidence(tmp_path):
 (tmp_path/'index.html').write_text('<table>'+row('r1c1')+row('r1c2','Low','public comparator')+'</table>')
 assert extract_kcb_confidence(str(tmp_path))==[{'region_anchor':'r1c2','confidence':'Low','known_cluster':'public comparator'}]

def test_intervening_blank_keeps_both_labeled_rows_bound(tmp_path):
 (tmp_path/'index.html').write_text('<table>'+row('r1c1','High','first comparator')+row('r1c2')+row('r1c3','Low','second comparator')+'</table>')
 assert extract_kcb_confidence(str(tmp_path))==[{'region_anchor':'r1c1','confidence':'High','known_cluster':'first comparator'},{'region_anchor':'r1c3','confidence':'Low','known_cluster':'second comparator'}]

def test_duplicate_source_rows_still_deduplicate(tmp_path):
 html=row('r1c2','Low','public comparator');(tmp_path/'index.html').write_text('<table>'+html+html+'</table>')
 assert len(extract_kcb_confidence(str(tmp_path)))==1
