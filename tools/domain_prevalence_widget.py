#!/usr/bin/env python3
"""domain_prevalence_widget.py (v9.7.413): host filter + single-strain drill-down + evidence + rare-loci + SVG export.
Usage: python3 tools/domain_prevalence_widget.py <ranking_dir>  (dir containing domain_prevalence_ranking.json)."""

def main():
    import json, html
    import sys
    OUT=sys.argv[1] if len(sys.argv)>1 else "."
    D=json.load(open(f"{OUT}/domain_prevalence_ranking.json"))
    rows=D["rows"]; NS=D["scope"]["strains"]; hostdist=D["host_distribution"]
    import os as _os
    _pf=f"{OUT}/pfam_desc_map.json"
    _desc=json.load(open(_pf)) if _os.path.exists(_pf) else {}
    _pflabels={r["domain_label"] for r in D["rows"] if r["source_tool"]=="clusterhmmer"}
    descmap={k:(v.get("desc","")+(f' [{v.get("acc")}]' if v.get("acc") else '')) for k,v in _desc.items() if k in _pflabels and v.get("desc")}
    strains=D["strains_sorted"]; strain_host=D["strain_host"]
    BEEWASP={"bee","wasp","bee_or_wasp"}; n_bw=sum(v for k,v in hostdist.items() if k in BEEWASP)
    def mask(idx):
        m=0
        for i in idx: m|=(1<<i)
        return format(m,'x')
    def bh(r): return {h:v["strains"] for h,v in r["by_host"].items() if v["strains"]}
    def ev(r):
        e=r["evidence"]; return [e["nr"]["hit"],e["nr"]["nohit"],e["nr"]["missing"],e["sp"]["hit"],e["sp"]["nohit"],e["cnr"]["hit"]]
    # compact row: 0 tool,1 label,2 feat,3 loci,4 strains,5 core,6 by_host,7 hexmask,8 ev[6],9 loci_list
    comp=[[r["source_tool"],r["domain_label"],r["feature_occurrences"],r["loci"],r["strains"],
           1 if r["biosynthetic_relevance"]=="core" else 0, bh(r), mask(r["strain_idx"]), ev(r), r["loci_list"]] for r in rows]
    def svg_bar(title,items,denom):
        W,b,pad,lw=680,18,4,250; H=44+len(items)*(b+pad)+10; mx=max((v for _,v,_ in items),default=1)
        o=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="system-ui" font-size="11">',
           f'<text x="12" y="20" font-size="14" font-weight="600">{html.escape(title)}</text>',
           f'<text x="12" y="34" fill="#666">denominator {denom} strains</text>']; y=44
        for lab,v,core in items:
            w=int((W-lw-60)*v/mx); col="#a03050" if core else "#7b3f6f"
            o+= [f'<text x="12" y="{y+13}">{html.escape(lab[:38])}</text>',
                 f'<rect x="{lw}" y="{y}" width="{max(w,1)}" height="{b}" fill="{col}"></rect>',
                 f'<text x="{lw+w+5}" y="{y+13}">{v}</text>']; y+=b+pad
        o.append('</svg>'); return "\n".join(o)
    def topview(hs,dn,n=20):
        sc=[(f'{r["domain_label"]} ({r["source_tool"]})', (r["strains"] if hs is None else sum(r["by_host"].get(h,{}).get("strains",0) for h in hs)), r["biosynthetic_relevance"]=="core") for r in rows]
        sc=[x for x in sc if x[1]>0]; sc.sort(key=lambda x:-x[1]); return sc[:n]
    open(f"{OUT}/figure_top20_all_strains.svg","w").write(svg_bar(f"Top 20 domains — all {NS} strains",topview(None,NS),NS))
    open(f"{OUT}/figure_top20_bees_wasps.svg","w").write(svg_bar(f"Top 20 domains — Bees & Wasps (n={n_bw})",topview(BEEWASP,n_bw),n_bw))
    J=lambda x:json.dumps(x,separators=(",",":"))
    tmpl=r"""<!doctype html><meta charset=utf-8><title>Domain Prevalence — Sapote AS cohort</title>
    <style>body{font:14px system-ui,sans-serif;margin:0;background:#faf8fb;color:#1a1a1a}
    header{background:#4a2540;color:#fff;padding:12px 18px}h1{font-size:17px;margin:0}.sub{opacity:.85;font-size:12px;margin-top:3px}
    .controls{padding:10px 18px;background:#fff;border-bottom:1px solid #e6dfe8;display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end}
    label{font-size:11px;color:#555;display:block}select,input{font:13px system-ui;padding:3px 6px}
    .wrap{display:flex;gap:16px;padding:14px 18px;flex-wrap:wrap}.panel{background:#fff;border:1px solid #e6dfe8;border-radius:8px;padding:12px;flex:1;min-width:340px}
    table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:3px 7px;text-align:right;border-bottom:1px solid #f0ebf2}
    th{cursor:pointer;position:sticky;top:0;background:#f3eef5}td:first-child,th:first-child{text-align:left}
    .tblbox{max-height:520px;overflow:auto}.rel-core{color:#a03050;font-weight:600}.ev{font-size:11px;color:#456}.loci{font-size:10px;color:#888;max-width:260px;text-align:left;white-space:normal}
    button{font:13px system-ui;padding:5px 10px;background:#7b3f6f;color:#fff;border:0;border-radius:5px;cursor:pointer}.note{font-size:11px;color:#777;padding:8px 18px}.dsc{font-size:10px;color:#999;font-weight:400;white-space:normal;margin-top:1px}</style>
    <header><h1>Domain prevalence — Sapote-Mamey AS cohort</h1>
    <div class=sub>__NS__ strains · __NLOCI__ loci · __NGENES__ genes · __NFAM__ (tool,domain) families · nr/ClusteredNR/Swiss-Prot evidence · v0.1 2026-09-07</div></header>
    <div class=controls>
    <span><label>Strain drill-down</label><select id=strain><option value="">(whole cohort)</option></select></span>
    <span><label>Host filter</label><select id=host><option value=ALL>All strains (n=__NS__)</option><option value=BW>Bees &amp; Wasps (n=__NBW__)</option>
    <option value=bee>bee</option><option value=wasp>wasp</option><option value=bee_or_wasp>bee_or_wasp</option><option value=ant>ant</option><option value=moss>moss</option><option value=other>other</option><option value=fungus_assoc>fungus_assoc</option></select></span>
    <span><label>Namespace</label><select id=tool><option value=all>all</option><option>clusterhmmer</option><option>nrps_pks_domains</option><option>tigrfam</option><option>antismash</option><option>RREfinder</option></select></span>
    <span><label>View</label><select id=mode><option value=common>Most common</option><option value=rare>Rarest (review queue)</option></select></span>
    <span><label>Top N</label><input id=topn type=number value=20 min=5 max=120 style=width:56px></span>
    <span><label>&nbsp;</label><button onclick=dl()>Download chart (SVG)</button></span></div>
    <div class=wrap><div class=panel style=flex:1.1><div id=chart></div></div>
    <div class=panel><div class=tblbox><table id=tbl><thead><tr><th>domain</th><th>ns</th><th>str</th><th>loci</th><th>nr h/n/m</th><th>sp h/n</th><th>loci (rare)</th></tr></thead><tbody></tbody></table></div></div></div>
    <div class=note>Rarity, biosynthetic relevance and evidence are SEPARATE axes — a rare domain is a review candidate, not a novelty claim. nr/ClusteredNR are selectively searched (missing ≠ no-hit); Swiss-Prot is complete. Absent annotation ≠ absent biology; similarity ≠ function. Class-level; judgment deferred.</div>
    <script>
    var DATA=__DATA__,HOST=__HD__,STRAINS=__STR__,SHOST=__SH__,NS=__NS__,DESC=__DESC__,BW=["bee","wasp","bee_or_wasp"];
    var S=document.getElementById('strain');STRAINS.forEach(function(s,i){var o=document.createElement('option');o.value=i;o.text=s+' ('+SHOST[s]+')';S.add(o);});
    function hv(r,h){if(h=='ALL')return r[4];if(h=='BW')return BW.reduce(function(a,k){return a+(r[6][k]||0)},0);return r[6][h]||0;}
    function dn(h){if(h=='ALL')return NS;if(h=='BW')return BW.reduce(function(a,k){return a+(HOST[k]||0)},0);return HOST[h]||0;}
    function esc(s){return(s+'').replace(/[&<>]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;'}[c]});}
    function cur(){var si=S.value,h=host.value,tool=document.getElementById('tool').value,mode=document.getElementById('mode').value,n=+topn.value,out=[];
     for(var k=0;k<DATA.length;k++){var r=DATA[k];if(tool!='all'&&r[0]!=tool)continue;var v,d;
      if(si!==''){if(((BigInt('0x'+(r[7]||'0'))>>BigInt(+si))&1n)===0n)continue;v=r[4];d=NS;}
      else{v=hv(r,h);if(v<=0)continue;d=dn(h);}
      out.push({tool:r[0],label:r[1],loci:r[3],strains:r[4],core:r[5],v:v,ev:r[8],ll:r[9],d:d});}
     out.sort(function(a,b){return mode=='rare'?(a.v-b.v||a.loci-b.loci):(b.v-a.v||b.loci-a.loci);});
     return{rows:out.slice(0,n),d:out.length?out[0].d:NS,si:si};}
    function ttl(c){var m=document.getElementById('mode').value;return c.si!==''?(m=='rare'?'Rarest':'Top')+' domains in '+STRAINS[+c.si]+' (bar=cohort strains)':(m=='rare'?'Rarest':'Top')+' domains — '+host.options[host.selectedIndex].text;}
    function svg(c){var it=c.rows,W=680,b=18,pad=4,lw=250,H=44+it.length*(b+pad)+10,mx=Math.max(1);it.forEach(function(r){mx=Math.max(mx,r.v)});
     var s=['<svg xmlns="http://www.w3.org/2000/svg" id="fig" viewBox="0 0 '+W+' '+H+'" font-family="system-ui" font-size="11">'];
     s.push('<text x="12" y="20" font-size="14" font-weight="600">'+esc(ttl(c))+'</text>');s.push('<text x="12" y="34" fill="#666">denominator '+c.d+' strains</text>');var y=44;
     it.forEach(function(r){var w=Math.round((W-lw-60)*r.v/mx),col=r.core?'#a03050':'#7b3f6f';
      s.push('<text x="12" y="'+(y+13)+'">'+esc(r.label.slice(0,36)+' ('+r.tool.slice(0,8)+')')+'</text>');
      s.push('<rect x="'+lw+'" y="'+y+'" width="'+Math.max(w,1)+'" height="'+b+'" fill="'+col+'"></rect>');
      s.push('<text x="'+(lw+w+5)+'" y="'+(y+13)+'">'+r.v+'</text>');y+=b+pad;});s.push('</svg>');return s.join('');}
    function render(){var c=cur();document.getElementById('chart').innerHTML=svg(c);
     document.querySelector('#tbl tbody').innerHTML=c.rows.map(function(r){var e=r.ev,loci=(r.ll&&r.ll.length)?r.ll.map(esc).join('<br>'):'';
      var dsc=(r.tool=='clusterhmmer'&&DESC[r.label])?DESC[r.label]:'';return '<tr><td class='+(r.core?'rel-core':'')+' title="'+esc(dsc)+'">'+esc(r.label)+(dsc?'<div class=dsc>'+esc(dsc.length>64?dsc.slice(0,64)+'\u2026':dsc)+'</div>':'')+'</td><td>'+esc(r.tool)+'</td><td>'+r.strains+'</td><td>'+r.loci+'</td><td class=ev>'+e[0]+'/'+e[1]+'/'+e[2]+'</td><td class=ev>'+e[3]+'/'+e[4]+'</td><td class=loci>'+loci+'</td></tr>';}).join('');}
    function dl(){var b=new Blob([document.getElementById('fig').outerHTML],{type:'image/svg+xml'}),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='domain_prevalence_'+(S.value!==''?STRAINS[+S.value]:host.value)+'.svg';a.click();}
    ['strain','host','tool','mode','topn'].forEach(function(id){document.getElementById(id).addEventListener('input',render);});
    render();
    </script>"""
    for k,v in {"__DATA__":J(comp),"__HD__":J(hostdist),"__STR__":J(strains),"__SH__":J(strain_host),
                "__NS__":str(NS),"__NLOCI__":str(D["scope"]["loci"]),"__NGENES__":str(D["scope"]["genes"]),
                "__NFAM__":str(len(rows)),"__NBW__":str(n_bw),"__DESC__":J(descmap)}.items():
        tmpl=tmpl.replace(k,v)
    open(f"{OUT}/domain_prevalence_widget.html","w").write(tmpl)
    print(f"  widget v3 written ({len(tmpl)//1024} KB): bitmask+flat evidence; strains={NS}, bees&wasps={n_bw}")


if __name__ == '__main__':
    main()
