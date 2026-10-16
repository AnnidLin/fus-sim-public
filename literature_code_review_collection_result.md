# tFUS 文献与公开代码参数对照

> 目标：围绕 `fus-sim` 当前经颅聚焦超声仿真平台，整理论文参数、公开工具、参数共识/特例和下一步复现路线。

## Codex 结构化校准层

本文件是可读版综述。供后续 Codex 对话直接使用的结构化文件已经拆分到项目根目录：

- `paper_parameter_matrix.csv`
- `paper_parameter_matrix.json`
- `tool_code_matrix.csv`
- `tool_code_matrix.json`
- `parameter_alignment_report.md`
- `reproduction_route_calibration.md`

建议后续对话优先读取 `parameter_alignment_report.md` 和 `reproduction_route_calibration.md`，再读取两个矩阵文件。

## 0. 核心结论先读

- `500 kHz` 可以暂时保留：它落在人类 tFUS 神经调控常见低频段内，也出现在 Legon 2014、本地高鹏皓论文、TUSX 验证和 BabelBrain 内置换能器示例中；但它不是唯一共识频率。
- `1 MPa` 不能直接当作领域共识：它属于人类神经调控常见声压范围的高端或偏高设置，必须区分“源面驱动声压”“自由场声压”和“颅内 in situ 声压”。
- `6% duty cycle / PRF 300 Hz / 67 ms train / 2.5 s interval` 更像高鹏皓论文的协议特例，可继续用于热模型回归测试，但不能当作通用 tFUS 神经调控协议。
- `aperture=25 mm, radius=30 mm` 属于小型单阵元换能器的合理尺度；`aperture=30 mm, radius=35 mm` 是当前平台调参值，需要文献/水槽/自由场对齐，不应写成论文共识。
- `42°C` 是热安全的常用粗阈值，但论文级复现应进一步记录热剂量、协议平均占空比、颅骨最高温和材料敏感性。
- 下一步优先对齐工具路线：`PRESTUS/TUSX` 的 k-Wave 管线组织方式 + `PlanTUS` 的 entry/target 规划思想 + `BabelBrain` 的输出/热安全报告结构。
- 下一步优先对齐论文路线：高鹏皓论文用于单阵元 CT/k-Wave/热效应复现；Leung 2019/HAS 用于快速声束和 tcMRgFUS 对照；Jin 2020/Kranion 用于相位校正参考。

## 1. 论文参数矩阵

| paper_id | title | year | application | data_input | solver | frequency | pressure_or_intensity | PRF | duty_cycle | pulse_train / interval | transducer | skull_model | acoustic_mapping | grid_setup | thermal_model | code_or_data | relevance_to_our_platform | notes |
|---|---:|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Gao2022_local | 经颅聚焦超声调控系统的参数仿真研究 | 2022 | neuromodulation / epilepsy simulation | CT/DICOM | MATLAB k-Wave | 500 kHz 主；对比 250 kHz | source pressure 1 MPa | 300 Hz | 6% | 67 ms train；2.5 s interval | single bowl；aperture 25 mm；radius 30 mm；F=1.67 | CT 二值颅骨；2D/3D；64/105/210/500 网格 | HU/孔隙率估计声速、密度、衰减 | 2D/3D k-Wave；高精度可到 0.42 mm/grid | Pennes/热效应；42°C 判断 | 本地 PDF | 直接复现参考 | 当前平台热协议和 500 kHz/1 MPa 多来自此文，应标记为“种子论文参数”而非领域共识 |
| Pan2021_local | 经颅聚焦超声联合微泡开放血脑屏障的数值仿真研究 | 2021 | BBB / microbubble / cavitation | CT + vessel model | FDTD；Westervelt；Pennes；Keller-Miksis | 0.2-0.7 MHz 扫描；0.7 MHz 示例 | sound power 0.2-0.7 W 安全有效区间；MI 0.3-0.7 | 1 Hz 示例 | 0.04% 示例 | PL、SD 扫描；5-10 us 短脉冲可减弱驻波 | 82-element phased array；aperture 100 mm；radius 80 mm | 62 岁女性 CT；3 mm 层间隔；1 mm pixel | HU 到密度/声速/衰减 | 120 mm cube；dx=0.4 mm；dt=10 ns | Pennes + CNT 成核阈值 | 本地 PDF | 综述/未来 BBB 模块参考 | 不要把 BBB 的 MI/微泡参数混入 neuromodulation 复现参数 |
| Sun2021_local | 经颅聚焦超声治疗脑血栓的数值仿真研究 | 2021 | thrombolysis / histotripsy simulation | CT + brain model | FDTD；Westervelt；Pennes | 0.5-1.1 MHz；0.8 MHz 经颅较优 | 以 PNP -6/-8 MPa 为溶栓阈值；经颅达阈值需更高功率 | T=0.2 ms -> 5 kHz equivalent | 10%；扫描到 50% | T1=0.02 ms；0.2-0.6 s exposure | 82-element bowl；aperture 100 mm；radius 80 mm；element 8 mm | 46 岁男性 CT；经颅/开颅对比 | HU/孔隙率映射颅骨参数 | brain: dx=0.25 mm；transcranial dx=0.3 mm；dt=10 ns | Pennes；最高温升 <2°C | 本地 PDF | 溶栓综述参考；不直接用于 tFUS 神经调控参数 | -6/-8 MPa 是溶栓/histotripsy 阈值，不能用于低强度 neuromodulation |
| Treeby2010 | k-Wave toolbox | 2010 | acoustic simulation toolbox | user-defined medium | k-space pseudospectral | 未限定 | 未限定 | 未限定 | 未限定 | 未限定 | arbitrary source/sensor | user-defined | user-defined sound speed/density/absorption | PML；time-domain grid | 可接热模型但本文不是热论文 | MATLAB k-Wave | 工具理论基础 | 支撑当前 k-wave-python 路线 |
| Treeby2012 | Nonlinear ultrasound in heterogeneous media | 2012 | nonlinear heterogeneous simulation | tissue-like media | k-space pseudospectral | 未限定 | 未限定 | 未限定 | 未限定 | 未限定 | clinical/source examples | heterogeneous media | power-law absorption / nonlinear parameters | k-space grid | 未报告 | 论文方法 | 进阶模块参考 | 后续加入非线性/吸收时再对齐 |
| Legon2014 | Transcranial focused ultrasound modulates S1 in humans | 2014 | human neuromodulation | human skull/targeting | experimental + beam characterization | 0.5 MHz | peak rarefactional pressure about 0.80 MPa；beam FWHM lateral 4.9 mm / axial 18 mm | 1 kHz | 36% by 360 us at 1 kHz（由参数推算） | pulse duration 360 us；total 0.5 s | single-element focused transducer | human transcranial targeting | 未报告 | 未报告 | 未报告 | no code | 参数范围参考 | 500 kHz 和 sub-MPa 级压力是人类神经调控的重要参照 |
| Mueller2016 | Computational exploration of wave propagation and heating from tFUS for neuromodulation | 2016 | neuromodulation simulation / heating | skull/brain geometry | computational acoustic + heating | 基于 human neuromodulation waveforms | abstract 报告 0.5 s exposure heating | 未报告 | 未报告 | 0.5 s exposure | single-element tFUS context | skull, scalp, CSF, gray/white matter, sulci | tissue property sensitivity | 未报告 | heating modeled；bone 0.16°C；brain 4.27e-3°C | no code | 热安全参考 | 支持“神经调控参数下温升通常很小，但颅骨域影响传播显著” |
| Lee2016_V1 | Transcranial focused ultrasound stimulation of human primary visual cortex | 2016 | human neuromodulation / V1 | CT + fMRI targeting | numerical retrospective simulation | 270 kHz | reported on-site intensity/pressure in paper；矩阵中需全文复核 | 未报告 | 未报告 | 未报告 | FUS through PVA hydrogel coupling | CT skull neuroanatomy | 未报告 | retrospective acoustic simulation | 未报告 | no code | 参数范围参考 | 270 kHz 提醒我们频率并不固定为 500 kHz |
| Leung2019_RapidBeam | A rapid beam simulation framework for transcranial focused ultrasound | 2019 | tcMRgFUS / ablation planning | CT/MRI + MR thermometry | rapid 3D numeric / HAS-like framework | tcMRgFUS 常见 650-670 kHz context | temperature rise calibrated against MR thermometry | continuous/therapy context | ablation context | treatment sonication context | phased array therapy system | patient-specific skull | HU attenuation relationship emphasized | rapid framework；not full FDTD | MR thermometry comparison | framework paper | 快速声束/温升校准参考 | 偏 ablation，不可直接拿强度做 neuromodulation |
| Jin2020_Kranion | Open-source phase correction toolkit | 2020 | phase correction / tool validation | CT of cadaver skull | ray-based correction + hydrophone validation | 650 kHz | PNP maps；correction improved peak pressure | 未报告 | 未报告 | sonication scans | ExAblate 1024-element | cadaver skullcap CT | ray tracing through CT skull | hydrophone 2D scan 10x10 mm；0.25 mm step | no | GitHub Kranion / MIT | 相位校正和输出格式参考 | 对当前平台 entry/target 后续相位补偿最有价值 |
| Leung2021_HAS | Transcranial FUS phase correction using HAS | 2021 | phase correction / ablation | CT/skull models | hybrid angular spectrum | ExAblate/tcFUS context | normalized target intensity 74±9%；positioning error 0.35±0.09 mm | 未报告 | 未报告 | 未报告 | phased array tcFUS | CT-based skull aberration | HAS phase correction | fast compared with full wave | ablation relevance | no standalone code found | 快速相位校正参考 | HAS 可作为 k-Wave 大网格前的快速预筛方向 |
| Chen2014_BBB | BBB opening dictated by acoustic pressure | 2014 | BBB / animal | mouse / microbubble | experiment | 1.5 MHz | 0.31/0.51/0.84 MPa | 未报告 | 未报告 | 11 min sonication | single-element FUS | no human skull | 不适用 | 不适用 | tissue histology | no code | BBB 综述参考 | BBB 参数不要用于神经调控；可用于未来 MI/PCD 模块 |
| Maxwell2009_Histotripsy | Noninvasive thrombolysis using histotripsy | 2009 | thrombolysis | in vitro clot | experiment | 未在本矩阵复核 | high PNP cavitation therapy | 未报告 | 未报告 | pulsed cavitation therapy | histotripsy transducer | no transcranial human skull | 不适用 | 不适用 | no thermal focus | no code | 溶栓综述参考 | -6/-8 MPa 阈值只适合溶栓/空化碎裂语境 |

## 2. 公开代码/工具矩阵

| tool_id | name | url | language | solver_backend | input_data | output_data | transducer_model | skull_modeling | thermal_modeling | validation | license | what_to_learn | risk_or_limit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TUSX | Transcranial Ultrasound Simulation Toolbox | https://www.tusx.org/ | MATLAB | k-Wave | structural MR or CT；binary skull volume；NIfTI voxel coordinates | pressure distribution / simulation volume | single-element disc or curved bowl；k-Wave makeBowl/focus | skull/brain processed from MR/CT；cropped ROI；PML sizing | 论文/预印本重点在 acoustic simulation；热支持未作为主页重点 | water tank validation；500 kHz Blatek transducer；diameter 3 cm；focus 3 cm | open-source; exact GitHub link需从官网跳转确认 | 学习“从 NIfTI 坐标指定 transducer 和 target”的轻量接口 | MATLAB + k-Wave；主页信息很简，需进一步拉 README/论文 |
| PRESTUS | PREprocessing & Simulations for TUS | https://github.com/Donders-Institute/PRESTUS | MATLAB | k-Wave | T1 MRI；SimNIBS charm；可用 pseudo-CT/CT informed skull | 3D NIfTI pressure/heating metrics; subject/MNI space | virtual multi-element calibration；entry-target coordinates | water/skin/multilayer skull/brain；continuous skull mapping | acoustic + heating simulations | pipeline/tool validation; Zenodo reference | GPL-3.0 | 最值得学习完整 pipeline：segmentation -> grid -> acoustic -> heating -> reporting | MATLAB/HPC/SimNIBS/k-Wave 依赖重；研究用途，不是医疗工具 |
| BabelBrain | BabelBrain v0.8.1 | https://github.com/ProteusMRIgHIFU/BabelBrain | Python GUI / mixed | BabelViscoFDTD FDTD | MRI/CT/ZTE/PETRA/density maps; planning models | acoustic field, thermal effects, NIfTI, reports | single/ring/dome/phased transducers；内置 H301、IGT64_500 等 | image processing prepares domains; air masks; tissue type support | supports grouped sonications and thermal modeling | BabelViscoFDTD experimentally validated; cross-validated | BSD-3-Clause | 学习 GUI 级输入组织、GPU backend、热协议组合、transducer profiles | GPU 推荐；Windows 需 CUDA/VS；复杂依赖 |
| BabelViscoFDTD | BabelViscoFDTD | BabelBrain dependency | C++/GPU backend | viscoelastic FDTD | prepared domains | pressure/time fields | driven by BabelBrain | isotropic viscoelastic skull/brain | backend for thermal source | Pichardo et al. validation / intercomparison | see upstream | 学习比 fluid-only k-Wave 更完整的 viscoelastic 传播 | 独立接入成本高；当前平台暂不优先 |
| TFUScapes | A Skull-Adaptive Framework for AI-Based 3D tFUS Simulation | https://github.com/CAMMA-public/TFUScapes | Python | AI surrogate / dataset framework | dataset/sample 3D skull-adaptive inputs | AI-predicted 3D tFUS simulation outputs / visualization | paper/dataset dependent | skull-adaptive framework | 未作为重点 | arXiv/project dataset | CC-BY-NC-SA 4.0 dataset | 学习数据集组织和 AI surrogate 评估思路 | 非商业限制；不是当前物理复现第一优先 |
| SynCT | SynCT_TcMRgFUS | https://github.com/han-liu/SynCT_TcMRgFUS | Python / PyTorch | 3D cGAN MRI->CT | T1-weighted MRI input；synthetic CT output | pseudo-CT | 不建模换能器 | synthetic CT skull generation | no | Journal of Medical Imaging paper | MIT | 学习 MRI-only / pseudo-CT 路线，未来无 CT 时有用 | 不是声场 solver；需要训练/模型/数据适配 |
| petra-to-ct | PETRA-TO-CT | https://github.com/ucl-bug/petra-to-ct | MATLAB | pseudo-CT conversion | Siemens PETRA MRI; NIfTI | pCT, debiased image, SPM segmentations | no | PETRA to pseudo-CT；SPM skull/head segmentation | no | conversion derived from paired PETRA/low-dose CT | MIT | 学习 pseudo-CT 与 HU/密度校准文件 | still under development；mapping from 3 subjects；air mapping limitation |
| Kranion | Kranion | https://github.com/jws2f/Kranion | Java GUI / GPU shader | ray tracing phase correction | CT/MRI registration; skullcap CT | phase correction file; ray visualization; PNP maps via validation | 1024-element ExAblate | ray tracing through skull | no | cadaver skull hydrophone validation | MIT per paper | 学习 phase correction、可视化和 ExAblate-style output | 主要是 correction/visualization，不是完整 acoustic/thermal solver |
| PlanTUS | Heuristic planning of TUS transducer placements | https://github.com/mlueckel/PlanTUS | Python | heuristic geometry planning | T1/T2 MRI; SimNIBS charm mesh; target ROI | transform matrices, .kps, candidate transducer placements | user-specified focal distance, aperture, tilt limits | uses skin/skull surfaces and geometric metrics | no | Brain Stimulation 2025 tool note | MIT | 学习 entry/target 候选筛选、avoidance regions、导出 neuronavigation/simulation inputs | 明确不能替代 acoustic simulation；必须后续声场验证 |
| BRIC_TUS | BRIC TUS Simulation Tools | https://github.com/sitiny/BRIC_TUS_Simulation_Tools | MATLAB | likely k-Wave-style scripts | T1 MRI + pseudo-CT | pressure field | NeuroFUS PRO CTX-500-4 only | pseudo-CT skull | 未报告 | tested on 1 mm isotropic images | GPL-3.0 | 学习特定商业换能器的简化脚本组织 | 仅 CTX-500-4；Ubuntu 测试；工具范围窄 |
| RapidBeam | Rapid beam simulation framework | https://www.nature.com/articles/s41598-019-43775-6 | research framework | rapid 3D / HAS-like | CT/MRI + MR thermometry | focal spot position, temperature rise prediction | tcMRgFUS therapy array | patient-specific skull | calibrated against MR thermometry | essential tremor MR thermometry validation | paper; code not confirmed | 学习快速预估与 MR thermometry 校准 | 偏 ablation; 不直接给 low-intensity neuromod 参数 |
| HAS | Hybrid Angular Spectrum phase correction | https://www.nature.com/articles/s41598-021-85535-5 | method/paper | HAS | CT/skull model | phase correction / normalized intensity | ExAblate/tcFUS phased array | CT skull aberration | no | reported target intensity and 0.35 mm positioning error | paper | 学习快速相位校正算法 | 需要实现或找到可用代码；偏 ablation system |
| mSOUND | mSOUND MATLAB toolbox | FUSF tools / mSOUND literature | MATLAB | acoustic wave solver | heterogeneous media / skull model | pressure field | general ultrasound | fully heterogeneous skull models in recent validation | unclear | recent numerical validation | open-source toolbox | 可作为 k-Wave 之外对照 solver | 当前平台已基于 Python/k-Wave，短期不建议迁移 |

## 3. 参数共识与特例判断

| 参数 | 判断 | 理由 | 对当前平台建议 |
|---|---|---|---|
| `500 kHz` | 领域常见范围内，但不是唯一共识 | 人类 neuromodulation 常见低频约 0.25-0.65 MHz；Legon 2014 和高鹏皓论文使用 0.5 MHz；TUSX 水槽验证也用 500 kHz | 可暂时保留为 baseline；后续扫描 270/300/500/650 kHz |
| `1 MPa` | 常见范围高端/论文特例，必须复核定义 | 2025 review 给出 human neuromodulation 约 0.1-1.0 MPa；Legon 2014 约 0.80 MPa；但源面/自由场/颅内声压不同 | 不要直接定为目标颅内声压；报告时写清 source/free-field/in situ |
| `6% duty cycle` | 高鹏皓协议特例 | 任务中来源主要是本地论文；不同人类 tFUS 文献 duty 差异很大 | 可作为热模型回归协议，不作为领域默认 |
| `PRF = 300 Hz` | 高鹏皓协议特例 | Legon 2014 使用 1 kHz；其他研究可用 10 Hz、100 Hz、1 kHz 等 | 保留为 seed protocol；后续做 PRF 参数表 |
| `67 ms train` | 高鹏皓协议特例 | 人类 neuromodulation train 可从数十 ms 到 0.5 s 或更长 | 热模型保留；声场仿真不依赖该值 |
| `2.5 s interval` | 高鹏皓协议特例 | 与其协议节律相关，不是跨文献共识 | 仅用于 protocol-averaged thermal checks |
| `aperture = 25 mm` | 小单阵元合理尺度，但非共识 | 高鹏皓使用 25 mm；TUSX 验证使用 3 cm diameter / 3 cm focus | 可作为单阵元 baseline |
| `radius = 30 mm` | 小单阵元合理尺度，但非共识 | 与 aperture 25 mm 的 F=1.67 组合来自本地论文 | 可保留；要与 aperture/radius sweep 对比 |
| `aperture = 30 mm` | 当前调参值；接近 TUSX 3 cm 验证尺度 | 但不是高鹏皓参数，也不是领域通用默认 | 必须标记为 current tuned parameter |
| `radius = 35 mm` | 当前调参值；非领域共识 | 可能改善当前几何，但缺少文献直接锚定 | 做 source safety + free-field focus calibration |
| `42°C` | 常用热安全粗阈值 | 本地论文和很多热安全评估会关注组织不超过 42°C | 保留，同时增加 thermal dose/CEM43 和 skull max temperature |
| `HU >= 300` | 常见实用起点，但非共识 | CT 骨阈值取决于扫描协议、kernel、目标骨结构；当前平台 250/300/400 HU 已显示敏感性 | 300 HU 可保留为 baseline；必须报告阈值敏感性 |
| CT-HU 到声速/密度/衰减映射 | 领域常用方法，但公式不是唯一共识 | Jin/Kranion、HAS、Leung 等均强调 CT skull modeling；petra-to-ct/PRESTUS 也围绕 CT/pseudo-CT | 把 mapping 函数参数化；避免硬编码单一公式 |

## 4. 当前平台差距

### 已经具备

- CT/NIfTI/DICOM 到 3D 声学模型。
- 3D k-Wave quick pressure。
- target/entry 候选筛选和 source safety 检查。
- Pennes 热模型、protocol-averaged duty 处理和敏感性扫描。
- 079 tuned best 和 Visible Human quick pipeline。
- CT 阈值敏感性、公开病例导入守门脚本、多病例报告骨架。

### 距离论文级复现还缺

1. **自由场/水槽校准层**
   - 需要先确认当前 bowl source 在水中焦距、焦域、峰值声压是否符合给定 aperture/radius/frequency。
   - 对齐 TUSX/Jin 的水槽思路，而不是直接相信颅骨模型结果。

2. **换能器模型校准**
   - 当前 `aperture/radius` 是几何参数，缺少真实设备或文献 transducer profile。
   - 需要明确 single bowl、annular、phased array 的差别。

3. **CT-HU 声学映射可配置化**
   - 当前有 HU 阈值和映射，但需要把声速/密度/衰减公式做成显式 profile，并输出到报告。
   - 需要区分 cortical/trabecular bone 或 continuous mapping。

4. **相位校正**
   - 当前更接近 single bowl / candidate placement；还没有 Kranion/HAS/时间反转式相位校正。
   - 若要做 phased array 论文复现，这是关键缺口。

5. **网格收敛和 PPW/PML 报告**
   - 论文级复现必须报告 dx、PPW、PML、CFL、运行时间、GPU/CPU。
   - 当前 quick runs 适合作工程筛选，不足以称为高精度复现。

6. **热剂量与安全指标扩展**
   - 已有 Pennes 和 42°C 判断，但还需要 skull max、brain target、CEM43 或至少 exposure-time-integrated summaries。

7. **跨病例统计**
   - 当前真实病例有限；Visible Human pipeline 已闭环但聚焦效果弱。
   - 论文级结论至少需要多个病例/公开样本的同一流程结果。

## 5. 推荐复现路线

### 5.1 当前参数怎么处理

可以暂时保留：

- `500 kHz`：baseline 频率。
- `aperture=25 mm / radius=30 mm`：高鹏皓论文复现 baseline。
- `aperture=30 mm / radius=35 mm`：当前 tuned candidate，但只写作 current tuned parameter。
- `6% duty / 300 Hz / 67 ms / 2.5 s`：热模型 seed protocol。
- `HU >= 300`：baseline segmentation threshold。
- `42°C`：粗热安全阈值。

必须复核：

- `1 MPa` 与当前输出 `target_window_peak_mpa` 的物理含义。
- aperture/radius 改变是否只是提升局部数值，还是符合真实换能器焦距。
- CT-HU 映射公式是否过于简化。
- Visible Human 中有效峰值远离 target 的原因：入射方向、source geometry、相位、网格、介质映射、target selection。

### 5.2 下一步优先对齐

第一优先：**TUSX/PRESTUS 式单阵元 k-Wave pipeline**

- 目标：把当前代码报告结构对齐公开工具的输入/输出组织。
- 产出：一个标准 case report，必须列出 input image、skull threshold、mapping profile、transducer profile、grid/PML/PPW、source safety、pressure metrics、thermal metrics。

第二优先：**PlanTUS 式 entry/target 规划**

- 目标：把当前 `scan_ct_entry_positions.py` 的几何筛选升级成可解释 metrics。
- 学习：distance to target、tilt angle、skin/skull normal angle、avoidance region。

第三优先：**自由场/水槽校准**

- 目标：对当前 `aperture/radius` 做水介质焦点验证，先确认源模型正确。
- 学习：TUSX water tank、Jin hydrophone scan 思路。

第四优先：**Kranion/HAS 相位校正**

- 目标：当 single bowl 路线稳定后，再做 phased/ray/HAS correction。

### 5.3 不适合直接混入当前复现的方向

- BBB 微泡参数：适合未来综述和 MI/PCD 模块，不适合直接校准神经调控声压。
- 溶栓/Histotripsy 阈值：适合综述，不适合当前 low-intensity tFUS 平台。
- tcMRgFUS ablation 强度和温升：可学习 CT/HAS/MR thermometry 校准，但不能把 ablation dose 作为 neuromodulation dose。
- AI surrogate 工具如 TFUScapes：适合长期方向，不适合当前物理模型尚未校准时直接替代 k-Wave。

## 6. 参考来源

- TUSX 官网：https://www.tusx.org/
- BabelBrain GitHub：https://github.com/ProteusMRIgHIFU/BabelBrain
- TFUScapes GitHub：https://github.com/CAMMA-public/TFUScapes
- SynCT_TcMRgFUS GitHub：https://github.com/han-liu/SynCT_TcMRgFUS
- Rapid beam simulation framework：https://www.nature.com/articles/s41598-019-43775-6
- Kranion / Jin 2020：https://bmcbiomedeng.biomedcentral.com/articles/10.1186/s42490-020-00043-3
- HAS phase correction：https://www.nature.com/articles/s41598-021-85535-5
- PlanTUS GitHub：https://github.com/mlueckel/PlanTUS
- PRESTUS GitHub：https://github.com/Donders-Institute/PRESTUS
- PETRA-TO-CT GitHub：https://github.com/ucl-bug/petra-to-ct
- BRIC TUS Simulation Tools：https://github.com/sitiny/BRIC_TUS_Simulation_Tools
- Mueller 2016：https://doi.org/10.1088/1741-2560/13/5/056002
- Legon 2014：https://www.nature.com/articles/nn.3620
- Lee 2016 V1：https://www.nature.com/articles/srep34026
- Panoramic review 2025：https://jneuroengrehab.biomedcentral.com/articles/10.1186/s12984-025-01753-2
