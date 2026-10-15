# 出价/自建折扣

入口：[出价与折扣技能](../../skills/dewu-confirm-bid-discount/SKILL.md)。技能目录包含纯本地价格计算器，已同步2026-10-14的批量报名要求。

```sh
python skills/dewu-confirm-bid-discount/scripts/price_for_takehome.py --target 159 --discount 8
```

命令从仓库根目录执行。优先复用现有预出价，按最新货盘 E 列折扣和 F 列目标到手价处理本次货号，不重复新增出价，不将所有款统一为8折。用户明确要求出价且不存在已有出价时，按已核实规格、资格及有依据的库存处理。已有编码完成记录可直接使用，不重复逐款检查编码页。升级礼盒价格与成本规则见[经营口径](../../docs/business-rules.md)。

多款优先使用官方Excel模板。10月14日已实测的“按照SPU维度设置折扣”只填SPU ID、折扣、库存，名称和货号由平台补全；库存-1代表不限制。实际使用时先确认当前模板仍支持该规则，导入后核对清单，再提交并回读审核结果。

[4款实测记录](../../skills/dewu-confirm-bid-discount/references/bulk-enrollment-20261014.md)与[原模板生成脚本](archive/20261014/fill-template.mjs)一并归档。脚本依赖本地官方模板和Codex的`@oai/artifact-tool`，包含固定历史货号，不是直接用于下一批商品的通用入口。

活动ID、报名范围与有效时间使用当前后台。上传、提交、审核通过分别记录，已正确报名的商品直接保留。此前为4款安排的5分钟跟进已按用户要求暂停，本仓库不创建或恢复定时任务。
