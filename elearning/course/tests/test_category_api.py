from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import Category, User
from course.serializers import CategorySerializer
import json

class CategoryAPITests(APITestCase):
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.client = APIClient()

        # Create instructor user
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role='Instructor'
        )

        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='user@test.com',
            password='testpass123',
            role='Student'
        )

        # Create some test categories
        self.category1 = Category.objects.create(
            name='Programming',
            description='Learn programming languages'
        )
        self.category2 = Category.objects.create(
            name='Design',
            description='Learn design principles'
        )

        # URLs
        self.list_create_url = reverse('course:category-list')
        self.detail_url = lambda pk: reverse('course:category-detail', kwargs={'pk': pk})

    def test_list_categories(self):
        """Test retrieving a list of categories"""
        response = self.client.get(self.list_create_url)
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(len(response.data), 2)

    def test_create_category_as_instructor(self):
        """Test creating a new category as instructor"""
        self.client.force_authenticate(user=self.instructor)
        data = {
            'name': 'Business',
            'description': 'Business courses'
        }

        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 3)
        self.assertEqual(Category.objects.get(name='Business').description, 'Business courses')

    def test_create_category_as_regular_user(self):
        """Test creating a category as regular user (should fail)"""
        self.client.force_authenticate(user=self.regular_user)
        data = {
            'name': 'Business',
            'description': 'Business courses'
        }

        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Category.objects.count(), 2)

    def test_create_category_unauthenticated(self):
        """Test creating a category without authentication (should fail)"""
        data = {
            'name': 'Business',
            'description': 'Business courses'
        }

        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Category.objects.count(), 2)

    def test_retrieve_category(self):
        """Test retrieving a single category"""
        response = self.client.get(self.detail_url(self.category1.pk))
        serializer = CategorySerializer(self.category1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_update_category_as_instructor(self):
        """Test updating a category as instructor"""
        self.client.force_authenticate(user=self.instructor)
        data = {
            'name': 'Programming Updated',
            'description': 'Updated description'
        }

        response = self.client.put(self.detail_url(self.category1.pk), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category1.refresh_from_db()
        self.assertEqual(self.category1.name, 'Programming Updated')

    def test_partial_update_category_as_instructor(self):
        """Test partially updating a category as instructor"""
        self.client.force_authenticate(user=self.instructor)
        data = {
            'description': 'Updated description only'
        }

        response = self.client.patch(self.detail_url(self.category1.pk), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category1.refresh_from_db()
        self.assertEqual(self.category1.description, 'Updated description only')
        self.assertEqual(self.category1.name, 'Programming')  # Name should remain unchanged

    def test_delete_category_as_instructor(self):
        """Test deleting a category as instructor"""
        self.client.force_authenticate(user=self.instructor)
        response = self.client.delete(self.detail_url(self.category1.pk))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Category.objects.count(), 1)

    def test_delete_category_as_regular_user(self):
        """Test deleting a category as regular user (should fail)"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.delete(self.detail_url(self.category1.pk))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Category.objects.count(), 2)

    def test_create_duplicate_category(self):
        """Test creating a category with duplicate name (should fail)"""
        self.client.force_authenticate(user=self.instructor)
        data = {
            'name': 'Programming',  # This name already exists
            'description': 'Another programming category'
        }

        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Category.objects.count(), 2)

    def test_create_category_without_name(self):
        """Test creating a category without name (should fail)"""
        self.client.force_authenticate(user=self.instructor)
        data = {
            'description': 'Category without name'
        }

        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_categories(self):
        """Test searching categories"""
        response = self.client.get(f"{self.list_create_url}?search=prog")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Programming')

    def test_category_name_max_length(self):
        """Test creating a category with name exceeding max length"""
        self.client.force_authenticate(user=self.instructor)
        data = {
            'name': 'a' * 256,  # Assuming max_length is 255
            'description': 'Test description'
        }

        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)