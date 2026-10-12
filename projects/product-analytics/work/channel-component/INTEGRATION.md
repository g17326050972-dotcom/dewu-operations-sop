# 流量来源独立组件

本目录仅含组件资产及合成 fixture 测试，尚未修改 Site checkout 或发布。

1. 将 `channel-section.css` 内容加入已有内嵌 `<style>`。
2. 将 `channel-section.html` 插到现有每日读数表之后、footer 之前。
3. 先初始化 `window.CHANNEL_DATA`，再加载/内嵌 `channel-section.js`；把组件脚本放在 `offlineApp` 前，避免首次 `render()` 时接口尚未定义。
4. 在现有 `render()` 尾部调用 `window.renderChannelSection?.(codes[0])`。核心两款模式显示第一款的渠道；切换“所选单款”后按所选货号刷新。也可由 root 添加一个独立渠道商品选择器，继续调用同一接口。

数据接口：

```js
window.CHANNEL_DATA = {
  dates: ['2026-10-02', /* ... */ '2026-10-08'],
  channels: [
    { id: 'competition', name: '商品竞争力', parent_id: null },
    { id: 'search', name: '商品搜索', parent_id: 'competition' }
    // 提供完整 6 个一级渠道及已核实的所有子渠道；顺序即展示顺序。
    // 新品保量可新增 {id:'new_product_support',name:'新品保量',parent_id:'competition'}。
  ],
  products: {
    YX9524001: {
      name: '商品简称',
      source_status: 'not_exposed_in_backend',
      source_note: '已核验单品分析，仅有核心指标，未提供流量分析或渠道明细入口。',
      days: {} // 没有渠道来源时不把核心指标总PV塞进days伪装渠道日记录。
    },
    YX9354001: {
      name: '月光舞裙', // 可选
      days: {
        '2026-10-08': {
          total: 288,
          values: { competition: 84, search: 80 },
          reported_changes: {
            total: { pct: -22.58, comparison_date: '2026-10-07' },
            competition: { pct: -29.41, comparison_date: '2026-10-07' }
          }
        }
      }
    }
  }
};
```

`pct` 是百分数数值，如 `-22.58` 表示 `-22.58%`。`reported_changes` 可继续保留在源数据，不在界面重复展示，也不用于推算历史 PV。缺失日、缺失渠道可省略或写 `null`；只有实采 0 才写 `0`。`total` 保留后台全部 PV 原值，不从父子渠道推导。

已确认后台未提供渠道入口时，保留该商品元数据，写 `source_status: 'not_exposed_in_backend'`、具体核验 `source_note`，并保持渠道 `days: {}`。组件显示“后台当前未提供该商品的渠道来源明细”和说明，用户仍可切换经营趋势。只有核心指标总 PV 时也不能当作完整渠道来源记录。

精确增减仅使用所选双日的实采值。占比以当前商品全部 PV 为分母，包含子渠道行；下降渠道内份额只在双日 6 个一级渠道全部实采、且各自合计与后台全部 PV 一致时显示，不把它称作净下降贡献。子渠道不纳入一级合计或下降份额。任一日合计不一致时明确报警，下降份额留空。

总 PV 摘要下方在双日一级完整对账通过时归纳前三个最大减少来源和增加渠道抵消量；总增时改为前三个最大增加来源和减少渠道抵消量。它只陈述数值分解，不推测投放或商品原因。新增任意子渠道会动态缩进显示，不要求固定 4 个子级，也不影响一级汇总。

窄屏可读性：一级渠道增减采用 6 行 HTML/CSS 正负条形，渠道名与增减值固定 14px，只有中间条宽随空间变化；正负两侧共享绝对值刻度。渠道折线在 480px 以下将 SVG 日期/刻度/点值提高到 24 个 SVG 单位，缺失提示为 18，另增加图内留白避免裁剪。大屏文字仍保持原 12px。

验证：运行 bundled Node 的 `validate-component.mjs`。这个脚本使用最小 DOM 契约和明确标记的合成数据，覆盖父子层级、总 PV、子渠道分母、真实 0、断线、日期切换、后台环比隔离及空态。root 集成后仍需在网站预览中检查手机排版和已有商品切换。
