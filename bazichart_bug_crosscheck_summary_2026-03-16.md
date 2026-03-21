# BaZiChart Bug 交叉对比总结

日期：2026-03-16

对比来源：
- Claude 清单：[bazichart-bugs.md](/Users/mars/Desktop/bazichart-bugs.md)
- 我方检查报告：[website_bug_check_report_2026-03-16.md](/Users/mars/Desktop/website_bug_check_report_2026-03-16.md)

## 总结结论

Claude 的清单整体方向是对的，但不同条目的确定性不同。更适合拆成三类：

1. 已确认问题
2. 高概率问题，需再复现
3. 数据质量或体验问题，不应直接当阻断 bug

## 一、已确认问题

### 1. Google Fonts 全站加载失败

结论：已确认

说明：
- 浏览器控制台已抓到 `fonts.googleapis.com` 加载失败
- 这和 Claude 的 `#2` 一致

影响：
- 字体回退
- 控制台报错
- 东方风格排版不稳定

### 2. 名人页查看命盘链接写死 `hour=6`

结论：已确认

代码证据：
- [FamousListPage.jsx](/Users/mars/Claude-Workspace/destiny-platform/bazichart-frontend/src/pages/FamousListPage.jsx#L193)

说明：
- 这和 Claude 的 `#7` 一致
- 属于明确代码问题

### 3. 日期没有按年月动态校验

结论：基本确认

说明：
- 表单中存在固定 `1-31` 天选项生成逻辑
- 这和 Claude 的 `#9` 一致

影响：
- 用户可以选到 2 月 31 日、4 月 31 日等无效日期

### 4. `Ma Shan Zheng` 相关字体问题存在

结论：问题存在，但表述应修正

说明：
- Claude `#10` 说“从未导入”不完全准确
- 实际情况是：代码多处引用该字体，但依赖 Google Fonts 外链，当前环境加载失败

相关文件：
- [ChartReveal.css](/Users/mars/Claude-Workspace/destiny-platform/bazichart-frontend/src/components/ChartReveal/ChartReveal.css)
- [PsychologyPanel.jsx](/Users/mars/Claude-Workspace/destiny-platform/bazichart-frontend/src/components/PsychologyPanel.jsx#L81)

## 二、高概率问题

### 1. CityPicker 省份选择器/城市加载状态异常

结论：高概率成立，但我本次未稳定复现

对应 Claude：
- `#1`

代码证据：
- [CityPicker.jsx](/Users/mars/Claude-Workspace/destiny-platform/bazichart-frontend/src/components/CityPicker.jsx#L389)
- [CityPicker.jsx](/Users/mars/Claude-Workspace/destiny-platform/bazichart-frontend/src/components/CityPicker.jsx#L400)

说明：
- `selectedCountry`、`selectedProvince` 是组件内部状态
- 城市输入框会在 `loading` 或缺省份时 disabled
- 从代码结构看，路由切换后状态错位是有可能发生的

建议：
- 这条应作为后续第一优先级复现和修复项

### 2. MBTI 类型名缺失

结论：高概率成立

对应 Claude：
- `#3`

代码证据：
- [PsychologyPanel.jsx](/Users/mars/Claude-Workspace/destiny-platform/bazichart-frontend/src/components/PsychologyPanel.jsx#L391)

说明：
- 前端直接读取 `MBTI倾向`
- 如果后端返回空值，前端没有明显强兜底

### 3. Recharts 初始尺寸异常

结论：可信，但我本次未独立抓到同一条控制台日志

对应 Claude：
- `#6`

说明：
- 该类报错与当前 `ResponsiveContainer` 使用方式匹配
- 值得纳入修复列表

### 4. 五行计数显示 0

结论：高概率是真问题，但建议改写描述

对应 Claude：
- `#4`

建议改写为：
- “五行计数动画可能未触发，导致显示为 0”

原因：
- 组件里的 `CountUp` 依赖 `IntersectionObserver`
- 更像渲染/动画触发问题，不像纯数据缺失

## 三、应降级处理的问题

### 1. 流年评级全为“中吉”

对应 Claude：
- `#5`

判断：
- 更像业务数据质量问题
- 需要先核对后端返回值，不应直接定义为前端 bug

### 2. 名人国籍标注历史错误

对应 Claude：
- `#8`

判断：
- 这是内容/数据源问题
- 不是前端实现 bug

### 3. 合婚性别按钮、学习菜单、语言切换器

对应 Claude：
- `#11`
- `#12`
- `#13`

判断：
- 更偏体验缺口或功能未完成
- 不建议和阻断 bug 混列

## 四、Claude 清单未覆盖，但应保留的问题

### 1. AuthGate 密码说明存在全角/半角混淆风险

说明：
- 代码实际匹配的是半角 `Mars2026!`
- 如果文档或人工说明误写成全角，会导致用户无法进入站点

### 2. 首屏资源体积过大

说明：
- 构建已通过，但首屏资源偏重
- 属于明显性能风险，不是功能阻断

## 五、建议的合并优先级

1. CityPicker 异常复现与修复
2. 字体外链失败
3. 五行计数显示异常
4. 日期无效值选择
5. 名人页 `hour=6` 硬编码
6. MBTI 空值兜底
7. 数据质量项：流年评级、名人国籍

## 六、当前建议

目前先不进入修复。

后续如果开始维修，建议先从：

1. `CityPicker`
2. `字体`
3. `五行计数`

这三个点开始。
