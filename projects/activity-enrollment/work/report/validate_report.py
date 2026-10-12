"""Read-only verification of the exported report against its canonical data."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def same_number(actual, expected, cell):
    if not isinstance(actual, (int, float)) or not math.isclose(actual, expected, abs_tol=1e-7):
        raise AssertionError(f"{cell}: {actual!r} != {expected!r}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    data = json.loads((HERE / "report_data.json").read_text())
    if args.final:
        assert not data["gaps"], f"Unresolved data fields: {len(data['gaps'])}"
    cached = openpyxl.load_workbook(args.workbook, data_only=True)
    formulas = openpyxl.load_workbook(args.workbook, data_only=False)
    assert cached.sheetnames == ["报名明细", "活动概览"]
    detail = cached["报名明细"]
    assert detail.max_row == len(data["rows"]) + 9
    assert detail["J9"].value == "实际价格折扣"
    assert formulas["报名明细"].freeze_panes == "C10"
    assert formulas["活动概览"].freeze_panes == "C11"
    assert "EnrollmentDetails" in formulas["报名明细"].tables
    assert "ActivitySummary" in formulas["活动概览"].tables
    errors = []
    for sheet in cached:
        for cells in sheet:
            errors.extend(f"{sheet.title}!{cell.coordinate}:{cell.value}" for cell in cells if cell.data_type == "e")
    assert not errors, errors
    checked_money = 0
    for index, record in enumerate(data["rows"], start=10):
        assert detail.cell(index, 1).value == record["article_no"]
        assert str(detail.cell(index, 19).value) == record["sku_id"]
        assert str(detail.cell(index, 21).value) == record["activity_id"]
        for column, field in ((9, "registration_price"), (12, "extra_merchant_reduction"),
                              (13, "estimated_received"), (14, "profit"), (15, "margin")):
            expected = record[field]
            if expected is not None:
                same_number(detail.cell(index, column).value, expected,
                            f"报名明细!{detail.cell(index, column).coordinate}")
                checked_money += 1
        if record["effective_discount"] is not None:
            same_number(detail.cell(index, 10).value, record["effective_discount"], f"J{index}")
        assert formulas["报名明细"].cell(index, 14).data_type == "f"
        assert formulas["报名明细"].cell(index, 15).data_type == "f"
        assert "疯狂周末" not in record["activity_name"]
        style = "".join(record["style"].split())
        assert not ("小米珠" in style and any(t in style for t in ("套装", "组合", "叠戴", "套组", "+", "＋")))
        if record["origin"] not in ("hold", "failed"):
            # The all-channel coupon is an old participation record retained
            # without modification; all new entries are official-only.
            if not (record["activity_id"] == "3902516" and record["origin"].startswith("existing")):
                assert record["channel"] == "品牌官方", record
            assert record["inventory"] in ("不限制", "无限制"), record
    assert sum(r["origin"].startswith("new") for r in data["rows"]) == data["summary"]["new_submitted_sku"]
    assert sum(r["origin"] not in ("hold", "failed") for r in data["rows"]) == data["summary"]["registered_sku_records"]
    overview = cached["活动概览"]
    same_number(overview["B4"].value, data["summary"]["new_submitted_sku"], "活动概览!B4")
    same_number(overview["D4"].value, data["summary"]["registered_sku_records"], "活动概览!D4")
    same_number(overview["F4"].value, data["summary"]["held_sku_records"], "活动概览!F4")
    same_number(overview["H4"].value, data["summary"]["failed_sku_records"], "活动概览!H4")
    cached.close()
    formulas.close()
    audit = {"workbook": str(args.workbook.resolve()), "final": args.final,
             "summary": data["summary"], "rows": len(data["rows"]),
             "checked_money_cells": checked_money, "formula_errors": errors,
             "missing_fields": len(data["gaps"]), "freeze_panes": ["C10", "C11"],
             "filters": ["EnrollmentDetails", "ActivitySummary"]}
    (HERE / "export_validation.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
