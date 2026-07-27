from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.shortcuts import render
from .auth_views import login_view, logout_view

def landing_page(request):
    return render(request, 'index.html')

def attendance_live_page(request):
    return render(request, 'attendance_live.html')

schema_view = get_schema_view(
    openapi.Info(
        title="Smart Attendance API",
        default_version='v1',
        description="Face recognition based smart attendance system with anti-spoofing detection.",
        contact=openapi.Contact(name="Samir Pokhrel", email="poksamir6@gmail.com"),
        license=openapi.License(name="All CopyRight Reserved by Samir Pokhrel"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/students/', include('students.urls')),  # NEW — we'll create this file next
    path('api/attendance/', include('attendance.urls')),
    path('', landing_page, name='landing_page'),
    path('attendance-live/', attendance_live_page, name='attendance_live_page'),
    path('login/', login_view, name='login_page'),
    path('logout/', logout_view, name='logout_page'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)