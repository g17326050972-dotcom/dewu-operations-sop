# 报名汇总生成

根代理负责后台提交及核验，本目录只做本地报告；不读取浏览器、不提交报名、不写源货盘、不改外部导出。

## 最终更新

1. 根代理冻结 `work/enrollment_progress.json`，把本次实际已提交活动、数量、计划及读回 audit 路径填入 ledger。
2. 在 `work/report/activity_metadata.json` 填活动起止时间（后台实际时间精度；只显示分钟时不杜撰秒数）；仍未知时保持缺失，不按活动名称猜测。
3. 运行 `collect_report.py`，检查 `missing_fields.json`；再运行同一 `build_report.mjs` 输出正式文件。

```sh
/Users/nan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 work/report/collect_report.py
/Users/nan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node work/report/build_report.mjs --authoring-marked outputs/报名汇总.xlsx
```

本次创建操作的 authoring marker 已成功执行一次；同一次报告更新无需重复 marker。草稿保留在本目录，不向用户交付草稿。

## 活动元数据格式

```json
{
  "as_of": "2026-10-09 12:00:00",
  "phase": "报名核验完成，月光舞裙部分活动待确认",
  "activities": {
    "3595179": {
      "name": "后台完整活动名",
      "start": "2026-10-10 00:00:00",
      "end": "2026-10-11 23:59:59",
      "time_source": "得物活动详情",
      "moon_extra_merchant_reduction": 25,
      "stacking": "与满300减50券叠加，商家承担25元",
      "sku_overrides": {
        "1124109478": {
          "registration_price": 252,
          "estimated_received": 227,
          "estimate_evidence": "后台逐SKU预估到手价",
          "status": "报名成功"
        }
      }
    }
  }
}
```

上面的价格和时间只展示字段格式，未写入真实元数据。逐 SKU 原出价缺失时，可在 SKU override 写 `current_bid`。

## 数据含义及核验

- 一行是一条货号、SKU、活动记录。同一 SKU 参与多个活动保留多行。
- 新人及品牌首单 C 以下载的已报名读回为准，保留 5 个重复 SKU 的实际原价，且包含原有 YX9545001 基础礼盒；非货盘商品不计入报告。
- 只有 ledger 明确已提交/成功/原有报名时才报告已报名。计划 ready 不证明提交。Moon hold 行明确为未报名待确认。
- 固定全渠道活动跳过原因列在活动概览。原有满300减50券保留全渠道真实记录；9999占位价不当作售价。
- 品牌官方原出价来源为已下载出价列表。礼盒增量成本 13 元，货盘基础包装另保留在 14.5 元履约中。
- 所有已报 Moon 到手证据已逐场补齐：新人/C、学生A、双11A/B、特卖三场，以及品牌老客/运动/全类目两场明确核实 P-25；精选指定价实际252/279/283且到手相同，不扣25；多人团另按不叠加规则测算。旧会员 Moon 拟7折ceil280/310/315，若既有满300减50商家承担25时条件到手255/285/290，仍未报名待确认。
- 多人团后台到手价显示“-”，按不叠加商家优惠规则测算 P，不能归因成后台展示 P。原有新人及 C 的其他款、平价优品三款已读回 UI 到手等于报名价。
- 毛利额以报名价为起点，扣 MAX(报名价×22%,45)、14.5、报名价×10%、商品成本、礼盒增量及额外商家满减。毛利率以报名价为分母，费用保持保守口径。
- 到手价列为扣商家优惠后的商品预估金额，未扣平台费用和成本，不等于消费者实付款或商家净利润。排除规格同时检查“小米珠套装/组合/叠戴”等。
- `build_audit.json` 记录行数、独立毛利核对、公式错误扫描及两个还原后的输入变动重算测试。
- 最终生成后须查看三张预览图，确认两页排版，再用只读 openpyxl 检查实际 XLSX 的值/公式、筛选表及冻结窗格。不得用 openpyxl 作者化 XLSX。

- 旧会员活动最终下载仅有SPU折扣/状态/渠道/库存，不含SKU价格；12个当前在售SKU价格据原出价与已报名SPU折扣向上取整计算，不作为逐SKU UI价格读回。C列填报折扣与J列实际价格折扣分别展示。
- 正式导出后运行 `validate_report.py outputs/报名汇总.xlsx --final` 只读核验导出值、公式缓存、行数、筛选表、冻结窗格及全部已报字段。
