# BaZiChart 网站 Bug 检查报告

检查时间：2026-03-16

检查范围：
- 前端：`/Users/mars/Claude-Workspace/destiny-platform/bazichart-frontend`
- 后端：`/Users/mars/Claude-Workspace/destiny-platform/bazichart-engine/bazichart-engine`

执行情况：
- 本地后端已启动并通过健康检查
- 本地前端已启动并通过构建验证
- `/api/interpret` 本地请求成功返回完整排盘数据
- 浏览器侧完成了首页与排盘页的基础打开检查

## 一、结论

本次检查没有发现“后端排盘接口不可用”这类阻断性故障，但确认存在 3 类明显问题：

1. AuthGate 口令信息存在全角/半角不一致风险
2. 页面依赖 Google Fonts，当前环境下出现稳定的字体加载报错
3. 前端首屏资源体积过大，存在明显性能风险

另外，本地构建通过，后端 `/api/health` 和 `/api/interpret` 均工作正常，说明当前核心排盘链路的服务端部分是通的。

## 二、已确认问题

### 1. AuthGate 口令存在全角/半角不一致风险

严重度：高

证据：
- 前端密码门禁实现位于 `src/components/AuthGate.jsx`
- 代码中的 `CORRECT_HASH` 为：
  `91da1fafbb80caffc3809ef608788bd0db79bf95b7e482bff51e19b932fb75d4`
- 我核对了两种字符串的 SHA-256：
  - `Mars2026!` -> `91da1fafbb80caffc3809ef608788bd0db79bf95b7e482bff51e19b932fb75d4`
  - `Mars2026！` -> `b8202492dfa6a8d5748dcb495975296f406944509d67632aef316f21b5b565d0`

结论：
- 代码实际接受的是半角感叹号版本
- 如果团队内部或用户文档传播成全角版本，会直接导致无法通过门禁

影响：
- 用户会误以为站点或密码系统故障
- 自动化测试、联调和人工验收都容易卡在入口阶段

建议：
- 不修改 AuthGate 逻辑前提下，统一所有文档和口头说明中的密码写法
- 在内部说明中明确标注“英文半角 `!`”

### 2. Google Fonts 请求失败，页面出现稳定控制台错误

严重度：中

证据：
- 浏览器控制台记录到以下错误：
  - `ERR_TIMED_OUT @ https://fonts.googleapis.com/...`
  - `ERR_CONNECTION_CLOSED @ https://fonts.googleapis.com/...`
- 相关入口：
  - `index.html`
  - 全局字体依赖包含 `Cormorant Garamond`、`Ma Shan Zheng`、`Noto Serif SC`

结论：
- 页面当前强依赖外链字体
- 在网络受限、代理异常、Google 服务不可达环境下，会出现字体加载失败、样式回退和首屏闪烁

影响：
- 控制台持续报错
- 首屏字体风格不稳定
- 可能造成 FOUT/FOIT 和排版跳动

建议：
- 后续优先改为本地托管关键字体，或为中文正文设置更稳的本地 fallback

### 3. 前端资源体积过大，首屏性能风险明显

严重度：中到高

证据：
- `npm run build` 通过，但产物体积偏大：
  - `dist/assets/index-SBLSFWzp.js`：`2046.86 kB`
  - gzip 后：`787.86 kB`
  - `dist/assets/outermost-ring-BUMZX5Yn.png`：`3508.84 kB`
- Vite 明确给出 chunk 过大警告

结论：
- 当前站点尤其是齿轮盘面资源过重
- 即使功能正常，弱网和移动端首屏体验也会明显变差

影响：
- 首屏加载慢
- 渲染阻塞更明显
- 低性能设备更容易掉帧

建议：
- 不动齿轮动画逻辑的前提下，优先检查静态图资源压缩和分包策略
- 这是性能问题，不是立即阻断，但应尽快进入修复列表

## 三、本次未发现故障的部分

### 1. 后端服务正常

验证结果：
- `GET /api/health` 返回：
  - `{"status":"ok"}`
- 本地 `uvicorn api:app --host 127.0.0.1 --port 8000` 可正常启动

### 2. 排盘接口正常返回数据

验证方式：
- 本地调用 `POST /api/interpret`
- 使用测试数据：`1990-01-01 12:00 北京 male`

结果：
- 接口成功返回：
  - `input`
  - `four_pillars`
  - `canggan`
  - `shishen_per_pillar`
  - `nayin`
  - `shensha`
  - `wuxing_analysis`
  - 其他结果字段

结论：
- 本次没有发现后端排盘主链路故障

### 3. 前端可正常构建

验证结果：
- `npm run build` 成功

结论：
- 当前前端不存在构建级别的阻断错误
- 问题主要集中在运行时体验、入口口令一致性、外部资源依赖和性能层面

## 四、建议的修复优先级

P0：
- 统一 AuthGate 密码说明，消除全角/半角歧义

P1：
- 处理 Google Fonts 外链依赖，至少降低其失败时的页面影响

P1：
- 优化首屏超大图片与主 bundle 体积

P2：
- 再进入 UI/UX 结构优化，包括结果页导航、四柱信息分层、大运改版等

## 五、验证命令记录

后端健康检查：

```bash
curl -s http://127.0.0.1:8000/api/health
```

排盘接口验证：

```bash
curl -s -X POST http://127.0.0.1:8000/api/interpret \
  -H 'Content-Type: application/json' \
  -d '{"year":1990,"month":1,"day":1,"hour":12,"minute":0,"gender":"male","city":"北京","timezone":"Asia/Shanghai","longitude":116.39723}'
```

前端构建验证：

```bash
npm run build
```
