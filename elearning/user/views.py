from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .serializers import ChangePasswordSerializer, UserSerializer, RegisterSerializer, LoginSerializer
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from django_ratelimit.decorators import ratelimit


User = get_user_model()


# LoginView for JWT Authentication
@method_decorator(ratelimit(key='ip', rate='5/m', method='ALL'), name='dispatch')
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'status': 'success',
                'message': 'Login successful.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        return Response({
            'status': 'error',
            'message': 'Login failed. Please check your credentials.',
            'errors': serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)


# RegisterView for User Registration
@method_decorator(ratelimit(key='ip', rate='5/m', method='ALL'), name='dispatch')
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'status': 'success',
                'message': 'User registered successfully.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        return Response({
            'status': 'error',
            'message': 'User registration failed.',
            'errors': serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)


# Profile View (GET & PUT & DELETE & PATCH)
class ProfileView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user  # Return the current logged-in user

    def perform_update(self, serializer):
        # Here, you could add logic to send an email or trigger any signal
        serializer.save()

    def delete(self, request, *args, **kwargs):
        """Delete the current authenticated user."""
        user = request.user
        user.delete()  # Delete the user from the database
        return Response({
            'detail': 'Account deleted successfully.'
        }, status=status.HTTP_204_NO_CONTENT)


# Change Password View
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']

            # Check if the old password is correct
            if not user.check_password(old_password):
                return Response({
                    'detail': 'Old password is incorrect.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Set the new password and save
            user.set_password(new_password)
            user.save()
            return Response({
                'detail': 'Password changed successfully.'
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Logout View
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get("refresh")

            if not refresh_token:
                return Response({
                    "detail": "Refresh token is required to log out."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Decode and blacklist the refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()  # Blacklist the token

            return Response({
                "detail": "Successfully logged out."
            }, status=status.HTTP_205_RESET_CONTENT)

        except TokenError:
            return Response({
                "detail": "Invalid token or token has already been blacklisted."
            }, status=status.HTTP_400_BAD_REQUEST)


# List Users - Only Admins
class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.user.role != 'Admin':
            return Response({
                "detail": "You do not have permission to perform this action."
            }, status=status.HTTP_403_FORBIDDEN)
        return super().get(request, *args, **kwargs)


# User Detail View
class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'pk'
    permission_classes = [permissions.AllowAny]
