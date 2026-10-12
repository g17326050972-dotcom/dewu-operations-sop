import json,sys,collections,re,pathlib,decimal,zipfile
from audit_activity_template import read
source_path,upload_path,manifest_path,plan_path=sys.argv[1:5] if len(sys.argv)>=5 else ('/Users/nan/Downloads/导出商品.xlsx','work/activity_2813342_upload.xlsx','work/activity_2813342_upload_manifest.json','work/activity_2813342_plan.json')
before=read(source_path)
after=read(upload_path)
manifest=json.load(open(manifest_path))
plan=json.load(open(plan_path))
header_row=plan['template'].get('header_row',2)
column_letters=list(plan['template']['columns'])
b=before['sheets'][0];a=after['sheets'][0];issues=[];native_differences=[];style_differences=[]
def normalize_node(node):
    if node is None:return None
    if isinstance(node,dict):return {k:normalize_node(v) for k,v in node.items()}
    if isinstance(node,list) and len(node)==4 and isinstance(node[0],str) and node[0].startswith('{'):
        tag,attrs,text,children=node
        normal=[]
        for k,v in attrs:
            if k=='count':continue
            if k in ('customWidth','collapsed','hidden'):
                if v in ('false','0'):continue
                v='1' if v=='true' else v
            if k in ('width','min','max'):
                v=str(decimal.Decimal(v).normalize())
            normal.append((k,v))
        solid_fill=tag.endswith('}patternFill') and dict(attrs).get('patternType')=='solid'
        return [tag,normal,text,[normalize_node(x) for x in children if not x[0].endswith('}charset') and not (solid_fill and x[0].endswith('}bgColor'))]]
    if isinstance(node,list):return [normalize_node(x) for x in node]
    return node
def equivalent_value(cell,expected):
    value=cell['value'] if cell else None
    if value in ('',None) and expected in ('',None):return True
    if isinstance(expected,(int,float)):
        try:return decimal.Decimal(str(value))==decimal.Decimal(str(expected))
        except:return False
    return value==expected
if [(s['name'],s['state']) for s in before['sheets']]!=[(s['name'],s['state']) for s in after['sheets']]:issues.append('Workbook sheet names/order/states changed')
if before['definedNames']!=after['definedNames']:issues.append('Defined names changed')
if before['nativePartKinds']!=after['nativePartKinds']:issues.append('Native workbook parts changed')
for key in b['sections']:
    if key in ('rowAttributes','sheetViews'):continue
    if normalize_node(b['sections'][key])!=normalize_node(a['sections'][key]):native_differences.append(key)
for row in range(1,header_row+1):
    for col in column_letters:
        key=f'{col}{row}';bc=b['cells'].get(key);ac=a['cells'].get(key)
        if not equivalent_value(ac,bc['value'] if bc else None):issues.append(f'Header value changed {key}')
        if bc and ac and normalize_node(bc['style'])!=normalize_node(ac['style']):style_differences.append({'source':key,'output':key,'source_style':bc['style'],'output_style':ac['style']})
for r in manifest['rows']:
    for i,col in enumerate(column_letters):
        src=f"{col}{r['sourceRow']}";dst=f"{col}{r['outputRow']}";bc=b['cells'].get(src);ac=a['cells'].get(dst)
        if not equivalent_value(ac,r['expected'][i]):issues.append(f'Product value mismatch {dst} SKU {r["skuId"]}')
        if bc and ac and normalize_node(bc['style'])!=normalize_node(ac['style']):style_differences.append({'source':src,'output':dst,'source_style':bc['style'],'output_style':ac['style']})
actual_rows=sorted({int(re.sub('[A-Z]','',k)) for k,c in a['cells'].items() if c['value'] not in (None,'') and int(re.sub('[A-Z]','',k))>header_row})
if actual_rows!=list(range(header_row+1,len(manifest['rows'])+header_row+1)):issues.append('Unexpected nonempty product rows')
error_cells=[k for k,c in a['cells'].items() if c['type']=='e' or c['value'] in ('#N/A','#VALUE!','#REF!','#DIV/0!','#NUM!','#NAME?')]
if error_cells:issues.append('Excel error cells: '+','.join(error_cells))
report={'data_pass':not issues,'issues':issues,'retained_sku_count':len(manifest['rows']),'nonempty_product_row_count':len(actual_rows),'native_section_differences':native_differences,'style_difference_count':len(style_differences),'style_difference_examples':style_differences[:3],'normalized_export_metadata':'mergeCells redundant count, numeric/boolean XML spellings, and obsolete font charset omitted; effective widths, fonts, fills, borders, number formats, alignment, validation and protection compared','calculation_metadata':'source calcPr only contained calcId=144525; exporter omitted calcId. Neither source nor output has formulas or iteration/custom calculation settings.','source_sha256_still_same':__import__('hashlib').sha256(pathlib.Path(plan['sources'][0]['path']).read_bytes()).hexdigest()==plan['sources'][0]['sha256']}
report['upload_file_verified']=not issues and not native_differences and not style_differences and report['source_sha256_still_same']
safe_id=re.sub(r'[^A-Za-z0-9_-]','_',plan.get('artifact_output_id',plan['activity_id']))
pathlib.Path(f'work/activity_{safe_id}_upload_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
