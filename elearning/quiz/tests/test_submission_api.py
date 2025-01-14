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
        'profile_image': 'http://example.com/media/uploads/user_profiles/testuser.jpg',
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
        self.student = create_user(
            username='student',
            email='student@example.com',
            role='Student'
        )
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
            question_text='Who is the current president?',
            quiz=self.quiz,
            options={"1": "Washington", "2": "Jefferson", "3": "Lincoln", "4": "Shakespeare"},
            correct_option=1,
            points=1
        )
        self.question3 = Question.objects.create(
            question_text='What is the capital?',
            quiz=self.quiz,
            options={"1": "Maka", "2": "Gods", "3": "Andalos", "4": "Sham"},
            correct_option=1,
            points=7
        )

        # Standard valid payload that most tests can use
        self.valid_payload = {
            'student': self.student.id,
            'quiz': self.quiz.id,
            'answers': [
                {'question': self.question1.id, 'selected_option': 3},
                {'question': self.question2.id, 'selected_option': 1},
                {'question': self.question3.id, 'selected_option': 1}
            ]
        }

    def test_successful_submission(self):
        """Test successful quiz submission with correct answers"""
        self.client.force_authenticate(self.student)
        response = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            self.valid_payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['score'], 10)  # 2 + 1 + 7 points
        self.assertEqual(len(response.data['answers']), 3)

    def test_student_cannot_submit_twice(self):
        """Test that a student cannot submit the same quiz twice"""
        self.client.force_authenticate(self.student)

        # First submission
        response1 = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            self.valid_payload,
            format='json'
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second submission attempt
        response2 = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            self.valid_payload,
            format='json'
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response2.data['error'], "You have already submitted this quiz")

    def test_submission_with_missing_answers(self):
        """Test submission with missing answers"""
        self.client.force_authenticate(self.student)
        payload = {
            'answers': [
                {'question': self.question1.id, 'selected_option': 3},
                {'question': self.question2.id, 'selected_option': 1}
                # Missing question3
            ]
        }
        response = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("All questions must be answered", str(response.data))

    def test_submission_with_invalid_options(self):
        """Test submission with invalid answer options"""
        self.client.force_authenticate(self.student)
        payload = {
            'answers': [
                {'question': self.question1.id, 'selected_option': 5},  # Invalid option
                {'question': self.question2.id, 'selected_option': 1},
                {'question': self.question3.id, 'selected_option': 1}
            ]
        }
        response = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid option selected", str(response.data))

    def test_instructor_cannot_submit_quiz(self):
        """Test that an instructor cannot submit a quiz"""
        self.client.force_authenticate(self.instructor)
        response = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            self.valid_payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_submission_with_inactive_quiz(self):
        """Test that submissions are not allowed for inactive quizzes"""
        self.quiz.is_active = False
        self.quiz.save()
        self.client.force_authenticate(self.student)
        response = self.client.post(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id}),
            self.valid_payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "This quiz is no longer active")

    def test_get_student_submissions(self):
        """Test retrieving all submissions for a student"""
        submission = Submission.objects.create(
            student=self.student,
            quiz=self.quiz,
            score=10,
            answers=self.valid_payload['answers']
        )
        self.client.force_authenticate(self.student)
        response = self.client.get(
            reverse('quiz:quiz-submissions-list', kwargs={'quiz_pk': self.quiz.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['score'], submission.score)
        self.assertEqual(len(response.data[0]['answers']), 3)
