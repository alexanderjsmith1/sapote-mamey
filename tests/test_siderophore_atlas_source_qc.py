import importlib.util
from pathlib import Path
import hashlib,json,sqlite3
import pytest
spec=importlib.util.spec_from_file_location("atlas_builder",Path(__file__).parents[1]/"tools/build_siderophore_atlas.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_config_tamper_fails_before_reading_sources(tmp_path):
 p=tmp_path/"config.json";p.write_text("{}")
 with pytest.raises(ValueError,match="CONFIG_HASH_HOLD"):m.build(p,tmp_path,expected_config_sha256="0"*64)

def test_database_tamper_and_missing_source_fail(tmp_path):
 p=tmp_path/"source.sqlite";c=sqlite3.connect(p);c.execute("create table fixture(value)");c.commit();c.close()
 digest=m.sha(p);manifest=tmp_path/"manifest.json";manifest.write_text(json.dumps(dict(database_sha256=digest)))
 pin=dict(database=str(p),manifest=str(manifest),sha256=digest,manifest_sha256=m.sha(manifest),bytes=p.stat().st_size)
 c=m.readonly(pin);c.close()
 with p.open("ab") as f:f.write(b"tamper")
 with pytest.raises(ValueError,match="SOURCE_HASH_HOLD"):m.readonly(pin)
 pin["database"]=str(tmp_path/"missing.sqlite")
 with pytest.raises(FileNotFoundError):m.readonly(pin)

def test_changed_dependency_pin_and_root_drift(tmp_path):
 cfg=tmp_path/"config.json";cfg.write_text(json.dumps(dict(output_root=str(tmp_path.parent/"outside"))))
 with pytest.raises(ValueError,match="OUTPUT_ROOT_HOLD"):m.build(cfg,tmp_path,expected_config_sha256=m.sha(cfg))
