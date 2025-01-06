from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from core.models import Course
from .serializers import CourseSerializer
from rest_framework.response import Response


class CourseViewSet(viewsets.ViewSet):
    """
    ViewSet for listing courses with public access.
    """
    def list(self, request):
        courses = Course.objects.all()  # Fetch queryset dynamically
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)

    def get_permissions(self):
        """
        Return appropriate permissions based on the action.
        """
        if self.action == 'list':
            return [AllowAny()]  # Allow everyone to list courses
        return [IsAuthenticated()]  # Require authentication for other actions


class CourseCreateView(generics.CreateAPIView):
    """
    CreateAPIView for creating a new course.
    Only users with the role of 'Instructor' can create a course.
    """
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """
        Perform the save operation for creating a course.
        """
        user = self.request.user
        # Safely check if the user is an instructor
        if getattr(user, 'role', None) != 'Instructor':
            raise PermissionDenied("Only instructors can create courses.")
        serializer.save(instructor=user)
