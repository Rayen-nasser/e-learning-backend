from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Course, Lesson, Quiz, Question, Submission

def create_user(**params):
    """Helper function to create users."""
    defaults = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpass123',
        'first_name': 'Test',
        'last_name': 'User',
        'role': 'Student'
    }
    defaults.update(params)
    return get_user_model().objects.create_user(**defaults)

class SubmissionTests(TestCase):
    """Tests for the Submission model."""
    def setUp(self):
        self.user = create_user()
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
        # Create a Quiz
        self.quiz = Quiz.objects.create(
            title='Sample Quiz',
            description='This is a sample quiz.',
            lesson=self.lesson,
            time_limit=timedelta(minutes=30),
            is_active=True
        )
        self.question1 = Question.objects.create(
            question_text='What is 2+2?',
            quiz=self.quiz,
            options={"1": "2", "2": "3", "3": "4", "4": "5"},
            correct_option=3,
            points=2
        )
        self.question2 = Question.objects.create(
            question_text='Who is the current president of the United States?',
            quiz=self.quiz,
            options={"1": "George Washington", "2": "Thomas Jefferson", "3": "Abraham Lincoln", "4": "William Shakespeare"},
            correct_option=1,
            points=1
        )
        self.question3 = Question.objects.create(
            question_text='What is the capital of Moslimin?',
            quiz=self.quiz,
            options={"1": "Maka", "2": "Gods", "3": "Andalos", "4": "Sham"},
            correct_option=1,
            points=7
        )

    def test_student_can_submit_quiz(self):
        """Test that a student can submit a quiz"""
        self.client.force_authenticate(self.student)
        payload = {
            'student': self.student.id,
            'quiz': self.quiz.id,
            'score': 7
        }
        response = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['score'], 7)

    def test_submission_model_str(self):
        """Test the string representation of the Submission model"""
        submission = Submission.objects.create(
            student=self.student,
            quiz=self.quiz,
            score=7
        )
        expected_str = f"{self.student.username}'s submission for {self.quiz.title}"
        self.assertEqual(str(submission), expected_str)

    def test_student_cannot_submit_twice(self):
        """Test that a student cannot submit the same quiz twice"""
        self.client.force_authenticate(self.student)
        payload = {
            'student': self.student.id,
            'quiz': self.quiz.id,
            'score': 7
        }
        # First submission
        response1 = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            payload
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second submission attempt
        response2 = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            {'score': 8}
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_instructor_cannot_submit_quiz(self):
        """Test that an instructor cannot submit a quiz"""
        self.client.force_authenticate(self.instructor)
        response = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            {'score': 7}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_submission_score_validation(self):
        """Test that submission score cannot be negative"""
        self.client.force_authenticate(self.student)
        response = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            {'score': -5}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submission_with_inactive_quiz(self):
        """Test that submissions are not allowed for inactive quizzes"""
        self.quiz.is_active = False
        self.quiz.save()
        self.client.force_authenticate(self.student)
        response = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            {'score': 7}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_student_submissions(self):
        """Test retrieving all submissions for a student"""
        submission = Submission.objects.create(
            student=self.student,
            quiz=self.quiz,
            score=7
        )
        self.client.force_authenticate(self.student)
        response = self.client.get(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['score'], submission.score)

    def test_delete_submission_not_allowed(self):
        """Test that submissions cannot be deleted"""
        submission = Submission.objects.create(
            student=self.student,
            quiz=self.quiz,
            score=7
        )
        self.client.force_authenticate(self.student)
        response = self.client.delete(
            reverse('quiz:quiz-submissions-detail',
                   kwargs={'quiz_pk': self.quiz.id, 'pk': submission.id})
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)