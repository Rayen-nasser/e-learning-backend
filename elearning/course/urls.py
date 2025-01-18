from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from .views import CourseViewSet, RatingViewSet, CategoryViewSet
from lesson.views import LessonFileViewSet, LessonViewSet
from enrollment.views import EnrollmentViewSet

app_name = 'course'

# Main router for courses
router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')

# router for category
router.register(r'categories', CategoryViewSet, basename='category')

# Nested router for lessons under courses
courses_router = NestedDefaultRouter(router, r'courses', lookup='course')
courses_router.register(r'lessons', LessonViewSet, basename='course-lessons')

# Nested router for enrollments under courses, change the 'course_pk' to 'course_id'
courses_router.register(r'enrollments', EnrollmentViewSet, basename='courses-enrollments')

# Nested router for lesson files under lessons
lessons_router = NestedDefaultRouter(courses_router, r'lessons', lookup='lesson')
lessons_router.register(r'lesson-files', LessonFileViewSet, basename='lesson-lesson-files')

# Register the Rating ViewSet for adding and viewing ratings
courses_router.register(r'ratings', RatingViewSet, basename='course-ratings')


# URLs
urlpatterns = [
    path('', include(router.urls)),
    path('', include(courses_router.urls)),
    path('', include(lessons_router.urls)),
]
