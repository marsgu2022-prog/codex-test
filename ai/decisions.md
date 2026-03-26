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

## 名人库增加敏感人物清洗管线

- 新增 `bazichart-engine/scripts/clean_famous_people.py`，对名人库做长期可复用的敏感人物过滤
- 清洗规则分为三层：明确黑名单直接删除、关键词高风险删除、不确定人物进入 `review_list.json`
- 清洗后会原地重写 `famous_people.json`，并重新生成 `day_pillar_index.json` 与 `deleted_report.json`

## 玄学资料库与案例库并行建模

- `crawl_mysticism_library.py` 采用单模块双载荷结构，同时输出 `topics` 和 `cases`
- `topics` 面向术语、流派、经典与人物知识；`cases` 面向八字、紫微斗数、风水验证案例
- 案例库先落最小 schema 和占位样本，后续再接真实可验证案例源

## 玄学资料库来源优先级

- 玄学资料库先以 Wikipedia 为一级来源，默认 `source_priority = 1`、`quality_tier = A`
- 其他渠道后续可以接入，但必须显式记录来源类型、优先级和质量等级后才能入库
- SQLite 数据库同时落主题、案例、标签、事件四类结构，便于后续检索、后台管理和持续更新

## 玄学案例源采用来源注册表与审核态

- 玄学数据库新增 `source registry` 结构，单独维护来源白名单、默认优先级、默认质量等级和是否允许入库
- `Wikipedia` 和当前 `wikipedia_seed` 作为一级来源可直接入库，审核态固定为 `approved`
- 除 Wikipedia 外的新来源默认归入 `external_pending_review`，必须人工审核通过后才能进入正式主题或案例表
- `source quality review` 记录扩展为带 `review_scope`、`review_status`、`requires_manual_approval`、`reviewed_by` 的审核元数据，后续可支持更细的来源审批流

## 玄学抓取改为部分成功优先

- `crawl_mysticism_library.py` 遇到单个分类、单语摘要或相关链接抓取失败时，不再整批失败
- 只要中英任一语言摘要成功，就保留该主题记录；仅在双语都失败时才跳过主题
- 报告中新增失败统计与失败样本，便于后续按失败点补跑，而不是阻塞整批落盘

## 2026-03-17 管理员登录先走服务端会话

- 当前仓库缺少可直接修改的独立前端工程，先在 `bazichart-engine/api.py` 内提供主页 HTML、管理员登录页和后台页
- 管理员登录成功后写入 `HttpOnly` Cookie，会话可直接访问后台，同时对深度解盘与 PDF 报告接口免邀请码
- 邀请码机制继续保留给普通用户；管理员接口同时兼容旧的 `admin_key` 调用方式，避免已有脚本失效

## 2026-03-22 高置信研读结果每日回流自动规则

- 新增 `bazichart-engine/scripts/rule_extractor.py`，每天从 `data/bazi_readings.json` 中筛选 `confidence >= 0.8` 的研读结果
- 按日主聚合格局、用神、职业倾向和性格特质，输出到 `knowledge/auto_rules.md` 与 `knowledge/auto_rules_stats.json`
- `auto_reader_cron.sh` 在研读成功后自动执行规则提炼，形成“研读 -> 规则回流 -> 知识沉淀”的每日闭环
