# Project Agent Rules

## Language
All responses must be written in Simplified Chinese.

## Behavior
- Default language: Chinese
- Do not switch to English unless explicitly requested
- All explanations, plans, summaries, and reasoning must be Chinese
- Code may stay in its programming language, but comments must be Chinese

## Scope
These rules apply to:
- Codex CLI
- All skills
- All agent operations
- All generated documentation

## Token Efficiency Rules

为了节省 token，必须遵守以下规则：

1. **只读取必要文件**
   - 禁止扫描整个仓库
   - 只读取完成任务所需的文件

2. **一次只处理一个任务**
   - 禁止同时实现多个功能
   - 每次只完成一个明确任务

3. **减少解释**
   - 默认只输出结果
   - 只在必要时给出简短说明

4. **优先最小修改**
   - 修改尽可能少的代码
   - 避免重写整个文件

5. **避免无关分析**
   - 不要进行大型架构分析
   - 不要读取不相关目录

## Project Rules

执行任务前必须读取：

- ai/memory.md
- ai/tasks.md
- ai/rules.md

这些文件包含项目长期规则与上下文。

## OpenClaw Maintenance Rules

当用户说：
“修一下 openclaw”
“检查 openclaw”
“维护 openclaw”

必须自动执行以下流程：

1. 运行健康检查
   openclaw doctor

2. 如果发现问题
   运行自动修复
   openclaw doctor --fix

3. 检查 gateway 状态
   openclaw gateway status

4. 如果 gateway 异常
   重新安装并启动
   openclaw gateway install
   openclaw gateway start

5. 再次运行最终检查
   openclaw doctor

限制：
- 不允许删除 ~/.openclaw
- 不允许执行 reset
- 不允许 uninstall
- 不允许修改其他目录

目标：
确保 OpenClaw 运行正常并恢复 gateway。

## OpenClaw Upgrade Rules

当用户说：
“升级 openclaw”
“更新 openclaw”

必须执行以下流程：

1. 检查当前版本
   openclaw --version

2. 执行升级
   openclaw update

3. 升级完成后重启 gateway
   openclaw gateway restart

4. 最后验证状态
   openclaw doctor

要求：
- 只升级 OpenClaw 本体
- 不修改 ~/.openclaw 数据
- 不删除插件
- 全程输出中文结果

## Bot Recovery Rules

当用户说：
“修复 bot”
“bot 失联”
“恢复 bot”

必须执行以下流程：

1. 检查 gateway
   openclaw gateway status

2. 如果 gateway 未运行
   openclaw gateway restart

3. 检查端口
   lsof -i :18789

4. 如果端口未监听
   openclaw gateway start

5. 检查插件
   openclaw plugins list

6. 最后执行健康检查
   openclaw doctor

目标：
恢复 OpenClaw bot 与 gateway 连接。

## OpenClaw Self-Maintenance Rule

对于 OpenClaw 的操作（升级、修复、维护、bot恢复）：

- 必须由 Codex 自己完成检查与验证
- 不需要 Claude Code 参与代码审查或验证

流程：

1. 执行操作（upgrade / fix / restart）
2. 运行健康检查
   openclaw doctor
3. 检查 gateway
   openclaw gateway status
4. 检查端口
   lsof -i :18789
5. 确认插件
   openclaw plugins list

只有当上述检查全部正常时，才认为任务完成。

## OpenClaw Backup Rule

在执行以下操作前必须自动备份：

- 升级 openclaw
- 修复 openclaw
- 重装 gateway

备份命令：

cp -R ~/.openclaw ~/openclaw-backup/openclaw-$(date +%Y%m%d-%H%M%S)

备份完成后再执行操作。

## OpenClaw Log Check

当用户说：

检查 openclaw
检查 bot

必须读取日志：

~/.openclaw/logs/gateway.log

如果发现：

- connection error
- timeout
- restart loop

则自动执行：

openclaw gateway restart
openclaw doctor

## Git Auto Commit Rule

当 Codex 修改或创建代码文件时：

必须执行：

git add .
git commit -m "codex update: describe change"

规则：
- 每次代码修改必须提交
- 不允许留下未提交修改
- 不自动 push
- push 必须用户确认

## Testing Rule

当 Codex 修改代码后必须运行：

pytest

如果测试失败：
- 修复问题
- 再运行测试

## Architecture Decision Rule

当项目出现重要技术决策时：

必须记录到：

ai/decisions.md

例如：
- 选择数据库
- 选择框架
- API设计
- 系统架构

## Bug Tracking Rule

当发现 bug 时：

必须记录到：

ai/bugs.md

内容包括：
- bug描述
- 复现方式
- 修复方案

## Testing Rule

当 Codex 修改代码后必须运行：

pytest

如果测试失败：
- 修复问题
- 再运行测试

## Project Memory Rules

在开始任何任务前，必须优先读取以下文件：

- ai/memory.md
- ai/tasks.md（如果存在）

执行规则：
- 先读取项目记忆，再开始分析和修改
- 将 ai/memory.md 视为项目长期上下文的唯一权威来源
- 对长期有效的重要信息、关键决策、架构原则，优先参考 ai/memory.md
- 若用户提供新的长期有效信息，应建议更新到 ai/memory.md
- 除非用户明确要求，否则不要忽略 ai/memory.md 中的约束
