"""Read-only audit of platform enrollment exports; writes JSON only."""
import argparse,collections,hashlib,json,pathlib,re,sys,warnings
from decimal import Decimal as D
import openpyxl
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import plan_activity as p

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--activity-id',required=True);parser.add_argument('--source',required=True);parser.add_argument('--plan',required=True)
parser.add_argument('--existing-duplicate-sku',action='append',default=[]);parser.add_argument('--task-id');parser.add_argument('--out')
parser.add_argument('--approved-moon-price',action='append',default=[],help='Explicit separately approved SKU:price for Moon, verified by parent human-approval/UI evidence.')
args=parser.parse_args()
plan=json.load(open(args.plan));catalog=json.load(open('work/catalog_costs.json'))['by_article_no']
candidate={r['sku_id']:r for r in plan['ready']};duplicates=set(args.existing_duplicate_sku)
approved_moon={}
for text in args.approved_moon_price:
    sku,price=text.split(':',1);price=D(price)
    original=next(r for r in plan['decisions'] if r['sku_id']==sku and r['article_no']=='YX9354001')
    assert price==D(str(original['proposed_price'])),'Approved Moon price differs from planned candidate.'
    candidate[sku]=dict(original,proposed_price=price,status='ready',hold_reasons=[])
    approved_moon[sku]=price
source=pathlib.Path(args.source);warnings.simplefilter('ignore')
wb=openpyxl.load_workbook(source,read_only=True,data_only=True);ws=wb.worksheets[0]
try:declared=ws.calculate_dimension()
except ValueError:declared='unsized'
ws.reset_dimensions();values=list(ws.iter_rows(values_only=True));headers=values[0]
required={'spuId','skuId','货号','规格','已参与渠道','已报名出价','已报名活动库存','活动剩余库存','驳回原因','已经报名审核状态'}
assert required.issubset(set(headers)),headers
source_rows=[dict(zip(headers,row)) for row in values[1:] if len(row)>1 and row[1] is not None]
for record in source_rows:
    record['skuId']=p.ident(record['skuId']);record['spuId']=p.ident(record['spuId'])
assert len({r['skuId'] for r in source_rows})==len(source_rows),'Duplicate actual SKU'
def normalized_spec(value):return sorted(v.strip() for v in re.split('[;；]',str(value or '')) if v.strip())
result=[];differences=[];new_deviations=[];existing_deviations=[];outside=[];margins=[];seen=set()
extra=plan.get('additional_activity_deductions',{});rate=D(str(extra.get('rate',0)));fixed=D(str(extra.get('fixed_per_order',0)))
for index,record in enumerate(source_rows,2):
    sku=record['skuId'];article=str(record['货号']).strip().upper();seen.add(sku);expected=candidate.get(sku)
    actual=D(str(record['已报名出价']));state=str(record['已经报名审核状态']);style=str(record['规格'] or '')
    channel=str(record['已参与渠道']);inventory=str(record['已报名活动库存']);remaining=str(record['活动剩余库存'])
    origin='existing_duplicate' if sku in duplicates else 'new_import' if expected else 'existing_outside_this_upload'
    planned=D(str(expected['proposed_price'])) if expected else None
    if channel!='品牌官方':differences.append({'sku_id':sku,'issue':'channel','actual':channel})
    if inventory not in ('不限制','无限制') or remaining not in ('不限制','无限制'):differences.append({'sku_id':sku,'issue':'inventory_not_unrestricted','activity':inventory,'remaining':remaining})
    if expected:
        if article!=expected['article_no'] or record['spuId']!=expected['spu_id']:differences.append({'sku_id':sku,'issue':'product_identity_mismatch'})
        if normalized_spec(style)!=normalized_spec(expected['style']):differences.append({'sku_id':sku,'issue':'variant_description_changed','expected':expected['style'],'actual':style})
        if actual!=planned:
            deviation={'sku_id':sku,'article_no':article,'actual_price':actual,'planned_price':planned,'origin':origin}
            (existing_deviations if origin=='existing_duplicate' else new_deviations).append(deviation)
        if actual> D(str(expected['platform_max_price'])):differences.append({'sku_id':sku,'issue':'actual_price_above_source_platform_max'})
    cost=catalog.get(article,{}).get('product_cost');gift=D(13) if any(v in style for v in ('钟意一生','炽热挚爱','炽烈挚爱')) else D(0)
    profit=actual-max(actual*D('.22'),D(45))-D('14.5')-actual*D('.10')-D(str(cost))-gift-rate*actual-fixed if cost is not None else None
    margin=profit/actual if profit is not None else None
    if margin is not None:margins.append((margin,sku,article,actual))
    if expected and margin is not None and margin<=D('.03'):differences.append({'sku_id':sku,'issue':'margin_not_above_3pct_at_actual_registration_price','margin':margin})
    r={'source_row':index,'sku_id':sku,'spu_id':record['spuId'],'article_no':article,'style':style,'status':state,'origin':origin,'actual_price':actual,'planned_price':planned,'price_result':'existing_price_unchanged_matches_plan' if origin=='existing_duplicate' and actual==planned else 'existing_price_not_changed' if origin=='existing_duplicate' else 'exact' if actual==planned else 'unplanned_existing' if expected is None else 'new_import_price_deviation','actual_activity_profit':profit,'actual_activity_margin':margin,'product_cost':cost,'giftbox_cost':gift,'channel':channel,'activity_inventory':inventory,'remaining_inventory':remaining,'reject_reason':record.get('驳回原因','')}
    result.append(r)
    if expected is None:outside.append(r)
missing=sorted(set(candidate)-seen)
if missing:differences.append({'issue':'missing_candidates','sku_ids':missing})
moon=[r for r in result if r['article_no']=='YX9354001'];pearls=[r for r in result if '小米珠' in r['style']]
unapproved_moon=[r for r in moon if r['sku_id'] not in approved_moon]
if unapproved_moon:differences.append({'issue':'unexpected_unapproved_moon_rows_present','sku_ids':[r['sku_id'] for r in unapproved_moon]})
if pearls:differences.append({'issue':'unexpected_pearl_combo_rows_present','sku_ids':[r['sku_id'] for r in pearls]})
new=[r for r in result if r['origin']=='new_import'];candidates=[r for r in result if r['sku_id'] in candidate]
summary={'export_rows':len(result),'unique_sku_count':len(seen),'export_status_counts':dict(collections.Counter(r['status'] for r in result)),'candidate_count':len(candidate),'candidate_present':len(candidates),'missing_candidates':missing,'candidate_status_counts':dict(collections.Counter(r['status'] for r in candidates)),'new_import_count':len(new),'new_import_status_counts':dict(collections.Counter(r['status'] for r in new)),'new_import_all_prices_exactly_match_plan':not new_deviations,'existing_duplicate_count':sum(r['origin']=='existing_duplicate' for r in result),'existing_outside_upload_count':len(outside),'all_candidate_prices_meet_platform_limit':all(r['actual_price']<=D(str(candidate[r['sku_id']]['platform_max_price'])) for r in candidates),'all_candidate_actual_margins_above_3pct':all(r['actual_activity_margin'] is not None and r['actual_activity_margin']>D('.03') for r in candidates),'all_channels_brand_official':all(r['channel']=='品牌官方' for r in result),'all_activity_and_remaining_inventory_unlimited':all(r['activity_inventory'] in ('无限制','不限制') and r['remaining_inventory'] in ('无限制','不限制') for r in result),'excluded_pearl_combination_skus_present':[r['sku_id'] for r in pearls],'moon_skus_present':[r['sku_id'] for r in moon],'outside_catalog_existing_skus_without_margin':sum(r['product_cost'] is None for r in outside),'readback_structural_and_candidate_checks_pass':not differences and not new_deviations}
if margins:
    minimum=min(margins);summary.update({'minimum_actual_margin':minimum[0],'minimum_margin_sku':minimum[1],'minimum_margin_article':minimum[2],'minimum_margin_price':minimum[3]})
columns=['sku_id','article_no','status','origin','actual_price','planned_price','price_result','actual_activity_margin']
out={'activity_id':args.activity_id,'activity_name':plan['activity_name'],'download_task_id':args.task_id,'source':str(source.resolve()),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'worksheet':ws.title,'reported_dimension':declared,'parsed_actual_range':f'A1:{p.column_letter(len(headers)-1)}{len(values)}','method':'openpyxl read_only; reset_dimensions before full read; Decimal for ID and monetary calculations. No source writes.','summary':summary,'actual_margin_formula':'(实际报名价-MAX(实际报名价*22%,45)-14.5-实际报名价*10%-产品成本-升级礼盒13-额外活动扣减)/实际报名价','margin_caveat':'Recalculates source-workbook margin at actual registration price. Actual coupon/full-reduction deductions are not available in this export; source10pct is not assumed to cover all actual coupons.','differences':differences,'price_deviations':new_deviations+existing_deviations,'existing_outside_upload':outside,'pending_review':[r for r in result if '审核中' in r['status'] or '待审核' in r['status']],'rejected_or_invalid':[r for r in result if r['status'] not in ('有效','报名成功','审核通过','审核中','待审核')],'duplicate_evidence':[r for r in result if r['origin']=='existing_duplicate'],'row_columns':columns,'rows':[[r[k] for k in columns] for r in result],'row_details':result}
out['approved_moon_price_evidence']=[{'sku_id':sku,'registration_price':price,'activity_id':args.activity_id,'evidence':'Parent explicitly reports user approval and successful UI submission of Moon for this activity.'} for sku,price in approved_moon.items()]
out['summary']['unapproved_moon_skus_present']=[r['sku_id'] for r in unapproved_moon]
destination=pathlib.Path(args.out or f'work/activity_{args.activity_id}_readback_audit.json');destination.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=p.encode))
print(json.dumps({'audit':str(destination.resolve()),'summary':summary,'differences':differences,'price_deviations':out['price_deviations'],'duplicate_evidence':out['duplicate_evidence'],'existing_outside_upload':outside},ensure_ascii=False,indent=2,default=p.encode))
wb.close()
