# Agent Skills 模板

本目录保存 `fus-sim` 项目的跨 Agent 协作技能模板。它们是项目资产，先纳入 Git 版本管理；如需在 Antigravity/Gemini 本机环境中启用，可再复制到对应的本地 skills 目录。

这些模板的目标不是替代 `AGENTS.md`、`EVIDENCE_DRIVEN_DEVELOPMENT.md` 或 `RELAY_PROTOCOL.md`，而是把项目规则拆成更容易被不同 Agent 激活的专用技能：

- `agent-relay-gatekeeper`：双 Agent 接力网关，防止上下文丢失、覆盖历史结果或接力状态混乱。
- `kwave-simulation-sentinel`：k-Wave 仿真安全哨兵，强制 dry-run quality、时间预算、检查点和停止条件。
- `edd-methodology-enforcer`：证据驱动开发合规官，强制 evidence brief 先行与 gap feedback 后置。

## 使用原则

1. Codex 当前仍是主执行位；Antigravity 暂作为 optional reviewer/planner。
2. 新 Agent 接手前必须先读项目根目录的 `AGENTS.md`、`ACTIVE_WORK.md`、`HANDOFF_LOG.md` 和相关 handoff 文件。
3. 任何 k-Wave 真实仿真前必须先执行 `--dry-run-quality`，并获得用户明确授权。
4. 任何新物理参数、材料映射或仿真 preset 前必须先生成 evidence brief。
5. 技能模板中的规则若与 `AGENTS.md` 冲突，以 `AGENTS.md` 为准。

