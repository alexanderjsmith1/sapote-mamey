"""Portable exploratory bee figures. Explicit JSON input, no implicit workspace discovery.

This is a candidate presentation module, not a scientific acceptance or release gate.
"""
from pathlib import Path
from mamey.csv_safety import SafeDictWriter, SafeWriter
from mamey.render_safe import safe_savefig_dpi

import argparse, collections, csv, hashlib, json

HOSTS=('Bombus sp.','Apis mellifera','Other Apidae (Andrena sp.)','Other Apidae (Unidentified)')
CALLS={'positive':0,'negative':1,'not_tested':2,'not_supplied':3}
CLASSES=('NRPS','NRPS-like','PKS','T1PKS','T2PKS','T3PKS','RiPP','RiPP-like','terpene','saccharide')
FAMILIES=('Glyco_hydro_18','Glyco_hydro_19','Glyco_hydro_20','CBM_5_12','LPMO_10','Glucosamine_iso')

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate(data):
    rows=data['selected']; owners=data['bee_owner_rows']
    ids=[r['binding']['strain'] for r in rows]
    if not rows or len(set(ids))!=len(ids): raise ValueError('EMPTY_OR_DUPLICATE_GENOME_STRAINS')
    owner_ids=[r['strain'] for r in owners]
    if len(set(owner_ids))!=len(owner_ids): raise ValueError('DUPLICATE_OWNER_STRAIN')
    if any(r['host_raw'] not in HOSTS for r in owners): raise ValueError('NON_BEE_OWNER_RECORD')
    owner_index={r['strain']:r for r in owners}
    for r in rows:
        sid=r['binding']['strain']
        if sid not in owner_index or r['assay']['host_raw'] not in HOSTS: raise ValueError('BEE_HOST_NOT_BOUND')
        if r['comparison']['disposition']!='REVIEW_CANDIDATE': raise ValueError('GENOME_HOLD_NOT_CLEARED')
        if r['comparison']['genome_input_sha256']!=r['chitin']['input_sha256']: raise ValueError('GENOME_CONTENT_MISMATCH')
        for target in ('Candida','MRSA'):
            if r['assay'][target] not in CALLS or r['assay'][target]!=owner_index[sid][target]: raise ValueError('ASSAY_CALL_MISMATCH')
        for family in FAMILIES:
            v=r['chitin'][family]
            if isinstance(v,bool) or not isinstance(v,int) or v<0: raise ValueError('INVALID_FAMILY_COUNT')
    return rows

def render(source,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap,BoundaryNorm
    from matplotlib.patches import Patch
    from matplotlib.text import Text
    import numpy as np
    data=json.loads(Path(source).read_text()); rows=validate(data)
    destination=Path(out).resolve()
    if destination.exists(): raise ValueError('OUTPUT_ALREADY_EXISTS')
    destination.mkdir(parents=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':12,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9,'svg.fonttype':'none','savefig.dpi':300,'axes.spines.top':False,'axes.spines.right':False})
    ids=[r['binding']['strain'] for r in rows]; results=[]
    def table(fid,records):
        p=destination/(fid+'_data.csv')
        with p.open('w',newline='') as f:
            w=SafeDictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
        return list(csv.DictReader(p.open()))
    def save(fig,fid,title,caption):
        fig.canvas.draw(); renderer=fig.canvas.get_renderer(); bounds=fig.bbox
        texts=[t for t in fig.findobj(Text) if t.get_visible() and t.get_text().strip()]
        outside=[]
        for t in texts:
            box=t.get_window_extent(renderer)
            if box.x0<bounds.x0-2 or box.y0<bounds.y0-2 or box.x1>bounds.x1+2 or box.y1>bounds.y1+2:outside.append(t.get_text())
        if outside: raise ValueError('TEXT_OUTSIDE_CANVAS: '+repr(outside))
        if min(t.get_fontsize() for t in texts)<8:raise ValueError('TEXT_BELOW_8PT')
        for ext in ['svg','png']:fig.savefig(destination/(fid+'.'+ext),dpi=safe_savefig_dpi(fig, 300),facecolor='white')
        result={'figure_id':fid,'title':title,'caption':caption,'width_inches':float(fig.get_figwidth()),'height_inches':float(fig.get_figheight()),'minimum_font_pt':min(t.get_fontsize() for t in texts),'text_inside_canvas':True,'source_sha256':digest(source),'svg':fid+'.svg','png':fid+'.png','data_csv':fid+'_data.csv','scientific_acceptance':'NOT_ASSESSED','status':'PRIVATE_PROTOTYPE','files':{ext:digest(destination/(fid+ext)) for ext in ['.svg','.png','_data.csv']}}
        results.append(result);plt.close(fig)
    # P01 extends the existing categorical assay-call presentation at a fixed print width.
    fid='BEE-P01'; values=table(fid,[{'strain':r['binding']['strain'],'target':target,'call':r['assay'][target],'source_row':r['assay']['source_row'],'source_sha256':r['assay']['source_sha256']} for r in rows for target in ('Candida','MRSA')])
    matrix=np.array([[CALLS[r['assay'][t]] for t in ('Candida','MRSA')] for r in rows])
    fig,ax=plt.subplots(figsize=(7.2,max(4.8,len(rows)*.24+1.6)))
    colors=['#2c6fbb','#cfe0f3','#d9dde0','#ffffff'];ax.pcolormesh(np.arange(3)-.5,np.arange(len(ids)+1)-.5,matrix,cmap=ListedColormap(colors),norm=BoundaryNorm(np.arange(-.5,4.5),4),rasterized=False);ax.invert_yaxis()
    ax.set_xticks([0,1],['Candida','MRSA']);ax.set_yticks(range(len(ids)),ids)
    symbols=['+','−','NT','NA']
    for y in range(len(ids)):
        for x in range(2):ax.text(x,y,symbols[matrix[y,x]],ha='center',va='center',fontsize=9,color='white' if matrix[y,x]==0 else '#17212b')
    ax.set_title('Recorded activity calls — bee genome subset',pad=15)
    fig.legend(handles=[Patch(facecolor=c,edgecolor='#76838a',label=l) for c,l in zip(colors,['Positive (+)','Negative (−)','Not tested','Not supplied'])],loc='lower center',ncol=2,bbox_to_anchor=(.5,.02),frameon=False)
    fig.subplots_adjust(left=.19,right=.94,top=.9,bottom=.19)
    save(fig,fid,'Recorded activity calls — bee genome subset',f'n={len(rows)} bee-associated review-candidate genomes. Calls are owner-recorded qualitative strain summaries, not standardized effect sizes. No common dose, replicate count, BGC causality or compound identity is established. Negative and not tested remain distinct.')
    # P02 adapts the existing class-by-strain figure contract; class labels overlap.
    fid='BEE-P02'; tidy=table(fid,[{'sid':r['binding']['strain'],'product_class':c,'n_bgcs':r['comparison']['product_counts'].get(c,0)} for r in rows for c in CLASSES])
    matrix=np.array([[int(x['n_bgcs']) for x in tidy if x['sid']==sid] for sid in ids])
    fig,ax=plt.subplots(figsize=(7.2,6.8));im=ax.pcolormesh(np.arange(len(CLASSES)+1)-.5,np.arange(len(ids)+1)-.5,np.log1p(matrix),cmap='viridis',rasterized=False);ax.invert_yaxis()
    ax.set_yticks(range(len(ids)),ids);ax.set_xticks(range(len(CLASSES)),CLASSES,rotation=60,ha='right');ax.set_title('Bee BGC class profiles — log1p counts',pad=15)
    cb=fig.colorbar(im,ax=ax,location='right',fraction=.04,pad=.035);cb.set_label('log(1 + region-label count)');cb.solids.set_rasterized(False)
    fig.subplots_adjust(left=.18,right=.86,top=.9,bottom=.20)
    save(fig,fid,'Bee BGC class profiles — log1p counts',f'n={len(rows)} review-candidate genomes. Ten declared source class labels; membership is nonexclusive, so columns must not be summed as distinct BGCs. Colour is log(1+count); sidecar preserves raw counts. Strain order uses Interior + 0.5 Edge + 0.25 Full-contig solely as an exploratory ordering rule, not biological yield.')
    # P03 family-positive proteins, not inferred chitin metabolism or bee adaptation.
    fid='BEE-P03'; tidy=table(fid,[{'strain':r['binding']['strain'],'family':family,'family_positive_proteins':r['chitin'][family],'genome_input_sha256':r['chitin']['input_sha256'],'receipt_sha256':r['chitin']['receipt_sha256']} for r in rows for family in FAMILIES])
    matrix=np.array([[int(x['family_positive_proteins']) for x in tidy if x['strain']==sid] for sid in ids])
    fig,ax=plt.subplots(figsize=(7.2,6.8));im=ax.pcolormesh(np.arange(len(FAMILIES)+1)-.5,np.arange(len(ids)+1)-.5,np.log1p(matrix),cmap='viridis',rasterized=False);ax.invert_yaxis()
    ax.set_yticks(range(len(ids)),ids);ax.set_xticks(range(6),['GH18','GH19','GH20','CBM5/12','AA10','NagB family'],rotation=45,ha='right');ax.set_title('Bee chitin-related family evidence — log1p',pad=15)
    cb=fig.colorbar(im,ax=ax,location='right',fraction=.04,pad=.035);cb.set_label('log(1 + family-positive proteins)');cb.solids.set_rasterized(False)
    fig.subplots_adjust(left=.18,right=.86,top=.9,bottom=.19)
    save(fig,fid,'Bee chitin-related family evidence — log1p',f'n={len(rows)} genome-content-bound evidence records. Reconciled family-positive protein counts, partly reused from older identical genomes; not new experimental measurements. Zero means no detection under the source workflow, not proven biological absence. Family detection does not establish secretion, catalytic specificity, complete chitin metabolism, activity, or ecological adaptation.')
    # P04 reports distinct strain labels, never counts assembly variants as independent isolates.
    fid='BEE-P04'; available=set(ids); held={r['strain'] for r in data['excluded_packages'] if r['reason'] not in ('WASP','BEE_HOST_NOT_BOUND')}
    records=[]
    for host in HOSTS:
        names={r['strain'] for r in data['bee_owner_rows'] if r['host_raw']==host}
        for label,subset in [('Selected genome',names&available),('Genome held',names&held),('No admitted genome in collection',names-available-held)]:records.append({'host_raw':host,'coverage':label,'isolates':len(subset)})
    tidy=table(fid,records);fig,ax=plt.subplots(figsize=(7.2,4.7));left=np.zeros(4)
    for label,color in [('Selected genome','#2c6fbb'),('Genome held','#7fa9d6'),('No admitted genome in collection','#d9dde0')]:
        vals=np.array([next(int(r['isolates']) for r in tidy if r['host_raw']==h and r['coverage']==label) for h in HOSTS]);ax.barh(range(4),vals,left=left,color=color,label=label);left+=vals
    ax.set_yticks(range(4),['Bombus sp.','Apis mellifera','Other Apidae\n(Andrena sp.)','Other Apidae\n(unidentified)']);ax.invert_yaxis();ax.set_xlabel('Distinct owner-recorded bee isolates');ax.set_title('Genome coverage of the bee isolate table',pad=15)
    ax.set_xlim(0,max(20,int(np.ceil(max(left)/20))*20));ax.set_axisbelow(True);ax.grid(axis='x',alpha=.25)
    fig.legend(loc='lower center',ncol=1,bbox_to_anchor=(.5,.01),frameon=False);fig.subplots_adjust(left=.28,right=.96,top=.88,bottom=.3)
    save(fig,fid,'Genome coverage of the bee isolate table',f'n={len(data["bee_owner_rows"])} owner-recorded bee isolates. Genome selection includes {len(available)} strains. Held genomes and unresolved variants are counted once per strain; lack of an admitted genome is not lack of a genome anywhere on disk. Wasps are excluded. The genomic subset is not representative by assumption.')
    (destination/'PROTOTYPE_MANIFEST.json').write_text(json.dumps({'schema':'bee-review-prototypes.v1','figures':results},indent=2)+'\n')
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);args=p.parse_args();print(json.dumps(render(args.input,args.out),indent=2))
