from django.urls import path
from . import views

urlpatterns = [
    path('page/', views.register_page, name='register_page'),
    path('register/', views.register_student, name='register_student'),
    path('', views.list_students, name='list_students'),
    path('<str:student_id>/', views.delete_student, name='delete_student'),
]