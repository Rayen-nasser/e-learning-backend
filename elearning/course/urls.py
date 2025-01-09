from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from .views import CourseViewSet
from lesson.views import LessonFileViewSet, LessonViewSet

from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from lesson.views import LessonFileViewSet

app_name = 'course'

router = DefaultRouter()
router.register(r'courses', CourseViewSet)

courses_router = NestedDefaultRouter(router, r'courses', lookup='course')
courses_router.register(r'lessons', LessonViewSet, basename='course-lessons')

# Nested URL for lesson files
lessons_router = NestedDefaultRouter(courses_router, r'lessons', lookup='lesson')
lessons_router.register(r'lesson-files', LessonFileViewSet, basename='lesson-lesson-files')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(courses_router.urls)),
    path('', include(lessons_router.urls)),
]

