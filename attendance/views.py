# import cv2
# import numpy as np
# from rest_framework.decorators import api_view, parser_classes
# from rest_framework.parsers import MultiPartParser
# from rest_framework.response import Response
# from rest_framework import status
# from drf_yasg.utils import swagger_auto_schema
# from drf_yasg import openapi
# from django.utils import timezone
# from .models import Attendance
# from .serializers import AttendanceSerializer
# from .face_match import detect_face, find_matching_student
# from .antispoof_check import check_real_or_fake
# from .liveness import get_average_ear, detect_blink
# from students.face_utils import get_face_and_landmarks, detect_all_faces
# from students.models import Student


# def is_teacher(user):
#     return user.is_authenticated and (user.groups.filter(name='Teacher').exists() or user.is_superuser)


# @swagger_auto_schema(
#     method='post',
#     operation_description="Mark attendance using face recognition with anti-spoof protection.",
#     manual_parameters=[
#         openapi.Parameter('photo', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
#     ],
#     responses={200: 'Attendance marked', 400: 'Spoof detected / no face / no match / already marked'}
# )
# @api_view(['POST'])
# @parser_classes([MultiPartParser])
# def mark_attendance(request):
#     photo = request.FILES.get('photo')

#     if not photo:
#         return Response({'error': 'Photo is required.'}, status=status.HTTP_400_BAD_REQUEST)

#     file_bytes = np.frombuffer(photo.read(), np.uint8)
#     image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

#     if image is None:
#         return Response({'error': 'Invalid image file.'}, status=status.HTTP_400_BAD_REQUEST)

#     # Step 1: Detect the face
#     face, bbox = detect_face(image)
#     if face is None:
#         return Response({'error': 'No face detected.'}, status=status.HTTP_400_BAD_REQUEST)

#     # Step 2: Anti-spoof check
#     label, confidence = check_real_or_fake(image, bbox)
#     if label == "fake":
#         return Response({
#             'error': 'Spoof detected. Attendance rejected.',
#             'confidence': confidence
#         }, status=status.HTTP_400_BAD_REQUEST)

#     # Step 3: Face recognition (only runs if real)
#     student, message = find_matching_student(face)
#     if not student:
#         return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

#     # Step 4: Check duplicate attendance
#     today = timezone.now().date()
#     existing = Attendance.objects.filter(student=student, date=today).first()
#     if existing:
#         return Response({'error': f'{student.name} already marked present today.'}, status=status.HTTP_400_BAD_REQUEST)

#     # Step 5: Mark attendance
#     record = Attendance.objects.create(student=student)
#     serializer = AttendanceSerializer(record)

#     return Response({
#         'message': f'Attendance marked for {student.name}',
#         'match_info': message,
#         'spoof_check': f'{label} ({confidence:.2%} confidence)',
#         'record': serializer.data
#     }, status=status.HTTP_200_OK)


# @swagger_auto_schema(
#     method='post',
#     operation_description="Mark attendance using LIVE face detection: requires multiple frames captured over ~3 seconds, checks for a genuine eye blink, runs anti-spoof detection, then matches the face.",
#     manual_parameters=[
#         openapi.Parameter('photos', openapi.IN_FORM, type=openapi.TYPE_ARRAY,
#                            items=openapi.Items(type=openapi.TYPE_FILE),
#                            required=True, description="Multiple frames captured over ~3 seconds"),
#     ],
#     responses={200: 'Attendance marked', 400: 'No blink detected / spoof / no match / already marked'}
# )
# @api_view(['POST'])
# @parser_classes([MultiPartParser])
# def mark_attendance_live(request):
#     if not request.user.is_authenticated:
#         return Response({'error': 'Please log in.'}, status=status.HTTP_401_UNAUTHORIZED)

#     photos = request.FILES.getlist('photos')

#     if len(photos) < 5:
#         return Response({'error': 'At least 5 frames are required for liveness verification.'}, status=status.HTTP_400_BAD_REQUEST)

#     ear_sequence = []
#     real_votes = 0
#     fake_votes = 0
#     last_face = None
#     last_bbox = None

#     for photo in photos:
#         file_bytes = np.frombuffer(photo.read(), np.uint8)
#         image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
#         if image is None:
#             continue

#         face, landmarks, bbox = get_face_and_landmarks(image)
#         if face is None:
#             continue

#         ear = get_average_ear(landmarks)
#         ear_sequence.append(ear)

#         label, _ = check_real_or_fake(image, bbox)
#         if label == "real":
#             real_votes += 1
#         else:
#             fake_votes += 1

#         last_face = face
#         last_bbox = bbox

#     if last_face is None:
#         return Response({'error': 'No face detected in any frame.'}, status=status.HTTP_400_BAD_REQUEST)

#     # Step 1: Liveness check — must see a genuine blink pattern
#     blinked = detect_blink(ear_sequence)
#     if not blinked:
#         return Response({'error': 'No blink detected. Please look at the camera naturally for a few seconds.'}, status=status.HTTP_400_BAD_REQUEST)

#     # Step 2: Anti-spoof majority vote across frames
#     if fake_votes >= real_votes:
#         return Response({'error': 'Spoof detected across frames. Attendance rejected.'}, status=status.HTTP_400_BAD_REQUEST)

#     # Step 3: Face recognition using the last good frame
#     student, message = find_matching_student(last_face)
#     if not student:
#         return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

#     # Step 4: Duplicate check
#     today = timezone.now().date()
#     existing = Attendance.objects.filter(student=student, date=today).first()
#     if existing:
#         return Response({'error': f'{student.name} already marked present today.'}, status=status.HTTP_400_BAD_REQUEST)

#     # Step 5: Mark attendance
#     record = Attendance.objects.create(student=student)
#     serializer = AttendanceSerializer(record)

#     return Response({
#         'message': f'Attendance marked for {student.name}',
#         'match_info': message,
#         'liveness': f'Blink detected across {len(ear_sequence)} frames',
#         'spoof_check': f'{real_votes} real votes / {fake_votes} fake votes',
#         'record': serializer.data
#     }, status=status.HTTP_200_OK)


# @swagger_auto_schema(method='get', operation_description="Get all attendance records.")
# @api_view(['GET'])
# def list_attendance(request):
#     records = Attendance.objects.all().order_by('-date', '-time')
#     serializer = AttendanceSerializer(records, many=True)
#     return Response(serializer.data)


# @swagger_auto_schema(method='delete', operation_description="Delete an attendance record.")
# @api_view(['DELETE'])
# def delete_attendance(request, record_id):
#     try:
#         record = Attendance.objects.get(id=record_id)
#     except Attendance.DoesNotExist:
#         return Response({'error': 'Record not found.'}, status=status.HTTP_404_NOT_FOUND)

#     record.delete()
#     return Response({'message': f'Attendance record {record_id} deleted.'}, status=status.HTTP_200_OK)


# @swagger_auto_schema(
#     method='post',
#     operation_description="Detects all faces in a frame and returns bounding boxes + matched student names (for live overlay display). Does NOT mark attendance.",
#     manual_parameters=[
#         openapi.Parameter('photo', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
#     ],
# )
# @api_view(['POST'])
# @parser_classes([MultiPartParser])
# def detect_faces_live(request):
#     if not request.user.is_authenticated:
#         return Response({'error': 'Please log in.'}, status=status.HTTP_401_UNAUTHORIZED)

#     photo = request.FILES.get('photo')
#     if not photo:
#         return Response({'error': 'Photo is required.'}, status=status.HTTP_400_BAD_REQUEST)

#     file_bytes = np.frombuffer(photo.read(), np.uint8)
#     image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
#     if image is None:
#         return Response({'error': 'Invalid image.'}, status=status.HTTP_400_BAD_REQUEST)

#     faces = detect_all_faces(image)
#     results = []

#     students = Student.objects.exclude(embedding__isnull=True)

#     for face_data in faces:
#         embedding = np.array(face_data['embedding'])
#         bbox = face_data['bbox']

#         best_match = None
#         best_similarity = -1

#         for student in students:
#             known_embedding = np.array(student.embedding)
#             similarity = np.dot(embedding, known_embedding) / (
#                 np.linalg.norm(embedding) * np.linalg.norm(known_embedding)
#             )
#             if similarity > best_similarity:
#                 best_similarity = similarity
#                 best_match = student

#         if best_match and best_similarity > 0.5:
#             results.append({
#                 'bbox': bbox,
#                 'name': best_match.name,
#                 'registered': True
#             })
#         else:
#             results.append({
#                 'bbox': bbox,
#                 'name': None,
#                 'registered': False
#             })

#     return Response({'faces': results})



# # import cv2
# # import numpy as np
# # import openpyxl
# # from openpyxl.styles import Font
# # from django.http import HttpResponse
# # from rest_framework.decorators import api_view, parser_classes
# # from rest_framework.parsers import MultiPartParser
# # from rest_framework.response import Response
# # from rest_framework import status
# # from drf_yasg.utils import swagger_auto_schema
# # from drf_yasg import openapi
# # from django.utils import timezone
# # from .models import Attendance
# # from .serializers import AttendanceSerializer
# # from .face_match import detect_face, find_matching_student
# # from .antispoof_check import check_real_or_fake
# # from .liveness import get_average_ear, detect_blink
# # from students.face_utils import get_face_and_landmarks, detect_all_faces
# # from students.models import Student


# # def is_teacher(user):
# #     return user.is_authenticated and (user.groups.filter(name='Teacher').exists() or user.is_superuser)


# # @swagger_auto_schema(
# #     method='post',
# #     operation_description="Mark attendance using face recognition with anti-spoof protection.",
# #     manual_parameters=[
# #         openapi.Parameter('photo', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
# #     ],
# #     responses={200: 'Attendance marked', 400: 'Spoof detected / no face / no match / already marked'}
# # )
# # @api_view(['POST'])
# # @parser_classes([MultiPartParser])
# # def mark_attendance(request):
# #     photo = request.FILES.get('photo')

# #     if not photo:
# #         return Response({'error': 'Photo is required.'}, status=status.HTTP_400_BAD_REQUEST)

# #     file_bytes = np.frombuffer(photo.read(), np.uint8)
# #     image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

# #     if image is None:
# #         return Response({'error': 'Invalid image file.'}, status=status.HTTP_400_BAD_REQUEST)

# #     face, bbox = detect_face(image)
# #     if face is None:
# #         return Response({'error': 'No face detected.'}, status=status.HTTP_400_BAD_REQUEST)

# #     label, confidence = check_real_or_fake(image, bbox)
# #     if label == "fake":
# #         return Response({
# #             'error': 'Spoof detected. Attendance rejected.',
# #             'confidence': confidence
# #         }, status=status.HTTP_400_BAD_REQUEST)

# #     student, message = find_matching_student(face)
# #     if not student:
# #         return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

# #     today = timezone.now().date()
# #     existing = Attendance.objects.filter(student=student, date=today).first()
# #     if existing:
# #         return Response({'error': f'{student.name} already marked present today.'}, status=status.HTTP_400_BAD_REQUEST)

# #     record = Attendance.objects.create(student=student)
# #     serializer = AttendanceSerializer(record)

# #     return Response({
# #         'message': f'Attendance marked for {student.name}',
# #         'match_info': message,
# #         'spoof_check': f'{label} ({confidence:.2%} confidence)',
# #         'record': serializer.data
# #     }, status=status.HTTP_200_OK)


# # @swagger_auto_schema(
# #     method='post',
# #     operation_description="Mark attendance using LIVE face detection: requires multiple frames captured over ~3 seconds, checks for a genuine eye blink, runs anti-spoof detection, then matches the face.",
# #     manual_parameters=[
# #         openapi.Parameter('photos', openapi.IN_FORM, type=openapi.TYPE_ARRAY,
# #                            items=openapi.Items(type=openapi.TYPE_FILE),
# #                            required=True, description="Multiple frames captured over ~3 seconds"),
# #     ],
# #     responses={200: 'Attendance marked', 400: 'No blink detected / spoof / no match / already marked'}
# # )
# # @api_view(['POST'])
# # @parser_classes([MultiPartParser])
# # def mark_attendance_live(request):
# #     if not request.user.is_authenticated:
# #         return Response({'error': 'Please log in.'}, status=status.HTTP_401_UNAUTHORIZED)

# #     photos = request.FILES.getlist('photos')

# #     if len(photos) < 5:
# #         return Response({'error': 'At least 5 frames are required for liveness verification.'}, status=status.HTTP_400_BAD_REQUEST)

# #     ear_sequence = []
# #     real_votes = 0
# #     fake_votes = 0
# #     last_face = None
# #     last_bbox = None

# #     for photo in photos:
# #         file_bytes = np.frombuffer(photo.read(), np.uint8)
# #         image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
# #         if image is None:
# #             continue

# #         face, landmarks, bbox = get_face_and_landmarks(image)
# #         if face is None:
# #             continue

# #         ear = get_average_ear(landmarks)
# #         ear_sequence.append(ear)

# #         label, _ = check_real_or_fake(image, bbox)
# #         if label == "real":
# #             real_votes += 1
# #         else:
# #             fake_votes += 1

# #         last_face = face
# #         last_bbox = bbox

# #     if last_face is None:
# #         return Response({'error': 'No face detected in any frame.'}, status=status.HTTP_400_BAD_REQUEST)

# #     blinked = detect_blink(ear_sequence)
# #     if not blinked:
# #         return Response({'error': 'No blink detected. Please look at the camera naturally for a few seconds.'}, status=status.HTTP_400_BAD_REQUEST)

# #     if fake_votes >= real_votes:
# #         return Response({'error': 'Spoof detected across frames. Attendance rejected.'}, status=status.HTTP_400_BAD_REQUEST)

# #     student, message = find_matching_student(last_face)
# #     if not student:
# #         return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

# #     today = timezone.now().date()
# #     existing = Attendance.objects.filter(student=student, date=today).first()
# #     if existing:
# #         return Response({'error': f'{student.name} already marked present today.'}, status=status.HTTP_400_BAD_REQUEST)

# #     record = Attendance.objects.create(student=student)
# #     serializer = AttendanceSerializer(record)

# #     return Response({
# #         'message': f'Attendance marked for {student.name}',
# #         'match_info': message,
# #         'liveness': f'Blink detected across {len(ear_sequence)} frames',
# #         'spoof_check': f'{real_votes} real votes / {fake_votes} fake votes',
# #         'record': serializer.data
# #     }, status=status.HTTP_200_OK)


# # @swagger_auto_schema(method='get', operation_description="Get all attendance records.")
# # @api_view(['GET'])
# # def list_attendance(request):
# #     records = Attendance.objects.all().order_by('-date', '-time')
# #     serializer = AttendanceSerializer(records, many=True)
# #     return Response(serializer.data)


# # @swagger_auto_schema(method='delete', operation_description="Delete an attendance record.")
# # @api_view(['DELETE'])
# # def delete_attendance(request, record_id):
# #     try:
# #         record = Attendance.objects.get(id=record_id)
# #     except Attendance.DoesNotExist:
# #         return Response({'error': 'Record not found.'}, status=status.HTTP_404_NOT_FOUND)

# #     record.delete()
# #     return Response({'message': f'Attendance record {record_id} deleted.'}, status=status.HTTP_200_OK)


# # @swagger_auto_schema(method='get', operation_description="Download all attendance records as an Excel (.xlsx) file.")
# # @api_view(['GET'])
# # def export_attendance_excel(request):
# #     records = Attendance.objects.all().order_by('-date', '-time')

# #     wb = openpyxl.Workbook()
# #     ws = wb.active
# #     ws.title = "Attendance"

# #     headers = ['Student ID', 'Name', 'Date', 'Time']
# #     ws.append(headers)
# #     for cell in ws[1]:
# #         cell.font = Font(bold=True)

# #     for record in records:
# #         ws.append([
# #             record.student.student_id,
# #             record.student.name,
# #             record.date.strftime('%Y-%m-%d'),
# #             record.time.strftime('%H:%M:%S'),
# #         ])

# #     for column_cells in ws.columns:
# #         max_length = max(len(str(cell.value)) for cell in column_cells)
# #         ws.column_dimensions[column_cells[0].column_letter].width = max_length + 4

# #     response = HttpResponse(
# #         content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
# #     )
# #     response['Content-Disposition'] = 'attachment; filename=attendance_report.xlsx'
# #     wb.save(response)
# #     return response


# # @swagger_auto_schema(
# #     method='post',
# #     operation_description="Detects all faces in a frame and returns bounding boxes + matched student names (for live overlay display). Does NOT mark attendance.",
# #     manual_parameters=[
# #         openapi.Parameter('photo', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
# #     ],
# # )
# # @api_view(['POST'])
# # @parser_classes([MultiPartParser])
# # def detect_faces_live(request):
# #     if not request.user.is_authenticated:
# #         return Response({'error': 'Please log in.'}, status=status.HTTP_401_UNAUTHORIZED)

# #     photo = request.FILES.get('photo')
# #     if not photo:
# #         return Response({'error': 'Photo is required.'}, status=status.HTTP_400_BAD_REQUEST)

# #     file_bytes = np.frombuffer(photo.read(), np.uint8)
# #     image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
# #     if image is None:
# #         return Response({'error': 'Invalid image.'}, status=status.HTTP_400_BAD_REQUEST)

# #     faces = detect_all_faces(image)
# #     results = []

# #     students = Student.objects.exclude(embedding__isnull=True)

# #     for face_data in faces:
# #         embedding = np.array(face_data['embedding'])
# #         bbox = face_data['bbox']

# #         best_match = None
# #         best_similarity = -1

# #         for student in students:
# #             known_embedding = np.array(student.embedding)
# #             similarity = np.dot(embedding, known_embedding) / (
# #                 np.linalg.norm(embedding) * np.linalg.norm(known_embedding)
# #             )
# #             if similarity > best_similarity:
# #                 best_similarity = similarity
# #                 best_match = student

# #         if best_match and best_similarity > 0.5:
# #             results.append({
# #                 'bbox': bbox,
# #                 'name': best_match.name,
# #                 'registered': True
# #             })
# #         else:
# #             results.append({
# #                 'bbox': bbox,
# #                 'name': None,
# #                 'registered': False
# #             })

# #     return Response({'faces': results})
# # import cv2
# # import numpy as np
# # from rest_framework.decorators import api_view, parser_classes
# # from rest_framework.parsers import MultiPartParser
# # from rest_framework.response import Response
# # from rest_framework import status
# # from drf_yasg.utils import swagger_auto_schema
# # from drf_yasg import openapi
# # from django.utils import timezone
# # from .models import Attendance
# # from .serializers import AttendanceSerializer
# # from .face_match import detect_face, find_matching_student
# # from .antispoof_check import check_real_or_fake
# # from .liveness import get_average_ear, detect_blink
# # from students.face_utils import get_face_and_landmarks, detect_all_faces
# # from students.models import Student


# # def is_teacher(user):
# #     return user.is_authenticated and (user.groups.filter(name='Teacher').exists() or user.is_superuser)


# # @swagger_auto_schema(
# #     method='post',
# #     operation_description="Mark attendance using face recognition with anti-spoof protection.",
# #     manual_parameters=[
# #         openapi.Parameter('photo', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
# #     ],
# #     responses={200: 'Attendance marked', 400: 'Spoof detected / no face / no match / already marked'}
# # )
# # @api_view(['POST'])
# # @parser_classes([MultiPartParser])
# # def mark_attendance(request):
# #     photo = request.FILES.get('photo')

# #     if not photo:
# #         return Response({'error': 'Photo is required.'}, status=status.HTTP_400_BAD_REQUEST)

# #     file_bytes = np.frombuffer(photo.read(), np.uint8)
# #     image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

# #     if image is None:
# #         return Response({'error': 'Invalid image file.'}, status=status.HTTP_400_BAD_REQUEST)

# #     # Step 1: Detect the face
# #     face, bbox = detect_face(image)
# #     if face is None:
# #         return Response({'error': 'No face detected.'}, status=status.HTTP_400_BAD_REQUEST)

# #     # Step 2: Anti-spoof check
# #     label, confidence = check_real_or_fake(image, bbox)
# #     if label == "fake":
# #         return Response({
# #             'error': 'Spoof detected. Attendance rejected.',
# #             'confidence': confidence
# #         }, status=status.HTTP_400_BAD_REQUEST)

# #     # Step 3: Face recognition (only runs if real)
# #     student, message = find_matching_student(face)
# #     if not student:
# #         return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

# #     # Step 4: Check duplicate attendance
# #     today = timezone.now().date()
# #     existing = Attendance.objects.filter(student=student, date=today).first()
# #     if existing:
# #         return Response({'error': f'{student.name} already marked present today.'}, status=status.HTTP_400_BAD_REQUEST)

# #     # Step 5: Mark attendance
# #     record = Attendance.objects.create(student=student)
# #     serializer = AttendanceSerializer(record)

# #     return Response({
# #         'message': f'Attendance marked for {student.name}',
# #         'match_info': message,
# #         'spoof_check': f'{label} ({confidence:.2%} confidence)',
# #         'record': serializer.data
# #     }, status=status.HTTP_200_OK)


# # @swagger_auto_schema(
# #     method='post',
# #     operation_description="Mark attendance using LIVE face detection: requires multiple frames captured over ~3 seconds, checks for a genuine eye blink, runs anti-spoof detection, then matches the face.",
# #     manual_parameters=[
# #         openapi.Parameter('photos', openapi.IN_FORM, type=openapi.TYPE_ARRAY,
# #                            items=openapi.Items(type=openapi.TYPE_FILE),
# #                            required=True, description="Multiple frames captured over ~3 seconds"),
# #     ],
# #     responses={200: 'Attendance marked', 400: 'No blink detected / spoof / no match / already marked'}
# # )
# # @api_view(['POST'])
# # @parser_classes([MultiPartParser])
# # def mark_attendance_live(request):
# #     if not request.user.is_authenticated:
# #         return Response({'error': 'Please log in.'}, status=status.HTTP_401_UNAUTHORIZED)

# #     photos = request.FILES.getlist('photos')

# #     if len(photos) < 5:
# #         return Response({'error': 'At least 5 frames are required for liveness verification.'}, status=status.HTTP_400_BAD_REQUEST)

# #     ear_sequence = []
# #     real_votes = 0
# #     fake_votes = 0
# #     last_face = None
# #     last_bbox = None

# #     for photo in photos:
# #         file_bytes = np.frombuffer(photo.read(), np.uint8)
# #         image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
# #         if image is None:
# #             continue

# #         face, landmarks, bbox = get_face_and_landmarks(image)
# #         if face is None:
# #             continue

# #         ear = get_average_ear(landmarks)
# #         ear_sequence.append(ear)

# #         label, _ = check_real_or_fake(image, bbox)
# #         if label == "real":
# #             real_votes += 1
# #         else:
# #             fake_votes += 1

# #         last_face = face
# #         last_bbox = bbox

# #     if last_face is None:
# #         return Response({'error': 'No face detected in any frame.'}, status=status.HTTP_400_BAD_REQUEST)

# #     # Step 1: Liveness check — must see a genuine blink pattern
# #     blinked = detect_blink(ear_sequence)
# #     if not blinked:
# #         return Response({'error': 'No blink detected. Please look at the camera naturally for a few seconds.'}, status=status.HTTP_400_BAD_REQUEST)

# #     # Step 2: Anti-spoof majority vote across frames
# #     if fake_votes >= real_votes:
# #         return Response({'error': 'Spoof detected across frames. Attendance rejected.'}, status=status.HTTP_400_BAD_REQUEST)

# #     # Step 3: Face recognition using the last good frame
# #     student, message = find_matching_student(last_face)
# #     if not student:
# #         return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

# #     # Step 4: Duplicate check
# #     today = timezone.now().date()
# #     existing = Attendance.objects.filter(student=student, date=today).first()
# #     if existing:
# #         return Response({'error': f'{student.name} already marked present today.'}, status=status.HTTP_400_BAD_REQUEST)

# #     # Step 5: Mark attendance
# #     record = Attendance.objects.create(student=student)
# #     serializer = AttendanceSerializer(record)

# #     return Response({
# #         'message': f'Attendance marked for {student.name}',
# #         'match_info': message,
# #         'liveness': f'Blink detected across {len(ear_sequence)} frames',
# #         'spoof_check': f'{real_votes} real votes / {fake_votes} fake votes',
# #         'record': serializer.data
# #     }, status=status.HTTP_200_OK)


# # @swagger_auto_schema(method='get', operation_description="Get all attendance records.")
# # @api_view(['GET'])
# # def list_attendance(request):
# #     records = Attendance.objects.all().order_by('-date', '-time')
# #     serializer = AttendanceSerializer(records, many=True)
# #     return Response(serializer.data)


# # @swagger_auto_schema(method='delete', operation_description="Delete an attendance record.")
# # @api_view(['DELETE'])
# # def delete_attendance(request, record_id):
# #     try:
# #         record = Attendance.objects.get(id=record_id)
# #     except Attendance.DoesNotExist:
# #         return Response({'error': 'Record not found.'}, status=status.HTTP_404_NOT_FOUND)

# #     record.delete()
# #     return Response({'message': f'Attendance record {record_id} deleted.'}, status=status.HTTP_200_OK)


# # import openpyxl
# # from openpyxl.styles import Font
# # from django.http import HttpResponse


# # @swagger_auto_schema(method='get', operation_description="Download all attendance records as an Excel (.xlsx) file.")
# # @api_view(['GET'])
# # def export_attendance_excel(request):
# #     records = Attendance.objects.all().order_by('-date', '-time')

# #     wb = openpyxl.Workbook()
# #     ws = wb.active
# #     ws.title = "Attendance"

# #     headers = ['Student ID', 'Name', 'Date', 'Time']
# #     ws.append(headers)
# #     for cell in ws[1]:
# #         cell.font = Font(bold=True)

# #     for record in records:
# #         ws.append([
# #             record.student.student_id,
# #             record.student.name,
# #             record.date.strftime('%Y-%m-%d'),
# #             record.time.strftime('%H:%M:%S'),
# #         ])

# #     for column_cells in ws.columns:
# #         max_length = max(len(str(cell.value)) for cell in column_cells)
# #         ws.column_dimensions[column_cells[0].column_letter].width = max_length + 4

# #     response = HttpResponse(
# #         content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
# #     )
# #     response['Content-Disposition'] = 'attachment; filename=attendance_report.xlsx'
# #     wb.save(response)

# # @api_view(['POST'])
# # @parser_classes([MultiPartParser])
# # def detect_faces_live(request):
# #     if not request.user.is_authenticated:
# #         return Response({'error': 'Please log in.'}, status=status.HTTP_401_UNAUTHORIZED)

# #     photo = request.FILES.get('photo')
# #     if not photo:
# #         return Response({'error': 'Photo is required.'}, status=status.HTTP_400_BAD_REQUEST)

# #     file_bytes = np.frombuffer(photo.read(), np.uint8)
# #     image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
# #     if image is None:
# #         return Response({'error': 'Invalid image.'}, status=status.HTTP_400_BAD_REQUEST)

# #     faces = detect_all_faces(image)
# #     results = []

# #     students = Student.objects.exclude(embedding__isnull=True)

# #     for face_data in faces:
# #         embedding = np.array(face_data['embedding'])
# #         bbox = face_data['bbox']

# #         best_match = None
# #         best_similarity = -1

# #         for student in students:
# #             known_embedding = np.array(student.embedding)
# #             similarity = np.dot(embedding, known_embedding) / (
# #                 np.linalg.norm(embedding) * np.linalg.norm(known_embedding)
# #             )
# #             if similarity > best_similarity:
# #                 best_similarity = similarity
# #                 best_match = student

# #         if best_match and best_similarity > 0.5:
# #             results.append({
# #                 'bbox': bbox,
# #                 'name': best_match.name,
# #                 'registered': True
# #             })
# #         else:
# #             results.append({
# #                 'bbox': bbox,
# #                 'name': None,
# #                 'registered': False
# #             })

# #     return Response({'faces': results})


import cv2
import numpy as np
from datetime import timedelta
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from .models import Attendance
from .serializers import AttendanceSerializer
from .face_match import detect_face, find_matching_student
from .antispoof_check import check_real_or_fake
from .liveness import get_average_ear, detect_blink, has_natural_movement
from students.face_utils import get_face_and_landmarks, detect_all_faces
from students.models import Student

ATTENDANCE_WINDOW = timedelta(hours=24)

def is_teacher(user):
    return user.is_authenticated and (user.groups.filter(name='Teacher').exists() or user.is_superuser)

def get_recent_attendance(student, teacher):
    return Attendance.objects.filter(
        student=student,
        teacher=teacher,
        taken_at__gte=timezone.now() - ATTENDANCE_WINDOW
    ).order_by('-taken_at').first()

def duplicate_attendance_response(student, existing):
    next_allowed_at = timezone.localtime(existing.taken_at + ATTENDANCE_WINDOW)
    return Response({
        'error': (
            f'{student.name} was already marked by this teacher within the last 24 hours. '
            f'Next attendance can be taken after {next_allowed_at.strftime("%Y-%m-%d %H:%M:%S %Z")}.'
        ),
        'record': AttendanceSerializer(existing).data,
        'next_allowed_at': next_allowed_at.isoformat(),
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='post',
    operation_description="Mark attendance using face recognition with anti-spoof protection.",
    manual_parameters=[
        openapi.Parameter('photo', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
    ],
    responses={200: 'Attendance marked', 400: 'Spoof detected / no face / no match / already marked'}
)
@api_view(['POST'])
@parser_classes([MultiPartParser])
def mark_attendance(request):
    if not is_teacher(request.user):
        return Response({'error': 'Only teachers can mark attendance.'}, status=status.HTTP_403_FORBIDDEN)

    photo = request.FILES.get('photo')

    if not photo:
        return Response({'error': 'Photo is required.'}, status=status.HTTP_400_BAD_REQUEST)

    file_bytes = np.frombuffer(photo.read(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if image is None:
        return Response({'error': 'Invalid image file.'}, status=status.HTTP_400_BAD_REQUEST)

    face, bbox = detect_face(image)
    if face is None:
        return Response({'error': 'No face detected.'}, status=status.HTTP_400_BAD_REQUEST)

    label, confidence = check_real_or_fake(image, bbox)
    if label == "fake":
        return Response({
            'error': 'Spoof detected. Attendance rejected.',
            'confidence': confidence
        }, status=status.HTTP_400_BAD_REQUEST)

    student, message = find_matching_student(face)
    if not student:
        return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

    existing = get_recent_attendance(student, request.user)
    if existing:
        return duplicate_attendance_response(student, existing)

    record = Attendance.objects.create(student=student, teacher=request.user, taken_at=timezone.now())
    serializer = AttendanceSerializer(record)

    return Response({
        'message': f'Attendance marked for {student.name}',
        'match_info': message,
        'spoof_check': f'{label} ({confidence:.2%} confidence)',
        'record': serializer.data
    }, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='post',
    operation_description="Mark attendance using LIVE face detection: requires multiple frames captured over ~3 seconds, checks for a genuine eye blink, runs anti-spoof detection, then matches the face.",
    manual_parameters=[
        openapi.Parameter('photos', openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                           items=openapi.Items(type=openapi.TYPE_FILE),
                           required=True, description="Multiple frames captured over ~3 seconds"),
    ],
    responses={200: 'Attendance marked', 400: 'No blink detected / spoof / no match / already marked'}
)
@api_view(['POST'])
@parser_classes([MultiPartParser])
def mark_attendance_live(request):
    if not is_teacher(request.user):
        return Response({'error': 'Only teachers can mark attendance.'}, status=status.HTTP_403_FORBIDDEN)

    photos = request.FILES.getlist('photos')

    if len(photos) < 5:
        return Response({'error': 'At least 5 frames are required for liveness verification.'}, status=status.HTTP_400_BAD_REQUEST)

    ear_sequence = []
    real_votes = 0
    fake_votes = 0
    last_face = None
    last_bbox = None

    for photo in photos:
        file_bytes = np.frombuffer(photo.read(), np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if image is None:
            continue

        face, landmarks, bbox = get_face_and_landmarks(image)
        if face is None:
            continue

        ear = get_average_ear(landmarks)
        ear_sequence.append(ear)

        label, _ = check_real_or_fake(image, bbox)
        if label == "real":
            real_votes += 1
        else:
            fake_votes += 1

        last_face = face
        last_bbox = bbox

    if last_face is None:
        return Response({'error': 'No face detected in any frame.'}, status=status.HTTP_400_BAD_REQUEST)

    print(f"DEBUG ear_sequence: {ear_sequence}")

    blinked = detect_blink(ear_sequence)
    moved = has_natural_movement(ear_sequence)

    print(f"DEBUG blinked={blinked}, moved={moved}")

    if not (blinked or moved):
        return Response({'error': 'No liveness detected. Please look at the camera naturally for a few seconds.'}, status=status.HTTP_400_BAD_REQUEST)

    if fake_votes >= real_votes:
        return Response({'error': 'Spoof detected across frames. Attendance rejected.'}, status=status.HTTP_400_BAD_REQUEST)

    student, message = find_matching_student(last_face)
    if not student:
        return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

    existing = get_recent_attendance(student, request.user)
    if existing:
        return duplicate_attendance_response(student, existing)

    record = Attendance.objects.create(student=student, teacher=request.user, taken_at=timezone.now())
    serializer = AttendanceSerializer(record)

    return Response({
        'message': f'Attendance marked for {student.name}',
        'match_info': message,
        'liveness': f'Blink detected across {len(ear_sequence)} frames',
        'spoof_check': f'{real_votes} real votes / {fake_votes} fake votes',
        'record': serializer.data
    }, status=status.HTTP_200_OK)

@swagger_auto_schema(method='get', operation_description="Get all attendance records.")
@api_view(['GET'])
def list_attendance(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Please log in.'}, status=status.HTTP_401_UNAUTHORIZED)

    records = Attendance.objects.filter(
        teacher=request.user,
        taken_at__gte=timezone.now() - ATTENDANCE_WINDOW
    ).order_by('-taken_at')
    serializer = AttendanceSerializer(records, many=True)
    return Response(serializer.data)

@swagger_auto_schema(method='delete', operation_description="Delete an attendance record.")
@api_view(['DELETE'])
def delete_attendance(request, record_id):
    if not request.user.is_authenticated:
        return Response({'error': 'Please log in.'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        record = Attendance.objects.get(id=record_id, teacher=request.user)
    except Attendance.DoesNotExist:
        return Response({'error': 'Record not found.'}, status=status.HTTP_404_NOT_FOUND)

    record.delete()
    return Response({'message': f'Attendance record {record_id} deleted.'}, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='post',
    operation_description="Detects all faces in a frame and returns bounding boxes + matched student names (for live overlay display). Does NOT mark attendance.",
    manual_parameters=[
        openapi.Parameter('photo', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
    ],
)
@api_view(['POST'])
@parser_classes([MultiPartParser])
def detect_faces_live(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Please log in.'}, status=status.HTTP_401_UNAUTHORIZED)

    photo = request.FILES.get('photo')
    if not photo:
        return Response({'error': 'Photo is required.'}, status=status.HTTP_400_BAD_REQUEST)

    file_bytes = np.frombuffer(photo.read(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if image is None:
        return Response({'error': 'Invalid image.'}, status=status.HTTP_400_BAD_REQUEST)

    faces = detect_all_faces(image)
    results = []

    students = Student.objects.exclude(embedding__isnull=True)

    for face_data in faces:
        embedding = np.array(face_data['embedding'])
        bbox = face_data['bbox']

        best_match = None
        best_similarity = -1

        for student in students:
            known_embedding = np.array(student.embedding)
            similarity = np.dot(embedding, known_embedding) / (
                np.linalg.norm(embedding) * np.linalg.norm(known_embedding)
            )
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = student

        if best_match and best_similarity > 0.5:
            results.append({
                'bbox': bbox,
                'name': best_match.name,
                'registered': True
            })
        else:
            results.append({
                'bbox': bbox,
                'name': None,
                'registered': False
            })

    return Response({'faces': results})
