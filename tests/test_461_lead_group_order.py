"""Graph component numbering must not depend on Python hash randomization."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

@pytest.mark.parametrize("seed", ["1", "2", "3", "4"])
def test_lead_groups_have_stable_tie_order(seed):
    code = """
import json
from tools.build_lead_detail import rescue_groups
rows = [
 {"bgc_a":"BGC003","bgc_b":"BGC004","pair":"second","strong_supporting_references":1},
 {"bgc_a":"BGC001","bgc_b":"BGC002","pair":"first","strong_supporting_references":1},
]
print(json.dumps([x["fragments"] for x in rescue_groups({"ranked_pairs":rows})]))
"""
    result = subprocess.run([sys.executable, "-B", "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env=dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True, text=True, check=True, timeout=20)
    assert json.loads(result.stdout) == [["BGC001", "BGC002"], ["BGC003", "BGC004"]]
