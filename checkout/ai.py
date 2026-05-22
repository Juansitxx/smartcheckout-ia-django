import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import Lock

import numpy as np
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont


@dataclass
class DetectionResult:
    class_id: int
    class_name: str
    confidence: float
    bbox_xyxy: list[float]
    bbox_norm: list[float]

    def as_dict(self):
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox_xyxy": self.bbox_xyxy,
            "bbox_norm": self.bbox_norm,
        }


class SmartCheckoutDetector:
    def __init__(self):
        self.model = None
        self.model_path = Path(settings.SMART_MODEL_PATH)
        self.device = settings.SMART_DEVICE

    def load(self):
        if self.model is not None:
            return
        if not self.model_path.exists():
            raise FileNotFoundError(f"Modelo no encontrado: {self.model_path}")

        from ultralytics import YOLO

        self.model = YOLO(str(self.model_path))
        self.model.to(self.device)

    def predict_image(self, input_path: Path, output_path: Path) -> dict:
        self.load()
        started = time.time()

        image = self._open_image(input_path)
        frame = np.array(image)
        result = self.predict_frame(frame, started_at=started)
        annotated = image.copy()
        for detection in result["detections"]:
            self._draw_box(
                annotated,
                detection["bbox_xyxy"],
                f"{detection['class_name']} {detection['confidence']:.2f}",
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        annotated.save(output_path, format="JPEG")
        return result

    def predict_jpeg_bytes(self, image_bytes: bytes) -> dict:
        self.load()
        frame = np.array(self._open_image(BytesIO(image_bytes)))
        return self.predict_frame(frame)

    def predict_frame(self, frame, started_at: float | None = None) -> dict:
        self.load()
        started = started_at or time.time()

        results = self.model.predict(
            frame,
            imgsz=settings.SMART_IMAGE_SIZE,
            conf=settings.SMART_CONFIDENCE,
            iou=settings.SMART_IOU,
            max_det=settings.SMART_MAX_DETECTIONS,
            device=self.device,
            verbose=False,
        )

        detections = []
        result = results[0]
        names = result.names

        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = str(names[class_id]).strip()
            confidence = round(float(box.conf[0]), 4)
            bbox_xyxy = [round(float(v), 2) for v in box.xyxy[0].tolist()]
            bbox_norm = [round(float(v), 6) for v in box.xywhn[0].tolist()]

            detections.append(
                DetectionResult(
                    class_id=class_id,
                    class_name=class_name,
                    confidence=confidence,
                    bbox_xyxy=bbox_xyxy,
                    bbox_norm=bbox_norm,
                )
            )

        return {
            "detections": [item.as_dict() for item in detections],
            "inference_time_ms": round((time.time() - started) * 1000, 2),
            "frame_width": int(frame.shape[1]),
            "frame_height": int(frame.shape[0]),
        }

    @staticmethod
    def _open_image(source) -> Image.Image:
        try:
            with Image.open(source) as image:
                return image.convert("RGB")
        except OSError as exc:
            raise ValueError(f"No se pudo leer la imagen: {source}") from exc

    @staticmethod
    def _draw_box(image: Image.Image, bbox_xyxy, label):
        x1, y1, x2, y2 = [int(v) for v in bbox_xyxy]
        color = (50, 205, 50)
        drawer = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        drawer.rectangle((x1, y1, x2, y2), outline=color, width=2)

        label_y = max(0, y1 - 18)
        text_box = drawer.textbbox((x1, label_y), label, font=font)
        drawer.rectangle(
            (text_box[0] - 3, text_box[1] - 2, text_box[2] + 3, text_box[3] + 2),
            fill=(255, 255, 255),
        )
        drawer.text((x1, label_y), label, fill=color, font=font)


_detector = None
_detector_lock = Lock()


def get_detector() -> SmartCheckoutDetector:
    global _detector
    with _detector_lock:
        if _detector is None:
            _detector = SmartCheckoutDetector()
        return _detector
