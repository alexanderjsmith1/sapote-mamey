"""The gate preserves its page output and exit status when the print ceiling drops."""
import importlib.util, json, sys
from pathlib import Path
import pytest

path=Path(__file__).resolve().parents[1]/"tools/compilation_gate.py"
spec=importlib.util.spec_from_file_location("compilation_gate_page_output",path)
tool=importlib.util.module_from_spec(spec);sys.modules[spec.name]=tool;spec.loader.exec_module(tool)

@pytest.mark.parametrize("page",[None,8])
@pytest.mark.parametrize("passed",[False,True])
@pytest.mark.parametrize("as_json",[False,True])
def test_page_output_and_exit(monkeypatch,capsys,page,passed,as_json):
    receipt={"gate":"PASS" if passed else "FAIL","mode_b_cards":0,"scorable_bgcs":0,"page_count":page,"page_floor":3,"checks":{"G1":passed,"G3":page is not None},"findings":[] if passed else ["synthetic finding"]}
    monkeypatch.setattr(tool,"run_gate",lambda *a,**kw:dict(receipt))
    monkeypatch.setattr(sys,"argv",["compilation_gate.py","--md","synthetic.md","--scorable-bgcs","0"]+(["--json"] if as_json else []))
    with pytest.raises(SystemExit) as exc:tool.main()
    stdout,stderr=capsys.readouterr()
    assert exc.value.code==(0 if passed else 1) and stderr==""
    if as_json:
        assert json.loads(stdout)["page_count"]==page
    else:
        assert ("  Page floor: 3 (pre-render; G3 deferred)" if page is None else "  Pages: 8 (floor 3)") in stdout.splitlines()
