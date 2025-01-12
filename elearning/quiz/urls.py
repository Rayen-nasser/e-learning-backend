# urls.py
from django.urls import path, include
from rest_framework_nested import routers
from .views import QuizViewSet, SubmissionViewSet

app_name = 'quiz'

router = routers.SimpleRouter()
router.register(r'quizzes', QuizViewSet)

quiz_router = routers.NestedSimpleRouter(router, r'quizzes', lookup='quiz')
quiz_router.register(r'submissions', SubmissionViewSet, basename='quiz-submissions')

urlpatterns = [
    path('', include(quiz_router.urls)),
]