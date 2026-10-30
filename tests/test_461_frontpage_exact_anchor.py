"""A selected source anchor must not include other anchors sharing its prefix."""
from argparse import Namespace
import json
import pytest
from mamey.kcb_frontpage import frontpage_command

@pytest.mark.parametrize('selection', ['r1c1','R1C1'])
def test_region_anchor_is_exact(tmp_path, capsys, selection):
    data={a: {'variant_name':'knownclusterblast','matches':[{'label':'public comparator','similarity':30,'genes':[1]*5}]} for a in ['r1c1','r1c10','r1c12','r1c13']}
    (tmp_path/'regions.js').write_text('var resultsData = '+json.dumps(data)+';\n')
    assert frontpage_command(Namespace(strain_dir=str(tmp_path),region=selection,top=20))==0
    rows=[line.split()[0] for line in capsys.readouterr().out.splitlines() if line.startswith('r1c')]
    assert rows==['r1c1']
