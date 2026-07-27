# import numpy as np
# from students.models import Student
# from students.face_utils import face_app

# def find_matching_student(image_array, threshold=0.5):
#     """
#     Takes an image (as a numpy array, already decoded), detects the face,
#     generates its embedding, and compares it against all registered students.
#     Returns the matched Student object, or None if no match found.
#     """
#     faces = face_app.get(image_array)

#     if len(faces) == 0:
#         return None, "No face detected."

#     new_embedding = np.array(faces[0].embedding)

#     students = Student.objects.exclude(embedding__isnull=True)

#     best_match = None
#     best_similarity = -1

#     for student in students:
#         known_embedding = np.array(student.embedding)

#         similarity = np.dot(new_embedding, known_embedding) / (
#             np.linalg.norm(new_embedding) * np.linalg.norm(known_embedding)
#         )

#         if similarity > best_similarity:
#             best_similarity = similarity
#             best_match = student

#     if best_match and best_similarity > threshold:
#         return best_match, f"Matched with {best_similarity:.2%} similarity"

#     return None, "No matching student found."

import numpy as np
from students.models import Student
from students.face_utils import face_app

def detect_face(image_array):
    """
    Detects a face and returns both the InsightFace face object (with embedding)
    and its bounding box, or (None, None) if no face found.
    """
    faces = face_app.get(image_array)
    if len(faces) == 0:
        return None, None

    face = faces[0]
    bbox = face.bbox.astype(int)  # [x1, y1, x2, y2]
    return face, bbox

def find_matching_student(face, threshold=0.5):
    """
    Takes an already-detected InsightFace face object and compares
    its embedding against all registered students.
    """
    new_embedding = np.array(face.embedding)

    students = Student.objects.exclude(embedding__isnull=True)

    best_match = None
    best_similarity = -1

    for student in students:
        known_embedding = np.array(student.embedding)
        similarity = np.dot(new_embedding, known_embedding) / (
            np.linalg.norm(new_embedding) * np.linalg.norm(known_embedding)
        )
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = student

    if best_match and best_similarity > threshold:
        return best_match, f"Matched with {best_similarity:.2%} similarity"

    return None, "No matching student found."
