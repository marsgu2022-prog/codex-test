# 数据质量抽检报告

抽检目录：`bazichart-engine/data/`

本次重点检查文件：
- [famous_people_astro.json](/Users/mars/codex-test/bazichart-engine/data/famous_people_astro.json)
- [famous_people_astrotheme.json](/Users/mars/codex-test/bazichart-engine/data/famous_people_astrotheme.json)
- [unified_people.json](/Users/mars/codex-test/bazichart-engine/data/unified_people.json)
- [unified_people_with_bazi.json](/Users/mars/codex-test/bazichart-engine/data/unified_people_with_bazi.json)
- [pipeline_report.json](/Users/mars/codex-test/bazichart-engine/data/pipeline_report.json)

## 汇总结论

本轮抽检未发现主数据文件内部的 `name + birthday` 重复，日期格式和时辰格式也未发现坏值。当前主要问题不是“脏数据爆炸”，而是统一库里“无时辰记录仍然占多数”。

## 1. 有时辰 vs 无时辰

### 源文件

| 文件 | 总数 | 有时辰 | 无时辰 | 有时辰占比 |
|---|---:|---:|---:|---:|
| `famous_people_astro.json` | 2600 | 2600 | 0 | 100.00% |
| `famous_people_astrotheme.json` | 6538 | 6538 | 0 | 100.00% |

### 统一库

| 文件 | 总数 | 有时辰 | 无时辰 | 有时辰占比 |
|---|---:|---:|---:|---:|
| `unified_people.json` | 22050 | 8327 | 13723 | 37.76% |
| `unified_people_with_bazi.json` | 22050 | 8327 | 13723 | 37.76% |

### Pipeline 摘要

来自 [pipeline_report.json](/Users/mars/codex-test/bazichart-engine/data/pipeline_report.json)：

- `total_records`: 22050
- `has_birth_time`: 8327
- `bazi_calculated`: 19539
- `bazi_with_birth_time`: 7879

## 2. 重复记录检查

检查规则：
- 主键：`name_en + birth_date`
- 如果 `name_en` 为空，则回退到 `name_zh / name`

结果：

| 文件 | 重复键数量 |
|---|---:|
| `famous_people_astro.json` | 0 |
| `famous_people_astrotheme.json` | 0 |
| `unified_people.json` | 0 |
| `unified_people_with_bazi.json` | 0 |

结论：
- 主数据文件内部未发现同键重复。
- 当前去重至少在“完全相同 name+birthday”层面是有效的。

## 3. 跨源重叠情况

`famous_people_astro.json` 与 `famous_people_astrotheme.json` 的同键重叠：

- `astro_only`: 1951
- `astrotheme_only`: 5689
- `overlap`: 849

重叠样例：
- `A. Chal / 1986-05-30`
- `A. K. Best / 1933-02-26`
- `Aarthi Agarwal / 1984-03-05`
- `Adriana Asti / 1933-04-30`
- `Adrienne Bailon / 1983-10-24`

结论：
- 两源重叠明显，但 Astrotheme 仍然贡献了更大的增量池。
- 统一库没有出现重复，说明当前合并去重链路基本有效。

## 4. 异常数据检查

检查项：
- 日期格式是否符合 `YYYY-MM-DD`
- 时辰格式是否符合 `HH:MM`
- 是否缺少关键字段：姓名、出生日期

结果：

| 文件 | 日期格式异常 | 时辰格式异常 | 缺失关键字段 |
|---|---:|---:|---:|
| `famous_people_astro.json` | 0 | 0 | 0 |
| `famous_people_astrotheme.json` | 0 | 0 | 0 |
| `unified_people.json` | 0 | 0 | 0 |
| `unified_people_with_bazi.json` | 0 | 0 | 0 |

结论：
- 本次抽检未发现结构性坏数据。
- 当前数据质量主要短板是“无时辰比例高”，不是字段污染。

## 5. 建议

- 继续优先扩有时辰来源，因为统一库当前有时辰占比只有 `37.76%`
- 后续数据巡检可增加：
  - 姓名标准化后的重复检测
  - `birth_country` / `occupation` 空值率统计
  - `source_url` 唯一性检查
