from django.urls import path, include
from .views import LessonFileViewSet, LessonViewSet
from rest_framework.routers import DefaultRouter

app_name = 'lessons'

# Use DefaultRouter to generate the routes
router = DefaultRouter()

# Include the router-generated routes
urlpatterns = [
    path('', include(router.urls)),
]
