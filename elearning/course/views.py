from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from core.models import Course
from .serializers import CourseSerializer
from rest_framework.response import Response

class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, creating, updating, and deleting courses.
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_permissions(self):
        """
        Return appropriate permissions based on the action.
        """
        if self.action == 'list':
            return [AllowAny()]  # Allow everyone to list courses
        if self.action in ['create', 'update', 'destroy']:
            return [IsAuthenticated()]  # Require authentication for other actions
        return super().get_permissions()

    def perform_create(self, serializer):
        """
        Perform the save operation for creating a course.
        Only instructors can create courses.
        """
        user = self.request.user
        if getattr(user, 'role', None) != 'Instructor':
            raise PermissionDenied("Only instructors can create courses.")
        serializer.save(instructor=user)
