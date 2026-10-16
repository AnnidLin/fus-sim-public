---
aliases: [k-Wave工具箱, kspace, 伪谱法, k-wave-python]
---
# k-Wave

k-Wave 是用于时域声波传播和光声重构仿真的开源工具箱，基于 k-space 伪谱时间域方法求解。

## 核心算法
- **伪谱法（Pseudospectral method）**：空间导数通过傅里叶变换在频域计算，大幅减少每个波长所需的网格数（PPW），提高大尺度声场计算速度。
- **吸收边界（PML）**：完美匹配层，防止计算边界的反射波干扰。
- **时间步长（CFL）**：Courant-Friedrichs-Lewy 稳定条件，决定声场随时间积分演进时的最大安全步长，防止计算色散或发散。
