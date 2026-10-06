from mamey.modeb_current50_v2 import v2_findings
import pytest
GOOD='NOT_RUN: GECCO was not evaluated because the source output is unavailable; no prediction is inferred'

def deferral(text):
 return any(f['code']=='V2_DEFERRAL' for f in v2_findings('## §22 GECCO\n'+text))

@pytest.mark.parametrize('text',[
 GOOD+'; regulators were not assessed.',
 '| '+GOOD+' | Regulators were not assessed |',
 '| Regulators were not assessed | '+GOOD+' |',
 'Regulators were not assessed; '+GOOD+'.',
 '| NOT_RUN: GECCO was not evaluated | because the source output is unavailable; no prediction is inferred |',
 '| NOT_RUN: GECCO was not evaluated because the source output is unavailable | no prediction is inferred |',
 GOOD+' and regulators were not assessed.',
])
def test_limitation_cannot_exempt_other_clause_or_table_cell(text):
 assert deferral(text)

@pytest.mark.parametrize('text',[
 GOOD+'.',
 '| '+GOOD+' | No supported regulatory assignment |',
 GOOD+'; UNAVAILABLE: regulators were not assessed because the source output is unavailable; no regulation is inferred.',
 '| '+GOOD+' | UNAVAILABLE: regulators were not assessed because the source output is unavailable; no regulation is inferred |',
 'NOT_RUN: GECCO was not evaluated because the output uses a literal \\| symbol and is unavailable; no prediction is inferred.',
])
def test_independently_complete_limitations_pass(text):
 assert not deferral(text)
