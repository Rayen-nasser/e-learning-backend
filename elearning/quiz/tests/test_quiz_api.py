from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Course, Lesson, Quiz, Question


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


def get_quiz_list_url(lesson_id):
    """Helper function to get the nested quizzes list URL."""
    return reverse('lesson:lesson-quizzes-list', args=[lesson_id])


def get_quiz_detail_url(lesson_id, quiz_id):
    """Helper function to get the nested quizzes detail URL."""
    return reverse('lesson:lesson-quizzes-detail', args=[lesson_id, quiz_id])


def get_question_list_url(lesson_id, quiz_id):
    """Helper function to get the nested questions list URL."""
    return reverse('lesson:quiz-quiz-questions-list', args=[lesson_id, quiz_id])


def get_question_detail_url(lesson_id, quiz_id, question_id):
    """Helper function to get the nested questions detail URL."""
    return reverse('lesson:quiz-quiz-questions-detail', args=[lesson_id, quiz_id, question_id])


class QuizAndQuestionTests(TestCase):
    """Tests for Quiz and Question models."""

    def setUp(self):
        self.client = APIClient()
        self.instructor = create_user(
            username='instructor',
            email='instructor@example.com',
            role='Instructor'
        )
        self.client.force_authenticate(self.instructor)
        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            instructor=self.instructor,
            price=99.99,
            category='Test Category'
        )
        self.lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Test Description',
            course=self.course,
        )
        # Create a student user
        self.student = create_user(
            username='student',
            email='student@example.com',
            role='Student'
        )

    def test_student_cannot_create_quiz(self):
        """Test that a student cannot create a quiz."""
        self.client.force_authenticate(self.student)
        payload = {
            'title': 'Sample Quiz',
            'description': 'This is a sample quiz.',
            'time_limit': timedelta(minutes=30),
            'lesson': self.lesson.id,
            'is_active': True
        }
        res = self.client.post(get_quiz_list_url(self.lesson.id), payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_create_question(self):
        """Test that a student cannot create a question."""
        quiz = Quiz.objects.create(
            title='Sample Quiz',
            description='This is a sample quiz.',
            lesson=self.lesson,
            time_limit=timedelta(minutes=30),
            is_active=True
        )
        self.client.force_authenticate(self.student)
        payload = {
            'question_text': 'What is 2+2?',
            'options': {"1": "2", "2": "3", "3": "4", "4": "5"},
            'correct_option': 3,
            'points': 5,
            'question_type': 'multiple_choice'
        }
        res = self.client.post(get_question_list_url(self.lesson.id, quiz.id), payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_instructor_can_create_quiz(self):
        """Test that an instructor can create a quiz."""
        self.client.force_authenticate(self.instructor)
        payload = {
            'title': 'Sample Quiz',
            'description': 'This is a sample quiz.',
            'time_limit': timedelta(minutes=30),
            'lesson': self.lesson.id,
            'is_active': True
        }
        res = self.client.post(get_quiz_list_url(self.lesson.id), payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_instructor_can_create_question(self):
        """Test that an instructor can create a question."""
        quiz = Quiz.objects.create(
            title='Sample Quiz',
            description='This is a sample quiz.',
            lesson=self.lesson,
            time_limit=timedelta(minutes=30),
            is_active=True
        )
        self.client.force_authenticate(self.instructor)
        payload = {
            'question_text': 'What is 2+2?',
            'options': {"1": "2", "2": "3", "3": "4", "4": "5"},
            'correct_option': 3,
            'points': 5,
            'question_type': 'multiple_choice'
        }
        res = self.client.post(get_question_list_url(self.lesson.id, quiz.id), payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_instructor_can_update_quiz(self):
        """Test that an instructor can update a quiz."""
        quiz = Quiz.objects.create(
            title='Sample Quiz',
            description='This is a sample quiz.',
            lesson=self.lesson,
            time_limit=timedelta(minutes=30),
            is_active=True
        )
        self.client.force_authenticate(self.instructor)
        payload = {'title': 'Updated Quiz Title'}
        res = self.client.patch(get_quiz_detail_url(self.lesson.id, quiz.id), payload)

        quiz.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(quiz.title, 'Updated Quiz Title')

    def test_student_cannot_update_quiz(self):
        """Test that a student cannot update a quiz."""
        quiz = Quiz.objects.create(
            title='Sample Quiz',
            description='This is a sample quiz.',
            lesson=self.lesson,
            time_limit=timedelta(minutes=30),
            is_active=True
        )
        self.client.force_authenticate(self.student)
        payload = {'title': 'Updated Quiz Title'}
        res = self.client.patch(get_quiz_detail_url(self.lesson.id, quiz.id), payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_instructor_can_update_question(self):
        """Test that an instructor can update a question."""
        quiz = Quiz.objects.create(
            title='Sample Quiz',
            description='This is a sample quiz.',
            lesson=self.lesson,
            time_limit=timedelta(minutes=30),
            is_active=True
        )
        question = Question.objects.create(
            quiz=quiz,
            question_text='What is 2+2?',
            options={"1": "2", "2": "3", "3": "4", "4": "5"},
            correct_option=3,
            points=5
        )
        self.client.force_authenticate(self.instructor)
        payload = {'question_text': 'Updated Question Text'}
        res = self.client.patch(get_question_detail_url(self.lesson.id, quiz.id, question.id), payload)

        question.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(question.question_text, 'Updated Question Text')

    def test_student_cannot_update_question(self):
        """Test that a student cannot update a question."""
        quiz = Quiz.objects.create(
            title='Sample Quiz',
            description='This is a sample quiz.',
            lesson=self.lesson,
            time_limit=timedelta(minutes=30),
            is_active=True
        )
        question = Question.objects.create(
            quiz=quiz,
            question_text='What is 2+2?',
            options={"1": "2", "2": "3", "3": "4", "4": "5"},
            correct_option=3,
            points=5
        )
        self.client.force_authenticate(self.student)
        payload = {'question_text': 'Updated Question Text'}
        res = self.client.patch(get_question_detail_url(self.lesson.id, quiz.id, question.id), payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
