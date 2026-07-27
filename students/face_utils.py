import insightface
import numpy as np
import cv2

face_app = insightface.app.FaceAnalysis(name='buffalo_l')
# face_app.prepare(ctx_id=0, det_size=(640, 640))
face_app.prepare(ctx_id=0, det_size=(320, 320))

def get_face_embedding(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return None

    faces = face_app.get(image)

    if len(faces) == 0:
        return None

    embedding = faces[0].embedding
    return embedding.tolist()


def get_face_and_landmarks(image_array):
    """
    Detects a face and returns (face_object, landmarks, bbox) or (None, None, None).
    landmarks is a numpy array of 106 (x, y) points.
    """
    faces = face_app.get(image_array)
    if len(faces) == 0:
        return None, None, None

    face = faces[0]
    landmarks = face.landmark_2d_106
    bbox = face.bbox.astype(int)
    return face, landmarks, bbox

def detect_all_faces(image_array):
    """
    Detects every face in the frame and returns a list of
    (embedding, bbox) tuples for each one.
    """
    faces = face_app.get(image_array)
    results = []
    for face in faces:
        bbox = face.bbox.astype(int).tolist()  # [x1, y1, x2, y2]
        results.append({'embedding': face.embedding, 'bbox': bbox})
    return results