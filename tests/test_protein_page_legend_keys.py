from pathlib import Path
import os,shutil,subprocess,json
import pytest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(os.environ.get('LANE06_PAGE_R_CANDIDATE',ROOT/'tools/protein_pcoa_page.R'))
R=shutil.which('Rscript')
R_CODE = "suppressPackageStartupMessages({library(ggplot2);library(jsonlite)})\npdf(NULL)\na<-commandArgs(TRUE);text<-readLines(a[1],warn=FALSE)\nstart<-grep('^lv <-',text);finish<-grep('^ps <-',text)-1L\n# Exact helper/global colour and mapping code, without the renderer main.\nfs<-8;page<-list(legend=list(ref='Reference',mibig='MIBiG',iso_low='Low',iso_mid='Mid',iso_high='High'),leader_colour='#555555')\neval(parse(text=text[start:finish]))\nstate<-a[2];layers<-c('ref','mibig','iso_low','iso_high');if(state=='occupied')layers<-c(layers,'iso_mid')\nsp<-list(points=list(x=seq_along(layers),y=seq_along(layers),layer=layers,size=rep(1,length(layers))),tag='Synthetic',xlab='x',ylab='y',xlim=c(0,6),ylim=c(0,6),labels=list(label=list()))\n# mt_floor cannot alter the key-visibility policy; no drawing/save is performed.\nmt_floor<-function(p,min_pt)p\np<-panel(sp);g<-ggplotGrob(p)\nbox<-g$grobs[[which(g$layout$name=='guide-box-bottom')]]\nif(inherits(box,'zeroGrob'))box<-g$grobs[[which(g$layout$name=='guide-box-right')]]\nguides<-box$grobs[vapply(box$grobs,inherits,logical(1),'gtable')]\nrows<-list()\nfor(guide in guides)for(i in which(grepl('^key-',guide$layout$name))){\n  key<-guide$grobs[[i]];children<-key$children\n  pt<-children[vapply(children,inherits,logical(1),'points')]\n  rows[[length(rows)+1L]]<-list(key=guide$layout$name[i],point_glyphs=length(pt),pch=if(length(pt))unname(pt[[1]]$pch)else NULL,fill=if(length(pt))unname(pt[[1]]$gp$fill)else NULL,col=if(length(pt))unname(pt[[1]]$gp$col)else NULL)\n}\ncat(toJSON(list(state=state,drawn_points=nrow(ggplot_build(p)$data[[1]]),keys=rows),auto_unbox=TRUE,null='null',pretty=TRUE))\n"
@pytest.mark.skipif(not R,reason='Rscript unavailable')
@pytest.mark.parametrize('state',['empty','occupied'])
def test_shared_identity_legend_keeps_all_encoding_glyphs(tmp_path,state):
    script=tmp_path/'inspect.R';script.write_text(R_CODE)
    cp=subprocess.run([R,str(script),str(SOURCE),state],cwd=tmp_path,capture_output=True,text=True,timeout=20)
    assert cp.returncode==0,cp.stderr
    v=json.loads(cp.stdout);keys=v['keys'];assert len(keys)==5 and all(k['point_glyphs']==1 for k in keys)
    assert [k['pch'] for k in keys]==[16,16,21,21,21]
    assert keys[3]['fill']=='#F4A582FF' and keys[3]['col']=='#D6604DFF'
    assert keys[2]['fill']=='#B2182BFF' and keys[4]['fill']=='#FFFFFFFF'
    assert v['drawn_points']==(4 if state=='empty' else 5), 'Legend glyphs must not create data observations'
