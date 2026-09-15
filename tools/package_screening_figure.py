#!/usr/bin/env python3
"""Package one screening figure with mandatory standalone reproduction companions."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['figure-dir','figure-stem','data-dir','caption','receipt','renderer','session-info','out']:
        ap.add_argument('--'+name,required=True)
    ap.add_argument('--score-0-100',action='store_true')
    a=ap.parse_args()
    import re
    if not re.fullmatch(r'[a-z0-9_]+',a.figure_stem):ap.error('Unsafe figure stem')
    data=Path(a.data_dir).resolve();out=Path(a.out).resolve()
    theme=Path(a.renderer).resolve().with_name('sapote_figure_theme.R')
    required=[theme,Path(a.caption),Path(a.receipt),Path(a.renderer),Path(a.session_info)]
    required += [Path(a.figure_dir)/(a.figure_stem+ext) for ext in ['.png','.pdf']]
    if not data.is_dir() or not list(data.glob('*.csv')):ap.error('CSV data directory required')
    for p in required:
        if not p.is_file() or p.stat().st_size==0:ap.error('Missing or empty required companion: '+str(p))
    json.loads(Path(a.receipt).read_text())
    if out.exists() or out.with_suffix('.zip').exists():ap.error('Output already exists')
    out.mkdir(parents=True);(out/'data').mkdir()
    shutil.copyfile(theme,out/'sapote_figure_theme.R')
    for p in data.glob('*.csv'):shutil.copyfile(p,out/'data'/p.name)
    for ext in ['.png','.pdf']:shutil.copyfile(Path(a.figure_dir)/(a.figure_stem+ext),out/(a.figure_stem+ext))
    for src,dst in [(a.caption,'CAPTION.txt'),(a.receipt,'SOURCE_RECEIPT.json'),(a.renderer,'render.R'),(a.session_info,'R_SESSION.txt')]:shutil.copyfile(src,out/dst)
    opts=', "--score-0-100"' if a.score_0_100 else ''
    runner='''#!/usr/bin/env Rscript
full <- commandArgs(trailingOnly=FALSE)
script <- sub("^--file=", "", full[grepl("^--file=", full)])
if (length(script)!=1L) stop("Run this file with Rscript")
script <- gsub("~+~", " ", script, fixed=TRUE)
here <- dirname(normalizePath(script,mustWork=TRUE))
extra <- commandArgs(trailingOnly=TRUE)
if(length(extra)>1L || (length(extra)==1L && extra!="--overwrite")) stop("Only --overwrite is accepted")
args <- c(file.path(here,"render.R"),file.path(here,"data"),file.path(here,"reproduced")__OPTS__,extra)
status <- system2(file.path(R.home("bin"),"Rscript"),args=shQuote(args))
quit(status=status)
'''.replace('__OPTS__',opts)
    (out/'reproduce.R').write_text(runner)
    (out/'README.txt').write_text('Standalone figure packet\n\nOpen the PNG or vector PDF and read CAPTION.txt.\n\nTo reproduce from any working directory:\n  Rscript /path/to/this/packet/reproduce.R\n\nRequires R, ggplot2 and patchwork. R_SESSION.txt records the generating versions.\nThe command uses only data and scripts inside this packet and writes reproduced/.\nRepeat with --overwrite only when you intend to replace reproduced outputs.\nEdit render.R to change ggplot2 appearance; edit a copy of data/ to explore changes.\nSource values and exact source locators are documented in SOURCE_RECEIPT.json.\nInput CSVs remain unchanged. No automatic install or network access is used.\n\nScoring: '+('Values below 0 become 0; above 100 become 100. Raw values remain in data/.\n' if a.score_0_100 else 'The supplied source scale is retained.\n')+'\nFor concentration views, the unbounded mode also creates its paired zoom/full-range view.\nThis packet reproduces the display; source admission and scientific acceptance are separate.\n')
    manifest=[]
    for p in sorted(out.rglob('*')):
        if p.is_file():
            b=p.read_bytes();manifest.append({'path':str(p.relative_to(out)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
    (out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(out.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file():z.write(p,str(Path(out.name)/p.relative_to(out)))
    print(out.with_suffix('.zip'))

if __name__=='__main__':main()
