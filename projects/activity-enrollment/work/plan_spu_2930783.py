"""Read-only source analysis for SPU-level discounts; writes JSON, never XLSX."""
import collections,hashlib,json,pathlib,sys,warnings
from decimal import Decimal as D
import openpyxl
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import plan_activity as p

warnings.simplefilter('ignore')
source=pathlib.Path('/Users/nan/Downloads/导出.xlsx')
bid_source=pathlib.Path('/Users/nan/Downloads/出价列表导出（品牌直发）（仅可使用一次）.xlsx')
catalog=json.load(open('work/catalog_costs.json'))['by_article_no']
discounts={'YX9638001':8,'YX9545001':8,'YX9611001':7,'YX9615001':7,'YX9341001':9}
wb=openpyxl.load_workbook(source,read_only=True,data_only=True)
ws=wb.worksheets[0];ws.reset_dimensions();raw=list(ws.iter_rows(values_only=True));headers=raw[1]
matches={str(r[2]).strip().upper():{'source_row':i,'spu_id':p.ident(r[0]),'original_template_values':list(r)} for i,r in enumerate(raw,1) if i>2 and str(r[2]).strip().upper() in catalog}
bid=p.read_table(bid_source,'bid');bm=bid['column_map'];bid_by_sku=collections.defaultdict(list)
for row in bid['rows']:
    if p.get(row['values'],bm,'bid_channel')=='品牌官方':bid_by_sku[p.ident(p.get(row['values'],bm,'sku_id'))].append(row)
prior=json.load(open('work/activity_C3054763_plan.json'))
known_skus={r['sku_id']:r for r in prior['decisions'] if r['article_no'] in discounts}
readback_evidence=collections.defaultdict(list)
for filename in ('work/newcomer_readback_audit.json','work/C3054763_readback_audit.json'):
    audit=json.load(open(filename))
    for values in audit['rows']:
        record=dict(zip(audit['row_columns'],values));sku=record['sku_id'];a=record['article_no']
        if a not in discounts:continue
        readback_evidence[sku].append({'activity_id':audit['activity_id'],'status':record['status'],'registered_price':record['actual_price'],'price_type':'existing activity price, never infer original bid from this'})
        if sku not in known_skus:
            style=next((r['style'] for r in audit.get('existing_outside_upload',[]) if r['sku_id']==sku),None)
            known_skus[sku]={'sku_id':sku,'article_no':a,'style':style,'extra_giftbox_cost':13 if style and any(v in style for v in ('钟意一生','炽热挚爱','炽烈挚爱')) else 0}
spus=[]
for article,fold in discounts.items():
    c=catalog[article];skus=[]
    for sku,old in sorted(known_skus.items()):
        if old['article_no']!=article:continue
        rows=bid_by_sku.get(sku,[]);prices=sorted({v for r in rows if (v:=p.number(p.get(r['values'],bm,'current_bid'))) is not None and v>0})
        price=prices[0] if prices else None;gift=D(str(old.get('extra_giftbox_cost',0)))
        computed=p.pricing(price,D(fold),D('999999'),D(str(c['product_cost'])),gift,price_decimals=0) if price is not None else {}
        skus.append({'sku_id':sku,'style':old.get('style'),'original_brand_official_bid':price,'bid_rows':[r['row'] for r in rows],'bid_prices':prices,'bid_states':sorted({str(p.get(r['values'],bm,'bid_state','')) for r in rows}),'product_cost':c['product_cost'],'extra_giftbox_cost':gift,'proposed_spu_discount':fold,'status':'known_active_bid_passes_margin' if computed.get('passes_user_margin_gate') else 'hold_missing_current_official_bid' if price is None else 'hold_margin','existing_activity_price_evidence':readback_evidence[sku],**computed})
    complete=bool(skus) and all(r['status']=='known_active_bid_passes_margin' for r in skus)
    spus.append({'article_no':article,**matches[article],'configured_discount_E':c['configured_discount'],'proposed_discount_input':fold,'discount_input_is_plain_number':True,'platform_discount_min':1,'platform_discount_max':9,'channel_input':'品牌官方','activity_stock_input':'不限制','product_cost':c['product_cost'],'known_sku_count':len(skus),'known_current_bid_sku_count':sum(bool(r['bid_rows']) for r in skus),'all_known_skus_current_bid_complete':complete,'minimum_margin_among_known_bid_skus':min((r['activity_margin'] for r in skus if 'activity_margin' in r),default=None),'minimum_margin_for_all_skus':min((r['activity_margin'] for r in skus),default=None) if complete else None,'status':'fully_measured_candidate' if complete else 'hold_incomplete_spu_bid_evidence','skus':skus})
out={'activity_id':'2930783','main_id':'5733','activity_name':'随心省会员专属折扣','source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_actual_spu_count':len(raw)-2,'matched_catalog_spu_count':len(matches),'source_headers':headers,'source_instruction':raw[0][0],'bid_source':str(bid_source),'bid_source_sha256':bid['sha256'],'discount_rule':'Whole SPU 1.0 to9.0; plain numeric input, at most one decimal. Prices below are conservative whole-RMB floor estimates, not registration-price inputs.','cost_rule':'floor(original bid * SPU discount/10) -max(price*.22,45)-14.5-price*.10-product_cost-upgraded giftbox13','additional_activity_deduction':0,'fee_caveat':'Source10pct remains included; no assumption it fully covers actual coupons. Parent UI confirms no extra full reduction for these non-Moon articles.','upload_created':False,'candidates':spus,'excluded':[{'article_no':'YX9339001','spu_id':matches['YX9339001']['spu_id'],'reason':'SPU-level discount includes pearl combination; exclude entire SPU per parent task.'}],'hold':[{'article_no':'YX9354001','spu_id':matches['YX9354001']['spu_id'],'reason':'Moon requires per-activity user confirmation of activity and backend estimated take-home price.'}],'checks':{'exactly_5_requested_spus':len(spus)==5,'all_discounts_within_platform_1_to_9':all(1<=r['proposed_discount_input']<=9 for r in spus),'all_measurable_sku_margins_above_3pct':all(r['activity_margin']>D('.03') for s in spus for r in s['skus'] if 'activity_margin' in r),'moon_absent_from_candidates':all(r['article_no']!='YX9354001' for r in spus),'pearl_spu_absent_from_candidates':all(r['article_no']!='YX9339001' for r in spus)}}
assert all(out['checks'].values())
pathlib.Path('work/activity_2930783_spu_plan.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=p.encode))
print(json.dumps({'summary':[{k:s[k] for k in ('article_no','spu_id','source_row','proposed_discount_input','status','minimum_margin_among_known_bid_skus','minimum_margin_for_all_skus')} for s in spus],'sku_detail':[{k:r.get(k) for k in ('sku_id','style','original_brand_official_bid','proposed_spu_discount','proposed_price','activity_profit','activity_margin','status')} for s in spus for r in s['skus']],'checks':out['checks']},ensure_ascii=False,indent=2,default=p.encode))
wb.close()
