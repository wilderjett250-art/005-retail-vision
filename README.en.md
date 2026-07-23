# Project 005: Modern Retail Terminal Intelligent Operations Platform

[简体中文](README.md) · [Original source guide](README_SOURCE.md)

This is an offline AI inspection platform for modern retail terminals. A browser-based interface uploads inspection images to a local Python service, which runs a YOLO11n-seg ONNX model for object detection, instance segmentation, visual annotation, and rule-based scoring. The frontend, backend, and model are delivered together. Runtime traffic is bound to `127.0.0.1`, with no external business API dependency.

![Five-item inspection and composite-rule regression](docs/images/ui-regression.png)

## Capabilities

- Upload, inspect, annotate, and score images for five inspection items.
- Accept JPG, PNG, BMP, and WEBP images up to 35 MB each.
- Run ONNX Runtime CPU inference on Windows terminals without a dedicated GPU.
- Display bounding boxes, segmentation masks, classes, confidence, and target counts.
- Run single-item or batch inspection, clear results, and export data.
- Build a Windows 7 SP1 x64 single-file executable and portable delivery ZIP.
- Verify the model with five exact regression images and a real browser automation test.

## Inspection classes and scoring

| Model class | Inspection item | Score |
| --- | --- | ---: |
| `license` | Front cigarette display cabinet | 10 |
| `signboard` | Back cigarette display cabinet | 15 |
| `cabinet_module` | License display compliance | 3 |
| `pillar` | Store sign type | 5 |
| `pack_cluster` | Cigarette sales cabinet facilities | 5 |

Each detected class contributes at most once per image. `total_score` is the sum of the detected class scores.

Item 5 uses a composite rule:

```text
Direct pack_cluster detection
               OR
Both license (front) and signboard (back)
               │
               ▼
        Item 5 passes inspection
```

For the composite route, the UI derives its detail score, maximum confidence, and target count from the detections that participate in the rule. Browser automation verifies a `25.00` detail score with two participating targets.

## Architecture

| Layer | Implementation |
| --- | --- |
| Frontend | HTML, CSS, vanilla JavaScript |
| Local service | Python `ThreadingHTTPServer` |
| Image processing | OpenCV Headless, NumPy |
| Inference | ONNX Runtime CPU |
| Model | YOLO11n-seg ONNX |
| Windows packaging | PyInstaller 5.13.2, PowerShell |
| Browser testing | Node.js, Playwright, Microsoft Edge |

```text
Browser UI
   │ multipart/form-data
   ▼
127.0.0.1 Python service
   │
   ├─ Image decoding and 1280×1280 preprocessing
   ├─ YOLO11n-seg ONNX inference
   ├─ NMS, mask processing, and rendering
   └─ Class scoring and detection metadata
   │
   ▼
Annotated image + detection details + score
```

## ONNX model

- Path: `backend_original/text/best.onnx`
- Size: approximately 12.1 MB
- SHA-256: `DD2C2EC45F8F657A53B78F812BC555D115754F4A745FDE9E1FFB034B39F51F40`
- Provider: `CPUExecutionProvider`
- Input: `images`, `[1, 3, 1280, 1280]`, `float32`
- Outputs:
  - `output0`: `[1, 41, 33600]`
  - `output1`: `[1, 32, 320, 320]`

## Repository layout

```text
005-modern-retail-terminal-ai-platform/
├─ app_win7/
│  ├─ launcher.py                 Local HTTP service and upload API
│  ├─ inference.py                ONNX inference, segmentation, and scoring
│  └─ web/                        HTML, CSS, and JavaScript frontend
├─ backend_original/text/
│  └─ best.onnx                   Deployment model
├─ tests/                         Exact model and browser regression tests
├─ diagnostics/                   Five samples and five reference results
├─ delivery_assets_win7/          Windows 7 delivery documentation
├─ docs/images/                   Real validation evidence
├─ build_win7.ps1                 Single-file EXE build
├─ package_win7.ps1               Portable runtime packaging
├─ package_source.ps1             Source ZIP packaging
├─ requirements-win7.txt          Pinned Python dependencies
├─ SOURCE_SHA256.txt              Original source package manifest
└─ README_SOURCE.md               Chinese development and packaging guide
```

## Run from source

Python 3.8.10 x64 is recommended:

```powershell
py -3.8 -m venv .venv-win7
.\.venv-win7\Scripts\python.exe -m pip install -r requirements-win7.txt
.\.venv-win7\Scripts\python.exe .\app_win7\launcher.py
```

Run on a fixed port:

```powershell
.\.venv-win7\Scripts\python.exe .\app_win7\launcher.py --no-browser --port 18768
```

Local endpoints:

- `GET /api/status`: model loading status.
- `GET /api/ping`: service health.
- `POST /api/infer`: image upload, inference, and scoring.
- `POST /api/shutdown`: controlled local shutdown.

## Tests

Exact five-image inference regression:

```powershell
.\.venv-win7\Scripts\python.exe .\tests\validate_inference_parity.py
```

Browser automation:

```powershell
npm install
$env:APP_BASE_URL = "http://127.0.0.1:18768/"
npm run test:ui
```

## Windows 7 / Windows 11 packaging

The Windows 7 build uses pinned dependencies:

- Python 3.8.10 x64
- NumPy 1.24.4
- ONNX Runtime 1.14.1 CPU x64
- OpenCV Headless 4.8.1.78
- PyInstaller 5.13.2

After installing the Windows SDK x64 UCRT Redistributable:

```powershell
.\build_win7.ps1
.\package_win7.ps1
```

Regenerate the source package:

```powershell
.\package_source.ps1
```

## Independent verification

| Check | Result |
| --- | --- |
| Original ZIP SHA-256 | `2C7C36D1AD26A8DC6D16FD4D0269C6C53E960B4B6C4BD45FDCE12875B9E05ECA`, exact match |
| ZIP payload | 27 source files |
| `SOURCE_SHA256.txt` | 26/26 entries verified, no unlisted payload file |
| Model loading | Bundled ONNX model loaded with the CPU provider |
| Source syntax | Python, JavaScript, and PowerShell checks passed |
| Five-image model regression | `25 / 20 / 0 / 10 / 0`; every result image matched exactly |
| Browser automation | Direct and front-plus-back composite rules passed |
| Source repackaging | Regenerated a clean 27-file ZIP |
| Single-file EXE | Built successfully; model status was ready and health check returned ok |
| External business dependency | None; runtime communication stays on `127.0.0.1` |

## Publication boundary

- The repository contains the complete frontend, backend, ONNX model, build scripts, samples, reference results, and integrity manifest.
- Virtual environments, `node_modules`, build caches, executables, DLL/PYD/PYC files, runtime logs, and duplicate archives remain outside version control.
- `SOURCE_SHA256.txt` describes the original 27-file source package. The bilingual repository guides and validation image are tracked by Git history.
- Model output supports field inspection and engineering validation; operational decisions should also follow the applicable inspection policy and human review.

