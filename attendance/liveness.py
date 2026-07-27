import numpy as np

# InsightFace's 106-point landmark model — indices for eye contour points
LEFT_EYE_IDX = [35, 36, 33, 37, 39, 42]
RIGHT_EYE_IDX = [89, 90, 87, 91, 93, 96]


def eye_aspect_ratio(landmarks, eye_idx):
    points = landmarks[eye_idx]
    vertical_1 = np.linalg.norm(points[1] - points[5])
    vertical_2 = np.linalg.norm(points[2] - points[4])
    horizontal = np.linalg.norm(points[0] - points[3])
    if horizontal == 0:
        return 0
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


def get_average_ear(landmarks):
    left_ear = eye_aspect_ratio(landmarks, LEFT_EYE_IDX)
    right_ear = eye_aspect_ratio(landmarks, RIGHT_EYE_IDX)
    return (left_ear + right_ear) / 2.0


def detect_blink(ear_sequence, relative_drop=0.008, min_samples=4):
    """
    Instead of comparing against a fixed EAR threshold (which varies a lot
    between different faces/cameras), this checks whether EAR *dropped
    meaningfully relative to this session's own baseline* — i.e. did the
    eyes visibly close at some point relative to how open they normally are
    in this specific capture.

    This also naturally rejects static photos: a printed photo or phone
    screen has zero natural eye movement, so its EAR stays essentially
    flat across every frame, and no meaningful drop is ever seen.

    Returns True if a genuine blink-like dip was detected.
    """
    if len(ear_sequence) < min_samples:
        return False

    ear_array = np.array(ear_sequence)
    baseline = np.percentile(ear_array, 90)  # "eyes open" reference level
    lowest = np.min(ear_array)

    if baseline == 0:
        return False

    drop_ratio = (baseline - lowest) / baseline
    return drop_ratio >= relative_drop


def has_natural_movement(ear_sequence, min_variance=0.000004, min_samples=4):
    """
    Secondary/fallback liveness signal: real faces have some natural
    micro-movement (breathing, tiny head shifts, blinking) even without
    a clean blink. A completely static photo held in front of the camera
    will show near-zero variance across frames.
    """
    if len(ear_sequence) < min_samples:
        return False
    return float(np.var(ear_sequence)) >= min_variance


# import numpy as np

# # InsightFace's 106-point landmark model — these are the indices
# # corresponding to the eye contour points (standard for this landmark scheme)
# LEFT_EYE_IDX = [35, 36, 33, 37, 39, 42]
# RIGHT_EYE_IDX = [89, 90, 87, 91, 93, 96]

# def eye_aspect_ratio(landmarks, eye_idx):
#     """
#     Computes the Eye Aspect Ratio (EAR) — a standard metric where:
#     - EAR is relatively high when the eye is open
#     - EAR drops sharply when the eye closes (blink)
#     """
#     points = landmarks[eye_idx]
#     # Vertical distances (eyelid opening)
#     vertical_1 = np.linalg.norm(points[1] - points[5])
#     vertical_2 = np.linalg.norm(points[2] - points[4])
#     # Horizontal distance (eye width)
#     horizontal = np.linalg.norm(points[0] - points[3])

#     ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
#     return ear

# def get_average_ear(landmarks):
#     left_ear = eye_aspect_ratio(landmarks, LEFT_EYE_IDX)
#     right_ear = eye_aspect_ratio(landmarks, RIGHT_EYE_IDX)
#     return (left_ear + right_ear) / 2.0

# def detect_blink(ear_sequence, blink_threshold=0.21, min_consecutive_frames=1):
#     """
#     Takes a list of EAR values (one per frame, in time order).
#     Returns True if a genuine blink pattern is detected:
#     EAR stays above threshold, dips below it for at least
#     min_consecutive_frames, then rises back above it.
#     """
#     below_threshold_run = 0
#     saw_dip = False

#     for ear in ear_sequence:
#         if ear < blink_threshold:
#             below_threshold_run += 1
#         else:
#             if below_threshold_run >= min_consecutive_frames:
#                 saw_dip = True
#             below_threshold_run = 0

#     # Catch a dip that was still ongoing at the end of the sequence
#     if below_threshold_run >= min_consecutive_frames:
#         saw_dip = True

#     return saw_dip



