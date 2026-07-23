# 项目 005：现代零售终端智慧运营平台

[English](README.en.md) · [原始源码使用说明](README_SOURCE.md)

这是一个面向现代零售终端现场检查的离线 AI 识别平台。系统通过浏览器页面上传检查图片，由 Python 本地服务调用 YOLO11n-seg ONNX 模型完成目标检测、实例分割、结果标注和规则计分。前端、后端和模型均随源码仓库交付，运行时仅监听 `127.0.0.1`，不依赖外部业务接口。

![五项检查与组合规则回归结果](docs/images/ui-regression.png)

## 核心能力

- 五项检查图片分别上传、检测、标注和计分。
- 支持 JPG、PNG、BMP、WEBP，单张图片限制为 35 MB。
- ONNX Runtime CPU 本地推理，适用于无独立显卡的 Windows 终端。
- 结果图展示检测框、分割区域、类别、置信度和目标数量。
- 支持逐项检测、批量检测、清空结果和导出数据。
- 提供 Windows 7 SP1 64 位单文件 EXE 构建与免安装 ZIP 打包脚本。
- 提供五张样图的精确模型回归测试和真实网页自动化测试。

## 检查类别与计分

| 模型类别 | 页面检查项 | 分值 |
| --- | --- | ---: |
| `license` | 卷烟陈列区域前柜 | 10 |
| `signboard` | 卷烟陈列区域背柜 | 15 |
| `cabinet_module` | 亮证经营 | 3 |
| `pillar` | 店招类型 | 5 |
| `pack_cluster` | 卷烟经营专柜设施 | 5 |

同一类别在一张图片中只计分一次，`total_score` 为已识别类别分值之和。

第 5 项“卷烟经营专柜（前柜＋背柜）设施”使用组合规则：

```text
直接识别到 pack_cluster
                 或
同时识别到 license（前柜）和 signboard（背柜）
                 │
                 ▼
          第 5 项判定通过
```

组合判定时，页面使用实际参与判定的检测结果计算细分值、最高置信度和目标数量。网页自动化测试固定验证该规则为 `25.00` 分、2 个参与目标。

## 技术架构

| 层级 | 实现 |
| --- | --- |
| 前端 | HTML、CSS、原生 JavaScript |
| 本地服务 | Python `ThreadingHTTPServer` |
| 图片处理 | OpenCV Headless、NumPy |
| 模型推理 | ONNX Runtime CPU |
| 模型 | YOLO11n-seg ONNX |
| Windows 打包 | PyInstaller 5.13.2、PowerShell |
| 网页测试 | Node.js、Playwright、Microsoft Edge |

```text
浏览器页面
   │ multipart/form-data
   ▼
127.0.0.1 Python 服务
   │
   ├─ 图片解码与 1280×1280 预处理
   ├─ YOLO11n-seg ONNX 推理
   ├─ NMS、掩膜处理与结果标注
   └─ 类别计分与检测元数据
   │
   ▼
结果图片 + 检测详情 + 计分结果
```

## ONNX 模型

- 路径：`backend_original/text/best.onnx`
- 大小：约 12.1 MB
- SHA-256：`DD2C2EC45F8F657A53B78F812BC555D115754F4A745FDE9E1FFB034B39F51F40`
- 提供器：`CPUExecutionProvider`
- 输入：`images`，`[1, 3, 1280, 1280]`，`float32`
- 输出：
  - `output0`：`[1, 41, 33600]`
  - `output1`：`[1, 32, 320, 320]`

## 项目结构

```text
005-modern-retail-terminal-ai-platform/
├─ app_win7/
│  ├─ launcher.py                 本地 HTTP 服务、上传接口与模型状态
│  ├─ inference.py                ONNX 推理、分割标注和计分
│  └─ web/                        HTML、CSS、JavaScript 前端
├─ backend_original/text/
│  └─ best.onnx                   部署模型
├─ tests/
│  ├─ validate_inference_parity.py 五图精确回归
│  └─ run_win7_ui_smoke.js        网页组合规则自动化测试
├─ diagnostics/                   五张样图与五张参考结果图
├─ delivery_assets_win7/          Windows 7 交付说明
├─ docs/images/                   本次真实验证截图
├─ build_win7.ps1                 单文件 EXE 构建
├─ package_win7.ps1               免安装运行版打包
├─ package_source.ps1             源码 ZIP 打包
├─ requirements-win7.txt          Python 固定依赖
├─ SOURCE_SHA256.txt              原始源码包文件校验清单
└─ README_SOURCE.md               中文开发、运行和打包说明
```

## 开发运行

建议使用 Python 3.8.10 64 位：

```powershell
py -3.8 -m venv .venv-win7
.\.venv-win7\Scripts\python.exe -m pip install -r requirements-win7.txt
.\.venv-win7\Scripts\python.exe .\app_win7\launcher.py
```

程序自动选择空闲本地端口并打开浏览器。固定端口运行：

```powershell
.\.venv-win7\Scripts\python.exe .\app_win7\launcher.py --no-browser --port 18768
```

服务接口：

- `GET /api/status`：模型加载状态。
- `GET /api/ping`：服务健康检查。
- `POST /api/infer`：图片上传、模型推理和计分。
- `POST /api/shutdown`：本地程序安全退出。

## 测试

五图精确回归：

```powershell
.\.venv-win7\Scripts\python.exe .\tests\validate_inference_parity.py
```

网页自动化：

```powershell
npm install
$env:APP_BASE_URL = "http://127.0.0.1:18768/"
npm run test:ui
```

## Windows 7 / Windows 11 构建

Windows 7 目标环境依赖已固定：

- Python 3.8.10 x64
- NumPy 1.24.4
- ONNX Runtime 1.14.1 CPU x64
- OpenCV Headless 4.8.1.78
- PyInstaller 5.13.2

安装 Windows SDK x64 UCRT Redistributable 后执行：

```powershell
.\build_win7.ps1
.\package_win7.ps1
```

源码包重新生成：

```powershell
.\package_source.ps1
```

## 本次独立性验证

| 检查 | 结果 |
| --- | --- |
| 原始 ZIP SHA-256 | `2C7C36D1AD26A8DC6D16FD4D0269C6C53E960B4B6C4BD45FDCE12875B9E05ECA`，与交付值一致 |
| ZIP 有效文件 | 27 个 |
| `SOURCE_SHA256.txt` | 26/26 文件校验通过，无漏列载荷文件 |
| 模型加载 | 包内 ONNX 模型通过 CPU 提供器加载 |
| Python / JavaScript / PowerShell | 语法检查全部通过 |
| 五图模型回归 | `25 / 20 / 0 / 10 / 0`，五张结果图逐张精确匹配 |
| 网页自动化 | 直检与“前柜＋背柜”组合规则均通过 |
| 源码自打包 | 重新生成 27 文件 ZIP，无嵌套压缩包或构建二进制 |
| 单文件 EXE | 实际构建成功，启动后模型 ready、健康检查 ok |
| 外部业务依赖 | 无；应用仅访问本机 `127.0.0.1` |

## 发布边界

- 仓库保留完整前端、后端、ONNX 模型、构建脚本、测试素材、参考结果和校验清单。
- 虚拟环境、`node_modules`、构建缓存、EXE、DLL、PYD、PYC、运行日志和重复 ZIP 不进入版本控制。
- `SOURCE_SHA256.txt` 对应用户提供的原始 27 文件源码包；本仓库新增的双语首页和验证截图由 Git 提交历史追踪。
- 模型输出用于现场检查辅助与工程验证，正式业务结论应结合现场规范和人工复核。

