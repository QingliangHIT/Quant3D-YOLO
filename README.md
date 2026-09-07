# Quant V1.1 使用说明

Quant 是一款面向工业影像场景的桌面软件，集 **图像采集、YOLO 目标检测、相机标定、二维/三维测量与体素分析** 于一体。基于 PyQt5 构建，支持单图浏览、批量处理与相机实时预览三种工作模式。

- 版本：1.1.0
- 入口：`python main.py`

---

## 目录

1. [功能特性](#功能特性)
2. [环境要求](#环境要求)
3. [安装与启动](#安装与启动)
4. [界面概览](#界面概览)
5. [快速上手](#快速上手)
6. [工程管理](#工程管理)
7. [打开图像与标注](#打开图像与标注)
8. [YOLO 检测](#yolo-检测)
9. [点检测（局部/跨图）](#点检测局部跨图)
10. [测量（2D / 3D）](#测量2d--3d)
11. [三维体素分析与分割算子](#三维体素分析与分割算子)
12. [批量检测与结果导出](#批量检测与结果导出)
13. [相机采集](#相机采集)
14. [相机标定](#相机标定)
15. [全局设置](#全局设置)
16. [快捷键](#快捷键)
17. [模型与标注文件格式](#模型与标注文件格式)
18. [常见问题](#常见问题)

---

## 功能特性

- **三种视图**：单图视图（Image View）、批量视图（Images View）、相机视图（Camera View），可随时切换。
- **YOLO 检测**：支持 `detect / segment / pose / classify / obb` 五类任务；整图检测与点击式局部检测。
- **模型管理**：模型下拉框自动合并「模型目录扫描到的本地 `.pt`」与「内置可选模型」，也可通过浏览按钮手动指定任意权重文件。
- **标注叠加**：可显示人工标注（标签文件）与检测结果，支持按类别筛选、框/置信度/标签开关。
- **测量分析**：右键即可测量单目标 2D/3D 尺寸、全图表面信息与体素信息。
- **三维体素**：阈值分割、二值化、填孔/留孔、高亮、标记等算子，配合 PyVista 三维窗口可视化。
- **批量导出**：检测结果可保存为 YOLO txt / labelme json / COCO json / 掩码图像 / 叠加图像。
- **相机采集**：拍照、录像、连拍、分辨率切换、自动/手动对焦、FPS 显示、实时检测。
- **相机标定**：棋盘格 / 圆点网格角点提取，单目标定，任务队列批处理，结果落盘。
- **工程持久化**：以工程目录组织数据，`config.ini` 记录输出目录与序号，自动恢复上次工程。

---

## 环境要求

| 项目 | 要求 |
|---|---|
| 操作系统 | Windows（相机枚举依赖 WMI，建议 Windows 10/11） |
| Python | 3.12（推荐 conda 环境，如 `quantv3-0`） |
| GPU | 可选。有 CUDA GPU 时 YOLO 推理更快；无 GPU 亦可运行 |

主要依赖（完整见 [`requirements.txt`](requirements.txt)）：

```
PyQt5, opencv-python, numpy, torch, ultralytics,
pyvista, scikit-image, matplotlib, tqdm, wmi, GPUtil
```

---

## 安装与启动

1. **创建并激活虚拟环境**（推荐 conda）：

   ```powershell
   conda create -n quantv3-0 python=3.12 -y
   conda activate quantv3-0
   ```

2. **安装依赖**：

   ```powershell
   pip install -r requirements.txt
   ```

   > `torch` 若需 GPU 加速，请按 [pytorch.org](https://pytorch.org) 说明安装对应 CUDA 版本。

3. **启动软件**：在项目根目录执行

   ```powershell
   python main.py
   ```

启动后会自动尝试打开上次使用的工程（记录在根目录 `settings.ini`）。若主窗口装配失败，会弹出错误提示并在控制台打印堆栈。

---

## 界面概览

主窗口由 **菜单栏、工具栏、中央视图、停靠面板、状态栏** 组成。

### 菜单栏

| 菜单 | 主要项 |
|---|---|
| **File** | 工程 Open / New / Save / Current / Load；Open（打开图像）、Open Folder（打开文件夹）、Load Label Paths（载入标注目录）、Exit |
| **Edit** | Undo、Redo、Zoom In、Zoom Out、Fit Window（适应窗口） |
| **View** | Image View / Images View / Camera View 三种视图开关、Fullscreen（全屏） |
| **Tools** | Show Label、Show YOLO Results、Show Calibration、YOLO Detect、YOLO Point Detect、Camera Calibration（子菜单）、Mask for Calculation、Settings |
| **Help** | About |

### 中央视图（三选一）

- **单图视图 Image View**：逐张浏览、检测、标注叠加、右键测量。
- **批量视图 Images View**：一键批量检测、结果导出、三维视图入口。
- **相机视图 Camera View**：实时预览、拍照、录像、连拍、标定采集。

### 常用停靠面板

- **Files（文件列表）**：图像队列、翻页跳转、右键批量操作。
- **YOLO Parameters（检测参数）**：模型/任务选择、置信度、IOU、点检测块大小、最大检测数、类别筛选。
- **Annotations（标注）**：检测结果树、统计、标注列表，及框/置信度/标签/筛选开关。
- **Categories（类别）**：当前图像命中的检测类别。
- **Info（信息）**：当前图像与目标的统计信息。
- **3D Control（三维控制）**：阈值/二值化参数、色图，及三维工具条。
- **Control（相机控制）**：拍照/录像/连拍、变焦、对焦、分辨率。

---

## 快速上手

一个典型的「打开图像 → 检测 → 查看/测量 → 导出」流程：

1. 启动软件，（可选）**File → New** 新建工程，指定工程名、保存路径与数据输出目录。
2. **File → Open Folder** 载入一个包含图像的文件夹，图像会出现在 Files 面板。
3. **View → Image View** 切换到单图视图，在 Files 面板点击任意图像显示。
4. **Tools → YOLO Detect** 打开整图检测；右侧 YOLO Parameters 面板选择模型与任务，调节置信度/IOU。
5. 结果会叠加显示在图像上；在 Annotations / Categories 面板查看明细。
6. 需要测量时，在图像上 **右键** 选择「Measure Object Information」等菜单项。
7. 切换到 **View → Images View**，点击工具栏「Batch Detect」批量检测，再通过「Save View」导出结果。

---

## 工程管理

工程用于组织采集与检测数据。

- **新建工程（File → New，Ctrl+N）**：填写
  - *Project Name*：工程名（会在保存路径下自动创建同名文件夹）；
  - *Save Path*：工程根目录；
  - *Data Save Directory*：数据输出子目录（默认 `capture`）。
  创建后在工程目录生成 `config.ini`，记录 `save_dir`、图像序号 `i_img`、视频序号 `i_vid`。
- **打开工程（File → Open）**：选择含 `config.ini` 的目录。
- **载入工程输出目录（File → Load，Ctrl+Shift+L）**：把工程 `save_dir` 下的图像/视频批量载入 Files 面板，并同步序号。
- **保存工程（File → Save，Ctrl+Shift+S）**：写回 `config.ini`，并记录为最近工程。
- **当前工程信息（File → Current）**：查看工程目录、输出目录与序号。

> 最近工程记录在项目根目录的 `settings.ini`（键 `last_project`），下次启动自动恢复。

---

## 打开图像与标注

- **打开图像（File → Open，Ctrl+O）**：多选 `*.png / *.jpg / *.jpeg / *.bmp`。
- **打开文件夹（File → Open Folder，Ctrl+Shift+O）**：载入目录下全部受支持图像。
- **载入标注目录（File → Load Label Paths）**：指定标注文件目录后，开启 **Tools → Show Label** 即可把人工标注叠加到图像。
  - 支持标注格式：YOLO `.txt`、labelme `.json`、Pascal VOC `.xml`，以及掩码图像（`.png/.jpg/.bmp` 等）。
  - 标注文件按 **同名匹配**（去掉扩展名后与图像同名）自动关联。

**显示开关（Tools 菜单）**：

- *Show Label*：显示人工标注叠加。
- *Show YOLO Results*：显示检测结果叠加。
- *Show Calibration*：显示标定角点检测结果。

在 **Annotations** 面板可进一步控制：切换任务档位、按类别筛选显示、开关检测框 / 置信度 / 标签文字。

---

## YOLO 检测

### 开启检测

- **Tools → YOLO Detect**：对当前图像做整图检测并叠加结果。首次开启会自动加载模型；加载失败会保持关闭并给出提示。
- 检测开关与参数面板联动：任一检测功能开启时，右侧 **YOLO Parameters** 面板自动显示。

### 选择模型（改进后）

YOLO Parameters 面板顶部的 **Model** 一行包含「可编辑下拉框 + 浏览按钮 `...`」：

- **下拉框内容 = 模型目录扫描 + 内置可选模型**
  - 软件启动时会扫描模型目录 `assets/models/` 下的全部 `.pt` 权重并列出（如 `hole`、`holeX`）；
  - 同时合并内置可选模型名（如 `yolov8n`、`yolov8n-seg` 等，这些在联网时可由 ultralytics 自动下载）；
  - 两者按名称去重，内置项在前、目录新增项在后。
- **手动指定模型**（两种方式）：
  1. 点击 `...` **浏览按钮**，在文件对话框中选择任意 `.pt` 权重（可不在模型目录内），选中后会以完整路径写入下拉框并立即加载；
  2. 下拉框可编辑，直接 **输入模型名或完整路径** 后回车。
- 解析规则：输入含路径分隔符时按该路径直接加载；否则先在 `assets/models/<名称>.pt` 查找，再回退到当前工作目录。

> 新增本地模型：把 `.pt` 文件放入 `assets/models/`，重启软件即可在下拉框看到；或直接用浏览按钮选择该文件，无需重启。

### 任务类型与参数

- **Task**：`detect / segment / pose / classify / obb`。切换模型时会自动同步为该模型的任务类型，也可手动切换以改变渲染方式。
- **Confidence**：置信度阈值（0–1）。
- **IOU**：非极大值抑制的交并比阈值。
- **Patch Size**：点检测时局部区域占图像的百分比。
- **Max Detections**：单图最大检测数量。
- **Classes**：类别筛选列表，可全选 / 全不选，仅显示勾选类别。

---

## 点检测（局部/跨图）

- **Tools → YOLO Point Detect** 开启后，鼠标变为十字光标。
- 在图像上 **单击** 即以该点为中心、按 *Patch Size* 裁出局部区域做检测，适合小目标精细定位。
- 局部检测框会短暂显示，随后自动隐藏。
- 另有跨图 3D 点检测：以点击点为种子，在所有已载入图像中查找包含该点的目标（用于三维体素关联）。

---

## 测量（2D / 3D）

在 **单图视图** 中，当已开启 *Show Label* 或 *Show YOLO Results* 且图像存在检测框时，**右键** 弹出测量菜单：

| 菜单项 | 说明 |
|---|---|
| Select: N | 选中并高亮第 N 个目标 |
| Measure Object Information | 测量单个目标的 2D 尺寸信息 |
| Measure 3D Object Information | 测量单个目标的 3D 尺寸信息 |
| Measure Surface Information | 统计全图 2D（表面）信息 |
| Measure Voxel Information | 统计全图 3D（体素）信息 |
| Delete Nearest Detection Result | 删除离光标最近的检测结果 |

> 像素到物理尺寸（mm）的换算比例由 `quant/core/config.py` 的 `MetricConfig`（`dx / dy / dz`）决定，可按实际标定结果调整。

---

## 三维体素分析与分割算子

切换到 **批量视图（Images View）** 后，可使用 **3D Control** 面板与其工具条。

### 面板参数

- **Process All**：对全部图像处理（否则仅当前页）。
- **Binarization**：是否二值化。
- **Threshold**：分割阈值（0–255）。
- **Color**：二值化颜色值。
- **Colormap**：三维渲染色图（Viridis / Plasma / Inferno / Magma / Jet / Hot / Gray）。

### 工具条算子

| 按钮 | 作用 |
|---|---|
| 3D View | 显示 / 隐藏 PyVista 三维窗口 |
| Hole | 对选中类别区域做填孔（膨胀） |
| Highlight | 高亮选中类别区域 |
| Show Hole | 仅保留（显示）选中类别区域 |
| Mark | 在图像上标记选中类别区域 |
| Threshold Segmentation | 按阈值分割图像 |
| 2D Calculation | 计算当前页 2D 特征 |
| 3D Calculation | 计算体素 3D 特征 |

---

## 批量检测与结果导出

在 **批量视图（Images View）** 的工具栏：

- **Batch Detect**：对 Files 面板中所有图像一键批量检测（带进度条，可取消）。
- **Reset View**：清空当前缓存与结果，重新加载。
- **3D View**：打开三维体素视图。
- **Save View**（带下拉菜单）：导出结果，可选格式
  - *Save as TXT*：YOLO txt；
  - *Save as JSON*：labelme / COCO json；
  - *Save Mask*：掩码图像；
  - *Save as Image*：叠加渲染后的图像（默认）；
  - *Auto Save*：检测后自动保存；
  - *Save All*：批量保存全部结果；
  - *Set Save Path*：设置默认保存目录（未设置时为 `./output`）。

---

## 相机采集

切换到 **相机视图（Camera View）**，使用 **Control** 面板：

| 控件 | 功能 |
|---|---|
| 📸 | 拍照（快捷键 F1） |
| 🎥 | 开始 / 停止录像（快捷键 F2） |
| 🔁 | 开始 / 停止连拍 |
| ⚙️ | 打开连拍参数设置（间隔、张数等） |
| 🔍+ / 🔎- | 视图放大 / 缩小 |
| AF | 自动对焦开关；关闭后可用 ➖ / ➕ 或数值框手动对焦 |
| FPS | 显示实时帧率 |
| 分辨率下拉框 + 🔄 | 选择/切换采集分辨率（支持自定义输入） |

- 采集到的图像/视频写入当前工程的 `save_dir`，文件名按序号递增。
- **Tools → Camera Calibration → Realtime detect**：开启相机实时检测（下次生效）。
- 相机页支持滚轮缩放、中键拖拽平移。

> 相机枚举在 Windows 下经 WMI 探测。若无可用设备，请检查驱动与占用情况。

---

## 相机标定

**Tools → Camera Calibration** 子菜单：

- **Start Calibration**：打开标定对话框，进行图像采集、角点预览、执行标定与结果展示。
- **Load Corner Detector**：加载角点检测器，设置标定图案类型（棋盘格 / 圆点网格）与内角点行列数。
- **Realtime detect**：相机实时检测开关。

标定流程概要：

1. 通过 *Load Corner Detector* 设置图案类型与行列数。
2. 采集若干张标定图（可从相机页触发采集）。
3. 在标定对话框中预览角点、执行标定。
4. 标定结果以 JSON 持久化，可用于后续测量换算。

> 标定支持任务队列：可新建多条标定/保存任务，逐条自动执行并回报进度。

---

## 全局设置

**Tools → Settings** 打开设置对话框：

- **Theme**：Light / Dark 主题（QSS 样式位于 `assets/styles/`）。
- **Language**：Chinese / English。
- **Camera**：选择相机设备索引。
- **Mask Opacity**：掩码叠加透明度（0–1）。

点击 **Apply** 生效。

**Tools → Mask for Calculation**：加载/管理用于计算的掩码，可设置透明度与是否反相。

---

## 快捷键

| 快捷键 | 功能 |
|---|---|
| Ctrl+O | 打开图像 |
| Ctrl+Shift+O | 打开文件夹 |
| Ctrl+N | 新建工程 |
| Ctrl+Shift+S | 保存工程 |
| Ctrl+Shift+L | 载入工程输出目录 |
| Ctrl+Q | 退出 |
| Ctrl+Z / Ctrl+Y | 撤销 / 重做 |
| Ctrl+= / Ctrl+- | 放大 / 缩小 |
| Ctrl+F | 适应窗口 |
| A / D | 上一张 / 下一张图像 |
| W / S | 跳到第一张 / 最后一张 |
| Ctrl+R | 重置当前视图 |
| Ctrl+Shift+R | 重置检测结果 |
| Ctrl+C / Ctrl+Shift+C | 标注色偏 +1 / -1 |
| Ctrl+M | 显示内存占用 |
| F1 | 相机拍照 |
| F2 | 相机录像 |

> 翻页与重置类快捷键在单图/批量视图下生效。

---

## 模型与标注文件格式

### 模型（权重）

- 默认模型目录：`assets/models/`，放置 `.pt` 权重（如 `hole.pt`、`holeX.pt`）。
- 下拉框列出「目录扫描到的本地权重」+「内置可选模型名」；内置名在联网时可由 ultralytics 自动下载。
- 也可用浏览按钮选择任意位置的 `.pt`，或直接输入完整路径。

### 标注导入（Show Label）

支持：YOLO `.txt`、labelme `.json`、Pascal VOC `.xml`、掩码图像。按同名匹配图像。

### 结果导出（批量视图 Save View）

支持：YOLO `.txt`、labelme `.json`、COCO `.json`、掩码图像、叠加渲染图像。

---

## 常见问题

- **启动报缺少 ultralytics / 无法加载模型**
  检测功能依赖 `ultralytics`，请执行 `pip install ultralytics`。软件会弹出「Missing Dependency」提示。

- **下拉框里没有我刚放入的模型**
  目录扫描在启动时进行。把 `.pt` 放入 `assets/models/` 后需重启；或直接用浏览按钮 `...` 选择该文件即时加载。

- **开启检测没有结果**
  检查置信度阈值是否过高、类别筛选是否把目标类别取消勾选、模型任务类型是否与权重匹配。

- **相机无画面**
  确认设备未被其他程序占用、驱动正常；在 Settings 中选择正确的相机索引。

- **GPU 未被使用 / 推理慢**
  确认安装的是对应 CUDA 版本的 `torch`；无 GPU 时以 CPU 运行，速度较慢属正常。

- **测量尺寸不准**
  测量依赖 `MetricConfig` 的 `dx/dy/dz` 像素-物理换算比例，请先完成相机标定并按结果调整。

---

## 目录结构（简）

```
QuantV3.1/
├── main.py              应用入口
├── requirements.txt     依赖清单
├── settings.ini         最近工程记录（运行时生成）
├── assets/
│   ├── icons/           界面图标
│   ├── models/          YOLO 权重（.pt）
│   └── styles/          light.qss / dark.qss 主题
├── demo/                示例图像 / 标注 / 掩码
└── quant/               产品代码（core/detection/imaging/analysis/
                         calibration/camera/io/project/ui 等模块）
```
