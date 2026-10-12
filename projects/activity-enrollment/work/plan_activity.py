"""Read-only Dewu activity planning. Reads XLSX and writes JSON; never authors XLSX."""
from __future__ import annotations
import argparse,collections,hashlib,json,pathlib,re,warnings
from decimal import Decimal,ROUND_DOWN
import openpyxl

D=Decimal
ALIASES={
 'spu_id':['SPUID','商品id（spuid）','商品ID(SPUID)'],
 'sku_id':['SKUID','商品skuId','商品SKU ID'],
 'article_no':['货号','商品货号'],
 'product_name':['商品名称','商品名'],
 'channels':['适用渠道','销售渠道','购买渠道'],
 'style':['款式','商品规格','规格'],
 'registration_price':['商品报名价','活动报名价','报名价格','报名价'],
 'stock_entry':['活动库存','报名库存'],
 'stock_requirement':['活动库存要求','报名库存要求'],
 'activity_min_bid':['我的最低出价(不包含促销价)','我的最低出价（不包含促销价）','我的最低出价','我的出价','当前出价'],
 'registration_state':['报名状态','活动报名状态','当前报名状态'],
 'current_bid':['当前出价','我的出价','出价'],
 'current_stock':['当前库存','可售库存'],
 'bid_state':['出价状态','售卖状态'],
 'bid_channel':['购买渠道','销售渠道','适用渠道'],
 'failure_reason':['失败原因','错误原因'],
}
MAX_ALIASES=['报名价要求（要求小于等于如下价格）','需小于等于','最高报名价','活动最高价','报名价上限']
MIN_ALIASES=['需大于等于','最低报名价','报名价下限']
def normalize(s):return re.sub(r'\s+','',str(s or '')).replace('（','(').replace('）',')').upper()
def number(x):
    try:
        value=D(str(x)) if x not in ('',None) else None
        return value if value is not None and value.is_finite() else None
    except:return None
def ident(x):
    v=number(x)
    return str(int(v)) if v is not None and v.is_finite() and v==int(v) else str(x or '').strip()
def encode(x):
    if isinstance(x,D):return int(x) if x==int(x) else float(x)
    raise TypeError(str(type(x)))
def column_letter(index):
    answer='';n=index+1
    while n:n,r=divmod(n-1,26);answer=chr(65+r)+answer
    return answer
def header_map(values):
    normalized=[normalize(v) for v in values];mapping={}
    for key,aliases in ALIASES.items():
        hits=[i for i,v in enumerate(normalized) if v in {normalize(a) for a in aliases}]
        if hits:mapping[key]=hits[0]
    maxnames={normalize(v) for v in MAX_ALIASES};minnames={normalize(v) for v in MIN_ALIASES}
    mapping['max_price_columns']=[i for i,v in enumerate(normalized) if v in maxnames or ('报名价要求' in v and '小于等于' in v)]
    mapping['min_price_columns']=[i for i,v in enumerate(normalized) if v in minnames]
    return mapping
def read_table(file,kind='activity',sheet_name=None):
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always')
        wb=openpyxl.load_workbook(file,read_only=True,data_only=False)
        candidates=[]
        for sheet in wb:
            if sheet_name and sheet.title!=sheet_name:continue
            declared=sheet.calculate_dimension();sheet.reset_dimensions()
            rows=[{'row':i,'values':list(values)} for i,values in enumerate(sheet.iter_rows(values_only=True),1) if any(v is not None for v in values)]
            for row in rows[:20]:
                mapping=header_map(row['values'])
                required={'sku_id','article_no'} if kind!='activity' else {'spu_id','sku_id','article_no','registration_price'}
                if not required.issubset(mapping):continue
                score=len(mapping)+(5 if kind=='bid' and 'current_bid' in mapping else 0)
                candidates.append((score,sheet.title,declared,rows,row,mapping))
        if not candidates:raise ValueError(f'No recognizable {kind} header in {file}')
        _,name,declared,rows,header,mapping=max(candidates,key=lambda c:c[0])
        data=[r for r in rows if r['row']>header['row'] and ident(get(r['values'],mapping,'sku_id'))]
        return {'path':str(pathlib.Path(file).resolve()),'size':pathlib.Path(file).stat().st_size,'sha256':hashlib.sha256(pathlib.Path(file).read_bytes()).hexdigest(),'sheet':name,'declared_dimension':declared,'header_row':header['row'],'headers':header['values'],'column_map':mapping,'instruction_rows':[r for r in rows if r['row']<header['row']],'rows':data,'warnings':sorted(set(str(n.message) for n in notices))}
def get(values,mapping,key,default=None):
    index=mapping.get(key)
    return values[index] if index is not None and index<len(values) else default
def cell(values,index):return values[index] if index<len(values) else None
def pricing(bid,discount,ceiling,cost,gift_cost=D('0'),extra_rate=D('0'),extra_fixed=D('0'),price_decimals=2):
    quantum=D(1).scaleb(-price_decimals)
    configured=(bid*discount/10).quantize(quantum,rounding=ROUND_DOWN)
    lower=configured>ceiling
    price=min(configured,ceiling).quantize(quantum,rounding=ROUND_DOWN)
    if price<=0:raise ValueError('Rounded registration price must be positive.')
    fee=max(price*D('.22'),D('45'))
    standard_extra=price*D('.10');additional=price*extra_rate+extra_fixed
    profit=price-fee-D('14.5')-standard_extra-cost-gift_cost-additional
    margin=profit/price
    return {'configured_discount_unrounded':bid*discount/10,'configured_discount_price':configured,'platform_requires_lower_discount':lower,'proposed_price':price,'effective_discount':price/bid*10,'platform_fee':fee,'fulfillment_cost':D('14.5'),'activity_ten_percent_deduction':standard_extra,'additional_activity_deduction':additional,'activity_profit':profit,'activity_margin':margin,'passes_user_margin_gate':margin>D('.03')}
def plan(args):
    catalog_path=pathlib.Path(args.catalog_index)
    catalog=json.loads(catalog_path.read_text())['by_article_no']
    catalog={k.strip().upper():v for k,v in catalog.items()}
    activity=read_table(args.source,'activity',args.sheet)
    bids=read_table(args.bid_source,'bid',args.bid_sheet) if args.bid_source else None
    bid_by_sku=collections.defaultdict(list)
    if bids:
        for row in bids['rows']:
            ch=str(get(row['values'],bids['column_map'],'bid_channel',''))
            if ch=='品牌官方':bid_by_sku[ident(get(row['values'],bids['column_map'],'sku_id'))].append(row)
    already={ident(x) for x in args.already_registered_sku}
    registered_log=None
    if args.already_registered_log:
        registered_log=read_table(args.already_registered_log,'failure')
        for row in registered_log['rows']:
            reason=str(get(row['values'],registered_log['column_map'],'failure_reason',''))
            if '已报入当前活动' in reason or '重复报名' in reason:already.add(ident(get(row['values'],registered_log['column_map'],'sku_id')))
    extra_rate=D(args.extra_rate);extra_fixed=D(args.extra_fixed)
    if not extra_rate.is_finite() or not extra_fixed.is_finite() or extra_rate<0 or extra_fixed<0:raise ValueError('Extra deductions must be finite and nonnegative.')
    if not 0<=args.price_decimals<=4:raise ValueError('price-decimals must be between 0 and 4.')
    excluded_activity=bool('疯狂' in args.activity_name and ('周末' in args.activity_name or '折扣' in args.activity_name))
    confirmation_articles={str(v).strip().upper() for v in getattr(args,'require_confirmation_article',['YX9354001'])}
    decisions=[];anomalies=[];unmatched=set(catalog);m=activity['column_map'];seen_skus=set();prices_compared=0;prices_agree=0
    for row in activity['rows']:
        values=row['values'];article=str(get(values,m,'article_no','')).strip().upper()
        if article not in catalog:continue
        unmatched.discard(article);c=catalog[article];sku=ident(get(values,m,'sku_id'));spu=ident(get(values,m,'spu_id'));reasons=[];excluded=[];notes=[]
        if sku in seen_skus:reasons.append('duplicate_sku_in_export')
        seen_skus.add(sku)
        matches=bid_by_sku.get(sku,[]);bm=bids['column_map'] if bids else {}
        current_prices=sorted({p for r in matches if (p:=number(get(r['values'],bm,'current_bid'))) is not None and p>0})
        template_bid=number(get(values,m,'activity_min_bid'));bid=min(current_prices) if current_prices else template_bid
        upper=[p for i in m['max_price_columns'] if (p:=number(cell(values,i))) is not None and p>0]
        lower=[p for i in m['min_price_columns'] if (p:=number(cell(values,i))) is not None]
        ceiling=min(upper) if upper else None;floor=max(lower) if lower else None
        style=str(get(values,m,'style','') or '')
        gift=any(x in style for x in ('钟意一生','炽热挚爱','炽烈挚爱'))
        combo='小米珠' in style
        channels=str(get(values,m,'channels','') or '')
        if '品牌官方' not in re.split('[,，、;；]',channels):reasons.append('brand_official_channel_unavailable')
        if not style:reasons.append('missing_variant_description')
        if bid is None or bid<=0:reasons.append('missing_current_bid')
        if ceiling is None:reasons.append('missing_platform_price_requirement')
        if not matches:reasons.append('no_brand_official_bid_record')
        states=sorted({str(get(r['values'],bm,'bid_state','')) for r in matches})
        positive_stock=any((n:=number(get(r['values'],bm,'current_stock'))) is not None and n>0 for r in matches)
        if matches and not any(get(r['values'],bm,'bid_state')=='售卖中' for r in matches):reasons.append('no_selling_bid')
        if matches and not positive_stock:reasons.append('sold_out_or_stock_unavailable')
        if any(str(get(r['values'],bm,'article_no','')).strip().upper()!=article for r in matches):reasons.append('sku_article_identity_mismatch')
        if combo:excluded.append('excluded_pearl_combo_per_user')
        if excluded_activity:excluded.append('excluded_crazy_discount_or_weekend_series_per_user')
        state=str(get(values,m,'registration_state','') or '')
        if sku in already or any(x in state for x in ('已报名','报名成功','待审核','审核中','已入选','已报入')):excluded.append('already_registered_in_current_activity')
        if len(current_prices)>1:anomalies.append({'sku_id':sku,'article_no':article,'issue':'multiple_current_bid_prices','prices':current_prices})
        if current_prices and template_bid is not None:
            prices_compared+=1
            if template_bid==min(current_prices):prices_agree+=1
            else:anomalies.append({'sku_id':sku,'article_no':article,'issue':'activity_min_bid_vs_current_export_differ','activity_min_bid':template_bid,'current_prices':current_prices})
        cost=number(c.get('product_cost'));discount=number(c.get('configured_discount'));gift_cost=D('13') if gift else D('0')
        if cost is None or cost<0:reasons.append('missing_product_cost')
        if discount is None or discount<=0 or discount>10:reasons.append('invalid_configured_discount')
        computed={}
        if bid is not None and bid>0 and ceiling is not None and cost is not None and cost>=0 and discount is not None and 0<discount<=10:
            try:computed=pricing(bid,discount,ceiling,cost,gift_cost,extra_rate,extra_fixed,args.price_decimals)
            except ValueError:reasons.append('nonpositive_registration_price_after_platform_rounding')
            if computed and not computed['passes_user_margin_gate']:reasons.append('activity_margin_not_above_3pct_after_platform_rounding')
            if computed and floor is not None and computed['proposed_price']<floor:reasons.append('below_platform_minimum_price')
        if article in confirmation_articles:reasons.append('requires_per_activity_user_confirmation_of_activity_and_net_price')
        status='excluded' if excluded else ('hold' if reasons else 'ready')
        decisions.append({'source_row':row['row'],'sheet':activity['sheet'],'spu_id':spu,'sku_id':sku,'article_no':article,'product_name':get(values,m,'product_name'),'style':style,'channel':'品牌官方','stock_entry':'不限制','current_bid':bid,'current_bid_source':'brand-official current bid export' if current_prices else 'activity template minimum bid','activity_template_min_bid':template_bid,'current_bid_export_rows':[r['row'] for r in matches],'current_bid_prices':current_prices,'current_bid_states':states,'has_positive_current_stock':positive_stock,'platform_max_price':ceiling,'platform_min_price':floor,'configured_discount':discount,'product_cost':cost,'extra_giftbox_cost':gift_cost,'registration_state_in_source':state or None,'catalog_row':c.get('row'),'catalog_cost_from_external_cache':'G' in c.get('formulas',{}),'status':status,'hold_reasons':reasons,'exclusion_reasons':excluded,'notes':notes,'original_template_values':values,**computed})
    ready=[r for r in decisions if r['status']=='ready'];held=[r for r in decisions if r['status']=='hold'];excluded=[r for r in decisions if r['status']=='excluded']
    summary={'all_export_sku_count':len(activity['rows']),'all_export_spu_count':len({ident(get(r['values'],m,'spu_id')) for r in activity['rows']}),'catalog_count':len(catalog),'matched_sku_count':len(decisions),'matched_article_count':len({r['article_no'] for r in decisions}),'ready_sku_count':len(ready),'ready_spu_count':len({r['spu_id'] for r in ready}),'ready_article_count':len({r['article_no'] for r in ready}),'held_sku_count':len(held),'held_reasons':dict(collections.Counter(x for r in held for x in r['hold_reasons'])),'excluded_sku_count':len(excluded),'excluded_reasons':dict(collections.Counter(x for r in excluded for x in r['exclusion_reasons'])),'ready_using_configured_discount':sum(not r['platform_requires_lower_discount'] for r in ready),'ready_using_platform_max':sum(r['platform_requires_lower_discount'] for r in ready),'minimum_ready_margin':min((r['activity_margin'] for r in ready),default=None),'minimum_ready_margin_sku':min(ready,key=lambda r:r['activity_margin'])['sku_id'] if ready else None,'unmatched_catalog_article_count':len(unmatched)}
    checks={'partition_reconciles':len(ready)+len(held)+len(excluded)==len(decisions),'ready_sku_unique':len({r['sku_id'] for r in ready})==len(ready),'ready_article_matches':all(r['article_no'] in catalog for r in ready),'ready_prices_positive_and_at_most_max':all(0<r['proposed_price']<=r['platform_max_price'] for r in ready),'ready_lower_discount_margin_above_3pct':all(not r['platform_requires_lower_discount'] or r['activity_margin']>D('.03') for r in ready),'ready_no_pearl_combinations':all('小米珠' not in r['style'] for r in ready),'ready_no_already_registered_skus':all(r['sku_id'] not in already for r in ready),'ready_official_channel_and_unrestricted_stock':all(r['channel']=='品牌官方' and r['stock_entry']=='不限制' for r in ready),'bid_prices_compared':prices_compared,'bid_prices_agree':prices_agree}
    if any(v is False for v in checks.values()):raise AssertionError(f'Plan self-check failed: {checks}')
    def source_meta(t):return {k:t[k] for k in ('path','size','sha256','sheet','declared_dimension','header_row','warnings')}
    sources=[source_meta(activity)]+([source_meta(bids)] if bids else [])+([source_meta(registered_log)] if registered_log else [])
    output={'activity_id':args.activity_id,'activity_name':args.activity_name,'activity_excluded_by_name':excluded_activity,'sources':sources,'catalog_index':{'path':str(catalog_path.resolve()),'sha256':hashlib.sha256(catalog_path.read_bytes()).hexdigest()},'template':{'sheet':activity['sheet'],'header_row':activity['header_row'],'instruction_rows':activity['instruction_rows'],'columns':{column_letter(i):h for i,h in enumerate(activity['headers'])},'column_map':m,'input_columns':{column_letter(m[k]):label for k,label in [('channels','适用渠道=品牌官方'),('registration_price','商品报名价'),('stock_entry','活动库存=不限制')] if k in m},'preserve_instruction_header_and_columns':True},'additional_activity_deductions':{'rate':extra_rate,'fixed_per_order':extra_fixed,'amount_formula':'proposed_price * rate + fixed_per_order','provided_explicitly':args.extra_rate!='0' or args.extra_fixed!='0' or bool(args.extra_note),'note':args.extra_note or 'No additional activity deductions supplied; explicitly assumed 0. Current source-table 10% deduction remains included.'},'rules':{'discount':'Per-SKU current original bid * catalog E/10; when above platform maximum use maximum and require activity margin >3%.','margin':'price - MAX(price*22%,45) -14.5 -price*10% -product_cost -giftbox_cost -extra_rate*price -extra_fixed','giftbox':'钟意一生/炽热挚爱/炽烈挚爱 +13; brand box +0','excluded_combinations':'All extra-pearl combinations are excluded per user; basic SKU of the same article remains eligible.','excluded_activity_series':'All Crazy Weekend / Crazy Discount activities excluded per user.','price_rounding':f'Down to {args.price_decimals} decimal places, calculate actual profit after rounding.','registration_state':'Only explicit source states or supplied already-registered SKU/log evidence can prove prior enrollment; otherwise source does not prove absence.'},'summary':summary,'checks':checks,'anomalies':anomalies,'unmatched_catalog_articles':sorted(unmatched),'already_registered_sku_evidence':sorted(already),'decisions':decisions,'ready':ready,'hold':held,'excluded':excluded,'baselineVisualReviewed':False,'generated_upload':None}
    output['template']['last_source_row']=max((r['row'] for r in activity['rows']),default=activity['header_row'])
    output['rules']['discount']='Use current per-SKU original bid * catalog E/10; use platform maximum if lower; floor final price to platform precision and require every actual final margin strictly above 3%.'
    output['rules']['requires_per_activity_user_confirmation_articles']=sorted(confirmation_articles)
    output['pending_user_confirmation']=[r for r in held if r['article_no'] in confirmation_articles]
    output['checks']['ready_no_articles_requiring_user_confirmation']=all(r['article_no'] not in confirmation_articles for r in ready)
    output['checks']['ready_all_margins_above_3pct']=all(r['activity_margin']>D('.03') for r in ready)
    output['checks']['ready_all_integer_prices']=args.price_decimals!=0 or all(r['proposed_price']==int(r['proposed_price']) for r in ready)
    if not output['checks']['ready_all_margins_above_3pct'] or not output['checks']['ready_all_integer_prices']:raise AssertionError('Final price/margin self-check failed.')
    return output
def arguments():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--activity-id',required=True);p.add_argument('--activity-name',required=True);p.add_argument('--source',required=True)
    p.add_argument('--bid-source');p.add_argument('--catalog-index',default='work/catalog_costs.json');p.add_argument('--out-plan');p.add_argument('--sheet');p.add_argument('--bid-sheet')
    p.add_argument('--extra-rate',default='0',help='Additional rate as a fraction: 0.02 = 2%%; source-table 10%% is already included.')
    p.add_argument('--extra-fixed',default='0',help='Additional amount per order in RMB.');p.add_argument('--extra-note');p.add_argument('--price-decimals',type=int,default=0,help='Default 0: platform was observed truncating registration prices to whole RMB.')
    p.add_argument('--already-registered-sku',action='append',default=[]);p.add_argument('--already-registered-log')
    p.add_argument('--require-confirmation-article',action='append',default=['YX9354001'],help='Default Moonlight Dress must remain held until per-activity human confirmation; repeat to require other articles too.')
    return p.parse_args()
if __name__=='__main__':
    args=arguments();result=plan(args)
    safe_id=re.sub(r'[^A-Za-z0-9_-]','_',args.activity_id)
    destination=pathlib.Path(args.out_plan or f'work/activity_{safe_id}_plan.json');destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=encode))
    print(json.dumps({'plan':str(destination.resolve()),'summary':result['summary'],'checks':result['checks'],'additional_activity_deductions':result['additional_activity_deductions']},ensure_ascii=False,default=encode))
