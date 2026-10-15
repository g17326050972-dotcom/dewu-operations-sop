# -*- coding: utf-8 -*-
from pathlib import Path
import json,re
O=Path('/Users/nan/Documents/Codex/2026-10-09/zai/outputs/2026-10-14')
def parse(p):
 out=[]
 for row in re.split(r'\n\s*\d+ row\n',p.read_text())[1:]:
  code=re.search(r'text 货号： (\S+)',row)
  if not code:continue
  cells=re.split(r'(?:^|\n)\s*\d+ 单元格[^\n]*\n',row)[1:]
  def n(i):
   m=re.search(r'\d+ (?:文本|text) ([\d,.]+)',cells[i]);return float(m[1].replace(',','')) if m else None
  out.append(dict(code=code[1],amount=n(1),conversionPct=n(2),orders=n(3),uv=n(4),favorites=n(5),observed=True))
 return out
for stem in ['2026-10-13_商品日数据','2026-09-30_10-06_商品区间数据']:
 r=parse(O/(stem+'原始.txt'))
 (O/(stem+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2))
 print(stem,len(r),r[:3])
