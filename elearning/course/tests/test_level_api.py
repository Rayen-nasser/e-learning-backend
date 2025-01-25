from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import Level, User, Enrollment, Course
from course.serializers import LevelSerializer


class LevelAPITests(APITestCase):
    def setUp(self):
        """Set up test data for Level API tests."""
        self.client = APIClient()

        # Create test users
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role='Instructor'
        )
        self.student1 = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='testpass123',
            role='Student'
        )
        self.student2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='testpass123',
            role='Student'
        )

        # Create levels
        self.level1 = Level.objects.create(name='Beginner', description='Beginner level courses')
        self.level2 = Level.objects.create(name='Intermediate', description='Intermediate level courses')

        # Create courses
        self.course1 = Course.objects.create(
            title='Course 1',
            description='Course 1 description',
            level=self.level1,
            price=30.0,
            instructor=self.instructor
        )
        self.course2 = Course.objects.create(
            title='Course 2',
            description='Course 2 description',
            level=self.level2,
            price=50.0,
            instructor=self.instructor
        )

        # Enroll students
        Enrollment.objects.create(student=self.student1, course=self.course1)
        Enrollment.objects.create(student=self.student2, course=self.course1)

        # URLs
        self.list_create_url = reverse('course:level-list')
        self.detail_url = lambda pk: reverse('course:level-detail', kwargs={'pk': pk})

    def test_list_levels(self):
        """Test retrieving a list of levels."""
        response = self.client.get(self.list_create_url)
        levels = Level.objects.all()
        serializer = LevelSerializer(levels, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(len(response.data), 2)

    def test_student_count_in_level(self):
        """Test counting students enrolled in a level."""
        response = self.client.get(self.detail_url(self.level1.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check the student count in the response
        self.assertEqual(response.data['students'], 2)

    def test_create_level_as_instructor(self):
        """Test creating a level as an instructor."""
        self.client.force_authenticate(user=self.instructor)
        data = {
            'name': 'Advanced',
            'description': 'Advanced level courses'
        }

        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Level.objects.count(), 3)
        self.assertEqual(Level.objects.get(name='Advanced').description, 'Advanced level courses')

    def test_update_level_as_instructor(self):
        """Test updating a level as an instructor."""
        self.client.force_authenticate(user=self.instructor)
        data = {
            'name': 'Beginner Updated',
            'description': 'Updated description'
        }

        response = self.client.put(self.detail_url(self.level1.pk), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.level1.refresh_from_db()
        self.assertEqual(self.level1.name, 'Beginner Updated')

    def test_delete_level_as_instructor(self):
        """Test deleting a level as an instructor."""
        self.client.force_authenticate(user=self.instructor)
        response = self.client.delete(self.detail_url(self.level1.pk))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Level.objects.count(), 1)

    def test_level_student_count_logic(self):
        """Test logic for counting students in a level."""
        # Add another student to a different level
        Enrollment.objects.create(student=self.student1, course=self.course2)

        response = self.client.get(self.detail_url(self.level2.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Only one student is enrolled in level2 courses
        self.assertEqual(response.data['students'], 1)
