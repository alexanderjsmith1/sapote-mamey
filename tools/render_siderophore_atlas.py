"""Render a pinned atlas snapshot into a standalone local evidence drawer."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mamey.tool_database_reader import _digest

def render(atlas,expected_sha256,output,permitted_root):
 atlas=Path(atlas);output=Path(output).resolve();root=Path(permitted_root).resolve()
 if not output.is_relative_to(root):raise ValueError("OUTPUT_ROOT_HOLD")
 if output.exists():raise ValueError("ADDITIVE_OUTPUT_EXISTS_HOLD")
 if _digest(atlas)!=expected_sha256:raise ValueError("ATLAS_HASH_HOLD")
 data=json.loads(atlas.read_text());records=data["records"];pop=data["receipt"]["population"];f=pop["frozen45"];c=pop["current_handback"]
 template=(Path(__file__).parents[1]/"mamey/data/siderophore_atlas.html").read_text()
 replacements={"__ATLAS_SHA__":expected_sha256,"__STRAINS__":str(f["strains"]),"__LOCI__":str(f["loci"]),"__RUNS__":str(c["run_entries"]),"__BASES__":str(c["base_identity_count"]),"__ELIGIBLE__":str(c["eligible_base_count"]),"__PRODUCTS__":str(sum(r["biosynthesis_state"]=="SOURCE_PRODUCT_CLASS_OBSERVED" for r in records)),"__CASSETTES__":str(sum(r["biosynthesis_state"]=="IRON_CASSETTE_CONTEXT_ONLY" for r in records)),"__NEGATIVES__":str(sum(r["selection"]=="NEGATIVE_CONTROL" for r in records))}
 for key,value in replacements.items():template=template.replace(key,value)
 template=template.replace("__ATLAS_DATA__",json.dumps(data,separators=(",",":")).replace("<","\\u003c"))
 output.write_text(template)
 return dict(output_sha256=_digest(output),records=len(records),source_sha256=expected_sha256)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("atlas");p.add_argument("--sha256",required=True);p.add_argument("--output",required=True);p.add_argument("--permitted-root",required=True);a=p.parse_args();print(json.dumps(render(a.atlas,a.sha256,a.output,a.permitted_root),indent=2))
