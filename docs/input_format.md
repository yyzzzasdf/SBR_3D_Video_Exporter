# 三维功率输入格式

每个数据目录至少包含 `power_cube.npz` 和 `metadata.json`。建筑几何和内部掩码可选。常规读取使用 `allow_pickle=False`，所有 NPZ 字段都应为普通数值数组，不能存放 Python 对象。

## 功率立方体

| 字段 | 形状和类型 | 含义 |
|---|---|---|
| `x_centers` | `(Nx,)`，实数 | x 方向体素中心坐标，米 |
| `y_centers` | `(Ny,)`，实数 | y 方向体素中心坐标，米 |
| `z_centers` | `(Nz,)`，实数 | z 方向体素中心坐标，米 |
| `P_coherent_dB` | `(Nx,Ny,Nz)`，float32 或 float64 | 相干功率或相干路径增益 |
| `P_incoherent_dB` | `(Nx,Ny,Nz)`，float32 或 float64 | 非相干功率或非相干路径增益 |

只导出一种功率时，仅对应的 `P_*_dB` 字段必须存在。其他原项目字段如 `P_coherent`、`dx`、`dy`、`dz` 可以保留，本工具不读取它们。

坐标须有限、严格递增，每轴长度至少为 2；支持非等距坐标。数组值 `[ix,iy,iz]` 对应位置 `(x_centers[ix],y_centers[iy],z_centers[iz])`，不要交换 x 和 y。z 为竖直方向。若已有其他轴顺序，制作输入时先转置。

功率至少有一个有限值。未覆盖体素使用 `NaN`，不要用正负无穷；若旧数据将零瓦取对数得到 `-inf`，请先替换成 `NaN`。未覆盖区域会显示为色条最低颜色；只有建筑内部掩码区域显示为透明。

## 单位元数据

```json
{
  "schema_version": 1,
  "coordinate_unit": "m",
  "axis_order": ["x", "y", "z"],
  "value_kind": "received_power_dbw",
  "tx_power_w": 1.0,
  "dataset": "my_case"
}
```

`coordinate_unit`、`axis_order`、`value_kind` 必填。`schema_version` 和 `dataset` 用于记录。可增加数据来源、频率和生成参数等字段，它们会被保存进运行记录。

`value_kind` 允许两种值：

- `received_power_dbw`：数值为 `10 log10(P_rx / 1 W)`。
- `path_gain_db`：数值为 `10 log10(P_rx / P_tx)`。

使用 `--display path_gain` 将 dBW 接收功率转换为 dB 路径增益时，`tx_power_w` 必须为有限正数，转换公式为 `path_gain_dB = received_power_dBW - 10 log10(tx_power_w)`。仅当发射功率为 1 W 时，两者数值才相同。原项目的功率包含接收天线有效面积；准备外部数据时须保持自己的功率定义一致。

## 建筑与发射点

`scene.npz` 使用 VTK 多边形连接格式：

| 字段 | 形状和类型 | 含义 |
|---|---|---|
| `vertices` | `(N,3)`，有限实数 | 建筑顶点的 x、y、z 坐标，米 |
| `faces` | `(K,)`，整数 | 每个多边形写成 `[顶点数, 顶点索引…]`，然后连接起来 |
| `Tx`，可选 | `(3,)`，有限实数 | 发射点坐标，米 |

例如两个三角形可以写成 `faces=[3,0,1,2,3,0,2,3]`。每个面至少三个顶点，索引须落在 `vertices` 范围内。可以使用四边形和多边形，以保留原场景建筑面的外观。

几何必须与功率数据处于同一坐标系。缺少 `scene.npz` 时，只绘制地面与功率切片；不显示建筑或发射点。

## 建筑内部掩码

`inside_mask.npz` 包含 `inside`，类型为 bool、形状为 `(Nx,Ny,Nz)`。`True` 表示建筑内部体素，绘图时变为透明。可同时保存三个 `*_centers` 坐标字段；若保存，则三个字段都必须存在且与功率立方体完全一致。

工具不会从建筑多边形自动推断实体内部。没有掩码时保留功率切片，不挖空建筑。提供掩码可以避免把建筑内部误看作室外覆盖。

## 最小制作示例

```python
from pathlib import Path
import json
import numpy as np

out = Path("my_data")
out.mkdir(exist_ok=True)
x = np.array([0., 10., 20.])
y = np.array([0., 10., 20., 30.])
z = np.array([5., 15., 25.])
power_dbw = np.full((len(x), len(y), len(z)), -80., dtype=np.float32)
power_dbw[0, 0, :] = np.nan
np.savez_compressed(out / "power_cube.npz", x_centers=x, y_centers=y,
                    z_centers=z, P_incoherent_dB=power_dbw)
(out / "metadata.json").write_text(json.dumps({
    "coordinate_unit": "m", "axis_order": ["x", "y", "z"],
    "value_kind": "received_power_dbw", "tx_power_w": 1.0
}), encoding="utf-8")
```

然后运行 `python render_video.py --data my_data --quantities incoherent --out outputs/my_case`。
