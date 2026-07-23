# 现代零售终端智慧运营平台：源码说明

本源码包包含当前 Windows 7 SP1 64 位兼容版本的完整业务源码、YOLO11n-seg ONNX 模型、网页资源、构建脚本、交付脚本和回归测试数据。运行与推理均在本机完成，不依赖外部接口。

## 目录结构

- `app_win7/launcher.py`：本地 HTTP 服务、浏览器启动、上传接口、运行日志和安全退出。
- `app_win7/inference.py`：YOLO11n-seg 图像预处理、ONNX 推理、NMS、分割标注和计分逻辑。
- `app_win7/web/`：五项图片检测网页的 HTML、CSS 和 JavaScript。
- `backend_original/text/best.onnx`：当前推理使用的 ONNX 模型。
- `tests/validate_inference_parity.py`：五张样图的模型输出精确回归测试。
- `tests/run_win7_ui_smoke.js`：网页上传和结果显示自动化检查。
- `diagnostics/normal_detection/samples/`：五张回归样图。
- `diagnostics/header_fix_regression/`：原始推理程序生成的参考结果图。
- `requirements-win7.txt`：Python 3.8 固定依赖版本。
- `build_win7.ps1`：生成 Windows 7 兼容单文件 EXE。
- `package_win7.ps1`：整理最终免安装交付 ZIP。
- `delivery_assets_win7/`：最终交付说明。

## 开发环境

1. 安装 Python 3.8.10 64 位。
2. 安装带 x64 UCRT Redistributable 的 Windows 10/11 SDK。
3. 在源码根目录创建虚拟环境：

```powershell
py -3.8 -m venv .venv-win7
.\.venv-win7\Scripts\python.exe -m pip install -r requirements-win7.txt
```

## 本地运行

```powershell
.\.venv-win7\Scripts\python.exe .\app_win7\launcher.py
```

默认会打开本地网页。服务仅监听 `127.0.0.1`，默认置信度为 `0.25`，IoU 阈值为 `0.45`。

## 模型回归测试

```powershell
.\.venv-win7\Scripts\python.exe .\tests\validate_inference_parity.py
```

测试会运行五张样图，并要求每张输出结果图的 SHA256 与原始推理程序参考结果完全一致。

网页自动化检查为开发期可选测试，需要 Node.js、Microsoft Edge 和 Playwright：

```powershell
npm install
npm run test:ui
```

默认检查 `http://127.0.0.1:18768/`。如服务使用其他端口，可先设置 `APP_BASE_URL`。

## 生成 EXE 和交付 ZIP

```powershell
.\build_win7.ps1
.\package_win7.ps1
```

生成的 EXE 位于 `dist_win7`，最终免安装包位于 `delivery_win7`。

## 计分规则

- `license`：10 分
- `signboard`：15 分
- `cabinet_module`：3 分
- `pillar`：5 分
- `pack_cluster`：5 分

同一类别只计一次分；`total_score` 为本张图片识别到的类别分值之和。

第 5 项“卷烟经营专柜（前柜＋背柜）设施”采用组合判定：识别到 `pack_cluster`，或者同时识别到前柜 `license` 和背柜 `signboard`，均判定本项通过。组合判定时，本项细分值、最高置信度和目标数量取实际参与判定的检测结果。

## Windows 7 兼容版本

- Python 3.8.10 x64
- ONNX Runtime 1.14.1 CPU x64
- NumPy 1.24.4
- OpenCV Headless 4.8.1.78
- PyInstaller 5.13.2

目标系统为 Windows 7 SP1 64 位，并建议安装现有系统更新及 KB2533623。
