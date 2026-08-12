# 005 Retail Vision Inspection

> A local vision-inspection tool that detects retail objects, applies combination rules, scores the image, and exports results.

## Problem

Manual store inspections are slow and inconsistent, and their results are difficult to preserve and review.

## Demo

![Regression result](docs/images/ui-regression.png)

Upload a test image to see annotations, classes, confidence, counts, and the score.

Image upload, inference, scoring, and result export form one reproducible flow.

## Highlights

- Five inspection categories, including the front/back cabinet combination rule.
- YOLO11n-seg ONNX inference on CPU.
- Exports classes, confidence, counts, annotated images, and scores.
- Win7/Win11 build scripts with exact regression tests.

## Tech

`HTML · CSS · JavaScript · Python · OpenCV · NumPy · ONNX Runtime · PyInstaller`

## Reproduce from ZIP

1. Extract the ZIP and install the Python packages from `requirements-win7.txt`.
2. Run `python app_win7/launcher.py` and open the local page shown in the terminal.
3. Upload a test image from `diagnostics`.
4. Review the annotations and score; use the included Windows build scripts when packaging an EXE for users.

**Expected result:** After these steps, you should see the project's page, window, device output, or test result.

## Scope and Safety

The model and test images are delivery samples; re-evaluate thresholds and rules with your own data before production inspection.

## Contact

Open to technical exchange.
