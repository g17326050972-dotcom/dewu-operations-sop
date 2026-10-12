"""Read-only OOXML audit before/after an artifact-tool edit. Never writes XLSX."""
import sys, json, zipfile, collections, posixpath, functools
import xml.etree.ElementTree as ET

N={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def canonical(e):
    if e is None:return None
    return [e.tag,sorted(e.attrib.items()),(e.text or '').strip(),[canonical(c) for c in e]]
def read(path):
    with zipfile.ZipFile(path) as z:
        wb=ET.fromstring(z.read('xl/workbook.xml'))
        rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        relationships={r.attrib['Id']:r.attrib['Target'] for r in rels}
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            for si in ET.fromstring(z.read('xl/sharedStrings.xml')):strings.append(''.join(si.itertext()))
        styles=ET.fromstring(z.read('xl/styles.xml')) if 'xl/styles.xml' in z.namelist() else None
        fonts=list(styles.find('m:fonts',N)) if styles is not None and styles.find('m:fonts',N) is not None else []
        fills=list(styles.find('m:fills',N)) if styles is not None and styles.find('m:fills',N) is not None else []
        borders=list(styles.find('m:borders',N)) if styles is not None and styles.find('m:borders',N) is not None else []
        xfs=list(styles.find('m:cellXfs',N)) if styles is not None and styles.find('m:cellXfs',N) is not None else []
        numfmts={n.get('numFmtId'):n.get('formatCode') for n in styles.findall('m:numFmts/m:numFmt',N)} if styles is not None else {}
        @functools.lru_cache(None)
        def style_semantics(index):
            if index>=len(xfs):return None
            xf=xfs[index];attributes={k:v for k,v in xf.attrib.items() if k not in ('fontId','fillId','borderId','numFmtId','xfId')}
            return {'attributes':attributes,'numberFormat':numfmts.get(xf.get('numFmtId'),xf.get('numFmtId')),'font':canonical(fonts[int(xf.get('fontId','0'))]) if fonts else None,'fill':canonical(fills[int(xf.get('fillId','0'))]) if fills else None,'border':canonical(borders[int(xf.get('borderId','0'))]) if borders else None,'children':[canonical(c) for c in xf]}
        out={'sheets':[],'definedNames':canonical(wb.find('m:definedNames',N)),'calcPr':canonical(wb.find('m:calcPr',N)), 'nativePartKinds':collections.Counter()}
        for name in z.namelist():
            for prefix in ('xl/tables/','xl/drawings/','xl/charts/','xl/pivotTables/','xl/pivotCache/','xl/externalLinks/','xl/comments','xl/threadedComments/'):
                if name.startswith(prefix):out['nativePartKinds'][prefix]+=1
        for sheet in wb.find('m:sheets',N):
            target=relationships[sheet.attrib['{'+N['r']+'}id']]
            target=target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('xl',target))
            root=ET.fromstring(z.read(target));cells={}
            for c in root.findall('m:sheetData/m:row/m:c',N):
                t=c.get('t');f=c.find('m:f',N);v=c.find('m:v',N)
                if t=='s':value=strings[int(v.text)] if v is not None else None
                elif t=='inlineStr':value=''.join(c.find('m:is',N).itertext()) if c.find('m:is',N) is not None else None
                else:value=v.text if v is not None else None
                cells[c.get('r')]={'type':'text' if t in ('s','inlineStr') else t,'value':value,'formula':canonical(f),'style':style_semantics(int(c.get('s','0')))}
            sections={}
            for tag in ('dataValidations','mergeCells','autoFilter','tableParts','sheetProtection','sheetViews','cols','conditionalFormatting','drawing','legacyDrawing','extLst'):
                sections[tag]=[canonical(e) for e in root.findall('m:'+tag,N)]
            sections['rowAttributes']=[sorted(r.attrib.items()) for r in root.findall('m:sheetData/m:row',N)]
            out['sheets'].append({'name':sheet.get('name'),'state':sheet.get('state','visible'),'cells':cells,'sections':sections})
        out['nativePartKinds']=dict(out['nativePartKinds'])
        return out

if __name__=='__main__':
    before=read(sys.argv[1])
    if len(sys.argv)==2:
        print(json.dumps(before,ensure_ascii=False,indent=2));sys.exit()
    after=read(sys.argv[2]);plan=json.load(open(sys.argv[3])) if len(sys.argv)>3 else {'allowedCells':[]}
    allowed=set(plan['allowedCells']);issues=[]
    if [(s['name'],s['state']) for s in before['sheets']] != [(s['name'],s['state']) for s in after['sheets']]:issues.append('Sheet names/order/states changed')
    if before['definedNames'] != after['definedNames']:issues.append('Defined names changed')
    if before['calcPr'] != after['calcPr']:issues.append('Workbook calculation settings changed; inspect iteration and calculation mode')
    if before['nativePartKinds'] != after['nativePartKinds']:issues.append('Native workbook parts changed')
    for b,a in zip(before['sheets'],after['sheets']):
        for key,section in b['sections'].items():
            if section != a['sections'][key]:issues.append(f"{b['name']}: native section {key} changed; inspect semantics before upload")
        for cell in set(b['cells'])|set(a['cells']):
            bcell=b['cells'].get(cell);acell=a['cells'].get(cell)
            if f"{b['name']}!{cell}" not in allowed and bcell!=acell:issues.append(f"{b['name']}!{cell}: nonauthorized value/formula/style changed")
            if f"{b['name']}!{cell}" in allowed and bcell is not None and acell is not None and bcell['style']!=acell['style']:issues.append(f"{b['name']}!{cell}: authorized value patch changed cell style")
    print(json.dumps({'issues':issues,'pass':not issues,'allowed_cell_count':len(allowed)},ensure_ascii=False,indent=2))
    sys.exit(1 if issues else 0)
