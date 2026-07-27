from django.urls import path
from . import views

urlpatterns = [
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('mark_live/', views.mark_attendance_live, name='mark_attendance_live'),
    path('detect_live/', views.detect_faces_live, name='detect_faces_live'),
    path('', views.list_attendance, name='list_attendance'),
    path('<int:record_id>/', views.delete_attendance, name='delete_attendance'),
]