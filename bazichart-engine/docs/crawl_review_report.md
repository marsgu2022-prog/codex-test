# Astrotheme 抓取代码审查报告

审查对象：[crawl_astrotheme.py](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py)

审查范围：
- 新增分类：`media`、`visual_arts`、`spirituality`、`world_events`、`entertainment_stage`
- URL 拼接
- 翻页逻辑
- 去重逻辑
- 异常处理

## 结论

新增 5 个分类的参数映射与 Astrotheme 当前筛选页一致，URL 拼接和基本翻页逻辑可用，现有去重逻辑能避免大部分同源/跨源重复写入。当前实现可以继续生产使用，但有 3 个中风险点需要 Mars 明早重点看。

## 主要发现

### 1. 中风险：旧状态迁移只覆盖“已跑完旧 5 类”的场景

位置：
- [crawl_astrotheme.py:40](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L40)
- [crawl_astrotheme.py:305](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L305)

说明：
- `FIRST_NEW_CATEGORY_INDEX = 6` 的设计与当前分类顺序一致，意味着旧版已完成 5 组职业时，会从 `media` 开始继续。
- 但迁移条件只处理 `next_url is None` 且 `category_index >= 5` 的完成态。
- 如果未来存在“旧版中途停在 category 1-4”的状态文件，这个索引会直接落到新数组顺序中，语义不再完全对应。

影响：
- 当前线上已完成旧 5 类时没有问题。
- 未来若恢复历史中断任务，可能从错误分类继续。

建议：
- 后续可把状态文件从“数组索引”改成“分类 key”。

### 2. 中风险：去重键只用 `name_en + birth_date`，对别名/大小写/重音字符不鲁棒

位置：
- [crawl_astrotheme.py:282](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L282)
- [crawl_astrotheme.py:340](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L340)
- [crawl_astrotheme.py:375](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L375)

说明：
- 当前逻辑能挡住完全相同的 `name_en + birth_date`。
- 对以下边界情况无能为力：
  - 同人异名，如简称、艺名、带重音字符版本
  - 空格、大小写、标点差异
  - `name_en` 缺失时的弱去重

影响：
- 现有数据文件内部未发现同键重复，但跨源仍可能保留“同人不同写法”的重复人物。

建议：
- 后续增加标准化步骤，例如 `strip/lower/去重音`。
- 可考虑把 `source_url slug` 作为辅助键。

### 3. 中风险：页面结构变化时，部分数据会被静默丢弃

位置：
- [crawl_astrotheme.py:94](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L94)
- [crawl_astrotheme.py:240](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L240)
- [crawl_astrotheme.py:372](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L372)

说明：
- `parse_result_page()` 依赖页面中 `Next` 文本和 `/astrology/` 链接。
- `parse_person()` 若标题、出生日期、出生时辰任一解析失败，会直接返回 `None`。
- 这种失败不会进入 `errors`，只会表现为“新增变少”。

影响：
- 网站改版时，任务可能继续运行，但产出下降且不易被第一时间发现。

建议：
- 以后可增加“关键字段缺失”的显式错误记录。
- 对 `Next` 链接和结果列表容器增加更严格选择器。

## 正向检查

### URL 拼接

位置：
- [crawl_astrotheme.py:22](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L22)
- [crawl_astrotheme.py:101](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L101)
- [crawl_astrotheme.py:108](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L108)

结论：
- 使用 `BASE_URL` + `urljoin()`，详情页和翻页 URL 拼接方式正确。
- 新增分类参数与 Astrotheme 当前职业筛选页一致：
  - `entertainment_stage` -> `categorie[1]=0|2|7`
  - `media` -> `categorie[4]=1|3`
  - `visual_arts` -> `categorie[7]=9`
  - `spirituality` -> `categorie[8]=10`
  - `world_events` -> `categorie[10]=12`

### 翻页逻辑

位置：
- [crawl_astrotheme.py:350](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L350)
- [crawl_astrotheme.py:360](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L360)
- [crawl_astrotheme.py:383](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L383)

结论：
- 支持从 `state.next_url` 续跑。
- 支持分类内多页抓取，并在无下一页时进入下一分类。
- `max_pages_per_category` 与 `max_records` 两个上限都生效。

### 异常处理

位置：
- [crawl_astrotheme.py:62](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L62)
- [crawl_astrotheme.py:356](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L356)
- [crawl_astrotheme.py:380](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L380)
- [crawl_astrotheme.py:392](/Users/mars/codex-test/bazichart-engine/scripts/crawl_astrotheme.py#L392)

结论：
- 网络请求有 3 次重试和递增退避，基础健壮性足够。
- 搜索页、详情页、翻页失败都会落到 `errors`。
- 但对“结构变化导致解析为空”的情况仍偏弱，见上面的中风险 3。

## 总评

当前代码可以继续夜间抓取，质量处于“可运行、但需要后续补监控”的状态。最值得后续优化的是：
- 状态迁移改为按分类 key
- 去重键标准化
- 把静默解析失败转成可观测错误
