from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from .models import Role, UserProfile

User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer for Role model.
    """
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions', 'is_active']
        read_only_fields = ['id']


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for UserProfile model.
    """
    class Meta:
        model = UserProfile
        fields = [
            'id', 'department', 'position', 'bio', 'avatar',
            'birth_date', 'address', 'emergency_contact_name',
            'emergency_contact_phone', 'preferences', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomUser model.
    """
    role = RoleSerializer(read_only=True)
    role_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    profile = UserProfileSerializer(read_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_id', 'employee_id', 'phone_number',
            'is_active', 'date_joined', 'profile', 'password', 'password_confirm'
        ]
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True},
            'password_confirm': {'write_only': True}
        }
    
    def validate(self, attrs):
        """
        Validate password confirmation.
        """
        if 'password' in attrs and 'password_confirm' in attrs:
            if attrs['password'] != attrs['password_confirm']:
                raise serializers.ValidationError("Las contraseñas no coinciden.")
        return attrs
    
    def validate_role_id(self, value):
        """
        Validate that the role exists.
        """
        if value is not None:
            try:
                Role.objects.get(id=value, is_active=True)
            except Role.DoesNotExist:
                raise serializers.ValidationError("El rol especificado no existe o no está activo.")
        return value
    
    def create(self, validated_data):
        """
        Create user with encrypted password.
        """
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        role_id = validated_data.pop('role_id', None)
        
        user = User.objects.create_user(password=password, **validated_data)
        
        if role_id:
            user.role_id = role_id
            user.save()
        
        return user
    
    def update(self, instance, validated_data):
        """
        Update user instance.
        """
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password', None)
        role_id = validated_data.pop('role_id', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        if role_id is not None:
            instance.role_id = role_id
        
        instance.save()
        return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes user information.
    """
    
    def validate(self, attrs):
        """
        Validate credentials and return tokens with user data.
        """
        data = super().validate(attrs)
        
        # Add user information to the response
        user_data = UserSerializer(self.user).data
        data['user'] = user_data
        
        return data
    
    @classmethod
    def get_token(cls, user):
        """
        Add custom claims to the token.
        """
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.get_role_name() if user.role else None
        token['employee_id'] = user.employee_id if user.employee_id else None
        
        return token


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, write_only=True)
    
    def validate(self, attrs):
        """
        Validate user credentials.
        """
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            
            if not user:
                raise serializers.ValidationError(
                    'No se pudo autenticar con las credenciales proporcionadas.'
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    'La cuenta de usuario está desactivada.'
                )
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(
                'Debe incluir "username" y "password".'
            )


class TokenRefreshSerializer(serializers.Serializer):
    """
    Serializer for token refresh.
    """
    refresh = serializers.CharField()
    
    def validate(self, attrs):
        """
        Validate refresh token and return new access token.
        """
        refresh_token = attrs['refresh']
        
        try:
            refresh = RefreshToken(refresh_token)
            data = {
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }
            
            # Add user information
            user = User.objects.get(id=refresh['user_id'])
            data['user'] = UserSerializer(user).data
            
            return data
        except Exception as e:
            raise serializers.ValidationError('Token de actualización inválido.')


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """
    old_password = serializers.CharField(max_length=128, write_only=True)
    new_password = serializers.CharField(max_length=128, write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(max_length=128, write_only=True, min_length=8)
    
    def validate_old_password(self, value):
        """
        Validate old password.
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('La contraseña actual es incorrecta.')
        return value
    
    def validate(self, attrs):
        """
        Validate new password confirmation.
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError('Las nuevas contraseñas no coinciden.')
        return attrs
    
    def save(self):
        """
        Save new password.
        """
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'employee_id', 'phone_number', 'password', 'password_confirm'
        ]
    
    def validate(self, attrs):
        """
        Validate password confirmation.
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Las contraseñas no coinciden.")
        return attrs
    
    def create(self, validated_data):
        """
        Create new user.
        """
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user