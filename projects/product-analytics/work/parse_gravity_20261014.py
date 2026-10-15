# -*- coding: utf-8 -*-
from pathlib import Path
import re,json
O=Path('/Users/nan/Documents/Codex/2026-10-09/zai/outputs/2026-10-14')
old=json.loads((O.parent/'2026-10-13/引力内容新增读数.json').read_text())
mp={'曝光量':'exposure','阅读量':'reads','互动量':'interactions','商详访问量':'detail_visits','引导商品收藏数':'favorites','14日归因订单数':'attributed_orders_14d'}
n={'contents':{},'daily':[]}
for f in sorted(O.glob('引力_*_2026-10-13日值.txt')):
 cid=f.name.split('_')[1]; st=f.read_text(); part=st[st.index('流量走势'):st.index('流量场域分析')]
 vals={key:[int(x.replace(',','')) for x in re.findall(label+r' ([\d,]+)',part)] for label,key in mp.items()}
 assert all(len(v)==2 for v in vals.values()),(cid,vals)
 meta=old['contents'][cid].copy();detail=(O/('引力_'+cid+'_详情.txt')).read_text()
 meta.update(published_at=re.search(r'发布时间 (\d{4}-[^\n]+)',detail)[1],as_of=re.search(r'数据截止至(\d{4}-[^\n]+)',detail)[1],chart_cumulative={k:v[1] for k,v in vals.items()})
 n['contents'][cid]=meta;n['daily'].append(dict(content_id=cid,code=meta['code'],task_id=meta['task_id'],date='2026-10-13',**{k:v[0] for k,v in vals.items()}))
(O/'引力内容新增读数.json').write_text(json.dumps(n,ensure_ascii=False,indent=2));print(n['daily'])
