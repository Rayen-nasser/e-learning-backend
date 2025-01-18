import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Category, Course, Lesson, LessonFile
from lesson.serializers import LessonSerializer
from unittest.mock import MagicMock
from datetime import timedelta
from django.utils import timezone


def create_user(**params):
    """Helper function to create users."""
    defaults = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpass123',
        'profile_image': 'http://example.com/media/uploads/user_profiles/testuser.jpg',
        'role': 'Student'
    }
    defaults.update(params)
    return get_user_model().objects.create_user(**defaults)

def get_lesson_list_url(course_id):
    """Helper function to get the nested lesson list URL."""
    return reverse('course:course-lessons-list', args=[course_id])

def get_lesson_detail_url(course_id, lesson_id):
    """Helper function to get the nested lesson detail URL."""
    return reverse('course:course-lessons-detail', args=[course_id, lesson_id])

def get_lesson_file_list_url(course_id, lesson_id):
    """Helper function to get the nested lesson file list URL."""
    return reverse('course:lesson-lesson-files-list', args=[course_id, lesson_id])

def get_lesson_file_detail_url(course_id, lesson_id, file_id):
    """Helper function to get the nested lesson file detail URL."""
    return reverse('course:lesson-lesson-files-detail', args=[course_id, lesson_id, file_id])


class PublicLessonApiTests(TestCase):
    """Test unauthenticated lesson API access."""

    def setUp(self):
        self.client = APIClient()
        self.instructor = create_user(
            username='instructor',
            email='instructor@example.com',
            role='Instructor'
        )
        self.category = Category.objects.create(
            name='Test Category',
            description='Test Category Description',
        )
        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            instructor=self.instructor,
            price=99.99,
            category=self.category
        )
        self.LESSON_URL = get_lesson_list_url(self.course.id)

    def test_auth_required(self):
        """Test that authentication is required."""
        response = self.client.get(self.LESSON_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_lesson_unauthorized(self):
        """Test creating a lesson without authentication fails."""
        payload = {
            'title': 'Test Lesson',
            'description': 'Test Description',
            'course': self.course.id
        }
        response = self.client.post(self.LESSON_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateLessonApiTests(TestCase):
    """Test authenticated lesson API access."""

    def setUp(self):
        self.client = APIClient()
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
        self.category = Category.objects.create(
            name='Test Category',
            description='Test Category Description',
        )
        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            instructor=self.instructor,
            price=99.99,
            category=self.category
        )
        self.LESSON_URL = get_lesson_list_url(self.course.id)
        self.client.force_authenticate(self.instructor)

    def test_list_lessons(self):
        """Test retrieving a list of lessons."""
        Lesson.objects.all().delete()
        Lesson.objects.create(title='Lesson 1', description='Desc 1', course=self.course)
        Lesson.objects.create(title='Lesson 2', description='Desc 2', course=self.course)

        response = self.client.get(self.LESSON_URL)
        response = self.client.get(self.LESSON_URL)
        lessons = Lesson.objects.all().order_by('-created_at')
        serializer = LessonSerializer(lessons, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


    def test_create_lesson_success(self):
        """Test creating a lesson with valid data."""
        payload = {
            'title': 'New Lesson',
            'description': 'New Description',
            'course': self.course.id,
        }
        response = self.client.post(self.LESSON_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lesson = Lesson.objects.get(id=response.data['id'])
        for key in payload:
            if key == 'course':
                self.assertEqual(getattr(lesson, key).id, payload[key])
            else:
                self.assertEqual(getattr(lesson, key), payload[key])

    def test_create_lesson_invalid_data(self):
        """Test creating a lesson with invalid data fails."""
        payload = {
            'title': '',
            'description': '',
            'course': self.course.id
        }
        response = self.client.post(self.LESSON_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_update_lesson(self):
        """Test updating a lesson with PATCH."""
        lesson = Lesson.objects.create(
            title='Original Title',
            description='Original Description',
            course=self.course
        )
        payload = {'title': 'New Title'}
        url = get_lesson_detail_url(self.course.id, lesson.id)
        response = self.client.patch(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lesson.refresh_from_db()
        self.assertEqual(lesson.title, payload['title'])
        self.assertEqual(lesson.description, 'Original Description')

    def test_full_update_lesson(self):
        """Test updating a lesson with PUT."""
        lesson = Lesson.objects.create(
            title='Original Title',
            description='Original Description',
            course=self.course
        )
        payload = {
            'title': 'New Title',
            'description': 'New Description',
            'course': self.course.id
        }
        url = get_lesson_detail_url(self.course.id, lesson.id)
        response = self.client.put(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lesson.refresh_from_db()
        for key in payload:
            if key == 'course':
                self.assertEqual(getattr(lesson, key).id, payload[key])
            else:
                self.assertEqual(getattr(lesson, key), payload[key])

    def test_delete_lesson(self):
        """Test deleting a lesson."""
        lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Test Description',
            course=self.course
        )
        url = get_lesson_detail_url(self.course.id, lesson.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Lesson.objects.filter(id=lesson.id).exists())

    def test_student_cannot_create_lesson(self):
        """Test that students cannot create lessons."""
        self.client.force_authenticate(self.student)
        payload = {
            'title': 'Test Lesson',
            'description': 'Test Description',
            'course': self.course.id
        }
        response = self.client.post(self.LESSON_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_update_lesson(self):
        """Test that students cannot update lessons."""
        self.client.force_authenticate(self.student)
        lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Test Description',
            course=self.course
        )
        url = get_lesson_detail_url(self.course.id, lesson.id)
        response = self.client.patch(url, {'title': 'New Title'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_delete_lesson(self):
        """Test that students cannot delete lessons."""
        self.client.force_authenticate(self.student)
        lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Test Description',
            course=self.course
        )
        url = get_lesson_detail_url(self.course.id, lesson.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_lessons_by_course(self):
        """Test filtering lessons by course."""
        course2 = Course.objects.create(
            title='Second Course',
            description='Second Description',
            instructor=self.instructor,
            price=79.99,
            category=self.category
        )
        lesson1 = Lesson.objects.create(title='Lesson 1', course=self.course)
        lesson2 = Lesson.objects.create(title='Lesson 2', course=course2)

        response = self.client.get(self.LESSON_URL, {'course': self.course.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], lesson1.id)

    def test_search_lessons(self):
        """Test searching lessons by title and description."""
        Lesson.objects.create(
            title='Python Basics',
            description='Learn Python basics',
            course=self.course
        )
        Lesson.objects.create(
            title='Advanced JavaScript',
            description='Learn advanced JS concepts',
            course=self.course
        )

        response = self.client.get(self.LESSON_URL, {'search': 'python'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Python Basics')

    def test_upload_lesson_file(self):
        """Test uploading a file to a lesson."""
        lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Test Description',
            course=self.course
        )

        url = get_lesson_file_list_url(self.course.id, lesson.id)
        payload = {
            'lesson': lesson.id,
            'file': SimpleUploadedFile('testfile.txt', b'file content')
        }

        response = self.client.post(url, payload, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(LessonFile.objects.filter(lesson=lesson).exists())
        lesson_file = LessonFile.objects.get(lesson=lesson)
        self.assertTrue(lesson_file.file.name.endswith('.txt'))

    def test_retrieve_lesson_with_files(self):
        """Test retrieving a lesson includes its associated files."""
        lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Test Description',
            course=self.course
        )

        for i in range(2):
            LessonFile.objects.create(
                lesson=lesson,
                file=SimpleUploadedFile(f'test{i}.txt', b'content')
            )

        url = get_lesson_detail_url(self.course.id, lesson.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['files']), 2)

    def test_order_lessons_by_created_date(self):
        """Test lessons are ordered by creation date."""
        lesson1 = Lesson.objects.create(
            title='Old Lesson',
            description='Old Description',
            course=self.course
        )
        lesson2 = Lesson.objects.create(
            title='New Lesson',
            description='New Description',
            course=self.course
        )
        lesson2.created_at = timezone.now() + timedelta(days=1)
        lesson2.save()

        response = self.client.get(self.LESSON_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lessons = response.data
        self.assertEqual(lessons[0]['title'], 'Old Lesson')
        self.assertEqual(lessons[1]['title'], 'New Lesson')