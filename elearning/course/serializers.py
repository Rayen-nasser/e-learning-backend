from rest_framework import serializers
from core.models import Course, Category, Enrollment, Level, Rating
from django.db.models import Avg
from user.serializers import UserSerializer

class RatingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Rating
        fields = ['id', 'user', 'course', 'rating', 'comment', 'created_at']
        read_only_fields = ['user', 'course', 'created_at']

    def validate_rating(self, value):
        """Validate rating is within acceptable range"""
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

class CategorySerializer(serializers.ModelSerializer):
    course_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'course_count']

    def validate_name(self, value):
        """Ensure category name is unique (case-insensitive)"""
        if Category.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("A category with this name already exists")
        return value

    def get_course_count(self, obj):
        """Get the count of courses associated with the category"""
        return Course.objects.filter(category=obj).count()



class LevelSerializer(serializers.ModelSerializer):
    courses = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()

    class Meta:
        model = Level
        fields = ['id', 'name', 'description', 'courses', 'students']

    def validate_name(self, value):
        """Ensure level name is unique (case-insensitive)."""
        if Level.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("A level with this name already exists.")
        return value

    def get_courses(self, obj):
        """Get the count of courses associated with the level."""
        return obj.courses.count()

    def get_students(self, obj):
        """Get the count of unique students associated with all courses of this level."""
        return Enrollment.objects.filter(course__level=obj).values('student').distinct().count()


class CourseSerializer(serializers.ModelSerializer):
    ratings = RatingSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()  # Keep this for dynamic calculation
    student_count = serializers.SerializerMethodField()   # Keep this for dynamic calculation
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=True
    )
    instructor = UserSerializer(read_only=True)
    level = LevelSerializer(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'category', 'price', 'image', 'instructor', 'created_at',
            'ratings', 'level', 'average_rating', 'student_count'
        ]
        read_only_fields = ['instructor', 'level', 'created_at', 'ratings', 'average_rating', 'student_count']

    def get_average_rating(self, obj):
        """
        Calculate the average rating for the course.
        If the queryset is annotated with `average_rating`, use that value.
        Otherwise, calculate it dynamically.
        """
        if hasattr(obj, 'average_rating'):
            # Use the annotated value if available
            return round(obj.average_rating, 2)
        # Calculate dynamically if not annotated
        avg = obj.ratings.aggregate(average=Avg('rating')).get('average', 0)
        return round(avg, 2) if avg else 0

    def get_student_count(self, obj):
        """
        Get the number of students enrolled in the course.
        If the queryset is annotated with `student_count`, use that value.
        Otherwise, calculate it dynamically.
        """
        if hasattr(obj, 'student_count'):
            # Use the annotated value if available
            return obj.student_count
        # Calculate dynamically if not annotated
        return Enrollment.objects.filter(course=obj).count()

    def validate_price(self, value):
        """Validate price is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative")
        return value

    def validate_title(self, value):
        """Validate course title length and uniqueness"""
        if len(value) < 5:
            raise serializers.ValidationError("Course title must be at least 5 characters long")

        # Check for duplicate titles (case-insensitive)
        instance = getattr(self, 'instance', None)
        if instance:
            # Exclude current instance when updating
            exists = Course.objects.filter(title__iexact=value).exclude(id=instance.id).exists()
        else:
            exists = Course.objects.filter(title__iexact=value).exists()

        if exists:
            raise serializers.ValidationError("A course with this title already exists")
        return value

    def to_representation(self, instance):
        """Modify the response based on the context (list vs. detail view)"""
        representation = super().to_representation(instance)

        # Check if the request is for a list view
        is_list_view = self.context.get('is_list_view', False)

        if is_list_view:
            # Hide ratings when listing courses
            if 'ratings' in representation:
                del representation['ratings']

            # Replace 'category' field with a simplified version (excluding description)
            category = representation.get('category')
            if category:
                category_instance = Category.objects.get(id=category)
                category_detail = {
                    'id': category_instance.id,
                    'name': category_instance.name,
                    # Exclude 'description' here
                }
                representation['category'] = category_detail

            # Hide level details when listing courses
            if 'level' in representation:
                del representation['level']

            # Hide instructor email when listing courses
            instructor = representation.get('instructor')
            if instructor and 'email' in instructor:
                del instructor['email']

        return representation