from django.urls import path, include
from .views import CourseViewSet
from rest_framework.routers import DefaultRouter

app_name = 'course'

# Use DefaultRouter to generate the routes
router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')

# Include the router-generated routes
urlpatterns = [
    path('', include(router.urls)),
]
