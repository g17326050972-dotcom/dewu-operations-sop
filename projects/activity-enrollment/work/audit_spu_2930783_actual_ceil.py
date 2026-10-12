"""Recalculate parent-observed SPU discount prices without changing source plans."""
from pathlib import Path
from decimal import Decimal, ROUND_CEILING
import hashlib
import json

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / 'activity_2930783_spu_plan.json'
OUT = ROOT / 'activity_2930783_actual_ceil_audit.json'
OBSERVED = {
    'YX9638001': [359, 389, 395],
    'YX9611001': [159, 189, 189],
    'YX9615001': [179, 209, 214],
    'YX9341001': [180],
}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def number(value):
    return float(value) if value % 1 else int(value)

plan_before = digest(PLAN)
plan = json.loads(PLAN.read_text())
catalog_path = ROOT / 'catalog_costs.json'
catalog = json.loads(catalog_path.read_text())['by_article_no']
products, rows = [], []
for product in plan['candidates']:
    article = product['article_no']
    if article not in OBSERVED:
        continue
    prices = OBSERVED[article]
    assert len(prices) == len(product['skus'])
    assert product['all_known_skus_current_bid_complete']
    assert product['product_cost'] == catalog[article]['product_cost']
    actual_skus = []
    for sku, price in zip(product['skus'], prices):
        p = Decimal(str(price))
        bid = Decimal(str(sku['original_brand_official_bid']))
        discount = Decimal(str(product['proposed_discount_input']))
        raw = bid * discount / 10
        computed_ceil = int(raw.to_integral_value(rounding=ROUND_CEILING))
        assert computed_ceil == price, (article, sku['sku_id'], computed_ceil, price)
        cost = Decimal(str(sku['product_cost']))
        gift = Decimal(str(sku['extra_giftbox_cost']))
        fee = max(p * Decimal('.22'), Decimal(45))
        ten_pct = p * Decimal('.10')
        fulfillment = Decimal('14.5')
        profit = p - fee - ten_pct - fulfillment - cost - gift
        margin = profit / p
        assert margin > Decimal('.03')
        row = {
            'article_no': article,
            'spu_id': product['spu_id'],
            'product_name': product['original_template_values'][1],
            'sku_id': sku['sku_id'],
            'style': sku['style'],
            'original_brand_official_bid': number(bid),
            'configured_catalog_discount': product['configured_discount_E'],
            'actual_spu_discount_input': number(discount),
            'unrounded_discount_price': number(raw),
            'actual_price': price,
            'computed_ceil_price': computed_ceil,
            'ceil_matches_parent_observed_price': True,
            'original_bid_evidence_type': 'Official bid export snapshot used by the original plan; not independently refreshed in live UI.',
            'discount_evidence_type': 'Parent reported live UI submission success at this SPU discount.',
            'price_evidence_type': '据源计算ceil，且与根代理提供价格一致；未独立读取UI逐SKU价格，未取得该活动报名读回导出。',
            'previous_conservative_floor_price': sku['proposed_price'],
            'product_cost': number(cost),
            'extra_giftbox_cost': number(gift),
            'product_plus_upgraded_giftbox_cost': number(cost + gift),
            'platform_fee': number(fee),
            'fulfillment_cost': number(fulfillment),
            'source_ten_percent_deduction': number(ten_pct),
            'additional_activity_deduction': 0,
            'activity_profit_source_formula': number(profit),
            'activity_margin_source_formula': number(margin),
            'passes_user_margin_gate': True,
            'channel_reported_by_parent': '品牌官方',
            'activity_inventory_reported_by_parent': '不限制',
            'submission_state_evidence': 'Parent reports UI submission success; not a separately exported registration readback.',
        }
        actual_skus.append(row)
        rows.append(row)
    products.append({
        'article_no': article,
        'spu_id': product['spu_id'],
        'product_name': product['original_template_values'][1],
        'actual_spu_discount_input': product['proposed_discount_input'],
        'sku_count': len(actual_skus),
        'minimum_source_formula_margin': min(r['activity_margin_source_formula'] for r in actual_skus),
        'skus': actual_skus,
    })

assert len(products) == 4 and len(rows) == 10
assert digest(PLAN) == plan_before
audit = {
    'activity_id': '2930783',
    'main_id': plan['main_id'],
    'activity_name': plan['activity_name'],
    'evidence_scope': 'Parent reported live UI submission success for four SPUs and supplied a whole-RMB price list. Prices are verified by local ceil computation; this file does not establish a direct per-SKU UI price readback or exported registration state.',
    'original_floor_plan': str(PLAN),
    'original_floor_plan_sha256': plan_before,
    'catalog_cost_index': str(catalog_path),
    'catalog_cost_index_sha256': digest(catalog_path),
    'bid_source': plan['bid_source'],
    'bid_source_sha256': plan['bid_source_sha256'],
    'cost_formula': 'price - max(price * 22%, 45) - 14.5 - price * 10% - product_cost - upgraded_giftbox_cost',
    'rounding_formula': 'ceil(original_brand_official_bid * actual_spu_discount_input / 10)',
    'additional_activity_deduction': 0,
    'margin_scope': 'Source workbook 10% deduction retained. No assumption that it covers real coupons; parent reports no extra full reduction for these non-Moon articles.',
    'summary': {
        'submitted_spu_count_parent_reported': len(products),
        'verified_sku_count': len(rows),
        'all_actual_prices_equal_decimal_ceil': True,
        'all_source_formula_margins_strictly_above_3pct': True,
        'minimum_source_formula_margin': min(r['activity_margin_source_formula'] for r in rows),
        'minimum_margin_sku_id': min(rows, key=lambda r: r['activity_margin_source_formula'])['sku_id'],
        'original_floor_plan_unchanged': True,
    },
    'products': products,
    'rows': rows,
    'not_in_this_submitted_four': [
        {'article_no': 'YX9545001', 'spu_id': '84165066', 'base_sku_id': '1243533000', 'reason': 'Base SKU current original bid unresolved. Parent observed SPU minimum current bid 324; this does not identify base SKU bid. Do not impute 324 to base SKU.'},
        {'article_no': 'YX9339001', 'spu_id': '47171559', 'reason': 'Entire SPU excluded because it contains pearl-combination SKU.'},
        {'article_no': 'YX9354001', 'spu_id': '52189490', 'reason': 'Not included in parent-reported four submitted SPUs for this campaign.'},
    ],
}
OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'audit': str(OUT), 'summary': audit['summary'], 'rows': [[r['article_no'], r['sku_id'], r['actual_price'], r['activity_profit_source_formula'], r['activity_margin_source_formula']] for r in rows]}, ensure_ascii=False, indent=2))
