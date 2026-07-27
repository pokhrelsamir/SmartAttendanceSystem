from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Student
from .serializers import StudentSerializer
from .face_utils import get_face_embedding
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test


def is_admin(user):
    return user.is_authenticated and (user.groups.filter(name='Admin').exists() or user.is_superuser)


@login_required
@user_passes_test(is_admin, login_url='/login/')
def register_page(request):
    return render(request, 'register.html')


@swagger_auto_schema(
    method='post',
    operation_description="Register a new student with their photo. Generates a face embedding automatically.",
    manual_parameters=[
        openapi.Parameter('student_id', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
        openapi.Parameter('name', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
        openapi.Parameter('photo', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
    ],
    responses={201: StudentSerializer, 400: 'Bad request'}
)
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def register_student(request):
    if not request.user.is_authenticated or not (request.user.groups.filter(name='Admin').exists() or request.user.is_superuser):
        return Response({'error': 'Only admins can register students.'}, status=status.HTTP_403_FORBIDDEN)

    student_id = request.data.get('student_id')
    name = request.data.get('name')
    photo = request.FILES.get('photo')

    if not student_id or not name or not photo:
        return Response({'error': 'student_id, name, and photo are all required.'}, status=status.HTTP_400_BAD_REQUEST)

    student = Student(student_id=student_id, name=name, photo=photo)
    student.save()

    embedding = get_face_embedding(student.photo.path)

    if embedding is None:
        student.delete()
        return Response({'error': 'No face detected in the photo. Please try again with a clearer image.'}, status=status.HTTP_400_BAD_REQUEST)

    student.embedding = embedding
    student.save()

    serializer = StudentSerializer(student)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@swagger_auto_schema(method='get', operation_description="List all registered students.")
@api_view(['GET'])
def list_students(request):
    students = Student.objects.all()
    serializer = StudentSerializer(students, many=True)
    return Response(serializer.data)


@swagger_auto_schema(method='delete', operation_description="Delete a registered student.")
@api_view(['DELETE'])
def delete_student(request, student_id):
    try:
        student = Student.objects.get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    student.delete()
    return Response({'message': f'Student {student_id} deleted.'}, status=status.HTTP_200_OK)