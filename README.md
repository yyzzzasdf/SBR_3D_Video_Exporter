# 三维数据视频导出工具

读取一份三维数值数据，可选叠加场景，导出 x、y、z 三个方向的切片扫描视频和一张水平切片覆盖图。直接绘制输入数值，色条标题和单位由使用者设置。

随包 Manhattan 数据来自射线追踪仿真；`output/` 中的三个视频和覆盖图由 `data/` 中的数据生成。

## 安装与运行

建议使用 Python 3.11。已验证 Windows、Python 3.11 的实际导出；FFmpeg 随依赖安装。

在工具目录打开终端，运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe render_video.py
```

已有依赖环境时，直接运行 `python render_video.py`。

默认生成 `output/sweep_x.mp4`、`sweep_y.mp4`、`sweep_z.mp4` 和 `coverage.png`。重复运行会替换对应结果，开始替换前会先完成全部渲染。视频保持固定相机、统一色条，沿各轴扫描；覆盖图为俯视的 x-y 切片，标题标明实际高度。

## 目录与替换数据

```text
data/                输入：power_cube.npz，另可提供 scene.npz
output/              导出：三个视频和一张覆盖图
video_export/        代码：读取、校验、配置与渲染
render_video.py      运行入口
config.json          配置
requirements.txt     Python 依赖
README.md            使用说明
```

用自己的 `power_cube.npz` 替换 `data/` 中的文件即可。有对应场景时一起替换 `scene.npz`，没有场景时删除它，或使用 `--no-scene`。工具不会自动判断场景是否属于当前数据。

```powershell
python render_video.py --validate-only
python render_video.py --no-scene
python render_video.py --data "D:\my_data" --out "D:\my_videos"
```

配置中的 `input_dir`、`output_dir` 相对于配置文件所在目录；命令行 `--data`、`--out` 和 `--config` 相对于执行命令的当前目录。默认配置和输入输出位置相对于工具目录，因此也可以从其他目录执行入口。

## 输入格式

`power_cube.npz` 使用普通数值数组，字段如下：

| 字段 | 形状 | 含义 |
|---|---|---|
| `x_centers` | `(Nx,)` | x 方向采样坐标 |
| `y_centers` | `(Ny,)` | y 方向采样坐标 |
| `z_centers` | `(Nz,)` | z 方向采样坐标，z 为竖直方向 |
| `values` | `(Nx, Ny, Nz)` | 要显示的三维数值 |
| `inside`，可选 | `(Nx, Ny, Nz)` | 布尔掩码，`True` 区域透明 |

坐标须有限、严格递增，每轴至少两个点，支持非等距坐标。`values[ix, iy, iz]` 对应三个坐标数组中的同位置元素。缺失值用 `NaN`，显示为透明；不能使用无穷值。至少需要一个未被掩码遮挡的有限数值。若显示对数数值，请在制作输入时完成转换，工具不会自动取对数或更改单位。

最小输入示例：

```python
import numpy as np
from pathlib import Path

Path("data").mkdir(exist_ok=True)
x = np.array([0., 10., 20.])
y = np.array([0., 10., 20., 30.])
z = np.array([5., 15., 25.])
values = np.full((len(x), len(y), len(z)), -80., dtype=np.float32)
np.savez_compressed("data/power_cube.npz",
                    x_centers=x, y_centers=y, z_centers=z, values=values)
```

可选的 `scene.npz` 使用同一坐标系和坐标单位：

| 字段 | 形状 | 含义 |
|---|---|---|
| `vertices` | `(N, 3)` | 几何顶点坐标 |
| `faces` | 一维整数数组 | 多边形连接：依次存放顶点数、各顶点索引 |
| `marker`，可选 | `(3,)` | 红色标记点坐标 |

例如两个三角形的 `faces` 为 `[3, 0, 1, 2, 3, 0, 2, 3]`，索引从 0 开始。NPZ 不支持 Python 对象数组。几何不会自动生成内部掩码；需要挖空时提供 `inside`。

## 配置与常用参数

修改 `config.json` 即可调整画面，命令行参数优先。例如：

```powershell
python render_video.py --axes z --fps-z 2 --width 1920 --height 1440
python render_video.py --coverage-only --coverage-z 15
python render_video.py --scalar-label "Temperature (C)" --dyn-range 30
```

| 配置字段 | 默认配置 | 作用 |
|---|---|---|
| `input_dir`、`output_dir` | `data`、`output` | 输入和输出目录 |
| `axes` | `["x", "y", "z"]` | 扫描方向；只替换本次选中的视频 |
| `fps_x`、`fps_y`、`fps_z` | 10、10、3 | 每秒帧数 |
| `frames_x`、`frames_y`、`frames_z` | `null` | 各方向抽样帧数；`null` 使用全部切片 |
| `width`、`height` | 1280、960 | 输出像素尺寸，至少 320×240，须为 16 的倍数 |
| `coverage_z` | `null` | 覆盖图高度；`null` 使用最低层，否则取最近的现有层 |
| `scalar_label` | `Power (dBW)` | 色条标题，换数据时按实际含义修改 |
| `coordinate_unit` | `m` | 坐标单位标签，不转换坐标 |
| `vmin`、`vmax` | `null` | 色条上下限；默认上限为未被掩码遮挡的有限最大值 |
| `dyn_range` | 70 | 默认色条下限为上限减去该值，使用输入数值的单位 |
| `cmap` | `turbo` | 颜色映射 |
| `elevation`、`azimuth` | 28、-60 | 视频相机俯仰角和水平角，度 |
| `zoom`、`z_scale` | 1、1 | 相机缩放、竖直显示比例；数值不变 |
| `scene_opacity`、`slice_opacity` | 0.35、1 | 场景、数据切片透明度 |
| `marker_radius`、`ground_z` | 4.5、0 | 标记点半径和视频地面高度，使用坐标单位 |

覆盖图高度须位于数据的 z 范围内，标题显示实际选中的层。视频抽样包含首尾切片；单帧取首片；帧数最多为该轴层数，不通过复制帧延长视频。时长约为帧数除以帧率。Manhattan 数据尺寸为 40×55×9，默认三个视频分别为 4、5.5、3 秒；覆盖图位于 5 米层。

所有配置字段均有内置默认值，自定义配置可只写需要改变的项。数值和坐标标签由使用者负责；三个视频和覆盖图共用一个色条范围。图形驱动或离屏渲染失败时，先用 `--validate-only` 检查输入，再检查当前电脑的图形驱动。
