from rest_framework import serializers
from core.models import Course, Category, Rating

class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'user', 'course', 'rating', 'comment']
        read_only_fields = ['user', 'course', 'created_at']


class CourseSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    ratings = RatingSerializer(many=True, read_only=True)  # Nested ratings field if required
    average_rating = serializers.SerializerMethodField()  # For displaying the average rating

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'category', 'price', 'image', 'instructor', 'created_at', 'updated_at', 'ratings', 'average_rating']
        read_only_fields = ['instructor', 'created_at', 'updated_at', 'ratings', 'average_rating', 'student_count']

    def get_average_rating(self, obj):
        """
        Calculate the average rating for the course.
        """
        ratings = obj.ratings.all()
        if ratings:
            return sum(rating.rating for rating in ratings) / len(ratings)
        return 0  # Default to 0 if no ratings exist
