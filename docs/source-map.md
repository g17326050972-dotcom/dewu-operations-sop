# 项目来源和迁移说明

本次根据 Codex 侧栏「得物运营SOP」的 7 个项目整理，不复制聊天逐字记录。

| 原项目名称 | 本仓库目录 | 归档重点 |
| --- | --- | --- |
| 得物周报 | `projects/weekly-report` | 10 月 5—11 日可复建周报、核对器、9 月周报和月利润历史源码 |
| 新品上架 | `projects/new-product`、`skills/dewu-jewelry-new-product` | 现有技能和批量草稿流程 |
| 得物货品池编码填写 | `projects/merchant-pool-code`、`skills/dewu-merchant-pool-code` | 编码规则和导入/回读流程 |
| 自建折扣 | `projects/self-discount`、`skills/dewu-confirm-bid-discount` | 折扣、价格及验证脚本 |
| 活动报名 | `projects/activity-enrollment` | 筛选、模板与回读校验源代码 |
| 商品数据分析 | `projects/product-analytics`、`skills/dewu-product-analytics` | 分析技能、日报组件及 10 月 12 日草稿 |
| 优化落地 | `projects/action-plan` | 独立方案页面、生成器与规范 |

`import-manifest.json` 的 `files` 是直接复制的文件清单及复制时哈希；移植生成的两个入口脚本、清理后的汇总 JSON、样式提取和新增文档不在该原始复制清单中。整个交付目录的完整性以 `checksums.sha256` 为准。

迁移适配仅限周报示例构建器、订单核对器的输入路径与命令行参数。其他历史脚本尽量保留原样，包含日期、活动编号、源路径、运行库及未打包输入依赖。不能据语法检查推断所有历史业务流程已重新执行。

原始货盘、订单/售后/结算导出、批量报名工作簿、整批商品素材、聊天历史、浏览器状态和部署身份文件留在原电脑。仓库中只保留周报所需的 10 张商品实拍图副本及汇总结果。
