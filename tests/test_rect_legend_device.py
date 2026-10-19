from pathlib import Path
import os,shutil,subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]
R=shutil.which('Rscript')
@pytest.mark.skipif(not R,reason='Rscript unavailable')
@pytest.mark.parametrize('case',['no_device','caller_device','error'])
def test_legend_measurement_owns_only_its_null_device(tmp_path,case):
    src=(ROOT/'tools/ggtree_rect_heatmap.R').read_text();start=src.index('  legend_grob <- function(g) {');end=src.index('\n  if (n_strips',start)
    body='''suppressPackageStartupMessages(library(ggplot2))
p <- ggplot(data.frame(x=1:3,y=1:3,k=factor(c("A","B","A"))),aes(x,y,colour=k)) + geom_point()
'''+src[start:end]+'\n'
    if case=='caller_device':body+='grDevices::pdf(NULL)\n'
    body+='before <- grDevices::dev.cur()\n'
    body+=('tryCatch(legend_grob(structure(list(),class="bad_fixture")),error=function(e) cat("EXPECTED_ERROR\\n"))\n' if case=='error' else 'stopifnot(inherits(legend_grob(p),"gtable"))\n')
    body+='stopifnot(identical(before,grDevices::dev.cur()))\ncat("DEVICE_RESTORED\\n")\n'
    script=tmp_path/'probe.R';script.write_text(body)
    cp=subprocess.run([R,str(script)],cwd=tmp_path,capture_output=True,text=True,timeout=20)
    assert cp.returncode==0,cp.stdout+cp.stderr
    assert 'DEVICE_RESTORED' in cp.stdout and not (tmp_path/'Rplots.pdf').exists()
    if case=='error':assert 'EXPECTED_ERROR' in cp.stdout
