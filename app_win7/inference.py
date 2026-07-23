from __future__ import annotations

from typing import Dict, List, Tuple

import cv2
import numpy as np
import onnxruntime as ort


CLASS_MAPPING = {
    0: {"name": "license", "score": 10},
    1: {"name": "signboard", "score": 15},
    2: {"name": "cabinet_module", "score": 3},
    3: {"name": "pillar", "score": 5},
    4: {"name": "pack_cluster", "score": 5},
}

CLASS_COLORS = {
    0: (255, 0, 0),
    1: (0, 255, 0),
    2: (0, 0, 255),
    3: (255, 255, 0),
    4: (255, 0, 255),
}


class YOLO11Seg:
    """YOLO11 segmentation inference reconstructed from the supplied backend."""

    def __init__(self, onnx_model_path: str) -> None:
        self.session = ort.InferenceSession(
            onnx_model_path,
            providers=["CPUExecutionProvider"],
        )
        input_meta = self.session.get_inputs()[0]
        self.input_name = input_meta.name
        self.ndtype = np.float16 if input_meta.type == "tensor(float16)" else np.float32
        self.model_height = 1280
        self.model_width = 1280
        self.class_mapping = CLASS_MAPPING
        self.class_colors = CLASS_COLORS

    def get_color_for_class(self, class_id: int) -> Tuple[int, int, int]:
        return self.class_colors.get(class_id, (255, 255, 255))

    def get_name_for_class(self, class_id: int) -> str:
        return self.class_mapping.get(class_id, {}).get("name", "unknown")

    def get_score_for_class(self, class_id: int) -> int:
        return int(self.class_mapping.get(class_id, {}).get("score", 0))

    def __call__(
        self,
        image: np.ndarray,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        nm: int = 32,
    ):
        model_input, ratio, (pad_w, pad_h) = self.preprocess(image)
        predictions = self.session.run(None, {self.input_name: model_input})
        return self.postprocess(
            predictions,
            image,
            ratio,
            pad_w,
            pad_h,
            conf_threshold,
            iou_threshold,
            nm,
        )

    def preprocess(self, image: np.ndarray):
        shape = image.shape[:2]
        new_shape = (self.model_height, self.model_width)
        scale = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = (int(round(shape[1] * scale)), int(round(shape[0] * scale)))
        pad_w = (new_shape[1] - new_unpad[0]) / 2
        pad_h = (new_shape[0] - new_unpad[1]) / 2
        resized = cv2.resize(image, new_unpad, interpolation=cv2.INTER_LINEAR)
        top, bottom = int(round(pad_h - 0.1)), int(round(pad_h + 0.1))
        left, right = int(round(pad_w - 0.1)), int(round(pad_w + 0.1))
        padded = cv2.copyMakeBorder(
            resized,
            top,
            bottom,
            left,
            right,
            cv2.BORDER_CONSTANT,
            value=(114, 114, 114),
        )
        tensor = np.ascontiguousarray(
            np.einsum("HWC->CHW", padded)[::-1], dtype=self.ndtype
        ) / 255.0
        return tensor[None], (scale, scale), (pad_w, pad_h)

    def postprocess(
        self,
        predictions,
        image: np.ndarray,
        ratio,
        pad_w: float,
        pad_h: float,
        conf_threshold: float,
        iou_threshold: float,
        nm: int,
    ):
        boxes_output, prototypes = predictions[0], predictions[1]
        candidates = np.einsum("bcn->bnc", boxes_output)
        candidates = candidates[
            np.amax(candidates[..., 4:-nm], axis=-1) > conf_threshold
        ]
        if len(candidates) == 0:
            return np.array([]), [], []

        candidates = np.c_[
            candidates[..., :4],
            np.amax(candidates[..., 4:-nm], axis=-1),
            np.argmax(candidates[..., 4:-nm], axis=-1),
            candidates[..., -nm:],
        ]
        keep = cv2.dnn.NMSBoxes(
            candidates[:, :4],
            candidates[:, 4],
            conf_threshold,
            iou_threshold,
        )
        if len(keep) == 0:
            return np.array([]), [], []
        candidates = candidates[np.asarray(keep).reshape(-1)]

        candidates[..., [0, 1]] -= candidates[..., [2, 3]] / 2
        candidates[..., [2, 3]] += candidates[..., [0, 1]]
        candidates[..., :4] -= [pad_w, pad_h, pad_w, pad_h]
        candidates[..., :4] /= min(ratio)
        candidates[:, [0, 2]] = candidates[:, [0, 2]].clip(0, image.shape[1])
        candidates[:, [1, 3]] = candidates[:, [1, 3]].clip(0, image.shape[0])

        masks = self.process_mask(
            prototypes[0],
            candidates[:, 6:],
            candidates[:, :4],
            image.shape,
        )
        segments = self.masks2segments(masks)
        return candidates[..., :6], segments, masks

    @staticmethod
    def masks2segments(masks: np.ndarray) -> List[np.ndarray]:
        segments = []
        for mask in masks.astype("uint8"):
            contours = cv2.findContours(
                mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_NONE,
            )[0]
            if contours:
                largest = contours[np.asarray([len(contour) for contour in contours]).argmax()]
                segments.append(largest.reshape(-1, 2).astype("float32"))
            else:
                segments.append(np.zeros((0, 2), dtype="float32"))
        return segments

    @staticmethod
    def crop_mask(masks: np.ndarray, boxes: np.ndarray) -> np.ndarray:
        _, height, width = masks.shape
        x1, y1, x2, y2 = np.split(boxes[:, :, None], 4, 1)
        rows = np.arange(width, dtype=x1.dtype)[None, None, :]
        columns = np.arange(height, dtype=x1.dtype)[None, :, None]
        return masks * (rows >= x1) * (rows < x2) * (columns >= y1) * (columns < y2)

    def process_mask(
        self,
        prototypes: np.ndarray,
        mask_coefficients: np.ndarray,
        boxes: np.ndarray,
        original_shape,
    ) -> np.ndarray:
        channels, mask_height, mask_width = prototypes.shape
        masks = (
            np.matmul(mask_coefficients, prototypes.reshape(channels, -1))
            .reshape(-1, mask_height, mask_width)
            .transpose(1, 2, 0)
        )
        masks = np.ascontiguousarray(masks)
        masks = self.scale_mask(masks, original_shape)
        masks = np.einsum("HWN -> NHW", masks)
        masks = self.crop_mask(masks, boxes)
        return np.greater(masks, 0.5)

    @staticmethod
    def scale_mask(masks: np.ndarray, original_shape, ratio_pad=None) -> np.ndarray:
        current_shape = masks.shape[:2]
        if ratio_pad is None:
            gain = min(
                current_shape[0] / original_shape[0],
                current_shape[1] / original_shape[1],
            )
            pad = (
                (current_shape[1] - original_shape[1] * gain) / 2,
                (current_shape[0] - original_shape[0] * gain) / 2,
            )
        else:
            pad = ratio_pad[1]
        top, left = int(round(pad[1] - 0.1)), int(round(pad[0] - 0.1))
        bottom = int(round(current_shape[0] - pad[1] + 0.1))
        right = int(round(current_shape[1] - pad[0] + 0.1))
        masks = masks[top:bottom, left:right]
        masks = cv2.resize(
            masks,
            (original_shape[1], original_shape[0]),
            interpolation=cv2.INTER_LINEAR,
        )
        if len(masks.shape) == 2:
            masks = masks[:, :, None]
        return masks

    def calculate_score(self, boxes: np.ndarray):
        total_score = 0.0
        score_details = {
            config["name"]: {"score": 0, "detected": False}
            for config in self.class_mapping.values()
        }
        detected_classes = set()
        for box in boxes:
            class_id = int(box[5])
            if class_id not in self.class_mapping or class_id in detected_classes:
                continue
            class_score = self.get_score_for_class(class_id)
            class_name = self.get_name_for_class(class_id)
            total_score += class_score
            score_details[class_name]["score"] = class_score
            score_details[class_name]["detected"] = True
            detected_classes.add(class_id)
        return float(total_score), score_details

    def draw_and_visualize(
        self,
        image: np.ndarray,
        boxes: np.ndarray,
        segments: List[np.ndarray],
        masks: np.ndarray,
    ) -> np.ndarray:
        rendered = image.copy()
        if len(boxes) > 0:
            mask_canvas = np.zeros_like(rendered)
            for index, mask in enumerate(masks):
                class_id = int(boxes[index][5])
                color = self.get_color_for_class(class_id)
                mask_3d = np.stack([mask.astype(np.uint8) * 255] * 3, axis=-1)
                mask_canvas[mask_3d[:, :, 0] == 255] = color
            rendered = cv2.addWeighted(rendered, 0.7, mask_canvas, 0.3, 0)

            for segment, detection in zip(segments, boxes):
                color = self.get_color_for_class(int(detection[5]))
                if len(segment) > 0:
                    cv2.polylines(rendered, [np.int32(segment)], True, color, 2)

            for detection in boxes:
                box, confidence, class_value = detection[:4], detection[4], detection[5]
                class_id = int(class_value)
                color = self.get_color_for_class(class_id)
                cv2.rectangle(
                    rendered,
                    (int(box[0]), int(box[1])),
                    (int(box[2]), int(box[3])),
                    color,
                    2,
                    cv2.LINE_AA,
                )
                label = "{} {:.2f}".format(
                    self.get_name_for_class(class_id), confidence
                )
                (text_width, text_height), _ = cv2.getTextSize(
                    label,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    2,
                )
                cv2.rectangle(
                    rendered,
                    (int(box[0]), int(box[1]) - text_height - 10),
                    (int(box[0]) + text_width, int(box[1])),
                    color,
                    -1,
                )
                cv2.putText(
                    rendered,
                    label,
                    (int(box[0]), int(box[1]) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
        return rendered

    def infer_image_bytes(
        self,
        image_bytes: bytes,
        conf_threshold: float,
        iou_threshold: float,
    ):
        image_buffer = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(image_buffer, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("无法读取图片，请确认图片格式正确")
        boxes, segments, masks = self(image, conf_threshold, iou_threshold)
        total_score, score_details = self.calculate_score(boxes)
        detections = []
        for box in boxes:
            x1, y1, x2, y2, confidence, class_value = box
            class_id = int(class_value)
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": self.get_name_for_class(class_id),
                    "confidence": float(confidence),
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                }
            )
        result_image = self.draw_and_visualize(image, boxes, segments, masks)
        success, encoded = cv2.imencode(".jpg", result_image)
        if not success:
            raise RuntimeError("无法生成结果图片")
        return encoded.tobytes(), detections, total_score, score_details
