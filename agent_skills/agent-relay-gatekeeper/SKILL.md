---
name: agent-relay-gatekeeper
description: 处理 Codex 与 Antigravity 的接力对接。强制执行接手先读、先复述、只追加不覆盖，以及运行后更新 ACTIVE_WORK.md 和 HANDOFF_LOG.md，防范多 Agent 写入冲突。
---

# 双 Agent 接力网关

当用户要求切换 Agent、交接任务、整理 handoff，或当前对话需要接手 `fus-sim` 项目时，启用本技能。

## 必读文件

接手前必须先读：

- `AGENTS.md`
- `ACTIVE_WORK.md`
- `HANDOFF_LOG.md`
- `RELAY_PROTOCOL.md`
- 当前目标相关的 handoff 文件，例如 `HANDOFF_ANTIGRAVITY.md`、`HANDOFF_CODEX.md`

如果其中某个文件不存在，必须说明缺失，并使用现有项目文件和用户最新指令补齐上下文。

## 接手复述

开始执行前，必须先复述：

```text
我读取到当前状态是：
当前 active task 是：
上一个 agent 已完成：
我本轮只会做：
我不会动：
本轮验收标准：
```

如果复述与用户理解不一致，先等待用户纠正，不要直接执行。

## 锁定路径保护

默认只读、禁止覆盖：

- `data/raw_ct/`
- `outputs/ct_acoustic_model_3d/`
- `outputs/ct_transducer_stability_target_020/`
- `outputs/case_refinement_runs/079_candidate_006_offset_10_0/`
- `ACTIVE_WORK.md` 中列出的其他 locked paths

新的实验输出必须写入独立新目录，不得覆盖已有 best 或历史结果。

## 状态同步

每完成一个可验证阶段，必须追加 `HANDOFF_LOG.md`，并视情况更新 `ACTIVE_WORK.md`：

```md
## YYYY-MM-DD HH:MM Agent Step

完成内容：
修改文件：
新增/更新输出：
验证结果：
偏差/警告：
下一步：
禁止覆盖：
```

## Antigravity/Codex 分工

- Codex：默认主执行位，负责本地文件修改、PowerShell 命令、Git 提交推送和小步验证。
- Antigravity：可选审阅/规划位，适合高层方案、证据复核和多 Agent 并行设计；除非用户明确授权，不自动运行 k-Wave。

