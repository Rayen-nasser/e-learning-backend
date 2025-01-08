from django.urls import path, include
from .views import LessonFileViewSet, LessonViewSet
from rest_framework.routers import DefaultRouter

app_name = 'lessons'

# Use DefaultRouter to generate the routes
router = DefaultRouter()
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'lesson-files', LessonFileViewSet, basename='lesson-file')

# Include the router-generated routes
urlpatterns = [
    path('', include(router.urls)),
]
