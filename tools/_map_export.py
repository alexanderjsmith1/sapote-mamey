"""Shared input binding and print checks for supplied-data map renderers."""

import csv
import hashlib
import json
import math
from pathlib import Path
from mamey.figure_stamp import savefig_metadata
from mamey.figure_theme import apply_theme


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_table(path, fields):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader=csv.DictReader(f,delimiter='\t')
        if not set(fields)<=set(reader.fieldnames or []):
            raise ValueError('MISSING_COLUMNS: '+', '.join(fields))
        rows=list(reader)
        if not rows: raise ValueError('EMPTY_TABLE')
        return rows,reader.fieldnames


def write_table(path, rows, fields):
    try:
        from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
    except ImportError:
        import os as _cs_os, sys as _cs_sys
        _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
        from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        w=_SafeDictWriter(f,fieldnames=fields,delimiter='\t')
        w.writeheader();w.writerows(rows)


def print_setup(width, floor):
    if not math.isfinite(width) or width<4 or not math.isfinite(floor) or floor<8:
        raise ValueError('PRINT_GATE: width must be >=4 in and text >=8 pt')
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    apply_theme(plt,'manuscript')
    plt.rcParams.update({'font.size':floor,'axes.labelsize':floor,'xtick.labelsize':floor,
                         'ytick.labelsize':floor,'legend.fontsize':floor,'axes.titlesize':floor,
                         'text.parse_math':False,'pdf.fonttype':42})
    return plt


def output_preflight(out):
    out=Path(out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise FileExistsError('OUTPUT_EXISTS: '+str(out))


def check_text(fig, floor):
    from matplotlib.text import Text
    fig.canvas.draw();renderer=fig.canvas.get_renderer();page=fig.bbox
    excluded=set()
    for ax in fig.axes:
        for axis,limits in ((ax.xaxis,ax.get_xlim()),(ax.yaxis,ax.get_ylim())):
            low,high=sorted(limits)
            for tick in [*axis.get_major_ticks(),*axis.get_minor_ticks()]:
                if not ax.axison or not low<=tick.get_loc()<=high:
                    excluded.update((id(tick.label1),id(tick.label2)))
    for text in fig.findobj(Text):
        if id(text) in excluded:continue
        if not text.get_visible() or not text.get_text().strip(): continue
        box=text.get_window_extent(renderer)
        if text.get_fontsize()<floor or box.x0<page.x0-0.1 or box.y0<page.y0-0.1 or box.x1>page.x1+0.1 or box.y1>page.y1+0.1:
            raise ValueError('TEXT_DOES_NOT_FIT: '+text.get_text())


def export(fig, out, tool, inputs, info, floor):
    out=Path(out);output_preflight(out);check_text(fig,floor)
    out.mkdir(parents=True,exist_ok=True)
    outputs=[]
    for ext in ('pdf','png'):
        path=out/(tool+'.'+ext)
        fig.savefig(path,dpi=600,facecolor='white',metadata=savefig_metadata(path,tool))
        outputs.append({'path':path.name,'sha256':sha(path)})
    info.update(tool=tool,minimum_text_pt=floor,print_width_in=float(fig.get_figwidth()),dpi=600,
                inputs=[{'path':str(Path(p).resolve()),'sha256':sha(p)} for p in dict.fromkeys(inputs)],outputs=outputs)
    (out/'RUN_INFO.json').write_text(json.dumps(info,indent=2,ensure_ascii=False)+'\n')


def record_table_output(out, filename):
    out=Path(out);path=out/filename;receipt=out/'RUN_INFO.json'
    info=json.loads(receipt.read_text());info['outputs'].append({'path':filename,'sha256':sha(path)})
    receipt.write_text(json.dumps(info,indent=2,ensure_ascii=False)+'\n')
