from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from core.models import BaseModel


class Role(BaseModel):
    """
    Model to define user roles in the system.
    Each role has specific permissions stored as JSON.
    """
    ROLE_CHOICES = [
        ('Polinizador', 'Polinizador'),
        ('Germinador', 'Germinador'),
        ('Secretaria', 'Secretaria'),
        ('Administrador', 'Administrador'),
    ]
    
    name = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        unique=True,
        help_text="Nombre del rol en el sistema"
    )
    description = models.TextField(
        blank=True,
        help_text="Descripción detallada del rol y sus responsabilidades"
    )
    permissions = models.JSONField(
        default=dict,
        help_text="Permisos específicos del rol en formato JSON"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si el rol está activo en el sistema"
    )

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_default_permissions(self):
        """
        Returns default permissions for each role type.
        """
        default_permissions = {
            'Polinizador': {
                'modules': ['pollination'],
                'can_create': True,
                'can_read': True,
                'can_update': True,
                'can_delete': False,
                'can_generate_reports': False
            },
            'Germinador': {
                'modules': ['germination'],
                'can_create': True,
                'can_read': True,
                'can_update': True,
                'can_delete': False,
                'can_generate_reports': False
            },
            'Secretaria': {
                'modules': ['pollination', 'germination', 'alerts'],
                'can_create': True,
                'can_read': True,
                'can_update': True,
                'can_delete': False,
                'can_generate_reports': False
            },
            'Administrador': {
                'modules': ['pollination', 'germination', 'alerts', 'reports', 'authentication'],
                'can_create': True,
                'can_read': True,
                'can_update': True,
                'can_delete': True,
                'can_generate_reports': True
            }
        }
        return default_permissions.get(self.name, {})

    def save(self, *args, **kwargs):
        """
        Override save to set default permissions if not provided.
        """
        if not self.permissions:
            self.permissions = self.get_default_permissions()
        super().save(*args, **kwargs)


class CustomUser(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Adds role-based permissions and additional fields.
    """
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Rol asignado al usuario"
    )
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="Código de empleado único"
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="El número de teléfono debe tener entre 9 y 15 dígitos."
            )
        ],
        help_text="Número de teléfono del usuario"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si el usuario está activo en el sistema"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de creación del usuario"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Fecha de última actualización del usuario"
    )

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ['username']

    def __str__(self):
        return f"{self.username} - {self.get_full_name()}"

    def get_role_name(self):
        """
        Returns the name of the user's role.
        """
        return self.role.name if self.role else None

    def has_role(self, role_name):
        """
        Check if user has a specific role.
        """
        return self.role and self.role.name == role_name

    def has_module_permission(self, module_name):
        """
        Check if user has permission to access a specific module.
        """
        if self.is_superuser:
            return True
        
        if not self.role:
            return False
            
        return module_name in self.role.permissions.get('modules', [])

    def can_delete_records(self):
        """
        Check if user can delete records.
        """
        if self.is_superuser:
            return True
            
        if not self.role:
            return False
            
        return self.role.permissions.get('can_delete', False)

    def can_generate_reports(self):
        """
        Check if user can generate reports.
        """
        if self.is_superuser:
            return True
            
        if not self.role:
            return False
            
        return self.role.permissions.get('can_generate_reports', False)


class UserProfile(BaseModel):
    """
    Extended user profile with additional information.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile',
        help_text="Usuario asociado al perfil"
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        help_text="Departamento o área de trabajo"
    )
    position = models.CharField(
        max_length=100,
        blank=True,
        help_text="Cargo o posición en la organización"
    )
    bio = models.TextField(
        blank=True,
        help_text="Biografía o descripción del usuario"
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        help_text="Imagen de perfil del usuario"
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de nacimiento"
    )
    address = models.TextField(
        blank=True,
        help_text="Dirección del usuario"
    )
    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nombre del contacto de emergencia"
    )
    emergency_contact_phone = models.CharField(
        max_length=15,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="El número de teléfono debe tener entre 9 y 15 dígitos."
            )
        ],
        help_text="Teléfono del contacto de emergencia"
    )
    preferences = models.JSONField(
        default=dict,
        help_text="Preferencias del usuario en formato JSON"
    )

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        return f"Perfil de {self.user.username}"

    def get_full_profile_name(self):
        """
        Returns the full name with position if available.
        """
        full_name = self.user.get_full_name()
        if self.position:
            return f"{full_name} - {self.position}"
        return full_name
