from __future__ import annotations

import hashlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "app_win7"))

from inference import YOLO11Seg  # noqa: E402


EXPECTED_SCORES = {
    "01_store_interior": 25.0,
    "02_service_station": 20.0,
    "03_store_scene": 0.0,
    "04_front_cabinet": 10.0,
    "05_back_cabinet": 0.0,
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def main() -> int:
    model = YOLO11Seg(str(PROJECT_ROOT / "backend_original" / "text" / "best.onnx"))
    sample_dir = PROJECT_ROOT / "diagnostics" / "normal_detection" / "samples"
    reference_dir = PROJECT_ROOT / "diagnostics" / "header_fix_regression"
    failures = []
    for sample_path in sorted(sample_dir.iterdir()):
        if not sample_path.is_file():
            continue
        result_bytes, detections, total_score, _ = model.infer_image_bytes(
            sample_path.read_bytes(),
            0.25,
            0.45,
        )
        reference_path = reference_dir / (sample_path.stem + ".result.jpg")
        same_hash = sha256_bytes(result_bytes) == sha256_bytes(reference_path.read_bytes())
        expected_score = EXPECTED_SCORES[sample_path.stem]
        passed = same_hash and total_score == expected_score
        print(
            "{} score={} detections={} exact_image_match={}".format(
                sample_path.name,
                total_score,
                len(detections),
                same_hash,
            )
        )
        if not passed:
            failures.append(sample_path.name)
    if failures:
        print("FAILED: {}".format(", ".join(failures)))
        return 1
    print("PASS: all five inference outputs exactly match the supplied backend")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
