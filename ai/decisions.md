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
