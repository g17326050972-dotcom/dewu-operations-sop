import json
from pathlib import Path

root = Path('/Users/nan/Documents/Codex/2026-10-09/zai')
codes = ['YH9378001','YH9379001','YH9380001','YS407600A','YS9363001','YS9366001','YS9367001','YS9369001','YS9371001','YS9372001','YS9543001','YX243800A','YX243900A','YX9337001','YX9338001','YX9339001','YX9340001','YX9341001','YX9342001','YX9343001','YX9344001','YX9345001','YX9346001','YX9348001','YX9349001','YX9350001','YX9351001','YX9352001','YX9354001','YX9355001','YX9499001','YX9501001','YX9520001','YX9523001','YX9524001','YX9529001','YX9538001','YX9545001','YX9611001','YX9615001','YX9617001','YX9638001','YX9640001','YX9640002','YX9648001','YX9648002']
# Each omitted row in these compact observations was explicitly read as five
# zeros in the corresponding UI page. They are observed zeros, not imputation.
# Values: code, UV, payment orders, favorite users, backend conversion %, amount.
days = {
'2026-10-02': [
['YH9378001',1,0,0,0,0],['YH9380001',1,0,0,0,0],['YX243800A',5,0,0,0,0],['YX243900A',10,0,1,0,0],['YX9339001',3,0,0,0,0],['YX9340001',1,0,0,0,0],['YX9341001',2,0,0,0,0],['YX9352001',1,0,1,0,0],['YX9354001',597,4,40,.67,958],['YX9499001',1,0,0,0,0],['YX9501001',3,0,0,0,0],['YX9520001',1,0,0,0,0],['YX9523001',1,0,0,0,0],['YX9524001',5,0,0,0,0],['YX9545001',8,0,0,0,0],['YX9611001',5,0,0,0,0],['YX9615001',125,0,12,0,0],['YX9617001',2,0,0,0,0],['YX9638001',8,0,1,0,0],['YX9640001',60,0,2,0,0],['YX9640002',43,0,3,0,0],['YX9648001',1,0,0,0,0]],
'2026-10-03': [
['YS407600A',1,0,0,0,0],['YX243800A',5,0,1,0,0],['YX243900A',4,0,0,0,0],['YX9337001',2,0,0,0,0],['YX9338001',1,0,0,0,0],['YX9339001',3,0,0,0,0],['YX9340001',1,0,0,0,0],['YX9341001',1,0,0,0,0],['YX9344001',1,0,0,0,0],['YX9354001',316,5,27,1.27,1210],['YX9355001',1,0,0,0,0],['YX9501001',2,0,0,0,0],['YX9523001',3,0,0,0,0],['YX9524001',4,0,0,0,0],['YX9545001',8,0,1,0,0],['YX9611001',2,0,0,0,0],['YX9615001',162,0,7,0,0],['YX9638001',6,0,0,0,0],['YX9640001',44,0,0,0,0],['YX9640002',42,0,3,0,0]],
'2026-10-04': [
['YS407600A',2,0,0,0,0],['YX243800A',5,0,0,0,0],['YX243900A',7,0,0,0,0],['YX9339001',5,0,0,0,0],['YX9341001',1,0,0,0,0],['YX9348001',1,0,0,0,0],['YX9354001',248,4,14,1.61,975],['YX9499001',1,0,0,0,0],['YX9501001',4,0,0,0,0],['YX9523001',1,0,0,0,0],['YX9524001',6,0,1,0,0],['YX9545001',7,0,0,0,0],['YX9611001',10,0,0,0,0],['YX9615001',212,0,12,0,0],['YX9617001',1,0,0,0,0],['YX9638001',4,0,1,0,0],['YX9640001',42,0,3,0,0],['YX9640002',38,0,5,0,0],['YX9648001',1,0,0,0,0]],
'2026-10-05': [
['YX9640002',24,0,3,0,0],['YX9640001',32,0,2,0,0],['YX9638001',6,0,0,0,0],['YX9545001',3,0,0,0,0],['YS407600A',1,0,0,0,0],['YX243900A',6,0,0,0,0],['YX9617001',1,0,0,0,0],['YX9611001',3,0,0,0,0],['YX9615001',184,0,9,0,0],['YX9524001',3,0,0,0,0],['YX9345001',1,0,0,0,0],['YX9338001',2,0,0,0,0],['YX9340001',1,0,0,0,0],['YX9341001',3,0,0,0,0],['YX243800A',7,1,0,14.29,399],['YX9339001',4,1,0,25,299],['YX9354001',262,5,17,1.91,1252]],
'2026-10-06': [
['YX9640002',7,0,0,0,0],['YX9640001',4,0,0,0,0],['YX9638001',5,0,0,0,0],['YX9648001',1,0,0,0,0],['YX9499001',2,0,0,0,0],['YX9545001',12,0,0,0,0],['YX9501001',3,0,1,0,0],['YS407600A',3,0,0,0,0],['YX243800A',7,0,0,0,0],['YX243900A',9,0,0,0,0],['YX9617001',2,0,0,0,0],['YX9611001',3,0,0,0,0],['YX9523001',2,0,0,0,0],['YX9524001',5,0,0,0,0],['YX9345001',1,0,0,0,0],['YX9343001',2,0,0,0,0],['YX9342001',2,0,0,0,0],['YX9339001',6,0,0,0,0],['YX9337001',1,0,0,0,0],['YX9340001',2,0,1,0,0],['YX9341001',2,0,0,0,0],['YX9615001',265,1,19,.38,209],['YX9354001',251,2,18,.8,479]],
'2026-10-07': [
['YH9380001',1,0,0,0,0],['YS9543001',1,0,0,0,0],['YX243800A',7,0,0,0,0],['YX243900A',6,0,0,0,0],['YX9337001',1,0,0,0,0],['YX9338001',2,0,0,0,0],['YX9339001',2,0,0,0,0],['YX9341001',2,0,0,0,0],['YX9343001',1,0,0,0,0],['YX9345001',1,0,0,0,0],['YX9354001',272,4,21,1.47,1059],['YX9501001',3,0,0,0,0],['YX9523001',3,0,0,0,0],['YX9524001',5,0,1,0,0],['YX9529001',1,0,0,0,0],['YX9545001',7,0,0,0,0],['YX9611001',4,0,0,0,0],['YX9615001',280,1,21,.36,179],['YX9617001',1,0,0,0,0],['YX9638001',4,0,0,0,0],['YX9640001',6,0,0,0,0],['YX9640002',3,0,0,0,0],['YX9648001',1,0,0,0,0]]
}
previous=json.loads((root/'work/retry_metrics.json').read_text())
assert set(codes)=={row[0] for row in previous['rows']}
records=[]
raw_days={}
for date, nonzero in days.items():
    lookup={r[0]:r[1:] for r in nonzero}
    assert len(lookup)==len(nonzero) and set(lookup)<=set(codes)
    raw_days[date]={'source':'得物商品分析，原生UI逐页主值读数；5页，10+10+10+10+6条。', 'observed_zero_codes':[c for c in codes if c not in lookup], 'nonzero_primary_values':nonzero}
    for code in codes:
        uv,orders,favorites,conversion,amount=lookup.get(code,[0,0,0,0,0])
        records.append(dict(date=date,code=code,uv=uv,orders=orders,favorites=favorites,conversionPct=conversion,amount=amount))
for code,name,isnew,bid,week,day in previous['rows']:
    records.append(dict(date='2026-10-08',code=code,uv=day[6],orders=day[4],favorites=day[7],conversionPct=day[3],amount=day[0]))
records.sort(key=lambda r:(r['date'],r['code']))
assert len(records)==322 and len({(r['date'],r['code']) for r in records})==322
checks=[]
for code,name,isnew,bid,week,day in previous['rows']:
    rows=[r for r in records if r['code']==code]
    order_sum=sum(r['orders'] for r in rows)
    amount_sum=sum(r['amount'] for r in rows)
    assert order_sum==week[4],(code,'orders',order_sum,week[4])
    assert abs(amount_sum-week[0])<.01,(code,'amount',amount_sum,week[0])
    checks.append({'code':code,'payment_orders_sum':order_sum,'backend_week_orders':week[4],'amount_sum':amount_sum,'backend_week_amount':week[0]})
out={'period':['2026-10-02','2026-10-08'],'category':'流行饰品/眼镜/服配','collected_date':'2026-10-09','source':previous['source'],'coverage':'7个完整日 × 46款 = 322条；每日46个唯一货号，缺失0条。10月2—7日为本轮UI原始主值读数，10月8日为重试底表已核验读数。','notes':['支付订单数不同于销量；头部名单沿用后台近7天我的销量排序。','后台商详转化保持原值，未改为订单数/访客；收藏率为同日收藏用户数/商详访问人数。','真实首次上架日期尚未核验，后台新品标签仅作为观察名单。','零值全部为明确读取的真实0，未对缺失值填0。','7日订单数及支付金额逐款加总与后台7日同口径值全部一致；不把多日UV加总解释为去重UV。'],'records':records,'reconciliation':checks}
(root/'work/daily_trend.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
raw={'category':out['category'],'collected_date':out['collected_date'],'fields':['code','uv','orders','favorites','conversionPct','amount'],'days':raw_days,'2026-10-08_source':'页面原始读数_重试.json','zero_note':'observed_zero_codes 中的货号在该日期五项主值均明确为0；这不是缺失补零。'}
(root/'outputs/2026-10-08/逐日原始读数.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2))
(root/'outputs/2026-10-08/逐日整理数据.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({'rows':len(records),'days':7,'products':46,'orders_amount_reconciliation':'all 46 passed','core':{c:[r for r in records if r['code']==c] for c in ['YX9354001','YX9615001']}},ensure_ascii=False))
