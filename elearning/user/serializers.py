from django.forms import ValidationError
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password


User = get_user_model()

# Serializer for user registration
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_password(self, value):
        try:
            # Validate the password using Django's built-in password validation
            validate_password(value)
        except ValidationError as e:
            # If validation fails, raise a serializers.ValidationError with the appropriate message
            raise serializers.ValidationError({"password": ", ".join(e.messages)})
        return value

    def validate_role(self, value):
        valid_roles = ['Student', 'Admin', 'Instructor']
        if value not in valid_roles:
            raise serializers.ValidationError("Invalid role")
        return value

    def create(self, validated_data):
        # Create user instance with validated data
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError(
                    {"detail": "Invalid email or password."}
                )
            if not user.is_active:
                raise serializers.ValidationError(
                    {"detail": "This account is inactive."}
                )
        else:
            raise serializers.ValidationError(
                {"detail": "Must include both email and password."}
            )

        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']  # Exclude 'role' if not updatable


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        # Ensure the new password is valid
        validate_password(value)
        return value

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True,
        help_text="The refresh token to blacklist during logout."
    )