import json,collections,pathlib,hashlib,datetime
from decimal import Decimal,ROUND_DOWN

raw=json.load(open('work/activity_exports_raw.json'))
catalog=json.load(open('work/catalog_costs.json'))['by_article_no']
activity=raw[0]['sheets'][0]['rows'][2:]
bids=raw[1]['sheets'][0]['rows'][2:]
def number(x):
    try:return Decimal(str(x)) if x not in ('',None) else None
    except:return None
def ident(x):
    d=number(x)
    return str(int(d)) if d is not None and d==int(d) else str(x)
def encode(x):
    if isinstance(x,Decimal):return int(x) if x==int(x) else float(x)
    raise TypeError(str(type(x)))
bid_by_sku=collections.defaultdict(list)
for row in bids:
    v=row['values']
    if len(v)>34 and v[34]=='品牌官方':bid_by_sku[ident(v[6])].append(row)
decisions=[];unmatched=set(catalog);anomalies=[];comparison=[]
for row in activity:
    v=row['values'];article=str(v[2]).strip().upper()
    if article not in catalog:continue
    unmatched.discard(article);c=catalog[article];sku=ident(v[7]);spu=ident(v[0]);reasons=[]
    matching_bids=bid_by_sku.get(sku,[])
    actual_prices=sorted(set(number(r['values'][15]) for r in matching_bids if number(r['values'][15]) is not None))
    base_price=min(actual_prices) if actual_prices else number(v[12])
    activity_min_bid=number(v[12]);limit_candidates=[number(v[9]),number(v[14])]
    limits=[x for x in limit_candidates if x is not None and x>0]
    maxprice=min(limits) if limits else None
    mindiscount_price=number(v[15])
    styles=str(v[6] or '');gift='钟意一生' in styles or '炽热挚爱' in styles or '炽烈挚爱' in styles
    combo='小米珠' in styles
    cost=Decimal(str(c['product_cost']));giftcost=Decimal('13') if gift else Decimal('0')
    discount=Decimal(str(c['configured_discount']))
    if '品牌官方' not in str(v[5]).split(','):reasons.append('brand_official_channel_unavailable')
    if base_price is None or base_price<=0:reasons.append('missing_current_bid')
    if maxprice is None:reasons.append('missing_platform_price_requirement')
    if not matching_bids:reasons.append('no_brand_official_bid_record')
    states=sorted(set(str(r['values'][18]) for r in matching_bids))
    stock_values=[number(r['values'][17]) for r in matching_bids]
    has_stock=any(x is not None and x>0 for x in stock_values)
    has_active=any(r['values'][18]=='售卖中' for r in matching_bids)
    if matching_bids and not has_active:reasons.append('no_selling_bid')
    if matching_bids and not has_stock:reasons.append('sold_out_or_stock_unavailable')
    if combo:reasons.append('excluded_pearl_combo_per_user')
    if len(actual_prices)>1:anomalies.append({'sku_id':sku,'article_no':article,'issue':'multiple_current_bid_prices','prices':actual_prices})
    if activity_min_bid is not None and actual_prices and activity_min_bid!=min(actual_prices):anomalies.append({'sku_id':sku,'article_no':article,'issue':'activity_min_bid_vs_current_export_differ','activity_min_bid':activity_min_bid,'current_prices':actual_prices})
    configured_price=(base_price*discount/10).quantize(Decimal('.01'),rounding=ROUND_DOWN) if base_price else None
    lower_required=configured_price is not None and maxprice is not None and configured_price>maxprice
    proposed_price=min(configured_price,maxprice).quantize(Decimal('.01'),rounding=ROUND_DOWN) if configured_price is not None and maxprice is not None else None
    platformfee=max(proposed_price*Decimal('.22'),Decimal('45')) if proposed_price else None
    extra10=proposed_price*Decimal('.10') if proposed_price else None
    profit=proposed_price-platformfee-Decimal('14.5')-extra10-cost-giftcost if proposed_price else None
    margin=profit/proposed_price if proposed_price else None
    if lower_required and (margin is None or margin<=Decimal('.03')):reasons.append('platform_required_margin_not_above_3pct')
    if mindiscount_price is not None and proposed_price is not None and proposed_price<mindiscount_price:reasons.append('below_platform_minimum_price')
    status='ready' if not reasons else 'hold'
    d={'source_row':row['row'],'sheet':'Sheet1','spu_id':spu,'sku_id':sku,'article_no':article,'product_name':v[1],'style':styles,'channel':'品牌官方','stock_entry':'不限制','current_bid':base_price,'current_bid_source':'brand-official current bid export' if actual_prices else 'activity template M (excludes promotion price)','current_bid_export_rows':[r['row'] for r in matching_bids],'current_bid_prices':actual_prices,'current_bid_states':states,'has_positive_current_stock':has_stock,'platform_max_price':maxprice,'platform_min_price':mindiscount_price,'configured_discount':discount,'configured_discount_price':configured_price,'platform_requires_lower_discount':lower_required,'proposed_price':proposed_price,'effective_discount':proposed_price/base_price*10 if proposed_price and base_price else None,'product_cost':cost,'extra_giftbox_cost':giftcost,'platform_fee':platformfee,'fulfillment_cost':Decimal('14.5'),'activity_ten_percent_deduction':extra10,'activity_profit':profit,'activity_margin':margin,'cost_is_lower_bound_due_to_unconfirmed_combo':combo,'status':status,'hold_reasons':reasons,'catalog_row':c['row'],'catalog_cost_from_external_cache':'G' in c['formulas'],'original_template_values':v}
    decisions.append(d)
    if ('品牌礼盒' in styles or '礼盒:' not in styles) and not combo:
        comparison.append({'article_no':article,'sku_id':sku,'current_bid':base_price,'catalog_original_bid_D':c['bid_price'],'catalog_discounted_price_F':c['current_take_home_price'],'configured_discount':discount})
ready=[r for r in decisions if r['status']=='ready'];holds=[r for r in decisions if r['status']!='ready']
plan={'activity_id':'2813342','activity_name':'新人折扣','sources':[{'path':r['path'],'size':r['size'],'sha256':hashlib.sha256(pathlib.Path(r['path']).read_bytes()).hexdigest()} for r in raw],'template':{'sheet':'Sheet1','instruction_row':1,'header_row':2,'columns':dict(zip('ABCDEFGHIJKLMNOPQ',raw[0]['sheets'][0]['rows'][1]['values'])),'input_columns':{'F':'适用渠道=品牌官方','I':'商品报名价','K':'活动库存=不限制'},'reported_dimension_was_wrong':'A1:R2','actual_dimension':'A1:Q1985','preserve_instruction_header_and_columns':True},'pricing_evidence':{'activity_M_label':'我的最低出价(不包含促销价)','current_export_P_label':'当前出价','comparison':comparison,'conclusion':'For every matched SKU, activity M agrees with the minimum current brand-official bid; current bid corresponds to the raw original bid rather than catalog discounted F, so apply catalog E once to current per-SKU bid.'},'rules':{'match':'Exact article number after uppercase/whitespace normalization; only official-brand channel','discount':'Use per-SKU current bid * catalog E/10; if greater than platform max use platform max and require activity margin strictly above 3%.','margin':'price - MAX(price*22%,45) - 14.5 - price*10% - product_cost - upgraded_giftbox_cost','giftbox':'钟意一生/炽热挚爱/炽烈挚爱 cost +13; brand box no +13','price_rounding':'down to two decimal places, then calculate actual profit','unknown_variant_cost':'Hold extra pearl combinations pending cost; their shown profit is only an upper bound','inventory':'不限制; does not lock inventory'},'summary':{'all_export_sku_count':len(activity),'all_export_spu_count':len(set(ident(r['values'][0]) for r in activity)),'catalog_count':len(catalog),'matched_sku_count':len(decisions),'matched_article_count':len(set(r['article_no'] for r in decisions)),'ready_sku_count':len(ready),'ready_spu_count':len(set(r['spu_id'] for r in ready)),'ready_article_count':len(set(r['article_no'] for r in ready)),'held_sku_count':len(holds),'held_reasons':dict(collections.Counter(x for r in holds for x in r['hold_reasons'])),'ready_using_configured_discount':sum(not r['platform_requires_lower_discount'] for r in ready),'ready_using_platform_max':sum(r['platform_requires_lower_discount'] for r in ready),'minimum_ready_margin':min(r['activity_margin'] for r in ready),'minimum_ready_margin_sku':min(ready,key=lambda r:r['activity_margin'])['sku_id'],'unmatched_catalog_article_count':len(unmatched)},'anomalies':anomalies,'unmatched_catalog_articles':sorted(unmatched),'decisions':decisions,'ready':ready,'hold':holds,'baselineVisualReviewed':True,'generated_upload':None}
excluded=[r for r in plan['hold'] if r['hold_reasons']==['excluded_pearl_combo_per_user']]
for r in excluded:r['status']='excluded'
plan['excluded']=excluded
plan['hold']=[r for r in plan['hold'] if r not in excluded]
plan['summary']['excluded_sku_count']=len(excluded)
plan['summary']['held_sku_count']=len(plan['hold'])
plan['summary']['held_reasons']=dict(collections.Counter(x for r in plan['hold'] for x in r['hold_reasons']))
plan['rules'].pop('unknown_variant_cost',None)
plan['rules']['excluded_combinations']='User explicitly excludes every extra-pearl set/combination SKU; retain the same article basic SKU.'
upload=pathlib.Path('work/activity_2813342_upload.xlsx')
audit=pathlib.Path('work/activity_2813342_upload_audit.json')
if upload.exists() and audit.exists():
    audit_result=json.loads(audit.read_text())
    if audit_result.get('upload_file_verified'):
        plan['generated_upload']={'path':str(upload.resolve()),'sha256':hashlib.sha256(upload.read_bytes()).hexdigest(),'audit_path':str(audit.resolve()),'verified':True}
pathlib.Path('work/activity_2813342_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2,default=encode))
print(json.dumps({'summary':plan['summary'],'anomalies':anomalies,'lowest_margins':sorted([{'article_no':r['article_no'],'sku_id':r['sku_id'],'style':r['style'],'price':r['proposed_price'],'profit':r['activity_profit'],'margin':r['activity_margin'],'lower_required':r['platform_requires_lower_discount']} for r in ready],key=lambda x:x['margin'])[:8],'hold':[{'source_row':r['source_row'],'article_no':r['article_no'],'sku_id':r['sku_id'],'style':r['style'],'reasons':r['hold_reasons']} for r in holds]},ensure_ascii=False,default=encode))
