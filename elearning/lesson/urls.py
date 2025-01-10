from django.urls import path, include
from rest_framework_nested.routers import DefaultRouter, NestedDefaultRouter
from lesson.views import LessonViewSet
from quiz.views import QuizViewSet, QuestionViewSet

app_name = 'lesson'

# Base router
router = DefaultRouter()
router.register(r'lessons', LessonViewSet)

# Nested router for quizzes under lessons
lesson_router = NestedDefaultRouter(router, r'lessons', lookup='lesson')
lesson_router.register(r'quizzes', QuizViewSet, basename='lesson-quizzes')

# Nested router for questions under quizzes
quiz_router = NestedDefaultRouter(lesson_router, r'quizzes', lookup='quiz')
quiz_router.register(r'questions', QuestionViewSet, basename='quiz-quiz-questions')

urlpatterns = [
    path('', include(lesson_router.urls)),  # Nested quiz routes
    path('', include(quiz_router.urls)),    # Nested question routes
]
