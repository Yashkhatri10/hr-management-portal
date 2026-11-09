import json
from io import BytesIO
from typing import Any

from fastapi import HTTPException


MODEL_NAME = "insightface-buffalo_l"
_face_app: Any = None


def _get_face_app() -> Any:
    global _face_app
    if _face_app is not None:
        return _face_app
    try:
        from insightface.app import FaceAnalysis
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Face verification is not configured. Install the InsightFace runtime and model assets.",
        ) from exc
    try:
        _face_app = FaceAnalysis(name=MODEL_NAME, providers=["CPUExecutionProvider"])
        _face_app.prepare(ctx_id=-1, det_size=(640, 640))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Face verification model could not be initialized") from exc
    return _face_app


def _read_image(image_bytes: bytes) -> Any:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="OpenCV is required for face verification") from exc
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=422, detail="The captured image is not a valid image")
    return image


def extract_embedding(image_bytes: bytes) -> list[float]:
    if not image_bytes or len(image_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="Face image must be present and no larger than 8 MB")
    faces = _get_face_app().get(_read_image(image_bytes))
    if len(faces) == 0:
        raise HTTPException(status_code=422, detail="No face detected in the image")
    if len(faces) > 1:
        raise HTTPException(status_code=422, detail="Capture exactly one face")
    face = faces[0]
    if float(getattr(face, "det_score", 0)) < 0.65:
        raise HTTPException(status_code=422, detail="The face image quality is too low")
    import numpy as np
    embedding = np.asarray(face.normed_embedding, dtype=np.float32)
    if embedding.ndim != 1 or embedding.size == 0:
        raise HTTPException(status_code=422, detail="Face embedding could not be generated")
    return embedding.tolist()


def serialize_embedding(embedding: list[float]) -> str:
    return json.dumps(embedding, separators=(",", ":"))


def verify_embedding(image_bytes: bytes, stored_embedding: str, threshold: float = 0.45) -> None:
    import numpy as np
    candidate = np.asarray(extract_embedding(image_bytes), dtype=np.float32)
    enrolled = np.asarray(json.loads(stored_embedding), dtype=np.float32)
    if candidate.shape != enrolled.shape:
        raise HTTPException(status_code=403, detail="Face template is incompatible with the active recognition model")
    similarity = float(np.dot(candidate, enrolled) / (np.linalg.norm(candidate) * np.linalg.norm(enrolled)))
    if not np.isfinite(similarity) or similarity < threshold:
        raise HTTPException(status_code=403, detail="Face verification failed")
