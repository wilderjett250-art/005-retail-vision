# 005 零售终端视觉巡检 / Retail Vision Inspection

> 上传门店图片，在本地完成目标检测、组合规则判断、计分和结果导出。
>
> **English:** A local vision-inspection tool that detects retail objects, applies combination rules, scores the image, and exports results.

## 解决什么问题 / Problem

人工巡店耗时、检查标准不一致，而且检查结果难以保存和复核。

**English:** Manual store inspections are slow and inconsistent, and their results are difficult to preserve and review.

## 项目展示 / Demo

![回归测试结果 / Regression result](docs/images/ui-regression.png)

上传测试图片后，页面展示标注图、识别类别、置信度、目标数量和评分。

从图片上传到识别、计分、结果图导出是一条可复现流程。

**English:** Image upload, inference, scoring, and result export form one reproducible flow.

## 高光亮点 / Highlights

- 五类检查项和第 5 项前柜/背柜组合规则。
  **English:** Five inspection categories, including the front/back cabinet combination rule.
- YOLO11n-seg ONNX CPU 推理。
  **English:** YOLO11n-seg ONNX inference on CPU.
- 输出类别、置信度、目标数量、标注图和分数。
  **English:** Exports classes, confidence, counts, annotated images, and scores.
- Win7/Win11 构建脚本与精确回归测试。
  **English:** Win7/Win11 build scripts with exact regression tests.

## 技术名词 / Tech

`HTML · CSS · JavaScript · Python · OpenCV · NumPy · ONNX Runtime · PyInstaller`

## 从 ZIP 开始复现 / Reproduce from ZIP

1. 解压 ZIP，安装 `requirements-win7.txt` 中的 Python 依赖。
2. 执行 `python app_win7/launcher.py`，按终端提示打开本地页面。
3. 上传 `diagnostics` 中的测试图片。
4. 查看标注结果和分数；需要交付给普通用户时使用包内 Windows 构建脚本生成 EXE。

**Expected result:** 完成上述步骤后，应能看到项目的页面、窗口、设备输出或测试结果。

**Expected result:** After these steps, you should see the project's page, window, device output, or test result.

## 范围与安全 / Scope and Safety

模型和测试图片属于交付样例；生产巡检前应使用自己的数据重新评估阈值和规则。

**English:** The model and test images are delivery samples; re-evaluate thresholds and rules with your own data before production inspection.

## 交流 / Contact

欢迎交流技术。

Open to technical exchange.

[English full version](README.en.md)
