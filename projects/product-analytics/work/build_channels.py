#!/usr/bin/env python3
"""Merge observed channel counts into standalone raw data and CHANNEL_DATA.

Reads local evidence only. Never reads browsers or edits a Site checkout.
Missing observations remain absent; no rates are inverted to create history.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
WORK = BASE / 'work'
CHANNELS = [
    {'id': 'competition', 'name': '商品竞争力', 'parent_id': None},
    {'id': 'recommend', 'name': '商品推荐', 'parent_id': 'competition'},
    {'id': 'search', 'name': '商品搜索', 'parent_id': 'competition'},
    {'id': 'new_guarantee', 'name': '新品保量', 'parent_id': 'competition'},
    {'id': 'paid', 'name': '付费推广', 'parent_id': None},
    {'id': 'push', 'name': '得物推', 'parent_id': 'paid'},
    {'id': 'gravity', 'name': '引力', 'parent_id': 'paid'},
    {'id': 'activity', 'name': '平台活动', 'parent_id': None},
    {'id': 'content', 'name': '内容自运营', 'parent_id': None},
    {'id': 'users', 'name': '用户运营', 'parent_id': None},
    {'id': 'other', 'name': '其他', 'parent_id': None},
]
NAME_TO_ID = {c['name']: c['id'] for c in CHANNELS}
PRIMARY = [c['id'] for c in CHANNELS if c['parent_id'] is None]
CORES = ['YX9354001', 'YX9615001']


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def clean_name(name):
    return name.split('(')[0].strip()


def valid_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def main():
    metrics = read_json(WORK / 'retry_metrics.json')
    trend = read_json(WORK / 'daily_trend.json')
    date = metrics['date']
    output = BASE / 'outputs' / date
    dates = sorted({r['date'] for r in trend['records']})
    assert dates[0] == metrics['week_start'] and dates[-1] == metrics['week_end']
    metadata = sorted(metrics['rows'], key=lambda r: (-r[4][1], -r[4][6], r[0]))
    active_metadata = [row for row in metadata if row[2] or row[4][1] > 0 or row[4][7] > 0]
    active_positions = {row[0]: index for index, row in enumerate(active_metadata)}
    products = {}
    for row in metadata:
        code, name, backend_new, _bid, week, _day = row
        index = active_positions.get(code)
        top_observation = index is not None and index < 10
        reasons = [label for label, matches in (
            ('backend_new_label', bool(backend_new)),
            ('week_sales_positive', week[1] > 0),
            ('week_favorites_positive', week[7] > 0),
        ) if matches]
        products[code] = {
            'code': code, 'name': name, 'backendNew': backend_new,
            'weekSales': week[1], 'weekUv': week[6], 'weekFavorites': week[7],
            'rank': 1 + sum(other[4][1] > week[1] for other in metadata),
            'topObservation': top_observation,
            'eligible': code in active_positions, 'eligibilityReasons': reasons,
            'exclusionReason': None if reasons else '非后台新品且近7天销量与收藏均为0',
            'group': '范围外' if not reasons else ('有销量款' if week[1] else ('零销量观察' if top_observation else '零销量')),
            'confirmedListingDate': None,
            'listingDateStatus': '待确认',
            'days': {},
        }

    raw_records = []
    for row in read_json(WORK / 'channel-observations.json'):
        raw_records.append({
            **row,
            'source': {
                'file': 'work/channel-observations.json',
                'kind': 'parent_relay_of_observed_cua_counts',
                'collected_at': None,
            },
        })
    for code in CORES:
        path = output / f'{code}_渠道原始读数_重试.json'
        original = read_json(path)
        original_rows = original.get('day_rows', original.get('rows'))
        assert original['date'] == date and original['code'] == code
        raw_records.append({
            'code': code, 'date': date,
            'comparison_date': (datetime.strptime(date, '%Y-%m-%d').date() - timedelta(days=1)).isoformat(),
            'rows': [
                {'name': clean_name(r[0]), 'count': r[1],
                 'reported_change_pct': r[2], 'reported_share_pct': r[3]}
                for r in original_rows
            ],
            'source': {'file': str(path.relative_to(BASE)), 'kind': 'observed_ui_raw_json',
                       'description': original['source'], 'collected_at': None},
        })

    seen = set()
    daily_checks = []
    for record in raw_records:
        code, observed_date = record['code'], record['date']
        assert code in products, f'Unknown code {code}'
        assert observed_date in dates, f'Out-of-period date {observed_date}'
        assert (code, observed_date) not in seen, f'Duplicate observation {code} {observed_date}'
        seen.add((code, observed_date))
        names = [r['name'] for r in record['rows']]
        assert len(names) == len(set(names)), f'Duplicate channel names {code} {observed_date}'
        assert all(valid_count(r['count']) for r in record['rows'])
        assert all(name == '全部' or name in NAME_TO_ID for name in names)
        observed = {r['name']: r['count'] for r in record['rows']}
        values = {NAME_TO_ID[name]: value for name, value in observed.items() if name != '全部'}
        total = observed.get('全部')
        assert total is not None, f'Missing observed total {code} {observed_date}'
        primary_complete = all(channel in values for channel in PRIMARY)
        primary_sum = sum(values[channel] for channel in PRIMARY) if primary_complete else None
        competition_children = sum(values[channel] for channel in ('recommend', 'search', 'new_guarantee') if channel in values)
        paid_children = sum(values[channel] for channel in ('push', 'gravity') if channel in values)
        check = {
            'code': code, 'date': observed_date,
            'primary_complete': primary_complete,
            'total': total, 'primary_sum': primary_sum,
            'primary_sum_matches_total': primary_sum == total,
            'competition_children_match': competition_children == values.get('competition'),
            'paid_children_match': paid_children == values.get('paid'),
        }
        check['pass_check'] = all(check[key] for key in ('primary_complete', 'primary_sum_matches_total', 'competition_children_match', 'paid_children_match'))
        assert check['pass_check'], f'Channel reconciliation failed: {check}'
        if observed_date == date:
            source_row = next(row for row in metadata if row[0] == code)
            check['matches_existing_day_pv'] = total == source_row[5][2]
            assert check['matches_existing_day_pv'], f'Existing day PV mismatch {code}'
        daily_checks.append(check)
        day = {
            'total': total, 'values': values, 'observed': True,
            'primary_complete': primary_complete, 'primary_sum': primary_sum,
            'primary_sum_matches_total': primary_sum == total,
            'source': record['source'],
        }
        reported = {}
        for row in record['rows']:
            if 'reported_change_pct' in row:
                channel_id = 'total' if row['name'] == '全部' else NAME_TO_ID[row['name']]
                reported[channel_id] = {'pct': row['reported_change_pct'], 'comparison_date': record['comparison_date']}
        if reported:
            day['reported_changes'] = reported
            day['comparison_date'] = record['comparison_date']
            day['reported_shares_pct'] = {
                'total' if row['name'] == '全部' else NAME_TO_ID[row['name']]: row['reported_share_pct']
                for row in record['rows'] if 'reported_share_pct' in row
            }
        products[code]['days'][observed_date] = day

    availability_path = WORK / 'channel-source-availability.json'
    availability = read_json(availability_path) if availability_path.exists() else {}
    assert all(code in products for code in availability), 'Unknown availability product code'
    for code, product in products.items():
        product['source_status'] = 'observed' if product['days'] else 'not_collected'
        product['source_note'] = '已取得实采渠道日数据' if product['days'] else '尚未采集渠道日数据，后台入口可用性未核验'
        if code in availability:
            entry = availability[code]
            assert entry['source_status'] in ('observed', 'not_collected', 'not_exposed_in_backend')
            product.update(entry)
            if product['source_status'] == 'not_exposed_in_backend':
                assert not product['days'], f'Availability conflicts with observed dates: {code}'
    website_products = {code: product for code, product in products.items() if product['eligible']}
    target_codes = list(website_products)
    head_codes = [code for code, p in website_products.items() if p['topObservation']]
    head_new_union_codes = [code for code, p in website_products.items() if p['topObservation'] or p['backendNew']]
    active_raw_records = [record for record in raw_records if record['code'] in website_products]
    previous_date = dates[-2] if len(dates) > 1 else None
    per_date = Counter(record['date'] for record in active_raw_records)
    raw_per_date = Counter(record['date'] for record in raw_records)
    observed_products = [code for code, p in website_products.items() if p['days']]
    raw_observed_products = [code for code, p in products.items() if p['days']]
    complete_pairs = [code for code in target_codes if date in website_products[code]['days'] and previous_date in website_products[code]['days']]
    complete_series = [code for code, p in website_products.items() if all(d in p['days'] for d in dates)]
    excluded_observed_codes = [code for code in raw_observed_products if code not in website_products]
    source_status_counts = Counter(product['source_status'] for product in website_products.values())
    scope_filter = {
        'rule': 'backendNew || weekSales > 0 || weekFavorites > 0',
        'period_start': metrics['week_start'], 'period_end': metrics['week_end'],
        'source': 'work/retry_metrics.json',
        'source_fields': {'backendNew': 'row[2]', 'weekSales': 'row[4][1]', 'weekFavorites': 'row[4][7]'},
        'category_product_count': len(products), 'active_product_count': len(website_products),
        'active_codes': list(website_products),
        'excluded_products': [
            {key: product[key] for key in ('code', 'name', 'backendNew', 'weekSales', 'weekFavorites', 'exclusionReason')}
            for product in products.values() if not product['eligible']
        ],
        'raw_observations_preserved': True,
    }
    coverage = {
        'scope': 'website_active_products',
        'category_product_count': len(products),
        'active_product_count': len(website_products),
        'excluded_product_count': len(products) - len(website_products),
        'metadata_product_count': len(website_products),
        'period_date_count': len(dates),
        'category_expected_product_day_count': len(products) * len(dates),
        'expected_product_day_count': len(website_products) * len(dates),
        'observed_product_day_count': len(active_raw_records),
        'observed_product_count': len(observed_products),
        'observed_counts_by_date': {d: per_date[d] for d in dates},
        'raw_observed_product_day_count': len(raw_records),
        'raw_observed_product_count': len(raw_observed_products),
        'excluded_observed_codes': excluded_observed_codes,
        'excluded_observed_record_count': len(raw_records) - len(active_raw_records),
        'source_status_counts': dict(source_status_counts),
        'source_not_exposed_codes': [code for code, p in website_products.items() if p['source_status'] == 'not_exposed_in_backend'],
        'source_not_yet_verified_codes': [code for code, p in website_products.items() if p['source_status'] == 'not_collected'],
        'source_availability_evidence_file': str(availability_path.relative_to(BASE)) if availability_path.exists() else None,
        'target_codes': target_codes, 'target_product_count': len(target_codes),
        'head_observation_codes': head_codes,
        'head_new_union_codes': head_new_union_codes,
        'target_products_with_complete_latest_pair': complete_pairs,
        'target_latest_pair_count': len(complete_pairs),
        'products_with_complete_period': complete_series,
        'complete_period_product_count': len(complete_series),
        'missing_dates_by_code': {code: [d for d in dates if d not in p['days']] for code, p in website_products.items()},
    }
    notes = [
        '渠道指标为商详访问次数PV，不是商详访客UV；不可按渠道PV分摊UV增减。',
        '六个一级渠道分解总PV；商品竞争力含推荐、搜索及页面明确展示时的新品保量，付费推广含得物推、引力；父子不重复求和。',
        '缺失日期不出现在days中，未采集商品days为空对象；缺失渠道不补0。',
        '新品保量0仅在明确读取该行的商品和日期保存，不替其他页面推断0。',
        '后台涨跌与其原对比日期另存；未用百分比反推或周汇总补造逐日数据。',
        '后台新品标签的真实首次上架日期待确认；商品名为底表简称。',
        'source_status=not_exposed_in_backend表示已核验后台不提供渠道明细入口，关注商品仍保留且days为空；不同于尚未采集或尚未核验。',
        '看板范围保留后台新品或近7天销量/收藏至少一项大于0的商品；近7天销量与收藏均为0且非后台新品的商品仅从派生看板排除，原始观察保留。',
        f'原一级类目{len(products)}款中仅4款七天有销量；当前看板{len(website_products)}款内销量相同时按七天UV降序、再货号排序取前10观察，零销量仍并列第5。',
    ]
    common = {
        'schema_version': 1, 'data_date': date, 'dates': dates,
        'metric': {'key': 'detail_pv', 'label': '商详访问次数', 'unit': '次'},
        'category': '流行饰品/眼镜/服配',
        'built_at': datetime.now(timezone.utc).isoformat(),
        'collected_date': metrics.get('collected_date'),
        'collected_at': None, 'scope_filter': scope_filter, 'notes': notes,
    }
    raw_records.sort(key=lambda r: (list(products).index(r['code']), r['date']))
    raw_coverage = {
        'scope': 'raw_category_history', 'category_product_count': len(products),
        'metadata_product_count': len(products), 'period_date_count': len(dates),
        'expected_product_day_count': len(products) * len(dates),
        'observed_product_day_count': len(raw_records),
        'observed_product_count': len(raw_observed_products),
        'observed_counts_by_date': {d: raw_per_date[d] for d in dates},
        'website_active_product_count': len(website_products),
        'website_expected_product_day_count': len(website_products) * len(dates),
        'website_observed_product_day_count': len(active_raw_records),
    }
    raw_output = {
        **common, 'coverage': raw_coverage, 'website_coverage': coverage,
        'product_metadata': {code: {key: value for key, value in product.items() if key != 'days'} for code, product in products.items()},
        'records': raw_records,
    }
    payload = {**common, 'coverage': coverage, 'channels': CHANNELS, 'products': website_products}
    observation_validation_path = WORK / 'channel-observations-validation.json'
    prior_validation = read_json(observation_validation_path)
    weekly_checks = []
    for reference in prior_validation['weekly_checks']:
        code = reference['code']
        expected = reference['expected']
        complete = all(d in products[code]['days'] for d in dates)
        computed = {}
        if complete:
            for name in expected:
                if name == '全部':
                    computed[name] = sum(products[code]['days'][d]['total'] for d in dates)
                else:
                    computed[name] = sum(products[code]['days'][d]['values'][NAME_TO_ID[name]] for d in dates)
        check = {**reference, 'days': dates, 'computed': computed,
                 'complete_period': complete, 'pass_check': complete and computed == expected}
        assert check['pass_check'], f'Weekly reference mismatch: {check}'
        weekly_checks.append(check)
    observation_checks = [check for check in daily_checks if (check['code'], check['date']) in {
        (record['code'], record['date']) for record in raw_records
        if record['source']['kind'] == 'parent_relay_of_observed_cua_counts'
    }]
    observation_validation = {
        **prior_validation,
        'record_count': len(observation_checks),
        'daily_checks': observation_checks, 'weekly_checks': weekly_checks,
        'all_pass': all(check['pass_check'] for check in observation_checks + weekly_checks),
    }
    scope_checks = {
        'category_product_count': len(products), 'active_product_count': len(website_products),
        'active_rule_matches': all(p['eligible'] == (p['backendNew'] or p['weekSales'] > 0 or p['weekFavorites'] > 0) for p in products.values()),
        'active_metadata_has_week_favorites': all('weekFavorites' in p for p in website_products.values()),
        'excluded_absent_from_website': all(code not in website_products for code in excluded_observed_codes),
        'excluded_observations_retained': all(any(r['code'] == code for r in raw_records) for code in excluded_observed_codes),
        'unexposed_products_have_empty_days': all(not p['days'] for p in website_products.values() if p['source_status'] == 'not_exposed_in_backend'),
        'head_codes': head_codes, 'website_expected_day_count': len(website_products) * len(dates),
    }
    assert all(scope_checks[key] for key in ('active_rule_matches', 'active_metadata_has_week_favorites', 'excluded_absent_from_website', 'excluded_observations_retained', 'unexposed_products_have_empty_days'))
    validation = {'all_pass': True, 'coverage': coverage, 'scope_checks': scope_checks,
                  'daily_checks': daily_checks, 'weekly_checks': weekly_checks}
    raw_path = output / '渠道逐日原始读数.json'
    normalized_path = output / '渠道逐日整理数据.json'
    write_json(raw_path, raw_output)
    write_json(normalized_path, payload)
    write_json(WORK / 'channel-build-validation.json', validation)
    write_json(observation_validation_path, observation_validation)
    assert read_json(raw_path)['records'] == raw_records
    assert len(read_json(normalized_path)['products']) == len(website_products)
    print(json.dumps({
        'raw': str(raw_path), 'normalized': str(normalized_path),
        'category_products': len(products), 'products': len(website_products),
        'expected_product_days': len(website_products) * len(dates),
        'raw_observed_records': len(raw_records), 'observed_records': len(active_raw_records),
        'observed_products': len(observed_products),
        'target_pair_count': len(complete_pairs), 'target_products': len(target_codes),
        'complete_series_count': len(complete_series), 'all_pass': True,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
