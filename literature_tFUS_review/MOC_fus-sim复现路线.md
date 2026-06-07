# MOC：fus-sim 复现路线

## 当前状态

`fus-sim` 已有轻量球面聚焦声场模型，可用于检查换能器几何、频率、声压和输出流程。

相关文件：

- `D:\AIprogram\fus-sim\README.md`
- `D:\AIprogram\fus-sim\simulate_spherical_focus.py`
- `D:\AIprogram\fus-sim\outputs\spherical_focus\summary.txt`
- `D:\AIprogram\fus-sim\项目任务总结.md`

## 建议路线

### 1. 二维简化颅骨层

目标：比较无颅骨/有颅骨时的声压衰减和焦点偏移。

参考：

- [[MOC_声场仿真与相位校正]]
- [[01_seed_papers_summary#1 高鹏皓 2022经颅聚焦超声调控系统的参数仿真研究|高鹏皓 2022]]

### 2. 热效应最小模型

目标：加入 Pennes 热传导，输出温升曲线和 42 摄氏度安全判断。

参考：

- [[03_experimental_steps#A 经颅聚焦超声声场仿真与相位校正]]

### 3. 三维均匀介质小模型

目标：跑通 k-wave-python 三维工作流，不急于使用真实 CT。

### 4. 相控阵与相位延迟

目标：从单阵元模型走向 82 阵元或简化阵列。

参考：

- [[notes/04_Jin2020_open_source_phase_correction]]
- [[01_seed_papers_summary#3 孙天宇 2021经颅聚焦超声治疗脑血栓的数值仿真研究]]

### 5. BBB/MI 风险指标

目标：不急着完整模拟微泡群，先计算 MI 和风险分区。

参考：

- [[MOC_BBB微泡与空化监测]]

### 6. 公开 CT 数据接入

目标：进入真实颅骨个体化建模。

## Codex 使用提示

你可以直接这样问：

- “Codex，查看 `literature_tFUS_review/Home.md`，根据知识库帮我规划下一步仿真。”
- “Codex，根据 `MOC_声场仿真与相位校正` 实现二维颅骨层模型。”
- “Codex，参考 `03_experimental_steps.md` 把热效应最小模型加到 fus-sim。”
- “Codex，帮我把新论文整理成 Obsidian 笔记并加入对应 MOC。”

