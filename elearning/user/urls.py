from django.urls import path
from .views import ProfileView, RefreshTokenView, RegisterView, LoginView, ChangePasswordView, LogoutView, UserListView, UserDetailView

app_name = 'user'

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/token/refresh/', RefreshTokenView.as_view(), name='token_refresh'),

    # User management endpoints
    path('users/', UserListView.as_view(), name='users-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/password/', ChangePasswordView.as_view(), name='change-password'),  # PATCH for password change
    path('users/<int:pk>/profile/', ProfileView.as_view(), name='profile'),  # GET, PUT, DELETE for profile
]

