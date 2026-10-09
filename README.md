# 三维功率数据视频导出工具

将已有的三维功率数据导出为 x、y、z 三个方向的切片扫描视频，支持相干功率和非相干功率。可叠加建筑、发射点和建筑内部透明区域，并生成预览图。

整个 `video_export_tool` 目录可以直接复制到其他电脑使用。运行时只依赖本目录和 `requirements.txt` 中的 Python 包；输入功率数据由使用者提供，工具不重新执行 SBR 仿真。

## 安装与第一次运行

已验证环境为 Windows 64 位、Python 3.11.9。FFmpeg 随 `imageio-ffmpeg` 安装，无需单独配置。

打开 PowerShell，进入本工具目录。新电脑可以创建一个环境并安装依赖：

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -X utf8 -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe render_video.py --config configs/quick.json
```

下文的 `python` 均指安装了本工具依赖的环境解释器。没有激活环境时，将它替换为 `.\.venv\Scripts\python.exe`；当前 SBR 电脑则使用 `D:\python_env\SBR\python.exe`。

第一次运行使用随包的合成样例，输出位于 `outputs/synthetic/`：六个 MP4、六张预览图和一份 `run.json`。重复运行请换一个输出目录，或加 `--overwrite` 覆盖上次生成的文件。

当前已经部署 SBR 环境的电脑无需重复安装。进入本工具目录后运行：

```powershell
& D:\python_env\SBR\python.exe render_video.py --config configs/quick.json
```

使用其他系统时，可以用环境内的 `python` 执行相同脚本；其他系统的图形驱动和离屏渲染能力未在本次验证中测试。

## 随包数据与视频

| 目录 | 内容 | 用途 |
|---|---|---|
| `examples/synthetic/` | 8×10×6 的合成场，含一个简单建筑 | 快速检查环境和演示输入格式，可用脚本重新生成 |
| `examples/manhattan/` | 新计算的 40×55×9 Manhattan 功率场，间隔 20×20×10 米 | 用真实场景测试导出流程 |
| `reference/synthetic/` | 本工具生成的小样例视频、预览和运行记录 | 对照运行效果 |
| `reference/manhattan_coarse/` | 本工具生成的 Manhattan 小样例视频、预览和运行记录 | 对照真实场景的导出效果 |
| `reference/full_resolution/` | 1920×1440 分辨率的短视频与预览 | 查看默认分辨率的输出 |
| `reference/manhattan/` | 2026 年 7 月 16 日原始运行的六个视频、对比图及元数据副本 | 查看历史 1 米结果的外观 |
| `outputs/` | 使用者生成的结果 | 与随包参考文件分开保存 |

Manhattan 小样例在 2026 年 10 月 9 日使用主项目的 ray 路线新计算：20,000 条发射射线、最多五次反射、28 GHz。它用于演示数据到视频的流程，精度和规模与历史 1 米 ray-d 结果不同。历史视频对应的原始 1 米功率立方体不在本包中，不能用小样例逐帧复现它。

运行真实场景小样例：

```powershell
python render_video.py --data examples/manhattan --config configs/quick.json --out outputs/manhattan
```

## 使用自己的数据

准备一个目录，放入 `power_cube.npz` 和 `metadata.json`。需要叠加建筑时放入 `scene.npz`；需要挖空建筑内部时再放入 `inside_mask.npz`。

```powershell
python render_video.py --data "D:\my_data\case1" --validate-only
python render_video.py --data "D:\my_data\case1" --preview-only --out outputs/case1_preview
python render_video.py --data "D:\my_data\case1" --out outputs/case1_video
```

也可以直接指定文件：

```powershell
python render_video.py --cube "D:\my_data\cube.npz" --metadata "D:\my_data\metadata.json" --scene "D:\my_data\scene.npz" --out outputs/case1_video
```

数组的轴顺序为 `(Nx, Ny, Nz)`，坐标必须严格递增。每个方向至少需要两个体素中心。未覆盖功率使用 `NaN`，建筑内部由布尔掩码表示。详细字段、单位和数据制作示例见 [输入格式](docs/input_format.md)。

## 调整画面与视频

默认参数在 `configs/default.json`，低分辨率快速验证参数在 `configs/quick.json`。配置文件只需写要改变的字段；命令行参数优先于配置文件。

```powershell
python render_video.py --data examples/manhattan --axes z --quantities incoherent --frames-z 9 --fps-z 6 --width 1280 --height 960 --elevation 35 --azimuth -45 --zoom 1.0 --dyn-range 60 --out outputs/custom
```

默认按输入的实际单位标注色条。接收功率使用 dBW；输入本身是路径增益时使用 dB。要将接收功率显示为路径增益，请在元数据填写 `tx_power_w`，并加 `--display path_gain`。完整参数表、帧数与时长关系见 [参数说明](docs/parameters.md)。

## 数据转换与测试

重新生成合成数据：

```powershell
python scripts/generate_synthetic.py --out outputs/new_synthetic_data
```

旧 My_SBR 的 `scene_overlay.npz` 使用 object 数组。只对可信的旧文件运行转换器，将它转换为本工具的纯数值 `scene.npz`：

```powershell
python scripts/convert_legacy_overlay.py "D:\old_data\scene_overlay.npz" "D:\new_data\scene.npz"
```

旧功率 NPZ 里的 `P_coherent_dB`、`P_incoherent_dB`、`x_centers`、`y_centers`、`z_centers` 可直接使用；补上元数据即可，不需要把主项目的 `.pkl` 缓存或计算代码交给使用者。

运行工具自身的输入校验和实际 MP4 渲染测试：

```powershell
python -X utf8 -m pip install -r requirements-dev.txt
python -m pytest -c pytest.ini -q -p no:cacheprovider
```

验证结果见 [验证记录](docs/validation.json)，完整验证环境版本见 [环境记录](docs/environment-tested.txt)，源码与数据来源见 [来源说明](docs/provenance.md)。

## 文件组织

`render_video.py` 是入口；`src/video_export/` 保存读取、校验、配置、渲染代码；`configs/` 保存参数；`examples/` 保存输入；`reference/` 保存随包参考结果；`outputs/` 保存新结果；`scripts/` 保存数据辅助工具；`tests/` 保存验证；`docs/` 保存格式、参数和来源说明。

## 常见问题

- **输出目录已存在结果**：使用新的 `--out`，或明确加 `--overwrite`。
- **画面边缘被裁掉**：降低 `--zoom`，默认 1.0 会按完整场景贴合相机。
- **建筑内仍有颜色**：检查是否提供了与功率网格坐标一致的 `inside_mask.npz`。
- **视频很短**：抽样帧数最多等于该轴的体素数，不会通过复制帧延长时长；降低帧率可让扫描更慢。
- **加载全城数据占用内存较多**：NPZ 会整体解压为数组。两个 74M 体素的 float32 功率场约占 592 MB，另外还需要掩码和渲染缓冲；只导出一种功率可以减少加载量。
- **图形驱动或离屏渲染失败**：先用 `--validate-only` 检查数据，再用快速配置生成单方向预览；安装或更新图形驱动后重试。数据校验通过不等于当前机器已经具备渲染能力。
