import sys,json,pathlib,openpyxl,warnings,zipfile
out=[]
for file in sys.argv[1:]:
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always')
        wb=openpyxl.load_workbook(file,read_only=True,data_only=False)
        sheets=[]
        for ws in wb:
            declared_dimension=ws.calculate_dimension()
            ws.reset_dimensions()
            rows=[]
            for rn,row in enumerate(ws.iter_rows(values_only=True),1):
                if any(v is not None for v in row):rows.append({'row':rn,'values':list(row)})
            sheets.append({'name':ws.title,'state':ws.sheet_state,'declared_dimension':declared_dimension,'dimensions':ws.calculate_dimension(force=True),'rows':rows})
        item={'path':file,'size':pathlib.Path(file).stat().st_size,'warnings':[str(n.message) for n in notices],'sheets':sheets}
        out.append(item)
pathlib.Path('work/activity_exports_raw.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str))
print(json.dumps([{'path':i['path'],'size':i['size'],'warnings':i['warnings'],'sheets':[{'name':s['name'],'state':s['state'],'dimensions':s['dimensions'],'nonempty_rows':len(s['rows']),'head':s['rows'][:8]} for s in i['sheets']]} for i in out],ensure_ascii=False,default=str))
