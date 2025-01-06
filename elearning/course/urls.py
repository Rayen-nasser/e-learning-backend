from django.urls import path
from .views import CourseViewSet, CourseCreateView

app_name = 'course'

urlpatterns = [
    path('courses/', CourseViewSet.as_view({'get': 'list'}), name='course-list'),
    path('courses/create/', CourseCreateView.as_view(), name='course-create'),
]
