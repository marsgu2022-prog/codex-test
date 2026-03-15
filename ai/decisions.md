# 2026-03-14

## AI 解读模块最小实现

- 新增 `src/ai_interpreter.py` 作为独立解释器模块
- API 先以纯 Python 函数形式暴露：`post_interpret`、`get_interpret_archetypes`
- 不引入外部依赖，不接入真实 LLM，不改前端与排盘核心
- 中文输出单独本地化生成，避免把英文 narrative 直接混入 `lang="zh"` 响应

## 节气数据生成方案

- 新增 `bazichart-engine/scripts/generate_solar_terms.py` 生成 1900-2100 年二十四节气北京时间数据
- 主计算采用 `ephem` 的太阳几何黄经，并用二分搜索求解每个 15 度节点的分钟级时刻
- 校验脚本采用 `lunar_python` 作为现有排盘依赖基线，并附加香港天文台公开时刻样本做抽样复核

## 名人抓取切换为可积累管线

- `crawl_famous_people.py` 不再把在线 SPARQL 当一次性全量源，而是按“页级缓存 + 失败队列”运行
- 成功抓到的查询页会写入本地候选池缓存，后续同参数任务优先命中缓存，减少对 Wikidata 的重复请求
- 失败查询页会进入本地失败队列，后续单独补跑，而不是每次从零开始扫描

## 科学家焦点单独阈值

- `scientists` 焦点使用独立最小阈值 `5000`，不再沿用综合名人库的 `10000`
- 科学家抓取范围扩展到数学、物理、化学、生物、天文、计算机科学、发明家等细分职业
- 正式产物先以科学家专题库单独落盘，后续再向七大标准分类映射收敛

## 名人职业统一到七大分类

- 抓取产物新增 `occupation` 字段，统一输出中文数组分类
- 当前标准分类固定为：企业家、政治家、演员、运动员、科学家、作家、音乐家
- 保留原始 `field_zh` 和 `field_en` 作为细职业原文，避免丢失可追溯信息

## 名人库同步三语结构字段

- 为支持英文站和繁体中文站，名人记录同步输出简中、繁中、英文结构字段
- 当前已补充 `name_zh_hant`、`nationality_zh_hant`、`occupation_en`、`occupation_zh_hant`、`bio_zh`、`bio_zh_hant`、`bio_en`
- 旧字段 `summary`、`field_zh`、`field_en` 继续保留，前台可以逐步迁移

## 三语字段命名统一

- 名称字段统一为 `name_zh_hans`、`name_zh_hant`、`name_en`
- 简介字段统一为 `bio_zh_hans`、`bio_zh_hant`、`bio_en`
- 旧字段保留兼容，后续前台和检索优先切到新命名
