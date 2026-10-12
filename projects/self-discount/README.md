# 自建折扣

入口：[预出价与折扣技能](../../skills/dewu-confirm-bid-discount/SKILL.md)。技能目录包含纯本地价格计算器。

```sh
python skills/dewu-confirm-bid-discount/scripts/price_for_takehome.py --target 159 --discount 8
```

命令从仓库根目录执行。先确认现有预出价，按最新货盘 E 列折扣和 F 列目标到手价处理本次货号，不重复新增出价，不将所有款统一为 8 折。升级礼盒价格与成本规则见[经营口径](../../docs/business-rules.md)。

活动 ID、报名范围与有效时间使用当前后台。在线或模板报名后检查处理结果，再回读实际报名价、折扣和到手价；上传成功不能替代报名成功的证据。
