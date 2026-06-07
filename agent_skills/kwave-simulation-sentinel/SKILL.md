---
name: kwave-simulation-sentinel
description: 用于 k-Wave 仿真运行前的参数审核与内存/耗时网关校验。强制执行 dry-run quality，阻止盲目的大网格 3D 仿真。
---

# k-Wave 仿真安全哨兵

当任务涉及运行、修改、扩展或评估 k-Wave 声场仿真时，启用本技能。典型脚本包括：

- `simulate_kwave_3d_focus.py`
- `simulate_freefield_transducer.py`
- `simulation_quality.py`

## 禁止盲跑

任何真实 k-Wave 运行前必须满足：

1. 对应模块已有 evidence brief。
2. 输出目录不会覆盖历史 best 或 locked paths。
3. 已执行 `--dry-run-quality` 或等价的 `simulation_quality.py` 质量估算。
4. 已明确 preset：`smoke`、`quick`、`standard` 或 `paper-grade`。
5. 已写明时间预算、2 分钟检查点和硬停止条件。
6. 用户明确授权真实运行，尤其是 `standard` 或 `paper-grade`。

## Dry-run 门控

优先使用现有脚本：

```powershell
D:\AIprogram\python-envs\kwave312\Scripts\python.exe simulate_kwave_3d_focus.py --preset quick --dry-run-quality ...
```

或：

```powershell
D:\AIprogram\python-envs\kwave312\Scripts\python.exe simulate_freefield_transducer.py --preset quick --dry-run-quality ...
```

如果未来新增统一 runner，例如 `run_kwave_command.py`，可以再把它设为默认启动入口；当前阶段不要把不存在或未验证的 runner 写成强制依赖。

## 必查字段

dry-run 或 summary 必须尽量记录：

- preset
- dx / grid size
- PPW
- PML
- CFL
- dt / nt
- backend / device
- memory estimate
- runtime estimate 或实际 runtime

## 偏差处理

如果出现以下情况，必须暂停并复盘：

- 超过硬停止时间仍无 `summary.json` 或核心输出。
- global peak 贴源面且 target window 无增强。
- source mask 含 skull label 或进入软组织/颅骨。
- PPW/PML/CFL 不满足当前 preset 的质量要求。
- 输出目录无更新或进程无明确进展。

复盘必须基于证据：日志、summary、进程状态、输出文件更新时间、JSON 指标，而不是重复运行同一命令。

## 结果措辞

- `smoke`：只能说明流程跑通。
- `quick`：只能用于筛选和趋势比较。
- `standard`：可用于较稳健的工程复核。
- `paper-grade`：必须有网格收敛、边界/PML 复核、运行环境记录和证据审计。

quick/cropped-domain 结果不得写成论文级复现或医学安全结论。

