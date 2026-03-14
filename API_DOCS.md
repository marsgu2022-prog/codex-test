# API 文档

服务端口：`8000`

启动方式：

```bash
bash start.sh
```

基础地址：

```text
http://localhost:8000
```

## 1. GET /api/health

用途：健康检查。

请求参数：无。

成功响应：

```json
{
  "status": "ok"
}
```

curl 示例：

```bash
curl http://localhost:8000/api/health
```

## 2. POST /api/interpret

用途：生成完整八字解读数据。

### 请求参数

| 字段 | 类型 | 必填 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| `year` | integer | 是 | 出生年份，范围 `1900-2030` | `1990` |
| `month` | integer | 是 | 出生月份，范围 `1-12` | `1` |
| `day` | integer | 是 | 出生日期，范围 `1-31`，会校验真实日期 | `1` |
| `hour` | integer | 是 | 出生小时，范围 `0-23` | `11` |
| `minute` | integer | 否 | 出生分钟，范围 `0-59`，默认 `0` | `30` |
| `gender` | string | 是 | 性别，只接受 `male`/`female`/`男`/`女`，内部统一转为英文 | `"男"` |
| `city` | string | 否 | 出生城市，可用于经度查找与真太阳时修正 | `"上海"` |
| `timezone` | string | 否 | 时区，默认 `Asia/Shanghai` | `"Asia/Shanghai"` |
| `longitude` | number | 否 | 经度，优先级高于 `city` | `121.47` |

请求示例：

```json
{
  "year": 1990,
  "month": 1,
  "day": 1,
  "hour": 11,
  "minute": 30,
  "gender": "男",
  "city": "上海",
  "timezone": "Asia/Shanghai",
  "longitude": 121.47
}
```

### 成功响应结构

顶层字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `input` | object | 归一化后的输入参数 |
| `four_pillars` | object | 四柱排盘结果 |
| `shensha` | array | 神煞列表 |
| `wuxing_analysis` | object | 五行力量分析 |
| `dayun` | array | 8 步大运 |
| `liunian` | array | 10 条流年 |
| `ten_gods_analysis` | object | 十神解读 |
| `psychological_analysis` | object | 心理学分析 |
| `solar_time_info` | object | 真太阳时修正信息；未传 `longitude/city` 时可能不存在 |

`input` 结构：

```json
{
  "birth_year": 1990,
  "birth_month": 1,
  "birth_day": 1,
  "birth_hour": 11,
  "birth_minute": 30,
  "gender": "male",
  "birthplace": "上海",
  "timezone": "Asia/Shanghai",
  "longitude": 121.47
}
```

`four_pillars` 结构：

```json
{
  "year": {
    "heavenly_stem": "庚",
    "earthly_branch": "午"
  },
  "month": {
    "heavenly_stem": "壬",
    "earthly_branch": "子"
  },
  "day": {
    "heavenly_stem": "壬",
    "earthly_branch": "寅"
  },
  "hour": {
    "heavenly_stem": "乙",
    "earthly_branch": "丑"
  }
}
```

`wuxing_analysis` 结构：

```json
{
  "wuxing_scores": {
    "金": 2.3,
    "木": 1.8,
    "水": 3.1,
    "火": 0.6,
    "土": 2.2
  },
  "wuxing_percentages": {
    "金": 23.0,
    "木": 18.0,
    "水": 31.0,
    "火": 6.0,
    "土": 22.0
  },
  "day_master": "壬",
  "day_master_element": "水",
  "day_master_strength": "偏强",
  "favorable_elements": ["土", "火"],
  "unfavorable_elements": ["水", "金"],
  "analysis": "日主壬水五行占比约31.0%，整体判断为偏强，喜土火，忌水金。"
}
```

`dayun` 单项结构：

```json
{
  "start_age": 3,
  "end_age": 12,
  "tiangan": "己",
  "dizhi": "卯",
  "wuxing": "土木",
  "detail": {
    "ganzhi": "己卯",
    "shishen": "正官",
    "overall": "中吉",
    "theme": "学习积累期，贵人运旺",
    "career": "正官主规则与位置，此运适合稳步建立职业信誉。",
    "wealth": "财运以稳为主，不宜激进投资。",
    "relationship": "与原局地支关系平稳，感情宜多沟通。",
    "health": "注意脾胃、睡眠与压力管理。",
    "advice": "宜守正出新，先稳后进。"
  }
}
```

`liunian` 单项结构：

```json
{
  "year": 2025,
  "tiangan": "乙",
  "dizhi": "巳",
  "wuxing": "木火",
  "detail": {
    "ganzhi": "乙巳",
    "shishen": "伤官",
    "overall": "中吉",
    "career": {
      "score": 75,
      "text": {
        "zh": "事业上适合突破和表达，但要注意节奏。",
        "en": "Career favors breakthrough and expression, but rhythm matters."
      }
    },
    "wealth": {
      "score": 80,
      "text": {
        "zh": "财运有起色，适合务实争取结果。",
        "en": "Wealth improves; practical action is favored."
      }
    },
    "relationship": {
      "score": 60,
      "text": {
        "zh": "关系层面宜减少争强，增加理解。",
        "en": "In relationships, soften rivalry and deepen understanding."
      }
    },
    "health": {
      "score": 70,
      "text": {
        "zh": "注意休息与情绪疏导。",
        "en": "Rest well and give emotion a clean outlet."
      }
    },
    "advice": {
      "zh": "宜主动但不宜冒进。",
      "en": "Take initiative, but do not rush beyond your footing."
    }
  }
}
```

说明：

- `dayun.detail` 为大运详细解读字段。
- `liunian.detail` 为流年详细解读字段。

`shensha` 单项结构：

```json
{
  "name": "天乙贵人",
  "type": "吉",
  "position": "月支、时支",
  "description": "遇难呈祥，逢凶化吉，一生多得贵人相助。"
}
```

`solar_time_info` 结构：

```json
{
  "beijing_time": "12:30",
  "longitude": 121.47,
  "equation_of_time": -3.5,
  "longitude_correction": 5.88,
  "true_solar_time": "12:32",
  "original_shichen": "午时",
  "corrected_shichen": "午时",
  "shichen_changed": false
}
```

完整响应示例：

```json
{
  "input": {
    "birth_year": 1990,
    "birth_month": 1,
    "birth_day": 1,
    "birth_hour": 11,
    "birth_minute": 30,
    "gender": "male",
    "birthplace": "上海",
    "timezone": "Asia/Shanghai",
    "longitude": 121.47
  },
  "four_pillars": {
    "year": {"heavenly_stem": "庚", "earthly_branch": "午"},
    "month": {"heavenly_stem": "壬", "earthly_branch": "子"},
    "day": {"heavenly_stem": "壬", "earthly_branch": "寅"},
    "hour": {"heavenly_stem": "乙", "earthly_branch": "丑"}
  },
  "shensha": [],
  "wuxing_analysis": {},
  "dayun": [],
  "liunian": [],
  "ten_gods_analysis": {
    "比肩": {"interpretation": "比肩体现自主驱动力、边界感与对平等关系的重视。"},
    "正印": {"interpretation": "正印体现吸收能力、安全感来源与对支持系统的需求。"}
  },
  "psychological_analysis": {
    "荣格原型": "更偏向英雄与照顾者并存的心理模式。",
    "MBTI倾向": "可能更偏向 INFJ / ENFJ 一类的共情与组织倾向。",
    "解读摘要": "..."
  },
  "solar_time_info": {
    "beijing_time": "11:30",
    "longitude": 121.47,
    "equation_of_time": -3.5,
    "longitude_correction": 5.88,
    "true_solar_time": "11:32",
    "original_shichen": "午时",
    "corrected_shichen": "午时",
    "shichen_changed": false
  }
}
```

### 错误响应

`400`：

```json
{
  "error": "请输入出生年份"
}
```

常见 `400` 错误信息：

- `请输入出生年份`
- `年份范围为1900-2030`
- `月份范围为1-12`
- `日期范围为1-31`
- `日期无效`
- `时辰范围为0-23`
- `分钟范围为0-59`
- `请选择性别`
- `经度格式无效`

`500`：

```json
{
  "detail": "解读生成失败: <具体错误>"
}
```

### curl 示例

```bash
curl -X POST http://localhost:8000/api/interpret \
  -H "Content-Type: application/json" \
  -d '{
    "year": 1990,
    "month": 1,
    "day": 1,
    "hour": 11,
    "minute": 30,
    "gender": "男",
    "city": "上海",
    "timezone": "Asia/Shanghai",
    "longitude": 121.47
  }'
```

## 3. POST /api/report/pdf

用途：生成 PDF 报告并以附件流返回。

### 请求参数

与 `POST /api/interpret` 完全相同。

### 成功响应

响应头：

```text
Content-Type: application/pdf
Content-Disposition: attachment; filename="bazi_report.pdf"
```

响应体：PDF 二进制内容。

### 错误响应

`400`：

```json
{
  "error": "请输入出生年份"
}
```

`500`：

```json
{
  "detail": "PDF 生成失败: <具体错误>"
}
```

### curl 示例

```bash
curl -X POST http://localhost:8000/api/report/pdf \
  -H "Content-Type: application/json" \
  -d '{
    "year": 1990,
    "month": 1,
    "day": 1,
    "hour": 11,
    "minute": 30,
    "gender": "男",
    "city": "上海",
    "longitude": 121.47
  }' \
  --output bazi_report.pdf
```

## 4. POST /api/report/hehun-pdf

用途：生成合婚 PDF 报告并以附件流返回。

### 请求参数

与 `POST /api/hehun` 完全相同。

### 成功响应

响应头：

```text
Content-Type: application/pdf
Content-Disposition: attachment; filename="hehun_report.pdf"
```

响应体：PDF 二进制内容。

### 错误响应

`400`：

```json
{
  "error": "请输入男方出生年份"
}
```

`500`：

```json
{
  "detail": "合婚 PDF 生成失败: <具体错误>"
}
```

### curl 示例

```bash
curl -X POST http://localhost:8000/api/report/hehun-pdf \
  -H "Content-Type: application/json" \
  -d '{
    "male_year": 1990,
    "male_month": 1,
    "male_day": 1,
    "male_hour": 11,
    "male_gender": "男",
    "female_year": 1991,
    "female_month": 2,
    "female_day": 2,
    "female_hour": 9,
    "female_gender": "女"
  }' \
  --output hehun_report.pdf
```

## 5. GET /api/daily-fortune

用途：返回指定日期的每日运势。只传 `date` 时返回通用运势；同时传入完整八字参数时返回个性化运势。

### 请求参数

| 字段 | 类型 | 必填 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| `date` | string | 是 | 目标日期，格式 `YYYY-MM-DD` | `2026-03-14` |
| `lang` | string | 否 | 返回语言，支持 `zh` / `en`，默认 `zh` | `en` |
| `year` | integer | 否 | 个性化运势用出生年份 | `1990` |
| `month` | integer | 否 | 个性化运势用出生月份 | `1` |
| `day` | integer | 否 | 个性化运势用出生日期 | `1` |
| `hour` | integer | 否 | 个性化运势用出生小时 | `11` |
| `gender` | string | 否 | 个性化运势用性别，规则同 `/api/interpret` | `男` |
| `minute` | integer | 否 | 个性化运势用出生分钟，默认 `0` | `0` |
| `city` | string | 否 | 个性化运势用城市 | `上海` |
| `timezone` | string | 否 | 个性化运势用时区 | `Asia/Shanghai` |
| `longitude` | number | 否 | 个性化运势用经度 | `121.47` |

注意：

- 如果 `year/month/day/hour/gender` 只传了一部分，会返回 `400`。
- 如果全部不传，则只返回通用运势。

### 成功响应结构

```json
{
  "date": "2026-03-14",
  "day_ganzhi": "丙午",
  "day_wuxing": "火",
  "fortune_level": "上吉",
  "lucky_color": "Crimson Red",
  "lucky_direction": "South",
  "lucky_number": 9,
  "general_message": "Fire crowns the day. Move boldly, speak clearly, and let yourself be seen.",
  "personal_message": "The day nourishes your core. Ask, connect, and let support find you.",
  "wallpaper_text": "Flame in your chest\nLight in each step",
  "blessing": "May every road beneath you open with ease."
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `date` | string | 查询日期 |
| `day_ganzhi` | string | 当日干支 |
| `day_wuxing` | string | 当日天干对应五行 |
| `fortune_level` | string | 运势等级：`大吉/上吉/中吉/小吉/平/小凶/凶` |
| `lucky_color` | string | 幸运颜色 |
| `lucky_direction` | string | 幸运方位 |
| `lucky_number` | integer | 幸运数字 |
| `general_message` | string | 通用运势文案 |
| `personal_message` | string | 个性化运势文案；未传个人参数时通常不存在 |
| `wallpaper_text` | string | 两行内短文案 |
| `blessing` | string | 祝福语 |
| `lang` | - | 不单独返回；但所有文案类字段会随请求参数 `lang` 切换为中文或英文 |

### 错误响应

`400`：

```json
{
  "detail": "个性化运势参数不完整"
}
```

或：

```json
{
  "detail": "time data '2026/03/14' does not match format '%Y-%m-%d'"
}
```

`500`：

```json
{
  "detail": "每日运势生成失败: <具体错误>"
}
```

### curl 示例

通用运势：

```bash
curl "http://localhost:8000/api/daily-fortune?date=2026-03-14&lang=zh"
```

个性化运势：

```bash
curl "http://localhost:8000/api/daily-fortune?date=2026-03-14&lang=en&year=1990&month=1&day=1&hour=11&minute=0&gender=男&city=上海"
```

## 6. POST /api/hehun

用途：基于男女双方八字生成合婚分析结果。

### 请求参数

| 字段 | 类型 | 必填 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| `male_year` | integer | 是 | 男方出生年份，范围 `1900-2030` | `1990` |
| `male_month` | integer | 是 | 男方出生月份，范围 `1-12` | `1` |
| `male_day` | integer | 是 | 男方出生日期，范围 `1-31` | `1` |
| `male_hour` | integer | 是 | 男方出生小时，范围 `0-23` | `11` |
| `male_gender` | string | 是 | 男方性别，只接受 `male`/`female`/`男`/`女` | `男` |
| `female_year` | integer | 是 | 女方出生年份，范围 `1900-2030` | `1991` |
| `female_month` | integer | 是 | 女方出生月份，范围 `1-12` | `2` |
| `female_day` | integer | 是 | 女方出生日期，范围 `1-31` | `2` |
| `female_hour` | integer | 是 | 女方出生小时，范围 `0-23` | `9` |
| `female_gender` | string | 是 | 女方性别，只接受 `male`/`female`/`男`/`女` | `女` |

请求示例：

```json
{
  "male_year": 1990,
  "male_month": 1,
  "male_day": 1,
  "male_hour": 11,
  "male_gender": "男",
  "female_year": 1991,
  "female_month": 2,
  "female_day": 2,
  "female_hour": 9,
  "female_gender": "女"
}
```

### 成功响应结构

```json
{
  "score": 85,
  "level": "上等婚配",
  "day_gan_he": {
    "matched": true,
    "detail": "甲己合化土，情投意合，彼此容易互相吸引。"
  },
  "year_zhi": {
    "relation": "六合",
    "detail": "子丑六合，天生缘分较深，容易相互扶持。"
  },
  "yongshen_match": {
    "score": 80,
    "detail": "男方喜水，女方对应五行得分较高；女方喜木，男方亦能形成一定补益。"
  },
  "wuxing_complement": {
    "score": 75,
    "detail": "男方水偏弱而女方水较旺；女方火偏弱而男方火较旺"
  },
  "summary": "此婚配属上等婚配，甲己合化土，情投意合，彼此容易互相吸引。子丑六合，天生缘分较深，容易相互扶持。用神匹配度为80分，五行互补度为75分。"
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `score` | integer | 综合评分，范围 `0-100` |
| `level` | string | 婚配等级：`上等婚配/中上婚配/中等婚配/中下婚配/下等婚配` |
| `day_gan_he` | object | 男女日干五合分析 |
| `year_zhi` | object | 年支关系分析，如六合、三合、相冲、相刑、相害、平 |
| `yongshen_match` | object | 用神互补评分与说明 |
| `wuxing_complement` | object | 五行互补评分与说明 |
| `summary` | string | 综合结论 |

### 错误响应

`400`：

```json
{
  "error": "请输入男方出生年份"
}
```

或：

```json
{
  "error": "请输入女方出生年份"
}
```

`500`：

```json
{
  "detail": "合婚分析失败: <具体错误>"
}
```

### curl 示例

```bash
curl -X POST http://localhost:8000/api/hehun \
  -H "Content-Type: application/json" \
  -d '{
    "male_year": 1990,
    "male_month": 1,
    "male_day": 1,
    "male_hour": 11,
    "male_gender": "男",
    "female_year": 1991,
    "female_month": 2,
    "female_day": 2,
    "female_hour": 9,
    "female_gender": "女"
  }'
```
