from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils.decorators import method_decorator
from .serializers import ChangePasswordSerializer, LogoutSerializer, RefreshTokenSerializer, UserSerializer, RegisterSerializer, LoginSerializer
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view


User = get_user_model()


# LoginView for JWT Authentication
@extend_schema(
    summary="User Login",
    description="Authenticate a user and return access and refresh tokens.",
    tags=["Authentication"]
)
@method_decorator(ratelimit(key='ip', rate='5/m', method='ALL'), name='dispatch')
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)

            profile_image_url = None
            if user.profile_image:
                profile_image_url = request.build_absolute_uri(user.profile_image.url)

            return Response({
                'status': 'success',
                'message': 'Login successful.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'profile_image': profile_image_url,
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
@extend_schema(
    summary="User Registration",
    description="Create a new user account.",
    examples=[
        OpenApiExample(
            "Successful Registration",
            value={
                'status': 'success',
                'message': 'User registered successfully.',
                'user': {
                    'id': 1,
                    'username': 'testuser',
                    'email': 'test@example.com',
                    'role': 'User',
                    'profile_image': 'http://example.com/media/uploads/user_profiles/testuser.jpg',
                },
                'tokens': {
                    'refresh': '...',
                    'access': '...'
                }
            }
        )
    ],
    tags=["Authentication"]
)
@method_decorator(ratelimit(key='ip', rate='5/m', method='ALL'), name='dispatch')
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            # Build the full URL for the profile image
            profile_image_url = None
            if user.profile_image:
                profile_image_url = request.build_absolute_uri(user.profile_image.url)

            return Response({
                'status': 'success',
                'message': 'User registered successfully.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'profile_image': profile_image_url,
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
@extend_schema(
    examples=[
        OpenApiExample(
            "Successful Response",
            value={"id": 1, "username": "user123", "email": "user@example.com", "profile_image": "http://example.com/media/uploads/user_profiles/testuser.jpg"}
        )
    ],
    tags=["User"]
)
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
@extend_schema(
    summary="Change Password",
    description="Allow authenticated users to change their password.",
    request=ChangePasswordSerializer,
    responses={
        200: {"description": "Password changed successfully."},
        400: {"description": "Validation error."},
    },
    tags=["User"],
)
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
@extend_schema(
    summary="User Logout",
    description="Blacklists the provided refresh token to log out the user.",
    request=LogoutSerializer,
    responses={
        205: {"description": "Successfully logged out."},
        400: {"description": "Invalid or missing refresh token."},
    },
    tags=["Authentication"],
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data.get("refresh")
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_205_RESET_CONTENT,
            )
        except TokenError:
            return Response(
                {"detail": "Invalid or already blacklisted token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

# List Users - Only Admins
@extend_schema(
    summary="List Users",
    description="Retrieve a list of all users. Only accessible to admins.",
    tags=["Admin"]
)
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
@extend_schema(
    summary="User Details",
    description="Retrieve details of a specific user by ID.",
    tags=["Admin"]
)
class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'pk'
    permission_classes = [permissions.AllowAny]


@extend_schema(
    summary="Refresh Access Token",
    description="Generates a new access token using the provided valid refresh token.",
    request=RefreshTokenSerializer,
    responses={
        status.HTTP_200_OK: {
            "type": "object",
            "properties": {
                "access": {"type": "string", "description": "The new access token."},
            },
        },
        status.HTTP_400_BAD_REQUEST: {
            "type": "object",
            "properties": {
                "detail": {"type": "string", "description": "Error message explaining why the request failed."},
            },
        },
    },
    tags=["Authentication"],
)
class RefreshTokenView(APIView):
    """
    Endpoint to refresh the access token using a valid refresh token.
    """
    serializer_class = RefreshTokenSerializer

    def post(self, request, *args, **kwargs):
        # Validate the incoming request data with the serializer
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data.get("refresh_token")

        try:
            # Use the provided refresh token to create a new access token
            token = RefreshToken(refresh_token)
            new_access_token = str(token.access_token)

            return Response({"access": new_access_token}, status=status.HTTP_200_OK)

        except Exception as e:
            # Handle any errors (invalid token or other issues)
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)