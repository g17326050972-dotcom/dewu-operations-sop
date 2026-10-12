# 活动报名

本目录归档历史活动的筛选、毛利计算、官方模板生成和报名结果核验脚本。`work/` 保留原始相对布局；`work/report/` 为报名汇总生成器。

流程：读取最新货盘及官方模板 → 取本次指定货号和可报名 SKU 的交集 → 核查已有价、升级礼盒和活动成本 → 按当次门槛筛选 → 生成官方上传文件 → 在授权范围内提交 → 下载报名结果并核对实际价格、状态和数量。

| 脚本 | 用途 |
| --- | --- |
| `read_catalog.py`、`plan_activity*.py` | 读货盘、匹配并计算候选方案 |
| `audit_activity_template.py`、`inspect_activity_exports.py` | 识别官方模板和字段 |
| `build_activity_upload.mjs`、`audit_compact_activity.py` | 生成和核对导入文件 |
| `audit_readback_activity.py`、`audit_spu_2930783_actual_ceil.py` | 回读价格、状态、毛利及取整结果 |
| `work/report/` | 汇总执行记录和核对结果 |

这些脚本仍引用历史活动编号、本地路径和未入库的输入 JSON/XLSX，**不是克隆即运行的当前活动服务**。执行前逐个检查入口参数和输入文件，替换当次路径、费用和规则。部分 `.mjs` 使用 Codex 提供的 `@oai/artifact-tool`，该运行库未打包进仓库。

历史门槛和礼盒成本见[经营口径](../../docs/business-rules.md)。保留月光舞裙逐活动核对规则，成本不明款不自动报名。任务结果应区分未提交、处理中、已报名、审核中、失败和待人工核查。
