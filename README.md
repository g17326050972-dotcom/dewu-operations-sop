# 得物运营 SOP

最近更新：2026-10-17；首次整理：2026-10-12。归档「得物运营SOP」分区的 7 个项目，保留 4 个可复用技能、业务规则、源代码、报表页面与校验方法。

仓库已由所有者设为 **Public**，可直接分享和下载。示例包含已选择公开的历史经营汇总和测算；原始订单、售后明细、客户联系方式、登录凭据和云站点部署身份文件不入库。

分享入口：[仓库首页](https://github.com/g17326050972-dotcom/dewu-operations-sop) · [下载最新 ZIP](https://github.com/g17326050972-dotcom/dewu-operations-sop/archive/refs/heads/main.zip) · [本次更新说明](docs/updates/2026-10-17.md)。这两个分享地址沿用不变，更新后可重新下载最新内容。

可浏览的报告：[商品日报](https://dewu-product-daily-trends.lucky-fawn-8231.chatgpt.site/) · [历史周报 · 可切换周次](https://dara-weekly-20260831.lucky-fawn-8231.chatgpt.site/)。仓库内也保留对应静态文件；报告截止日以页面标注为准。

## 项目入口

| 项目 | 内容 | 当前交付状态 |
| --- | --- | --- |
| [得物周报](projects/weekly-report/README.md) | 订单售后核对、退款剔除、收藏率、得物推 ROI、引力验收和内容链接、月度利润历史脚本 | 4 期历史周报、周次切换及指标对照；保留各期查询快照与核对口径 |
| [新品上架](projects/new-product/README.md) | 货盘、商品图片、属性、礼盒规格、草稿、上架核验 | 已有技能和操作流程 |
| [得物货品池编码填写](projects/merchant-pool-code/README.md) | 品牌礼盒及两类升级礼盒的商家编码、批量导入和回读 | 已有技能和操作流程 |
| [出价/自建折扣](projects/self-discount/README.md) | 按授权处理出价、多款优先官方表格报名、到手价校验 | 已加入 10 月 14 日4款批量导入并审核通过的流程 |
| [活动报名](projects/activity-enrollment/README.md) | 官方模板检查、货号交集、活动毛利门槛、导入文件和报名结果核验 | 历史脚本归档；执行前需提供当前数据与活动规则 |
| [商品数据分析](projects/product-analytics/README.md) | 商品日报、两周对比、渠道、年龄、引力内容及得物推采集规范 | 新增 10 月 14 日发布版本，数据截至 10 月 13 日；得物推近7天要求已写入技能，历史缺口保留 |
| [优化落地](projects/action-plan/README.md) | 独立行动方案、利润与预算、内容和推广排期、验收节点 | 10 月 10 日方案页面；方案不代表已执行 |

流程：新品草稿与上架 → 货品池编码 → 预出价与自建折扣 → 活动报名 → 日报/周报 → 独立优化方案。

## 快速使用

Python 3.10+；核心核对脚本依赖 `openpyxl`。历史绘图脚本另依赖 `matplotlib`。建议在虚拟环境中安装：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python tools/validate_bundle.py

# 计算到手价 159 元、8 折时的整数出价候选，不修改后台
python skills/dewu-confirm-bid-discount/scripts/price_for_takehome.py --target 159 --discount 8

# 重建随仓库附带的 2026-10-05 至 2026-10-11 周报示例
python projects/weekly-report/build_snapshot.py

# 浏览器打开 http://127.0.0.1:8000 即可查看
python -m http.server 8000 --bind 127.0.0.1 --directory projects/weekly-report/output/site
```

也可直接打开各项目 `examples/` 中的 `index.html`。示例构建器保留对应周的日期、分析文字和图表逻辑；制作新周报需更新全部证据及文字，不能仅替换日期。

`skills/` 中 4 个目录包含 `SKILL.md`、参考资料与代理配置，可供支持本地技能的客户端使用。2026-10-15已根据后续明确要求更新出价/自建折扣和商品分析两个仓库副本；本机安装目录及定时任务不在本次同步范围。技能描述后台操作步骤，本仓库不包含登录态或无人值守后台采集服务。继续操作前读取当前货盘和后台，沿用本次用户授权的范围。

## 使用边界与索引

- [经营口径](docs/business-rules.md)：礼盒成本、折扣计算、销售及利润、ROI 和引力时间口径。
- [项目来源和迁移说明](docs/source-map.md)：7 个项目的归档范围、历史依赖与未包含内容。
- [数据管理](docs/data-handling.md)：本地私有输入、上传范围及报告分享。
- [验收记录](docs/validation.md)：本次验证结果和未验证范围。
- [导入清单](docs/import-manifest.json)：复制文件的来源分类、大小和 SHA-256。
- [执行记录模板](templates/operation-log.csv)：逐款记录计划、提交和回读结果。

日期、活动编号、费率、价格、任务状态和站点地址均是历史证据。再次执行时以当次后台及最新货盘为准。准备、保存、提交、审核通过、实际生效分别记录。

仓库未附开源许可证；公开可查看不等于对代码、商品素材和数据授予任意再使用许可。
