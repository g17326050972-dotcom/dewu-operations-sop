"""Read enrollment evidence and prepare the report's canonical JSON.

Read-only toward all platform exports, plans, catalog and the root ledger.
The only editable report inputs are activity_metadata.json and optional
sku_overrides under that file. Never infer a submission from a ready plan.
"""
from __future__ import annotations
import json
import math
import warnings
from collections import Counter
from datetime import datetime
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "work"
REPORT = WORK / "report"
CAT = json.loads((WORK / "catalog_costs.json").read_text())
CATALOG = CAT["by_article_no"]
LEDGER = json.loads((WORK / "enrollment_progress.json").read_text())
META_PATH = REPORT / "activity_metadata.json"
META = json.loads(META_PATH.read_text()) if META_PATH.exists() else {"activities": {}}


def ident(value):
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(int(value))
    return str(value).strip()


def number(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_pearl_combination(style):
    compact = "".join(str(style).split())
    return "小米珠" in compact and any(token in compact for token in ("套装", "组合", "叠戴", "套组", "+", "＋"))


def was_enrolled(row):
    return row["origin"] not in ("hold", "failed")


def read_xlsx(path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet = workbook.active
        sheet.reset_dimensions()  # Dewu exports have deliberately short dimensions.
        rows = list(sheet.iter_rows(values_only=True))
        workbook.close()
    return rows


plans = {}
sku_index = {}
for path in sorted(WORK.glob("activity_*_plan.json")):
    data = json.loads(path.read_text())
    activity_id = str(data.get("activity_id", ""))
    if activity_id:
        plans[activity_id] = data
    for record in data.get("decisions", []):
        sku_index.setdefault(record["sku_id"], {}).update({
            k: v for k, v in record.items()
            if k in ("sku_id", "spu_id", "article_no", "product_name", "style",
                     "current_bid", "product_cost", "extra_giftbox_cost", "configured_discount")
        })

bid_path = Path("/Users/nan/Downloads/出价列表导出（品牌直发）（仅可使用一次）.xlsx")
if bid_path.exists():
    bid_rows = read_xlsx(bid_path)
    header = bid_rows[1]
    ix = {name: index for index, name in enumerate(header)}
    for row in bid_rows[2:]:
        if row[ix["购买渠道"]] != "品牌官方":
            continue
        sku = ident(row[ix["商品skuId"]])
        info = sku_index.setdefault(sku, {})
        info.update({"sku_id": sku, "spu_id": ident(row[ix["商品id（spuid）"]]),
                     "article_no": str(row[ix["商品货号"]]).strip().upper(),
                     "product_name": row[ix["商品名称"]],
                     "current_bid": number(row[ix["当前出价"]])})
        info.setdefault("style", ";".join(str(row[ix[f"规格{i}"]]) for i in range(1, 6)
                                          if row[ix[f"规格{i}"]]))


def record_for(activity_id, sku):
    for rec in plans.get(activity_id, {}).get("decisions", []):
        if rec["sku_id"] == sku:
            return rec
    return sku_index.get(sku, {})


def price_profile(activity_id, article, origin):
    """Keep UI observations separate from conditional coupon calculations."""
    if activity_id == "3902516":
        return {"reduction": 25.0, "mode": "不适用", "evidence": "既有满300减50券参与记录，无独立商品到手价",
                "rule": "满300减50，平台/商家各承担25"}
    if activity_id == "3368291":
        return {"reduction": 0.0, "mode": "规则测算", "evidence": "后台到手价显示“-”；按不叠加商家优惠规则测算",
                "rule": "不与任何商家活动优惠叠加"}
    if article == "YX9354001":
        if activity_id in ("2813342", "3054763"):
            return {"reduction": 25.0, "mode": "后台已核实", "evidence": "本场后台逐款已核实：报名价减25元",
                    "rule": "满300减50，商家承担25（本场后台已核实）"}
        if origin in ("hold", "failed") or activity_id in ("3988166", "3988145", "3940552"):
            return {"reduction": 25.0, "mode": "条件测算", "evidence": "若既有满300减50券适用、商家承担25时；本场后台尚未核实",
                    "rule": "条件：既有满300减50券适用，商家承担25"}
        return {"reduction": None, "mode": "待核实", "evidence": "本场后台到手价及既有满减券是否适用待核实",
                "rule": "本场叠加满减待核实，不默认扣25"}
    if activity_id in ("2813342", "3054763", "3103412"):
        return {"reduction": 0.0, "mode": "后台已核实", "evidence": "本场后台已核实：预估到手等于报名价",
                "rule": "本场后台未显示额外商家满减"}
    return {"reduction": 0.0, "mode": "按报名价测算", "evidence": "按报名价测算，尚无本场逐SKU后台到手价记录",
            "rule": "未另计商家满减，实际叠加待后台核实"}


def build_row(activity_id, sku, price, status, origin, source, override=None):
    act = LEDGER["activities"][activity_id]
    meta = META.get("activities", {}).get(activity_id, {})
    rec = record_for(activity_id, sku)
    info = dict(sku_index.get(sku, {}))
    info.update(rec)
    override = override or {}
    if origin == "hold":
        price = override.get("proposed_price", price)
    info.update(override)
    article = info.get("article_no", act.get("article", ""))
    if article not in CATALOG:
        return None  # User asked only about items in the supplied catalog.
    cat = CATALOG[article]
    style = info.get("style", "")
    if is_pearl_combination(style):
        raise ValueError(f"Excluded pearl combination appears as enrolled: {activity_id}/{sku}")
    gift = info.get("extra_giftbox_cost")
    if gift is None:
        gift = 13 if any(token in style for token in ("钟意一生", "炽热挚爱", "炽烈挚爱")) else 0
    profile = price_profile(activity_id, article, origin)
    reduction = override.get("extra_merchant_reduction", meta.get("moon_extra_merchant_reduction"
                        if article == "YX9354001" else "default_extra_merchant_reduction", profile["reduction"]))
    estimate_mode = override.get("estimate_mode", meta.get("estimate_mode", profile["mode"]))
    estimate_evidence = override.get("estimate_evidence", meta.get("estimate_evidence", profile["evidence"]))
    if override.get("estimate_verified", meta.get("estimate_verified", False)):
        estimate_mode = "后台已核实"
    estimated = override.get("estimated_received")
    if estimated is None and price is not None and reduction is not None:
        estimated = round(price - reduction, 2)
    if activity_id == "3902516":
        price = None
        estimated = None
        reduction = 25.0
    cost = info.get("product_cost", cat["product_cost"])
    bid = info.get("current_bid")
    fee = max(price * 0.22, 45) if price is not None else None
    extra_rate = meta.get("additional_activity_rate", 0)
    extra_fixed = meta.get("additional_activity_fixed", 0)
    profit = (price - fee - 14.5 - price * 0.10 - cost - gift - reduction
              - price * extra_rate - extra_fixed) if price is not None and reduction is not None else None
    notes = []
    if origin.startswith("existing"):
        notes.append("原有记录保留，未改价")
    if origin == "failed":
        notes.append("提交失败，未参加本活动；价格及毛利仅为失败尝试的方案测算")
    if estimate_mode == "条件测算":
        notes.append("条件测算：若既有满300减50券适用、商家承担25时；不是本场后台已核实到手价")
    elif article == "YX9354001" and reduction:
        notes.append("折后再扣商家承担25元；满减门槛按原出价")
    if activity_id == "3368291":
        notes.append("不与任何商家活动优惠叠加")
    if activity_id == "3902516":
        notes.append("满300减50，商家承担25；券参与记录无独立商品成交价")
    if not meta.get("start") or not meta.get("end"):
        notes.append("活动起止时间待补录")
    if override.get("note"):
        notes.append(override["note"])
    return {
        "article_no": article, "product_name": info.get("product_name", ""),
        "style": style, "sku_id": sku, "spu_id": info.get("spu_id", ""),
        "activity_id": activity_id, "activity_name": meta.get("name", act["name"]),
        "start": meta.get("start"), "end": meta.get("end"),
        "status": status, "origin": origin,
        "current_bid": bid, "current_bid_display": override.get("current_bid_display"),
        "configured_discount": cat["configured_discount"],
        "registration_price": price,
        "registration_discount_input": override.get("registration_discount_input"),
        "effective_discount": price / bid * 10 if price is not None and bid else None,
        "full_reduction_rule": override.get("full_reduction_rule", meta.get("full_reduction_rule", profile["rule"])),
        "extra_merchant_reduction": reduction,
        "estimated_received": estimated,
        "estimate_mode": estimate_mode,
        "estimate_evidence": estimate_evidence,
        "product_cost": cost, "giftbox_incremental_cost": gift,
        "platform_fee": fee, "fulfillment_cost": 14.5,
        "standard_activity_deduction_rate": 0.10,
        "extra_activity_rate": extra_rate, "extra_activity_fixed": extra_fixed,
        "profit": round(profit, 8) if profit is not None else None,
        "margin": profit / price if profit is not None else None,
        "channel": override.get("channel", act.get("channel", act.get("channel_observed", "品牌官方"))),
        "inventory": override.get("inventory", act.get("inventory", "不限制")),
        "notes": "；".join(notes), "source": override.get("source", source),
    }


rows = []
activity_summaries = []
gaps = []
for activity_id, act in LEDGER["activities"].items():
    stage = act.get("stage", "")
    meta = META.get("activities", {}).get(activity_id, {})
    registered = stage.startswith(("submitted", "enrolled", "already_enrolled", "import_success"))
    activity_rows = []
    overrides = meta.get("sku_overrides", {})
    audit_path = act.get("readback_audit")
    spu_audit_path = act.get("spu_readback_audit")
    if registered and spu_audit_path and (ROOT / spu_audit_path).exists():
        # This export proves SPU status/discount/channel/inventory, but has no
        # individual SKU prices. Keep the known active SKU expansion and ceil
        # calculation explicitly distinct from a SKU-price readback.
        audit = json.loads((ROOT / spu_audit_path).read_text())
        registered_spus = {rec["spu_id"]: rec for rec in audit["registered_catalog_spus"]}
        for raw in audit["active_sku_cost_and_ceil_estimates"]:
            sku = raw["sku_id"]
            spu = registered_spus[raw["spu_id"]]
            override = {
                "article_no": raw["article_no"], "spu_id": raw["spu_id"],
                "product_name": raw["product_name"], "style": raw["style"],
                "current_bid": raw["original_brand_official_bid"],
                "registration_discount_input": spu["registered_discount"],
                "channel": spu["registered_channel"], "inventory": spu["activity_inventory"],
            }
            override.update(overrides.get(sku, {}))
            row = build_row(activity_id, sku, raw["computed_ceil_price"], spu["status"],
                            "new_spu_submission", audit["source"], override)
            if row:
                activity_rows.append(row)
    elif registered and audit_path and (ROOT / audit_path).exists():
        audit = json.loads((ROOT / audit_path).read_text())
        columns = audit["row_columns"]
        exported = read_xlsx(audit["source"])
        header = {name: ix for ix, name in enumerate(exported[0])}
        exported_info = {ident(r[header["skuId"]]): {
            "article_no": r[header["货号"]], "style": r[header["规格"]],
            "product_name": r[header["商品名称"]], "spu_id": ident(r[header["spuId"]]),
            "channel": r[header["已参与渠道"]], "inventory": r[header["已报名活动库存"]],
        } for r in exported[1:]}
        for raw in audit["rows"]:
            record = dict(zip(columns, raw))
            sku = record["sku_id"]
            override = exported_info.get(sku, {}).copy()
            override.update(overrides.get(sku, {}))
            row = build_row(activity_id, sku, record["actual_price"], record["status"],
                            record["origin"], audit["source"], override)
            if row:
                activity_rows.append(row)
    elif registered:
        sku_prices = {**act.get("sku_prices", {}), **act.get("computed_sku_prices", {}),
                      **act.get("ui_confirmed_sku_prices", {})}
        if act.get("plan") and (ROOT / act["plan"]).exists():
            plan = json.loads((ROOT / act["plan"]).read_text())
            for record in plan.get("ready", []):
                sku_prices.setdefault(record["sku_id"], record["proposed_price"])
        sku_prices = dict(sku_prices)
        for sku, override in overrides.items():
            if "registration_price" in override:
                sku_prices[sku] = override["registration_price"]
        if not sku_prices and act.get("article") == "YX9354001":
            sku_prices = {"1124109478": None, "1196357917": None, "1196357918": None}
        for sku, price in sku_prices.items():
            awaiting_full_readback = not audit_path and ("await_readback" in stage or act.get("readback_refresh_pending"))
            status = ("已提交，待逐SKU读回" if awaiting_full_readback else
                      "审核中" if "pending_review" in stage else "报名成功")
            origin = "existing" if stage == "already_enrolled" else "new_ui_submission"
            override = overrides.get(sku, {})
            duplicate_ids = {str(x) for x in act.get("duplicate_existing_sku_ids", [])}
            if sku in duplicate_ids:
                origin = "existing_duplicate"
                status = "原有报名，价格待读回"
                price = None
            row = build_row(activity_id, sku, override.get("registration_price", price),
                            override.get("status", status), origin,
                            "导入成功，待逐SKU读回核验" if awaiting_full_readback else "得物商家后台已报名列表", override)
            if row:
                activity_rows.append(row)
    # A manual SKU submission may postdate the last full export. It is
    # explicit enrollment evidence and remains separately sourced until the
    # refreshed readback contains that SKU. Ready/hold plans do not qualify.
    seen_skus = {r["sku_id"] for r in activity_rows}
    if registered:
        for sku, price in act.get("ui_confirmed_sku_prices", {}).items():
            if sku in seen_skus:
                continue
            override = overrides.get(sku, {})
            row = build_row(activity_id, sku, price, override.get("status", "报名成功"),
                            "new_ui_submission", "本场后台手动提交及已报名成功状态", override)
            if row:
                activity_rows.append(row)
    if stage.startswith("failed") and act.get("failed_report"):
        failure_rows = read_xlsx(act["failed_report"])
        failure_columns = {name: ix for ix, name in enumerate(failure_rows[1])}
        for raw in failure_rows[2:]:
            sku = ident(raw[failure_columns["SKUID"]])
            override = {"article_no": raw[failure_columns["货号"]],
                        "style": raw[failure_columns["款式"]],
                        "product_name": raw[failure_columns["商品名称"]],
                        "channel": raw[failure_columns["适用渠道"]],
                        "inventory": raw[failure_columns["活动库存"]],
                        "note": raw[failure_columns["失败原因"]]}
            override.update(overrides.get(sku, {}))
            row = build_row(activity_id, sku, number(raw[failure_columns["商品报名价"]]),
                            act.get("reason", "提交失败"), "failed", act["failed_report"], override)
            if row:
                activity_rows.append(row)
    # Only explicit hold records appear as not yet enrolled. Ready plans alone
    # never become reported registrations.
    if activity_id in plans:
        held = plans[activity_id].get("hold", [])
        expanded_held = []
        for record in held:
            if record.get("sku_id"):
                expanded_held.append(record)
            elif record.get("article_no") == "YX9354001":
                # Membership is an SPU discount enrollment. Keep the known
                # three SKU identities, but do not invent an unfilled price.
                for sku, info in sku_index.items():
                    if info.get("article_no") == record["article_no"]:
                        expanded_held.append({**record, "sku_id": sku, "proposed_price": None})
        for record in expanded_held:
            if record.get("article_no") != "YX9354001":
                continue
            if record["sku_id"] in {r["sku_id"] for r in activity_rows}:
                continue
            hold_status = "未报名，用户已确认待提交" if meta.get("moon_user_confirmed") else "未报名，待用户确认"
            row = build_row(activity_id, record["sku_id"], record.get("proposed_price"),
                            hold_status, "hold", "可报名商品及活动规则", overrides.get(record["sku_id"]))
            if row:
                activity_rows.append(row)
    rows.extend(activity_rows)
    if registered:
        if act.get("readback_refresh_pending"):
            gaps.append({"activity_id": activity_id, "name": act["name"],
                         "missing": "最新提交后全量读回待更新",
                         "sku_count": sum(was_enrolled(row) for row in activity_rows)})
        if "await_readback" in stage and not audit_path and not act.get("readback_refresh_pending"):
            gaps.append({"activity_id": activity_id, "name": act["name"],
                         "missing": "逐SKU实际报名价及状态读回",
                         "sku_count": sum(was_enrolled(row) for row in activity_rows)})
        if not meta.get("start") or not meta.get("end"):
            gaps.append({"activity_id": activity_id, "name": act["name"], "missing": "活动开始和/或结束时间"})
        for row in activity_rows:
            if not was_enrolled(row):
                continue
            if row["article_no"] == "YX9354001" and was_enrolled(row) and row["estimate_mode"] in ("待核实", "条件测算"):
                gaps.append({"activity_id": activity_id, "name": act["name"], "sku_id": row["sku_id"],
                             "missing": "本场后台预估到手价及商家承担满减，当前未核实"})
            if row["registration_price"] is None and activity_id != "3902516":
                gaps.append({"activity_id": activity_id, "name": act["name"], "sku_id": row["sku_id"], "missing": "逐SKU实际报名价"})
            if row["current_bid"] is None and not row.get("current_bid_display") and activity_id != "3902516":
                gaps.append({"activity_id": activity_id, "name": act["name"], "sku_id": row["sku_id"], "missing": "逐SKU原出价"})
    if meta.get("old_base_verification_pending"):
        gaps.append({"activity_id": activity_id, "name": act["name"], "sku_id": "1124109478",
                     "missing": "旧会员基础SKU报名状态、折扣及到手价待核对"})
    counts = Counter(row["status"] for row in activity_rows if was_enrolled(row))
    activity_summaries.append({
        "activity_id": activity_id, "name": meta.get("name", act["name"]),
        "start": meta.get("start"), "end": meta.get("end"), "stage": stage,
        "registered_sku": sum(counts.values()), "new_submitted_sku": act.get("new_sku_submitted", 0),
        "valid_sku": sum(v for k, v in counts.items() if k in ("有效", "报名成功")),
        "pending_sku": None if not (audit_path or spu_audit_path) and ("await_readback" in stage or act.get("readback_refresh_pending")) else counts.get("审核中", 0),
        "held_sku": sum(row["origin"] == "hold" for row in activity_rows),
        "failed_sku": sum(row["origin"] == "failed" for row in activity_rows),
        "moon_user_confirmed": meta.get("moon_user_confirmed", False),
        "articles": sorted(set(row["article_no"] for row in activity_rows if was_enrolled(row))),
        "reason": act.get("reason", act.get("note", "")),
        "stacking": meta.get("stacking", act.get("stacking", act.get("ui_rules", ""))),
        "full_reduction_rule": meta.get("full_reduction_rule", ""),
        "source": meta.get("time_source", "得物商家后台实时读取"),
    })

keys = [(r["activity_id"], r["sku_id"]) for r in rows]
if len(keys) != len(set(keys)):
    raise ValueError("Duplicate activity-SKU row")
rows.sort(key=lambda r: (r["article_no"], r["sku_id"], r["activity_id"]))
data = {"as_of": META.get("as_of", datetime.now().astimezone().isoformat(timespec="minutes")),
        "phase": META.get("phase", "报名进行中"), "rows": rows,
        "activities": activity_summaries, "gaps": gaps,
        "catalog_source": CAT["source"],
        "source_paths": sorted(set([CAT["source"], str(bid_path)] +
                                   [r["source"] for r in rows if r["source"].startswith("/")])),
        "summary": {"new_submitted_sku": sum(a["new_submitted_sku"] for a in activity_summaries),
                    "registered_sku_records": sum(a["registered_sku"] for a in activity_summaries),
                    "registered_articles": len(set(r["article_no"] for r in rows if was_enrolled(r))),
                    "held_sku_records": sum(a["held_sku"] for a in activity_summaries),
                    "failed_sku_records": sum(a["failed_sku"] for a in activity_summaries)}}
REPORT.mkdir(exist_ok=True)
(REPORT / "report_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
(REPORT / "missing_fields.json").write_text(json.dumps(gaps, ensure_ascii=False, indent=2))
print(json.dumps({"summary": data["summary"], "missing_fields": len(gaps),
                  "registered_activities": [a["activity_id"] for a in activity_summaries if a["registered_sku"]]}, ensure_ascii=False))
