# 得物周报与利润核对

## 可直接查看和运行

- `examples/20261005-1011/site/index.html`：10 月 5—11 日静态周报，包含 TOP10 真实商品图、收藏率、退款剔除、优惠后引导支付 ROI、引力验收内容和链接。
- `examples/20261005-1011/*.json`：对应汇总证据，查询快照为 10 月 12 日；不含逐笔订单或客户信息。
- `build_snapshot.py`：从附带证据重建这份日期固定的示例，样式和脚本已本地化。
- `reconcile_orders.py`：读取同周订单、售后和商品导出，以货号汇总有效销售及待处理售后。

仓库根目录运行：

```sh
python projects/weekly-report/build_snapshot.py
python projects/weekly-report/reconcile_orders.py --manifest projects/weekly-report/config/sources.local.json --output projects/weekly-report/output/reconciliation
```

核对前复制 `config/sources.example.json` 为同目录 `sources.local.json`，配置统计起止日（含首尾日）、快照日期和 3 个 Excel 文件路径。相对路径以配置文件所在目录为基准；示例对应 `projects/weekly-report/data/private/`。这些输入和输出目录已被 Git 忽略。

导出表须保留平台中文原始表头。订单包括订单号、货号、商品名称、数量、出价金额、卖家承担优惠金额、支付时间、下单时间及订单状态；售后包括订单号、状态和退款金额；SPU 包括货号、支付金额、订单数、标题、类目、商详访问人数/次数及收藏用户数。实际精确字段见脚本。

遇到多行订单、数量不为 1、跨周支付、多笔成功退款、重复 SPU 或账目不符，程序应停止核查；不要用 `python -O` 禁用校验。输出仅为款级汇总，不能作为结算凭证。

## 当前示例核对结果

原支付金额 ¥41,307，剔除关闭订单 ¥16,185 后有效销售 ¥25,122。售后处理中风险金额 ¥1,463 单列，全部发生时的保守销售为 ¥23,659。125 笔支付订单、37 笔关闭、88 笔有效；TOP10 合计 ¥14,119。

得物推消耗 ¥4,639.75，优惠后引导支付金额 ¥8,774，ROI 1.89。引力本周新建 4、验收 2；查询时待验收 0。各项统计时间和归因口径以页面注明为准。

## 历史源码

`archive/20260907-0913/`、`archive/20260921-0927/` 保存此前周报源码；`archive/monthly-profit/` 保存 9 月订单利润核算、结算匹配与工作簿生成代码。历史数据、原始结算表、成本货盘和部分样式依赖未随仓库分发，使用前需补齐并修改路径。

升级礼盒每件额外 13 元成本、优惠和平台费用不能重复扣除等规则见[经营口径](../../docs/business-rules.md)。本次归档不重新计算 9 月利润，也不改变现有公开周报站点。
