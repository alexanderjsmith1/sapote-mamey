"""Dependency closure and missing-channel admission; no figure or GIS parsing run."""
import ast
import builtins
import json
from pathlib import Path
import re
from types import SimpleNamespace
import tomllib

import pytest

ROOT=Path(__file__).resolve().parents[1]


def config():
    return tomllib.loads((ROOT/"pyproject.toml").read_text())["project"]


def names(requirements):
    return {re.match(r"[A-Za-z0-9_.-]+", value).group().lower() for value in requirements}


def function(file, name):
    tree=ast.parse((ROOT/file).read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    return node


def test_pyshp_is_optional_figure_dependency_and_all_stays_closed():
    project=config();extras=project["optional-dependencies"]
    assert "pyshp" in names(extras["figures"])
    assert "pyshp" in names(extras["all"])
    assert "pyshp" not in names(project["dependencies"])
    assert "pyshp" not in names(extras["documents"])
    assert set(extras["all"])==set().union(*(set(extras[group]) for group in ("figures","bio","render","documents","slides")))
    active=[line.split("#",1)[0].strip() for line in (ROOT/"requirements.txt").read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
    assert "pyshp" in names(active)


def test_addon_installer_requests_and_reports_shapefile_module():
    source=(ROOT/"bundle_support/install_sapote_addons.sh").read_text()
    group=re.search(r'^FIGURE_PKGS="([^"]+)"',source,re.M).group(1).split()
    assert "pyshp" in group
    assert '"shapefile"' in source


@pytest.mark.parametrize("file,name,args",[("tools/collection_site_map.py","basemap",[Path("unused.shp")]),("tools/collection_map.py","read_polygons",[[Path("unused.shp")],(0,1,0,1)])])
def test_missing_pyshp_is_actionable_and_does_not_create_outputs(monkeypatch,tmp_path,file,name,args):
    original=builtins.__import__
    def missing(mod,*a,**kw):
        if mod=="shapefile":raise ModuleNotFoundError("No module named 'shapefile'")
        return original(mod,*a,**kw)
    monkeypatch.setattr(builtins,"__import__",missing)
    namespace={"Path":Path}
    exec(compile(ast.Module(body=[function(file,name)],type_ignores=[]),file,"exec"),namespace)
    before=list(tmp_path.iterdir())
    with pytest.raises(ValueError,match="MAP_DEPENDENCY_UNAVAILABLE.*pyshp.*figures"):
        namespace[name](*args)
    assert list(tmp_path.iterdir())==before


def test_geojson_and_no_basemap_do_not_import_shapefile(monkeypatch,tmp_path):
    original=builtins.__import__
    def missing(mod,*a,**kw):
        if mod=="shapefile":pytest.fail("GeoJSON/no basemap should not require PyShp")
        return original(mod,*a,**kw)
    monkeypatch.setattr(builtins,"__import__",missing)
    namespace={"Path":Path,"json":json,"math":__import__("math")}
    exec(compile(ast.Module(body=[function("tools/collection_site_map.py","basemap")],type_ignores=[]),"map.py","exec"),namespace)
    assert namespace["basemap"](None)==([],[])
    source=tmp_path/"polygon.geojson"
    polygon=[[[0,0],[1,0],[1,1],[0,0]]]
    source.write_text(json.dumps({"type":"Polygon","coordinates":polygon}))
    polygons,paths=namespace["basemap"](source)
    assert polygons==[polygon] and paths==[source]


@pytest.mark.parametrize("present",[False,True])
def test_doctor_names_distribution_and_limits_discovery_claim(present):
    node=function("mamey/cli.py","doctor_command")
    loop=next(n for n in node.body if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and len(n.target.elts)==3)
    ns={"_have":lambda mod:present,"ok":[],"warn":[]}
    exec(compile(ast.Module(body=[loop],type_ignores=[]),"doctor.py","exec"),ns)
    lines=ns["ok"]+ns["warn"]
    assert any("pyshp" in value and "shapefile" in value for value in lines)
    if not present:
        assert any("pyshp" in value and ".[figures]" in value for value in ns["warn"])
    else:
        assert any("pyshp" in value and "discoverable" in value for value in ns["ok"])



def test_site_map_cli_reports_missing_channel_without_traceback_or_output(tmp_path):
    import os,subprocess,sys
    source=tmp_path/"complete_module_overlay"
    for rel in ("tools/collection_site_map.py","tools/_map_export.py","mamey/__init__.py","mamey/figure_theme.py","mamey/render_safe.py","mamey/figure_stamp.py","mamey/csv_safety.py"):
        target=source/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/rel).read_bytes())
    sites=tmp_path/"sites.tsv"
    sites.write_text("site\tlatitude\tlongitude\tsource_group\tisolates\nSynthetic\t10\t20\tGroup A\t1\n")
    out=tmp_path/"held_map"
    # Only the unavailable optional channel is synthesized; the complete module,
    # its imports, argument parser, input validation and __main__ all execute.
    probe="""import importlib.abc,runpy,sys
class MissingShapefile(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname=='shapefile':raise ModuleNotFoundError('synthetic unavailable shapefile')
sys.meta_path.insert(0,MissingShapefile())
sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
"""
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1")
    result=subprocess.run([sys.executable,"-B","-c",probe,str(source/"tools/collection_site_map.py"),"--sites",str(sites),"--basemap",str(tmp_path/"land.shp"),"--out",str(out)],cwd=tmp_path,env=env,capture_output=True,text=True,timeout=15)
    assert result.returncode==2,result.stdout+result.stderr
    assert "MAP_DEPENDENCY_UNAVAILABLE" in result.stderr and "pyshp" in result.stderr
    assert "Traceback" not in result.stderr
    assert not out.exists()
    assert not list(source.rglob("*.pyc"))


def test_site_map_logging_has_no_new_counted_terminal_site(tmp_path):
    import importlib.util,sys
    spec=importlib.util.spec_from_file_location("lane07_repo_health",ROOT/"tools/repo_health.py")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    after=module.check_print_calls([ROOT/"tools/collection_site_map.py"],ROOT)
    assert after.detail.split()[0]=="0"
    control=tmp_path/"tools/control.py"
    control.parent.mkdir()
    control.write_text('print("count this site")\n')
    positive=module.check_print_calls([control],tmp_path)
    assert positive.detail.split()[0]=="1"
    assert module.PRINT_WARN_THRESHOLD==1240


def test_doctor_optional_check_is_spec_discovery_not_import(monkeypatch):
    import importlib.util
    doctor=function("mamey/cli.py","doctor_command")
    helper=next(node for node in doctor.body if isinstance(node,ast.FunctionDef) and node.name=="_have")
    calls=[]
    monkeypatch.setattr(importlib.util,"find_spec",lambda name:calls.append(name) or SimpleNamespace(name=name))
    original=builtins.__import__
    def forbidden(name,*args,**kwargs):
        if name=="shapefile":pytest.fail("doctor imported Shapefile instead of discovering spec")
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,"__import__",forbidden)
    namespace={"importlib":importlib}
    exec(compile(ast.Module(body=[helper],type_ignores=[]),"doctor.py","exec"),namespace)
    assert namespace["_have"]("shapefile") is True
    assert calls==["shapefile"]
    text=(ROOT/"mamey/cli.py").read_text()
    assert "module spec discoverable (find_spec); import and Shapefile parsing unverified" in text
