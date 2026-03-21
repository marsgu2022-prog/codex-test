# 模板清单与盘面情况

检查目录：`bazichart-engine/templates/`

## 总览

当前模板文件共 7 个：

| 模板 | 用途 | 是否有盘面 | 备注 |
|---|---|---|---|
| [base.html](/Users/mars/codex-test/bazichart-engine/templates/base.html) | 全站基础骨架，加载 Tailwind/Alpine/全局样式 | 否 | 只提供布局壳 |
| [index.html](/Users/mars/codex-test/bazichart-engine/templates/index.html) | 首页落地页 | 否 | 只有 `fade-in` 入场动效 |
| [reading.html](/Users/mars/codex-test/bazichart-engine/templates/reading.html) | 解读输入、加载、结果页 | 是 | 盘面主模板 |
| [dashboard.html](/Users/mars/codex-test/bazichart-engine/templates/dashboard.html) | 用户中心/档案页 | 否 | 账号与档案管理 |
| [classic.html](/Users/mars/codex-test/bazichart-engine/templates/classic.html) | 古籍参考占位页 | 否 | 仅占位内容 |
| [components/header.html](/Users/mars/codex-test/bazichart-engine/templates/components/header.html) | 顶部导航 | 否 | 登录态切换 |
| [components/footer.html](/Users/mars/codex-test/bazichart-engine/templates/components/footer.html) | 底部页脚 | 否 | 法务与版权信息 |

## 逐项说明

### 首页：index.html

位置：
- [index.html:5](/Users/mars/codex-test/bazichart-engine/templates/index.html#L5)
- [index.html:35](/Users/mars/codex-test/bazichart-engine/templates/index.html#L35)

用途：
- 首页 Hero
- 真实解读案例展示
- 信任背书与 CTA

盘面情况：
- 没有四柱盘面
- 没有 `canvas`
- 没有 `svg/SVG`
- 没有 `ChartReveal`
- 没有 `gear`

动画情况：
- 只有 `fade-in` 卡片入场延迟动画
- 动画样式定义在 [custom.css:82](/Users/mars/codex-test/bazichart-engine/static/css/custom.css#L82)

### 解读页：reading.html

位置：
- [reading.html:152](/Users/mars/codex-test/bazichart-engine/templates/reading.html#L152)
- [reading.html:183](/Users/mars/codex-test/bazichart-engine/templates/reading.html#L183)
- [reading.html:200](/Users/mars/codex-test/bazichart-engine/templates/reading.html#L200)
- [reading.html:218](/Users/mars/codex-test/bazichart-engine/templates/reading.html#L218)

用途：
- 输入出生信息
- 展示 loading 状态
- 展示解读结果与右侧数据面板

盘面情况：
- 有盘面
- 盘面内容包括：
  - 四柱排盘
  - 五行分布
  - 格局

动画情况：
- Loading 使用 `bagua-spin`
- 这是一个旋转太极图标，不是 `canvas/SVG` 盘面动画

### Dashboard：dashboard.html

位置：
- [dashboard.html:9](/Users/mars/codex-test/bazichart-engine/templates/dashboard.html#L9)
- [dashboard.html:39](/Users/mars/codex-test/bazichart-engine/templates/dashboard.html#L39)

用途：
- 注册/登录
- 用户档案管理
- 会员功能占位

盘面情况：
- 无盘面

### Classic：classic.html

位置：
- [classic.html:2](/Users/mars/codex-test/bazichart-engine/templates/classic.html#L2)

用途：
- 古籍参考占位页

盘面情况：
- 无盘面

### Base/Header/Footer

位置：
- [base.html:1](/Users/mars/codex-test/bazichart-engine/templates/base.html#L1)
- [header.html:1](/Users/mars/codex-test/bazichart-engine/templates/components/header.html#L1)
- [footer.html:1](/Users/mars/codex-test/bazichart-engine/templates/components/footer.html#L1)

用途：
- 站点基础框架、导航、页脚

盘面情况：
- 无盘面

## 搜索结果

在 `templates/` 中搜索以下关键词：
- `ChartReveal`
- `gear`
- `canvas`
- `SVG/svg`
- 动画关键词

结果：
- 未发现 `ChartReveal`
- 未发现 `gear`
- 未发现 `canvas`
- 未发现 `svg/SVG` 动画
- 仅发现首页 `fade-in` 动效和解读页的 `bagua-spin` 类使用

## 结论

- 真正带“盘面”的模板只有 [reading.html](/Users/mars/codex-test/bazichart-engine/templates/reading.html)
- 首页 [index.html](/Users/mars/codex-test/bazichart-engine/templates/index.html) 目前没有盘面动画，只有普通入场动效
- 如果 Mars 明天要找“首页盘面动画”，答案是：当前模板层没有这套实现
