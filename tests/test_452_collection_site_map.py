import csv,json
from pathlib import Path
import pytest
from PIL import Image
from pypdf import PdfReader
from tools import collection_site_map as m
from tools._map_export import sha


def table(tmp_path):
    p=tmp_path/'sites.tsv'
    p.write_text('site\tlatitude\tlongitude\tsource_group\tisolates\nSite A\t10\t20\tGroup A\t1\nSite B\t11\t21\tGroup A\t4\nSite C\t12\t20.5\tGroup B\t9\n')
    return p


def test_render(tmp_path):
    p=table(tmp_path);out=tmp_path/'out'
    geo=tmp_path/'base.geojson';geo.write_text(json.dumps({'type':'Polygon','coordinates':[[[19,9],[22,9],[22,13],[19,13],[19,9]]]}))
    assert m.main(['--sites',str(p),'--basemap',str(geo),'--out',str(out)])==0
    page=PdfReader(out/'collection_site_map.pdf').pages[0];sizes=[]
    text=page.extract_text(visitor_text=lambda t,cm,tm,f,s:sizes.append(s) if t.strip() else None)
    assert min(sizes)>=8 and float(page.mediabox.width)==pytest.approx(7.2*72)
    assert all(x in text for x in ('Site A','Site B','Site C'))
    assert 'Sapote-Mamey' in PdfReader(out/'collection_site_map.pdf').metadata.creator
    im=Image.open(out/'collection_site_map.png');assert im.width==4320 and 'Sapote-Mamey' in im.info['Software']
    receipt=json.loads((out/'RUN_INFO.json').read_text());assert receipt['dpi']==600
    assert {x['sha256'] for x in receipt['inputs']}>={sha(p),sha(geo)}
    rows=list(csv.DictReader((out/'numbers.tsv').open(),delimiter='\t'))
    assert rows==[dict(source_group='Group A',sites='2',isolates='5'),dict(source_group='Group B',sites='1',isolates='9')]
    with pytest.raises(FileExistsError):m.main(['--sites',str(p),'--out',str(out)])


def test_point_area_proportional(tmp_path):
    rows=m.sites(table(tmp_path));fig,_=m.draw(rows,[])
    sizes=fig.axes[0].collections[0].get_sizes()
    assert list(sizes/sizes[0])==[1,4,9]
    from matplotlib import pyplot as plt
    plt.close(fig)


@pytest.mark.parametrize('column,value,error',[(1,'','MISSING_COORDINATES: Site A'),(2,'','MISSING_COORDINATES: Site A'),(1,'nan','INVALID'),(2,'181','INVALID'),(4,'1.5','INVALID_COUNT'),(4,'0','INVALID_COUNT')])
def test_invalid_site(tmp_path,column,value,error):
    p=table(tmp_path);lines=p.read_text().splitlines();row=lines[1].split('\t');row[column]=value;lines[1]='\t'.join(row);p.write_text('\n'.join(lines)+'\n')
    with pytest.raises(ValueError,match=error):m.main(['--sites',str(p),'--out',str(tmp_path/'out')])
    assert not (tmp_path/'out').exists()


def test_shapefile_local(tmp_path):
    import shapefile
    p=tmp_path/'base.shp'
    with shapefile.Writer(str(p)) as w:
        w.field('name','C');w.poly([[[19,9],[19,13],[22,13],[22,9],[19,9]]]);w.record('Synthetic')
    p.with_suffix('.prj').write_text('GEOGCS["WGS 84",DATUM["WGS_1984"]]')
    polygons,bound=m.basemap(p);assert len(polygons)==1 and len(bound)==4
    p.with_suffix('.prj').write_text('PROJCS["WGS 84"]')
    with pytest.raises(ValueError,match='BASEMAP_CRS'):m.basemap(p)


def test_no_basemap_and_print_floor(tmp_path):
    assert m.basemap(None)==([],[])
    with pytest.raises(ValueError,match='PRINT_GATE'):m.draw(m.sites(table(tmp_path)),[],floor=7)
