from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password


User = get_user_model()

# Serializer for user registration
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role']  # Add the missing comma here
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_password(self, value):
        # Use Django's built-in password validation
        validate_password(value)
        return value

    def create(self, validated_data):
        # Create a user instance with validated data
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
