from pathlib import Path
import pytest
from mamey import cli, bgc_guide, packaging

@pytest.mark.parametrize('destination,expected',[('external',False),('default',True),('inside',True),('external_link',False)])
def test_guide_refresh_only_for_package_output(tmp_path,monkeypatch,destination,expected):
    package=tmp_path/'package';package.mkdir()
    external=tmp_path/'external';external.mkdir()
    linked=package/'linked_output';linked.symlink_to(external,target_is_directory=True)
    called=[]
    def generate(args):
        out=Path(args.outdir) if args.outdir else package/'guide'
        out.mkdir(parents=True,exist_ok=True);(out/'generated.md').write_text('guide')
        return 0
    monkeypatch.setattr(bgc_guide,'guide_command',generate)
    monkeypatch.setattr(packaging,'refresh_post_seal_checksums',lambda root:called.append(root))
    argv=['guide','--package',str(package),'--format','md']
    if destination!='default':argv+=['--outdir',str({'external':external,'inside':package/'guide','external_link':linked}[destination])]
    assert cli.main(argv)==0
    assert bool(called)==expected
