#!/usr/bin/env python3
"""Render supplied collection sites and an optional local geographic basemap."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
import textwrap
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools._map_export import read_table,write_table,print_setup,output_preflight,export,record_table_output
from mamey.figure_theme import PALETTE

TOOL='collection_site_map'
FIELDS=('site','latitude','longitude','source_group','isolates')


def sites(path):
    rows,_=read_table(path,FIELDS);missing=[r['site'] for r in rows if not r['latitude'].strip() or not r['longitude'].strip()]
    if missing: raise ValueError('MISSING_COORDINATES: '+', '.join(missing))
    seen=set()
    for r in rows:
        if not r['site'].strip() or not r['source_group'].strip(): raise ValueError('BLANK_SITE_OR_GROUP')
        if r['site'] in seen: raise ValueError('DUPLICATE_SITE: '+r['site'])
        seen.add(r['site'])
        lat,lon,count=map(float,(r['latitude'],r['longitude'],r['isolates']))
        if not all(map(math.isfinite,(lat,lon,count))) or not -90<=lat<=90 or not -180<=lon<=180:
            raise ValueError('INVALID_COORDINATES_OR_COUNT: '+r['site'])
        if count<1 or count!=int(count): raise ValueError('INVALID_COUNT: '+r['site'])
        r.update(latitude=lat,longitude=lon,isolates=int(count))
    if max(r['longitude'] for r in rows)-min(r['longitude'] for r in rows)>180:
        raise ValueError('ANTIMERIDIAN_LAYOUT_UNSUPPORTED')
    return rows


def area_points(rows):
    """Marker area in points squared, proportional to count within each figure."""
    maximum=max(r['isolates'] for r in rows)
    return [240*r['isolates']/maximum for r in rows]


def basemap(path):
    if path is None:return [],[]
    path=Path(path);bound=[path]
    if path.suffix.lower()=='.shp':
        import shapefile
        bound=[path.with_suffix(s) for s in ('.shp','.shx','.dbf','.prj')]
        if not all(p.is_file() for p in bound):raise ValueError('SHAPEFILE_COMPONENT_MISSING')
        prj=bound[-1].read_text().upper()
        if ('GEOGCS[' not in prj and 'GEOGCRS[' not in prj) or 'PROJCS[' in prj or 'PROJCRS[' in prj or not any(s in prj for s in ('WGS_1984','WGS 84','WGS_84')):
            raise ValueError('BASEMAP_CRS: geographic WGS84 required; no reprojection')
        with shapefile.Reader(str(path)) as reader: geometries=[s.__geo_interface__ for s in reader.shapes()]
    elif path.suffix.lower() in ('.json','.geojson'):
        obj=json.loads(path.read_text())
        if obj.get('crs'):raise ValueError('BASEMAP_CRS: use RFC 7946 longitude/latitude without legacy CRS')
        geometries=([f['geometry'] for f in obj['features']] if obj['type']=='FeatureCollection' else [obj['geometry']] if obj['type']=='Feature' else [obj])
    else:raise ValueError('BASEMAP_FORMAT: GeoJSON or Shapefile required')
    polygons=[]
    for geom in geometries:
        if geom['type'] not in ('Polygon','MultiPolygon'):raise ValueError('BASEMAP_GEOMETRY: polygons required')
        for polygon in ([geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates']):
            for ring in polygon:
                if len(ring)<4 or ring[0][:2]!=ring[-1][:2]:raise ValueError('BASEMAP_RING: closed polygon required')
                if any(not math.isfinite(float(v)) for xy in ring for v in xy[:2]) or any(not(-180<=xy[0]<=180 and -90<=xy[1]<=90) for xy in ring):raise ValueError('BASEMAP_COORDINATES')
            polygons.append(polygon)
    return polygons,bound


def draw(rows, polygons, width=7.2, floor=8):
    plt=print_setup(width,floor)
    from matplotlib.path import Path as MPath
    from matplotlib.patches import PathPatch
    from matplotlib.lines import Line2D
    groups=sorted({r['source_group'] for r in rows})
    colors=[PALETTE[k] for k in ('teal','gold','coral','navy','muted')]
    if len(groups)>len(colors):raise ValueError('GROUP_PALETTE_LIMIT: at most five source groups')
    palette=dict(zip(groups,colors));height=max(4.2,1.4+len(rows)*.21,1.5+len(groups)*.5)
    fig=plt.figure(figsize=(width,height));ax=fig.add_axes([.09,.15,.63,.78]);key=fig.add_axes([.77,.15,.21,.78]);key.axis('off')
    for polygon in polygons:
        paths=[]
        for i,ring in enumerate(polygon):
            ring=[tuple(x[:2]) for x in ring];signed=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]))
            if (signed>0)!=(i==0):ring=ring[::-1]
            paths.append(MPath(ring,[MPath.MOVETO]+[MPath.LINETO]*(len(ring)-2)+[MPath.CLOSEPOLY]))
        ax.add_patch(PathPatch(MPath.make_compound_path(*paths),facecolor='#EEF2F4',edgecolor='#A8B0B5',lw=.4))
    xs=[r['longitude'] for r in rows];ys=[r['latitude'] for r in rows];dx=max(max(xs)-min(xs),.1);dy=max(max(ys)-min(ys),.1)
    ax.set_xlim(min(xs)-dx*.65,max(xs)+dx*.65);ax.set_ylim(max(-90,min(ys)-dy*.3),min(90,max(ys)+dy*.3))
    ax.set_xlabel('Longitude (degrees)');ax.set_ylabel('Latitude (degrees)');ax.grid(color=PALETTE['grid'],lw=.3)
    ax.scatter(xs,ys,s=area_points(rows),c=[palette[r['source_group']] for r in rows],edgecolor='white',lw=.6,zorder=3)
    middle=(max(xs)+min(xs))/2;labels=[]
    for left in (True,False):
        side=sorted([r for r in rows if (r['longitude']<=middle)==left],key=lambda r:(-r['latitude'],r['site']))
        for i,r in enumerate(side):
            label=textwrap.fill(r['site'],max(8,int(width*2.5)),break_long_words=False,break_on_hyphens=False)
            labels.append(ax.annotate(label,(r['longitude'],r['latitude']),xytext=(.02 if left else .98,1-(i+1)/(len(side)+1)),textcoords='axes fraction',
                ha='left' if left else 'right',va='center',fontsize=floor,
                bbox=dict(boxstyle='round,pad=.15',fc='white',ec='none'),arrowprops=dict(arrowstyle='-',color='#8A94A3',lw=.5),zorder=4))
    handles=[Line2D([],[],marker='o',linestyle='',color=palette[g],label=textwrap.fill(g,16,break_long_words=False)) for g in groups]
    key.legend(handles=handles,loc='upper left',frameon=False,title='Source group',title_fontsize=floor,borderaxespad=0)
    counts=sorted({min(r['isolates'] for r in rows),max(r['isolates'] for r in rows)})
    for i,n in enumerate(counts):
        key.scatter([.1],[.27-i*.12],s=240*n/max(counts),c=PALETTE['muted'],transform=key.transAxes)
        key.text(.28,.27-i*.12,str(n),transform=key.transAxes,va='center',fontsize=floor)
    key.text(0,.37,'Isolates\n(marker area)',transform=key.transAxes,fontsize=floor)
    fig.canvas.draw();boxes=[t.get_bbox_patch().get_window_extent() for t in labels]
    if any(a.overlaps(b) for i,a in enumerate(boxes) for b in boxes[i+1:]):raise ValueError('SITE_LABELS_DO_NOT_FIT: increase print width')
    return fig,palette


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sites',required=True,type=Path);p.add_argument('--basemap',type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--print-width',type=float,default=7.2);p.add_argument('--min-text-pt',type=float,default=8)
    a=p.parse_args(argv);output_preflight(a.out);rows=sites(a.sites);polygons,bound=basemap(a.basemap)
    fig,palette=draw(rows,polygons,a.print_width,a.min_text_pt)
    info=dict(coordinates='WGS84 longitude/latitude; unprojected geographic axes',basemap_supplied=a.basemap is not None,
              marker_area='240 * isolates / maximum site isolates (pt squared)',source_group_colors=palette)
    export(fig,a.out,TOOL,[a.sites,*bound,Path(__file__),ROOT/'tools/_map_export.py',ROOT/'mamey/figure_theme.py',ROOT/'mamey/figure_stamp.py'],info,a.min_text_pt)
    summary=[dict(source_group=g,sites=sum(r['source_group']==g for r in rows),isolates=sum(r['isolates'] for r in rows if r['source_group']==g)) for g in sorted(palette)]
    write_table(a.out/'numbers.tsv',summary,['source_group','sites','isolates'])
    record_table_output(a.out,"numbers.tsv")
    from matplotlib import pyplot as plt
    plt.close(fig)
    return 0

if __name__=='__main__':raise SystemExit(main())
