# tFUS 仿真平台：论文与公开代码搜集任务说明

## 任务目标

请围绕“经颅聚焦超声 tFUS 仿真平台搭建”搜集论文和公开代码/工具资料，用于后续建立：

- 论文实验参数对照表
- 公开工具/代码路线对照表
- 当前平台与论文级复现之间的差距分析
- 后续复现路线校准建议

当前平台已经能跑通：

- CT/NIfTI/DICOM 到 3D 声学模型
- k-Wave quick 3D 声压仿真
- source safety 检查
- target/entry 候选筛选
- Pennes 热模型
- 079 病例 quick tuned best
- Visible Human 公开 CT quick pipeline

现在需要补充文献和公开工具依据，避免只围绕单篇论文参数盲调。

## 重点问题

请重点回答：

1. tFUS / tcMRgFUS / 经颅超声仿真中，常见参数范围是什么？
2. 哪些参数是领域共识，哪些只是某篇论文的特例？
3. CT/MRI/pseudo-CT 如何转成声学介质？
4. 公开工具如何组织输入、换能器、声场输出和热安全分析？
5. 我们当前平台下一步应优先对齐哪篇论文或哪套工具？

## 优先搜集来源

### 本地已有资料

- `经颅聚焦超声调控系统的参数仿真研究_高鹏皓.pdf`
- `经颅聚焦超声联合微泡开放血脑屏障的数值仿真研究_潘婷.pdf`
- `经颅聚焦超声治疗脑血栓的数值仿真研究_孙天宇.pdf`
- `literature_tFUS_review/` 中已有的论文笔记和主题综述

### 公开代码/工具

请重点搜集并确认以下工具：

- TUSX  
  https://www.tusx.org/

- BabelBrain  
  https://github.com/ProteusMRIgHIFU/BabelBrain

- TFUScapes  
  https://github.com/CAMMA-public/TFUScapes

- SynCT_TcMRgFUS  
  https://github.com/han-liu/SynCT_TcMRgFUS

- Rapid beam simulation framework  
  https://www.nature.com/articles/s41598-019-43775-6

如果发现其他高度相关工具，也请加入，例如：

- k-Wave based transcranial ultrasound tool
- mSOUND
- HAS / hybrid angular spectrum
- FDTD transcranial simulation
- Kranion
- PlanTUS
- BabelViscoFDTD

## 优先搜集方向

### 1. 经颅聚焦超声神经调控 / tFUS neuromodulation

重点关注：

- 频率
- 声压 / 声强 / MI / ISPPA / ISPTA
- PRF
- 占空比
- pulse duration / train duration
- inter-train interval
- 换能器 aperture / radius / focal length / F-number
- 是否使用 CT / MRI / ZTE / PETRA / pseudo-CT
- 是否做热安全分析

### 2. CT-based / MRI-based tFUS simulation

重点关注：

- HU 到声速、密度、衰减的映射
- 颅骨分割方法
- 皮质骨 / 松质骨是否区分
- 是否做相位校正
- 网格分辨率
- PPW
- PML
- 运行时间
- GPU/CPU

### 3. 热效应与安全性

重点关注：

- Pennes bioheat model
- 热源计算方式
- duty cycle 处理方式
- perfusion 参数
- skull / brain conductivity
- 安全阈值，例如 42°C
- 是否有 MR thermometry 或实验验证

## 每篇论文请提取这些字段

请尽量输出为 Markdown 表格或 CSV 风格表格。

| 字段 | 内容 |
|---|---|
| paper_id | 简短编号 |
| title | 论文标题 |
| year | 年份 |
| application | neuromodulation / BBB / ablation / epilepsy / thrombolysis / simulation validation 等 |
| data_input | CT / MRI / pseudo-CT / phantom / skull sample |
| solver | k-Wave / FDTD / HAS / mSOUND / BabelViscoFDTD / other |
| frequency | 频率 |
| pressure_or_intensity | 声压、声强、MI、ISPPA、ISPTA |
| PRF | 脉冲重复频率 |
| duty_cycle | 占空比 |
| pulse_train | pulse duration / train duration |
| interval | train 间隔 |
| transducer | aperture、radius、focal length、F-number |
| skull_model | 颅骨建模方式 |
| acoustic_mapping | HU/MRI 到声速、密度、衰减映射 |
| grid_setup | dx、PPW、PML、网格大小 |
| thermal_model | 是否有 Pennes 或其他热模型 |
| safety_metrics | 温升、42°C、MI、FDA/IEC 指标等 |
| code_or_data | 是否有公开代码/数据 |
| relevance_to_our_platform | 直接复现参考 / 参数范围参考 / 综述参考 / 工具接口参考 |
| notes | 重要备注 |

## 每个公开工具请提取这些字段

| 字段 | 内容 |
|---|---|
| tool_id | 工具简称 |
| name | 工具名称 |
| url | 链接 |
| language | MATLAB / Python / C++ / GUI / mixed |
| solver_backend | k-Wave / FDTD / HAS / custom |
| input_data | CT / MRI / ZTE / PETRA / pseudo-CT / DICOM / NIfTI |
| output_data | pressure map / temperature map / focus metrics / transducer coordinates |
| transducer_model | 单阵元 / 多阵元 / bowl / phased array |
| skull_modeling | 颅骨分割和材料映射方式 |
| thermal_modeling | 是否支持热模型 |
| validation | 是否有实验/论文验证 |
| license | 开源协议或使用限制 |
| what_to_learn | 我们平台可借鉴的部分 |
| risk_or_limit | 依赖、GPU、平台限制、数据限制 |

## 需要特别判断的参数

请特别判断下面这些参数是“领域常见”还是“某篇论文特例”：

- `500 kHz`
- `1 MPa`
- `6% duty cycle`
- `PRF = 300 Hz`
- `67 ms train`
- `2.5 s interval`
- `aperture = 25 mm`
- `radius = 30 mm`
- `aperture = 30 mm`
- `radius = 35 mm`
- `42°C` 安全阈值
- HU 阈值分割颅骨，例如 `HU >= 300`
- CT-HU 到声速/密度/衰减映射

## 输出要求

请最终输出三部分：

### 1. 论文参数矩阵

用 Markdown 表格或 CSV 风格均可，尽量字段完整。

### 2. 公开代码/工具矩阵

重点说明这些工具对我们平台有什么借鉴意义。

### 3. 复现路线建议

请明确回答：

- 我们当前平台哪些参数可以暂时保留？
- 哪些参数必须复核？
- 下一步应优先对齐哪篇论文或哪套工具？
- 我们距离论文级复现还差哪些关键模块？
- 哪些方向只适合综述，不适合直接用于当前仿真复现？

## 注意事项

- 不要把 BBB、血栓、热消融、Histotripsy 的参数直接混用到神经调控 tFUS。
- 不要把单篇论文参数误写成领域共识。
- 如果论文没有报告某个参数，请标记为 `未报告`，不要猜。
- 如果工具需要 GPU、大型数据或复杂依赖，请明确标记。
- 如果结论来自推断，请写明“推断”。
- 优先引用原论文、官方文档、GitHub README 或工具官网。

## 建议返回格式

请把结果整理成一个 Markdown 文档，建议结构如下：

```markdown
# tFUS 文献与公开代码参数对照

## 1. 论文参数矩阵

| paper_id | title | year | application | frequency | pressure_or_intensity | solver | data_input | acoustic_mapping | thermal_model | relevance_to_our_platform |
|---|---|---|---|---|---|---|---|---|---|---|

## 2. 公开代码/工具矩阵

| tool_id | name | url | language | solver_backend | input_data | output_data | what_to_learn | risk_or_limit |
|---|---|---|---|---|---|---|---|---|

## 3. 参数共识与特例

## 4. 当前平台差距

## 5. 推荐复现路线
```
