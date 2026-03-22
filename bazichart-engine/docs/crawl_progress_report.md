# 抓取进度报告

统计时间：2026-03-22 夜间  
统计目录：`bazichart-engine/data/`

## 1. 当前总体进度

来自 [pipeline_report.json](/Users/mars/codex-test/bazichart-engine/data/pipeline_report.json)：

- 总记录数：`22050`
- 有时辰：`8327`
- 无时辰：`13723`
- 有时辰占比：`37.76%`
- 已计算八字：`19539`
- 有时辰且已算八字：`7879`

## 2. Astrotheme 当前运行位置

来自 [astrotheme_crawl_state.json](/Users/mars/codex-test/bazichart-engine/data/astrotheme_crawl_state.json)：

- `category_index`: `7`
- `next_url`: `https://www.astrotheme.com/celestar/horoscope_celebrity_search_by_filters.php?page=6`
- `layout_version`: `2`

按当前分类顺序推算，`category_index = 7` 对应 `visual_arts`，说明当前夜间任务大概率正在视觉艺术分类中段继续抓取。

## 3. 每个分类已抓多少条

说明：
- 现有 `famous_people_astrotheme.json` 没有直接保存 `category_key`
- 以下数字按 `occupation` 标签反推，属于近似统计

基于 [famous_people_astrotheme.json](/Users/mars/codex-test/bazichart-engine/data/famous_people_astrotheme.json) 当前结果：

| 分类 | 估算条数 |
|---|---:|
| `entertainment_stage` | 4867 |
| `music` | 6538 |
| `politics` | 200 |
| `sports` | 298 |
| `writers` | 273 |
| `science` | 300 |
| `media` | 300 |
| `visual_arts` | 300 |
| `spirituality` | 0 |
| `world_events` | 0 |

说明：
- `music` 数字偏大，是因为当前 `classify_occupation()` 会对页面正文里出现 `singer/musician` 的人物附加“音乐家”标签，因此更像职业标签覆盖数，不是严格的爬虫分类批次数。
- `spirituality` 和 `world_events` 目前还没看到有效沉淀记录。

## 4. 有时辰 vs 无时辰

### Astrotheme 源数据

来自 [famous_people_astrotheme.json](/Users/mars/codex-test/bazichart-engine/data/famous_people_astrotheme.json)：

- 总数：`6538`
- 有时辰：`6538`
- 无时辰：`0`
- 有时辰占比：`100%`

### 统一库

来自 [unified_people.json](/Users/mars/codex-test/bazichart-engine/data/unified_people.json)：

- 总数：`22050`
- 有时辰：`8327`
- 无时辰：`13723`
- 有时辰占比：`37.76%`

## 5. 新 5 个分类的增量预估

本次按任务关注的 5 个分类：

- `media`
- `visual_arts`
- `spirituality`
- `world_events`
- `entertainment_stage`

估算口径：
- 先按 `occupation` 标签筛出这 5 类在 Astrotheme 数据中的记录
- 再和 Astro-Databank 主源做 `name + birth_date` 对比
- 计算“不在 Astro 主源里”的唯一人数，作为潜在有时辰补充量

结果：

- 新 5 类标签覆盖总数：`5467`
- 新 5 类唯一人物数：`5467`
- 新 5 类中不在 Astro 主源里的唯一人物：`4988`

结论：
- 保守估算，这 5 个分类理论上仍有接近 `5000` 条“相对 Astro 主源的新增有时辰人物池”。
- 这不是最终可入 unified 的净增量，因为其中仍可能与其他已有源重叠，也可能受后续解析质量和合并策略影响。
- 但从规模上看，新 5 类仍值得继续跑，不是已经榨干的状态。

## 6. 结论

- 当前统一库有时辰总数已经到 `8327`
- Astrotheme 仍在继续抓，且游标已推进到 `visual_arts`
- 新 5 类从规模看仍有较大补充潜力
- 当前最现实的限制不是源枯竭，而是：
  - 统一库里无时辰占比仍高
  - 分类统计口径还不够精确
  - 需要后续把 `category_key` 显式落盘，才能做更精确的分类进度统计
