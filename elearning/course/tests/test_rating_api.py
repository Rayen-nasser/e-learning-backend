from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Course, Rating, Category, Enrollment
from course.serializers import CourseSerializer, RatingSerializer
from decimal import Decimal

def create_user(**params):
    """Helper function to create new user"""
    defaults = {
        'email': 'test@example.com',
        'username': 'testuser',
        'password': 'testpass123',
        'role': 'Student'
    }
    defaults.update(params)
    return get_user_model().objects.create_user(**defaults)

def create_category(**params):
    """Helper function to create a category"""
    defaults = {
        'name': 'Programming',
        'description': 'Programming courses'
    }
    defaults.update(params)
    return Category.objects.create(**defaults)

def create_course(user, category, **params):
    """Helper function to create a course"""
    defaults = {
        'title': 'Python Course',
        'description': 'A comprehensive Python course',
        'category': category,
        'price': Decimal('99.99'),
        'instructor': user
    }
    defaults.update(params)
    return Course.objects.create(**defaults)

def rating_url(course_id):
    """Create rating URL for a specific course"""
    return reverse('course:course-ratings-list', args=[course_id])

def rating_detail_url(course_id, rating_id):
    """Create rating detail URL"""
    return reverse('course:course-ratings-detail', args=[course_id, rating_id])

class PublicRatingApiTests(TestCase):
    """Test the publicly available rating API"""

    def setUp(self):
        self.client = APIClient()
        self.category = create_category()
        self.instructor = create_user(
            username='instructor',
            email='instructor@example.com',
            role='Instructor'
        )
        self.course = create_course(self.instructor, self.category)

    def test_login_required_to_rate(self):
        """Test that login is required for rating a course"""
        url = rating_url(self.course.id)
        payload = {
            'rating': 5.0,
            'comment': 'Great course!'
        }
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_course_ratings(self):
        """Test retrieving course ratings without authentication"""
        student = create_user(username='student', email='student@example.com')
        Enrollment.objects.create(student=student, course=self.course)
        Rating.objects.create(
            user=student,
            course=self.course,
            rating=4.5,
            comment='Good course'
        )

        url = rating_url(self.course.id)
        res = self.client.get(url)

        ratings = Rating.objects.filter(course=self.course)
        serializer = RatingSerializer(ratings, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

class PrivateRatingApiTests(TestCase):
    """Test the private rating API"""

    def setUp(self):
        self.client = APIClient()
        self.category = create_category()
        self.instructor = create_user(
            username='instructor',
            email='instructor@example.com',
            role='Instructor'
        )
        self.student = create_user(
            username='student',
            email='student@example.com',
            role='Student'
        )
        self.course = create_course(self.instructor, self.category)
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course
        )
        self.client.force_authenticate(user=self.student)

    def test_create_rating_enrolled_student(self):
        """Test creating a rating by an enrolled student"""
        url = rating_url(self.course.id)
        payload = {
            'rating': 4.5,
            'comment': 'Excellent course content'
        }
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        rating = Rating.objects.get(id=res.data['id'])
        self.assertEqual(rating.rating, Decimal('4.5'))
        self.assertEqual(rating.user, self.student)

    def test_create_rating_unenrolled_student(self):
        """Test creating a rating by a student not enrolled in the course"""
        unenrolled_student = create_user(
            username='unenrolled',
            email='unenrolled@example.com'
        )
        self.client.force_authenticate(user=unenrolled_student)

        url = rating_url(self.course.id)
        payload = {
            'rating': 4.0,
            'comment': 'Good course'
        }
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Rating.objects.filter(user=unenrolled_student).exists())

    def test_duplicate_rating_not_allowed(self):
        """Test that a student cannot rate a course twice"""
        Rating.objects.create(
            user=self.student,
            course=self.course,
            rating=4.0
        )

        url = rating_url(self.course.id)
        payload = {
            'rating': 5.0,
            'comment': 'Updated rating'
        }
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Rating.objects.filter(user=self.student).count(), 1)

    def test_update_rating(self):
        """Test updating own rating"""
        rating = Rating.objects.create(
            user=self.student,
            course=self.course,
            rating=3.0,
            comment='Initial comment'
        )

        url = rating_detail_url(self.course.id, rating.id)
        payload = {
            'rating': 4.0,
            'comment': 'Updated comment'
        }
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        rating.refresh_from_db()
        self.assertEqual(rating.rating, Decimal('4.0'))
        self.assertEqual(rating.comment, 'Updated comment')

    def test_update_other_user_rating_not_allowed(self):
        """Test updating another user's rating is not allowed"""
        other_student = create_user(
            username='other_student',
            email='other@example.com'
        )
        Enrollment.objects.create(student=other_student, course=self.course)
        rating = Rating.objects.create(
            user=other_student,
            course=self.course,
            rating=3.0
        )

        url = rating_detail_url(self.course.id, rating.id)
        payload = {
            'rating': 1.0,
            'comment': 'Trying to modify'
        }
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        rating.refresh_from_db()
        self.assertEqual(rating.rating, Decimal('3.0'))

    def test_delete_rating_not_allowed(self):
        """Test that DELETE method is not allowed for ratings"""
        rating = Rating.objects.create(
            user=self.student,
            course=self.course,
            rating=4.0
        )

        url = rating_detail_url(self.course.id, rating.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Rating.objects.filter(id=rating.id).exists())

    def test_rating_invalid_score(self):
        """Test creating rating with invalid score"""
        url = rating_url(self.course.id)
        invalid_payloads = [
            {'rating': -1.0, 'comment': 'Invalid negative'},
            {'rating': 5.5, 'comment': 'Invalid over max'},
            {'rating': 'not a number', 'comment': 'Invalid type'}
        ]

        for payload in invalid_payloads:
            res = self.client.post(url, payload)
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_ratings_by_course(self):
        """Test that ratings are correctly filtered by course"""
        other_course = create_course(
            self.instructor,
            self.category,
            title='Other Course'
        )
        Enrollment.objects.create(student=self.student, course=other_course)

        # Create ratings for both courses
        Rating.objects.create(
            user=self.student,
            course=self.course,
            rating=4.0,
            comment='First course'
        )
        Rating.objects.create(
            user=self.student,
            course=other_course,
            rating=3.0,
            comment='Other course'
        )

        url = rating_url(self.course.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['comment'], 'First course')

    def test_rating_updates_course_average(self):
        """Test that course average rating is updated when new ratings are created"""
        url = rating_url(self.course.id)

        # Create the first rating
        self.client.post(url, {'rating': 4.0, 'comment': 'Good'})

        # Create the second rating from a different user
        other_student = create_user(
            username='other_student2',
            email='other2@example.com'
        )
        Enrollment.objects.create(student=other_student, course=self.course)
        self.client.force_authenticate(user=other_student)
        self.client.post(url, {'rating': 5.0, 'comment': 'Excellent'})

        # Refresh the course object from the database
        self.course.refresh_from_db()

        # Serialize the updated course object
        serializer = CourseSerializer(self.course)

        # Assert that the serializer's data reflects the correct average rating
        self.assertEqual(serializer.data['average_rating'], 4.5)  # Average of 4.0 and 5.0
        self.assertEqual(serializer.data['student_count'], 2)  # Two students rated the course
