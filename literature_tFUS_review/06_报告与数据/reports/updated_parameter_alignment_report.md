# 文献综述与实验结果对齐更新报告

> 生成时间：2026-07-03 14:09:46
> 生成时基于：07_tFUS文献与公开代码参数对照.md、08_参数对齐报告.md，以及现已归档的历史复刻路线。本文保留为阶段记录，不代表当前执行路线。

## 1. 参数对照更新表（我们的实际值 vs 文献值 vs 差异说明）

| 参数 | 我们的实际值 | 文献参考值 | 差异说明 | 证据等级 |
|---|---|---|---|---|
| 频率 | 500 kHz | Gao 2022: 500 kHz; Legon 2014: 500 kHz; Lee 2016: 270 kHz | 与 Gao/Legon 一致，但 Lee 2016 使用 270 kHz 提醒我们频率非唯一共识 | 原文明确 |
| Source pressure | 0.5–1.0 MPa (source) | Gao 2022: 1.0 MPa source; Legon 2014: ~0.80 MPa peak rarefactional | 我们使用 source pressure 而非 in-situ PNP，必须区分定义 | 由参数推算 |
| Target-window peak (in-situ) | 0.562–0.899 MPa (p500-p800) | Chen 2023: 低强度 tFUS 人体范围（需全文确认） | 0.899 MPa 落在低强度神经调控常见范围高端，需与 Chen 2023 对标 | 待全文复核 |
| Aperture | 25 mm (Gao baseline) / 30 mm (tuned) | Gao 2022: 25 mm; TUSX: 30 mm (3 cm) | 30 mm 为当前 tuned 值，不是文献共识，需自由场验证 | 当前调参值 |
| Radius (curvature) | 30 mm (Gao) / 35 mm (tuned) | Gao 2022: 30 mm; TUSX: 30 mm | 35 mm 为当前调参值，F 数变化影响焦域 | 当前调参值 |
| Duty cycle | 6% | Gao 2022: 6%; Legon 2014: 36% (360 us @ 1 kHz) | 6% 是 Gao 协议特例，不是跨文献共识 | 高鹏皓协议特例 |
| PRF | 300 Hz | Gao 2022: 300 Hz; Legon 2014: 1 kHz | 300 Hz 为 Gao 协议特例 | 高鹏皓协议特例 |
| Train duration | 67 ms | Gao 2022: 67 ms | Gao 协议特例 | 高鹏皓协议特例 |
| Interval | 2.5 s | Gao 2022: 2.5 s | Gao 协议特例 | 高鹏皓协议特例 |
| Grid resolution (dx) | 0.75 mm / 0.5 mm | Gao 2022: 0.42 mm (高精度); PRESTUS: 通常 0.5–1 mm | 0.75 mm 为 standard 预设，0.5 mm 为探索性 finer-grid | 工程验证级 |
| PML size | 12 | PRESTUS/BabelBrain: 通常 8–16 | 当前 12 在合理范围，自由场 pml=8/12 对比无显著差异 | 工程验证级 |
| CFL | 0.2 | k-Wave 默认 0.3; PRESTUS 通常 0.2–0.3 | 0.2 为保守选择，p3b CFL0.1 敏感性分析显示稳定 | 工程验证级 |
| HU threshold | 300 | Montanaro 2021: 阈值选择显著影响声场; 建议扫描 | 300 HU 为当前 baseline，但 250/400 HU 已显示差异 | 常见实用起点 |
| Alpha mapping | simple_hu300 (二值) | PRESTUS: Marsac/Mueller/continuous 多路线; BabelBrain: porosity/Webb | 当前 simple_hu300 为工程 baseline，continuous/prestus_marsac_mueller 处于 review-pending | 工程验证级 |
| Thermal model | Explicit Pennes, 5s+15s Gao cooling | Gao 2022: Pennes + 分段升温降温; Mueller 2016: heating modeled | 协议与 Gao 一致，但 material parameters 为近似值 | 协议对齐 |
| Temperature limit | 42°C (粗阈值) | 常用安全阈值; ITRUSST 建议更精细 | 42°C 为粗阈值，已补充 CEM43 和 skull max temperature | 常用粗阈值 |
| CEM43 limit | brain < 0.1 min, skull < 1 min (工程门控) | 无统一文献共识; ITRUSST 有建议 | 当前门控为工程保守设定，非临床标准 | 工程门控 |

## 2. 与 Gao 2022 等关键文献的对比

### 2.1 Gao 2022（经颅聚焦超声调控系统的参数仿真研究）

| 维度 | Gao 2022 | 我们的当前平台 | 对齐状态 |
|---|---|---|---|
| 换能器 | 单阵元凹球面，aperture 25 mm，radius 30 mm | 同规格为 baseline，另有 tuned 30/35 mm | ✅ 参数一致 |
| 频率 | 500 kHz | 500 kHz | ✅ 一致 |
| Source pressure | 1.0 MPa | 0.5–1.0 MPa 缩放扫描 | ⚠️ 已识别 1.0 MPa 热超标，降级至 0.8 MPa |
| 网格 | 2D/3D，最高 0.42 mm | 0.75 mm standard，0.5 mm 探索性 | ⚠️ 未达到 Gao 高精度，但工程验证级可用 |
| 热协议 | 5s heating + 15s cooling | 完全一致 | ✅ 对齐 |
| 安全阈值 | 42°C | 42°C + CEM43 扩展 | ✅ 扩展更精细 |
| 输出图表 | 候选网格、压力-位置曲线、温升-时间曲线、热图 | 已实现 candidate sweep、pressure profile、thermal time curve、slice plots | ✅ 功能对齐 |

**差异说明**：
- Gao 2022 的 2D/3D 最高 0.42 mm 网格属于论文级精度，当前 0.75 mm 为 engineering baseline，0.5 mm 因热点问题暂停。
- Gao 2022 未报告 skull CEM43 的爆炸性增长，我们的 Pennes 模型在 1.0 MPa source 下 skull CEM43 达到 346.88 min，说明材料参数/热模型假设可能有差异。
- Gao 2022 的 target 声压输出应接近 1.0 MPa 级别（source 直接驱动），而我们的 target-window peak 仅约 0.9–1.1 MPa，存在显著传播损耗，需复核声速/衰减映射。

### 2.2 Legon 2014（人类初级体感皮层调控）

- Legon 2014 使用 0.5 MHz、peak rarefactional pressure ~0.80 MPa，与我们 p700-p800 的 target-window peak（0.787–0.899 MPa）接近。
- 但 Legon 的 duty cycle 为 36%（1 kHz PRF，360 us pulse），远高于我们的 6%（300 Hz），热负荷不可直接比较。
- **定位**：我们的低 duty（6%）+ 短 train（67 ms）方案属于低热负荷神经调控，与 Legon 的高 duty 方案属于不同协议族。

### 2.3 Chen 2023（低强度 tFUS 人体颅骨声场数值与实验评估）

- Chen 2023 提供了真实人体颅骨声场的可量化基准范围，是验证我们仿真结果合理性的关键对标。
- 我们的 0.899 MPa target-window peak（p800）需要确认是否在 Chen 2023 的合理物理区间内。
- 若偏离 >20%，需检查：CT 映射公式、网格分辨率、PML 设置、换能器模型假设。
- **行动建议**：建立人体证据对标检查清单，在每次 CT 声场仿真后评估输出。

### 2.4 Montanaro 2021（CT 参数与颅骨异质性建模影响）

- Montanaro 2021 证明 CT 层厚、重建核、HU 阈值选择会改变声学属性分布，进而影响声场输出。
- 当前 `HU >= 300` 不应是唯一阈值，已建立 250/300/400 敏感性扫描，但 CT 层厚和重建核尚未纳入。
- **行动建议**：在 `build_ct_acoustic_model.py` 中增加 CT 参数敏感性扫描模块。

### 2.5 PRESTUS / BabelBrain（公开工具对标）

| 维度 | PRESTUS | BabelBrain | 我们的平台 | 差距 |
|---|---|---|---|---|
| 语言 | MATLAB | Python/C++ | Python | ✅ 语言一致 |
| Solver | k-Wave | BabelViscoFDTD | k-Wave | ✅ 同 family |
| Skull mapping | Marsac/Aubry/k-plan 多路线 | porosity/Webb | simple_hu300 二值 + continuous 草稿 | ⚠️ mapping 深度差距 |
| Phase correction | 无 | 支持 | 无（single bowl 路线） | ❌ 未实现 |
| Thermal | 支持 | 支持 | Pennes 近似 | ⚠️ 材料参数近似 |
| GPU | 可选 | 推荐 | CPU only | ❌ 算力差距 |
| GUI | 无 | 有 | CLI/脚本 | ⚠️ 无 GUI |

## 3. 当前实验结果在文献上下文中的定位

1. **声压等级**：p800 的 0.899 MPa target-window peak 属于低强度 tFUS 神经调控的高端范围（与 Legon 2014 的 ~0.80 MPa 可比），但 source pressure 0.8 MPa 到 target 的传输效率约 11%（0.899/8.0），说明颅骨衰减显著。
2. **热安全**：所有 p500-p800 的 max dT < 2°C，skull CEM43 < 4 min，在工程保守门控下全绿通过，但尚未与 ITRUSST 临床标准直接对标。
3. **网格分辨率**：0.75 mm 在 tFUS 仿真中属于中等分辨率（PPW≈4），低于 Gao 2022 的 0.42 mm 和 PRESTUS 常见的 0.5 mm，但高于 BabelBrain 的 1 mm 入门级。
4. **聚焦效率**：target-to-global peak ratio 仅 7.5%–8.5%，global peak 始终远离 target（30 mm+），这与 Gao 2022 声称的『靶点处声压最高』有明显差距，说明当前 entry plan 或换能器模型未实现最优聚焦。
5. **材料映射**：simple_hu300 二值映射过于简化，continuous_skull 和 prestus_marsac_mueller 处于 review-pending，与 PRESTUS/BabelBrain 的多路线精细映射有显著差距。

## 4. 建议补充的文献或实验方向

1. **获取 Chen 2023 全文**：建立人体颅骨声压基准范围对标清单，验证 0.899 MPa 的物理合理性。
2. **Pasquinelli 2020 换能器校准**：建立自由场 hydrophone-equivalent 验证流程，确认 aperture/radius 焦距和焦域大小。
3. **ITRUSST 安全标准**：补充 ITRUSST 2020/2023 的 tFUS 安全参数建议，将当前 42°C/CEM43 工程门控升级为文献对标门控。
4. **Leung 2019 / HAS 快速相位校正**：当 single bowl 路线稳定后，引入 HAS 或 Kranion 的相位校正预筛，改善聚焦效率。
5. **Mueller 2016 热安全参考**：该研究指出神经调控参数下温升通常很小但颅骨域影响传播显著，与我们的结果（skull dT > brain dT）一致。
6. **Li 2026 / Kong 2025 映射验证**：交叉验证 multiple mapping profile 的系统性差异，选择最接近实验数据的 profile。
7. **频率扫描**：补充 270 kHz 和 650 kHz 的对比仿真，验证 500 kHz 是否为当前病例最优频率。

## 关联

- [[07_tFUS文献与公开代码参数对照]] — 参数对照母表
- [[08_参数对齐报告]] — 参数定义对齐
- [[06_报告与数据/reports/历史路线/14_历史_本地论文实验步骤与输出复刻规划]] — 复刻路线
- 综合数据对比：[parallel_sweep_integration_report.md](../../../outputs/parallel_sweep_integration_report.md)（位于 `fus-sim/outputs/`，不在本库）
