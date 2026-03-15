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
