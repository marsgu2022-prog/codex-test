# 2026-03-14

## AI 解读模块最小实现

- 新增 `src/ai_interpreter.py` 作为独立解释器模块
- API 先以纯 Python 函数形式暴露：`post_interpret`、`get_interpret_archetypes`
- 不引入外部依赖，不接入真实 LLM，不改前端与排盘核心
- 中文输出单独本地化生成，避免把英文 narrative 直接混入 `lang="zh"` 响应
