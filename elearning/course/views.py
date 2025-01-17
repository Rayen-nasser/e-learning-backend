from rest_framework import viewsets, serializers, mixins
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied, Throttled
from core.models import Course, Enrollment, Rating, Category
from .serializers import CourseSerializer, RatingSerializer
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
import re
import bleach
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample


def sanitize_course_description(description):
    """
    Sanitize course description to allow only safe HTML tags.
    """
    allowed_tags = ['b', 'i', 'u', 'a', 'p', 'br']
    return bleach.clean(description, tags=allowed_tags, strip=True)

def validate_sql_injection(value):
    """
    Validate the value for SQL injection attempts.
    """
    sql_patterns = r".*[;'].*|.*--.*|.*drop.*|.*select.*|.*union.*"
    if re.match(sql_patterns, value.lower()):
        raise serializers.ValidationError("Invalid characters in value")
    return value


@extend_schema_view(
    list=extend_schema(
        description="Retrieve a list of all available courses.",
        parameters=[
            OpenApiParameter(name='search', type=str, description="Search for courses by title."),
        ],
        responses={200: CourseSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Sample Course List",
                value=[
                    {
                        "id": 1,
                        "title": "Python for Beginners",
                        "description": "A comprehensive course for Python programming.",
                        "instructor": "John Doe"
                    },
                    {
                        "id": 2,
                        "title": "Advanced Django",
                        "description": "Master Django with real-world projects.",
                        "instructor": "Jane Smith"
                    }
                ],
            )
        ],
        tags=["Course"],  # Tags applied here
    ),
    retrieve=extend_schema(
        description="Retrieve detailed information about a specific course.",
        responses={200: CourseSerializer},
        tags=["Course"],  # Tags applied here
    ),
    create=extend_schema(
        description="Create a new course. Only instructors are allowed to create courses.",
        request=CourseSerializer,
        responses={201: CourseSerializer},
        tags=["Course"],  # Tags applied here
    ),
    update=extend_schema(
        description="Update an existing course. Only the instructor who created the course can update it.",
        request=CourseSerializer,
        responses={200: CourseSerializer},
        tags=["Course"],  # Tags applied here
    ),
    partial_update=extend_schema(
        description="Partially update an existing course. Only the instructor who created the course can update it.",
        request=CourseSerializer,
        responses={200: CourseSerializer},
        tags=["Course"],
    ),
    destroy=extend_schema(
        description="Delete a course. Only the instructor who created the course can delete it.",
        responses={204: None},
        tags=["Course"],  # Tags applied here
    ),
)
@method_decorator(ratelimit(key='ip', rate='5/m', method='ALL'), name='dispatch')
class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, creating, updating, and deleting courses.
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def handle_no_permission(self):
        if getattr(self, 'ratelimit_reached', False):
            raise Throttled()
        return super().handle_no_permission()

    def get_permissions(self):
        """
        Return appropriate permissions based on the action.
        """
        if self.action == 'list' or self.action == 'retrieve':
            return [AllowAny()]  # Allow everyone to list courses
        if self.action in ['create', 'update', 'destroy']:
            return [IsAuthenticated()]  # Require authentication for other actions
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, 'role', None) != 'Instructor':
            raise PermissionDenied("Only instructors can create courses.")

        # Validate instructor and title for SQL injection
        instructor = self.request.data.get('instructor', '')
        title = self.request.data.get('title', '')
        validate_sql_injection(instructor)
        validate_sql_injection(title)

        # Sanitize course description
        description = self.request.data.get('description', '')
        sanitized_description = sanitize_course_description(description)

        category_name = self.request.data.get('category', '')
        if not category_name:
            raise PermissionDenied("Category is required.")
        category, created = Category.objects.get_or_create(name=category_name)

        # Save course with sanitized data and validated category
        serializer.save(description=sanitized_description, instructor=user, category=category)


@extend_schema_view(
    list=extend_schema(
        description="List all ratings for a specific course.",
        responses={200: RatingSerializer(many=True)},  # List of ratings
        tags=["rating"],
    ),
    create=extend_schema(
        description="Create a new rating for a specific course.",
        request=RatingSerializer,
        responses={201: RatingSerializer},  # Response after creating a rating
        tags=["rating"],
    ),
    retrieve=extend_schema(
        description="Retrieve a specific rating for a course.",
        responses={200: RatingSerializer},  # Response with rating details
        tags=["rating"],
    ),
    update=extend_schema(
        description="Update your rating for a specific course.",
        request=RatingSerializer,
        responses={200: RatingSerializer},  # Updated rating response
        tags=["rating"],
    ),
    partial_update=extend_schema(
        description="Partially update your rating for a specific course.",
        request=RatingSerializer,
        responses={200: RatingSerializer},  # Updated rating response
        tags=["rating"],
    ),
)
class RatingViewSet(mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                    mixins.UpdateModelMixin,
                    viewsets.GenericViewSet):
    """
    A viewset for viewing and editing ratings of courses.
    Allows only POST, GET, and PATCH methods.
    """
    serializer_class = RatingSerializer
    def get_permissions(self):
        """
        Assign permissions dynamically based on the action.
        """
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]  # Allow everyone to view ratings
        return [IsAuthenticated()]  # Require authentication for creating or updating ratings

    def get_course(self):
        """
        Helper method to get the course object based on the URL parameter.
        """
        course_id = self.kwargs.get('course_pk')
        return Course.objects.get(id=course_id)

    def get_queryset(self):
        """
        Override the default queryset to filter ratings by course.
        This is used for listing all ratings of a specific course.
        """
        course = self.get_course()
        return Rating.objects.filter(course=course)

    def perform_create(self, serializer):
        """
        Override the create method to ensure a user can only rate a course once.
        Also checks if the user is enrolled in the course.
        """
        course = self.get_course()
        user = self.request.user

        # Check if the user is enrolled in the course
        if not Enrollment.objects.filter(student=user, course=course).exists():
            raise PermissionDenied("You must be enrolled in the course to leave a rating.")

        # Check if the user has already rated this course
        if Rating.objects.filter(course=course, user=user).exists():
            raise PermissionDenied("You have already rated this course.")

        serializer.save(course=course, user=user)

    def perform_update(self, serializer):
        """
        Override the update method to allow users to update their rating.
        Ensures the user is enrolled in the course.
        """
        course = self.get_course()
        user = self.request.user

        # Ensure the user has rated the course
        rating_instance = self.get_object()
        if rating_instance.user != user:
            raise PermissionDenied("You can only update your own rating.")

        # Check if the user is enrolled in the course
        if not Enrollment.objects.filter(student=user, course=course).exists():
            raise PermissionDenied("You must be enrolled in the course to update your rating.")

        serializer.save(course=course, user=user)