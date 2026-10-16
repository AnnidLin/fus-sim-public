---
aliases: [Pennes, 生物热传导方程, Pennes Bioheat, Pennes热模型]
---
# Pennes 生物热传导方程

Pennes 方程是模拟生物组织中超声热效应、温升和热剂量（如累积热剂量 CEM43）分布的核心物理模型。

## 物理公式
$$\rho C_p \frac{\partial T}{\partial t} = K \nabla^2 T - w_b C_b (T - T_a) + Q_{met} + Q_{us}$$
其中各参数代表：
- $T$: 生物组织局部温度。
- $w_b C_b (T - T_a)$: 局部血液灌注产生的散热效应（灌注率 $w_b$ 越大散热越快）。
- $Q_{us}$: 超声辐射声能转化而来的热源贡献，由局部声强和介质声学吸收系数决定：
  $$Q_{us} = 2 \alpha I$$
