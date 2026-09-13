import numpy as np
from PIL import Image
from io import BytesIO
import cv2
import os

try:
    from keras_facenet import FaceNet
    embedder = FaceNet()
except Exception:
    embedder = None

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def _extract_cv_face_features(image_array: np.ndarray) -> np.ndarray:
    """Extract discriminative facial feature embedding using HSV and spatial grid descriptors."""
    bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR) if len(image_array.shape) == 3 else image_array
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
    if len(faces) == 0:
        h, w = gray.shape[:2]
        crop = bgr[int(h * 0.1):int(h * 0.9), int(w * 0.1):int(w * 0.9)]
        crop_gray = gray[int(h * 0.1):int(h * 0.9), int(w * 0.1):int(w * 0.9)]
    else:
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        x, y, w, h = faces[0]
        crop = bgr[y:y + h, x:x + w]
        crop_gray = gray[y:y + h, x:x + w]

    resized = cv2.resize(crop, (128, 128))
    resized_gray = cv2.resize(crop_gray, (128, 128))

    # HSV 2D color histogram (Hue & Saturation)
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    hsv_hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256]).flatten()

    # Spatial 4x4 grid histograms
    grid = []
    for r in range(4):
        for c in range(4):
            cell = resized_gray[r*32:(r+1)*32, c*32:(c+1)*32]
            grid.append(cv2.calcHist([cell], [0], None, [16], [0, 256]).flatten())

    vec = np.concatenate([hsv_hist] + grid)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return np.asarray(vec, dtype=np.float32)


def generate_embedding(image_data):
    """
    Generate a face embedding from image bytes or file path.

    Args:
        image_data: Raw image bytes or string path to image.

    Returns:
        NumPy array containing the face embedding.

    Raises:
        ValueError: If no face is detected or image cannot be read.
    """
    try:
        if isinstance(image_data, str):
            if not os.path.exists(image_data):
                raise ValueError(f"Image not found at {image_data}")
            with open(image_data, "rb") as f:
                image_data = f.read()

        image = Image.open(BytesIO(image_data)).convert("RGB")
        image_array = np.asarray(image)

        if embedder is not None:
            embeddings = embedder.extract(image_array, threshold=0.70)
            if not embeddings:
                raise ValueError("No face detected in image.")
            embedding = embeddings[0]["embedding"]
            return np.asarray(embedding, dtype=np.float32)
        else:
            return _extract_cv_face_features(image_array)

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Unable to process image: {str(e)}")