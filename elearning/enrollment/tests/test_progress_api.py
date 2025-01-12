import datetime
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from core.models import Course, Enrollment
from decimal import Decimal

User = get_user_model()

class ProgressionTestCase(TestCase):
    """Test Progression"""
    def setUp(self):
        # Create test users
        self.student = User.objects.create_user(
            email='student@test.com',
            username='student',
            password='testpass123',
            role='Student'
        )
        self.instructor = User.objects.create_user(
            email='instructor@test.com',
            username='instructor',
            password='testpass123',
            role='Instructor'
        )

        # Create a test course
        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            category='Test Category',
            price=Decimal('99.99'),
            instructor=self.instructor
        )

        # Create a test enrollment
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            progress=0.0,
            completed=False
        )

        # Set up the API client
        self.client = APIClient()
