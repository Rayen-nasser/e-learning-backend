from jsonschema import ValidationError
from rest_framework import viewsets, serializers, mixins, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied, Throttled
from core.models import Course, Enrollment, Level, Rating, Category
from course.pagination import CoursePagination
from .serializers import CategorySerializer, CourseSerializer, LevelSerializer, RatingSerializer
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
import re
import bleach
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiParameter, OpenApiExample
from django.db.models import Count, Avg, Q

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
             OpenApiParameter(name='search', type=str, description="Search for courses by title, description or instructor name."),
             OpenApiParameter(name='level', type=str, description="Filter by level name (e.g., 'beginner', 'intermediate')."),
            OpenApiParameter(name='min_price', type=float, description="Minimum price of the course"),
            OpenApiParameter(name='max_price', type=float, description="Maximum price of the course"),
            OpenApiParameter(name='category', type=int, description="Filter by category ID"),
            OpenApiParameter(name='category_name', type=str, description="Filter by category name"),
             OpenApiParameter(name='instructor', type=int, description="Filter by instructor ID"),
            OpenApiParameter(name='min_rating', type=float, description="Filter courses with a minimum average rating."),
            OpenApiParameter(name='ordering', type=str, description="Order by fields such as 'created_at', 'price', 'title', 'student_count', 'average_rating', prepended with '-' for descending order e.g '-price'."),
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
        tags=["Course"],
    ),
    retrieve=extend_schema(
        description="Retrieve detailed information about a specific course.",
        responses={200: CourseSerializer},
        tags=["Course"],
    ),
    create=extend_schema(
        description="Create a new course. Only instructors are allowed to create courses.",
        request=CourseSerializer,
        responses={201: CourseSerializer},
        tags=["Course"],
    ),
    update=extend_schema(
        description="Update an existing course. Only the instructor who created the course can update it.",
        request=CourseSerializer,
        responses={200: CourseSerializer},
        tags=["Course"],
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
        tags=["Course"],
    ),
)
@method_decorator(ratelimit(key='ip', rate='5/m', method='ALL'), name='dispatch')
class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling course operations with advanced filtering and search capabilities.
    """
    serializer_class = CourseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    filterset_fields = ['category', 'instructor']
    ordering_fields = ['created_at', 'price', 'title', 'student_count', 'average_rating']
    ordering = ['-created_at']
    pagination_class = CoursePagination


    def get_queryset(self):
        # Prefetch related fields for optimization
        queryset = Course.objects.all().select_related('category', 'instructor')

        # Annotate with student_count and average_rating
        queryset = queryset.annotate(student_count=Count('enrollment'))
        queryset = queryset.annotate(average_rating=Avg('ratings__rating'))

        # Get query parameters
        search_query = self.request.query_params.get('search', None)
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        category_name = self.request.query_params.get('category_name')
        min_rating = self.request.query_params.get('min_rating')
        level_name = self.request.query_params.get('level', None)

        # Search Logic
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(instructor__username__icontains=search_query) |
                Q(instructor__email__icontains=search_query)
            )

        # Price Range Filtering
        if min_price is not None:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass  # Ignore invalid min_price values
        if max_price is not None:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass  # Ignore invalid max_price values

        # Filter by Category Name
        if category_name:
            categories = category_name.split(',')  # Split by comma for multiple categories
            category_filters = Q()
            for category in categories:
                category_filters |= Q(category__name__iexact=category.strip())  # Case-insensitive match
            queryset = queryset.filter(category_filters)

        # Filter by Minimum Average Rating (after annotation)
        if min_rating is not None:
            try:
                queryset = queryset.filter(average_rating__gte=float(min_rating))
            except ValueError:
                pass  # Ignore invalid min_rating values

        # Filter by Level Name (filtering using level's name)
        if level_name:
            queryset = queryset.filter(level__name__iexact=level_name)

        return queryset

    def get_permissions(self):
        """
        Return appropriate permissions based on the action.
        """
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def handle_no_permission(self):
        if getattr(self, 'ratelimit_reached', False):
            raise Throttled(detail="Rate limit exceeded. Please try again later.")
        return super().handle_no_permission()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated or getattr(user, 'role', None) != 'Instructor':
            raise PermissionDenied("Only instructors can create courses.")

        # Validate and sanitize input
        instructor = self.request.data.get('instructor', '')
        title = self.request.data.get('title', '')
        validate_sql_injection(instructor)
        validate_sql_injection(title)

        description = self.request.data.get('description', '')
        sanitized_description = sanitize_course_description(description)

        try:
            serializer.save(
                description=sanitized_description,
                instructor=user
            )
        except Exception as e:
            raise ValidationError(f"Failed to create course: {str(e)}")

    def get_serializer_context(self):
        """
        Add context to indicate whether the request is for a list view or a detail view.
        """
        context = super().get_serializer_context()
        # Set 'is_list_view' to True for list actions, False for retrieve actions
        context['is_list_view'] = self.action == 'list'
        return context


@extend_schema_view(
    list=extend_schema(
        description="Retrieve the list of categories.",
        responses={200: CategorySerializer(many=True)},
        tags=["Category"],
    ),
    retrieve=extend_schema(
        description="Retrieve a specific category by ID.",
        responses={200: CategorySerializer},
        tags=["Category"],
    ),
    create=extend_schema(
        description="Create a new category. Only available for instructors.",
        responses={201: CategorySerializer},
        request=CategorySerializer,
        tags=["Category"],
    ),
    update=extend_schema(
        description="Update an existing category. Only available for instructors.",
        responses={200: CategorySerializer},
        request=CategorySerializer,
        tags=["Category"],
    ),
    partial_update=extend_schema(
        description="Partially update an existing category. Only available for instructors.",
        responses={200: CategorySerializer},
        request=CategorySerializer,
        tags=["Category"],
    ),
    destroy=extend_schema(
        description="Delete a category. Only available for instructors.",
        responses={204: OpenApiResponse(description="No Content")},
        tags=["Category"],
    )
)
class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for category management with caching and validation.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated or self.request.user.role != 'Instructor':
            raise PermissionDenied("Only instructors can create categories.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.is_authenticated or self.request.user.role != 'Instructor':
            raise PermissionDenied("Only instructors can update categories.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_authenticated or self.request.user.role != 'Instructor':
            raise PermissionDenied("Only instructors can delete categories.")
        instance.delete()

@extend_schema_view(
    list=extend_schema(
        description="Retrieve the list of levels.",
        responses={200: LevelSerializer(many=True)},
        tags=["Level"],
    ),
    retrieve=extend_schema(
        description="Retrieve a specific level by ID.",
        responses={200: LevelSerializer},
        tags=["Level"],
    ),
    create=extend_schema(
        description="Create a new level. Only available for instructors.",
        responses={201: LevelSerializer},
        request=LevelSerializer,
        tags=["Level"],
    ),
    update=extend_schema(
        description="Update an existing level. Only available for instructors.",
        responses={200: LevelSerializer},
        request=LevelSerializer,
        tags=["Level"],
    ),
    partial_update=extend_schema(
        description="Partially update an existing level. Only available for instructors.",
        responses={200: LevelSerializer},
        request=LevelSerializer,
        tags=["Level"],
    ),
    destroy=extend_schema(
        description="Delete a level. Only available for instructors.",
        responses={204: OpenApiResponse(description="No Content")},
        tags=["Level"],
    )
)
class LevelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for level management with caching and validation.
    """
    queryset = Level.objects.all()
    serializer_class = LevelSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']  # Assuming 'name' is a field in the Level model

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]  # Anyone can view the list and details
        return [IsAuthenticated()]  # Authenticated users required for create, update, delete

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated or self.request.user.role != 'Instructor':
            raise PermissionDenied("Only instructors can create levels.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.is_authenticated or self.request.user.role != 'Instructor':
            raise PermissionDenied("Only instructors can update levels.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_authenticated or self.request.user.role != 'Instructor':
            raise PermissionDenied("Only instructors can delete levels.")
        instance.delete()


@extend_schema_view(
    list=extend_schema(
        description="List all ratings for a specific course.",
        responses={200: RatingSerializer(many=True)},  # List of ratings
        tags=["Rating"],
    ),
    create=extend_schema(
        description="Create a new rating for a specific course.",
        request=RatingSerializer,
        responses={201: RatingSerializer},  # Response after creating a rating
        tags=["Rating"],
    ),
    retrieve=extend_schema(
        description="Retrieve a specific rating for a course.",
        responses={200: RatingSerializer},  # Response with rating details
        tags=["Rating"],
    ),
    update=extend_schema(
        description="Update your rating for a specific course.",
        request=RatingSerializer,
        responses={200: RatingSerializer},  # Updated rating response
        tags=["Rating"],
    ),
    partial_update=extend_schema(
        description="Partially update your rating for a specific course.",
        request=RatingSerializer,
        responses={200: RatingSerializer},  # Updated rating response
        tags=["Rating"],
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