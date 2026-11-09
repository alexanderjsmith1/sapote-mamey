import hashlib,json
from mamey.compile_report import _figures

def digest(b): return hashlib.sha256(b).hexdigest()
def pair(root):
 d=root/'figures';d.mkdir();png=d/'one.png';svg=d/'one.svg';png.write_bytes(b'PNG');svg.write_bytes(b'<svg/>')
 payload={'outputs':{kind:{'logical_locator':p.relative_to(root).as_posix(),'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size} for kind,p in [('png',png),('svg',svg)]}}
 (root/'figure_receipts.jsonl').write_text(json.dumps(payload)+'\n');return png,svg

def test_verified_pair_embeds_once_and_links_alternate(tmp_path):
 png,svg=pair(tmp_path);out=_figures(tmp_path,generate=False)
 assert out.count('![one](')==1 and '![one](figures/one.png)' in out
 assert '[SVG version](<figures/one.svg>)' in out

def test_unbound_pair_is_not_collapsed(tmp_path):
 png,svg=pair(tmp_path);(tmp_path/'figure_receipts.jsonl').unlink();out=_figures(tmp_path,generate=False)
 assert '![one](figures/one.png)' in out and '![one](figures/one.svg)' in out

def test_stale_pair_is_not_collapsed(tmp_path):
 png,svg=pair(tmp_path);svg.write_bytes(b'<svg>changed</svg>');out=_figures(tmp_path,generate=False)
 assert '![one](figures/one.png)' in out and '![one](figures/one.svg)' in out

def test_malformed_receipt_preserves_both(tmp_path):
 pair(tmp_path);(tmp_path/'figure_receipts.jsonl').write_text('{broken\n');out=_figures(tmp_path,generate=False)
 assert '![one](figures/one.png)' in out and '![one](figures/one.svg)' in out
 assert 'could not be verified' in out

def test_svg_only_remains_embedded(tmp_path):
 (tmp_path/'solo.svg').write_text('<svg/>');out=_figures(tmp_path,generate=False)
 assert '![solo](solo.svg)' in out

def test_non_utf8_receipt_preserves_both(tmp_path):
 pair(tmp_path);(tmp_path/'figure_receipts.jsonl').write_bytes(b'\xff\xfe');out=_figures(tmp_path,generate=False)
 assert '![one](figures/one.png)' in out and '![one](figures/one.svg)' in out
 assert 'could not be verified' in out


def test_svg_link_with_spaces_is_a_markdown_target(tmp_path):
 d=tmp_path/'figure folder';d.mkdir(); png=d/'first figure.png';svg=d/'first figure.svg';png.write_bytes(b'PNG');svg.write_bytes(b'<svg/>')
 payload={'outputs':{k:{'logical_locator':p.relative_to(tmp_path).as_posix(),'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size} for k,p in [('png',png),('svg',svg)]}}
 (tmp_path/'figure_receipts.jsonl').write_text(json.dumps(payload)+'\n');out=_figures(tmp_path,generate=False)
 assert '[SVG version](<figure folder/first figure.svg>)' in out
 assert '![first figure](<figure folder/first figure.png>)' in out
