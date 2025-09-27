import factory
from django.contrib.auth import get_user_model
from authentication.models import Role, UserProfile

User = get_user_model()


class RoleFactory(factory.django.DjangoModelFactory):
    """Factory for Role model."""
    
    class Meta:
        model = Role
        django_get_or_create = ('name',)
    
    name = factory.Iterator(['Polinizador', 'Germinador', 'Secretaria', 'Administrador'])
    description = factory.LazyAttribute(lambda obj: f"Rol de {obj.name} en el sistema")
    is_active = True
    
    @factory.post_generation
    def set_permissions(obj, create, extracted, **kwargs):
        """Set default permissions based on role name."""
        if not create:
            return
        
        if not obj.permissions:
            obj.permissions = obj.get_default_permissions()
            obj.save()


class CustomUserFactory(factory.django.DjangoModelFactory):
    """Factory for CustomUser model."""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    employee_id = factory.Sequence(lambda n: f"EMP{n:04d}")
    phone_number = factory.Faker('phone_number')
    is_active = True
    role = factory.SubFactory(RoleFactory)
    
    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Set password for the user."""
        if not create:
            return
        
        password = extracted or 'testpass123'
        obj.set_password(password)
        obj.save()


class PolinizadorUserFactory(CustomUserFactory):
    """Factory for Polinizador users."""
    role = factory.SubFactory(RoleFactory, name='Polinizador')


class GerminadorUserFactory(CustomUserFactory):
    """Factory for Germinador users."""
    role = factory.SubFactory(RoleFactory, name='Germinador')


class SecretariaUserFactory(CustomUserFactory):
    """Factory for Secretaria users."""
    role = factory.SubFactory(RoleFactory, name='Secretaria')


class AdministradorUserFactory(CustomUserFactory):
    """Factory for Administrador users."""
    role = factory.SubFactory(RoleFactory, name='Administrador')


class UserProfileFactory(factory.django.DjangoModelFactory):
    """Factory for UserProfile model."""
    
    class Meta:
        model = UserProfile
    
    user = factory.SubFactory(CustomUserFactory)
    department = factory.Faker('company')
    position = factory.Faker('job')
    bio = factory.Faker('text', max_nb_chars=200)
    birth_date = factory.Faker('date_of_birth', minimum_age=18, maximum_age=65)
    address = factory.Faker('address')
    emergency_contact_name = factory.Faker('name')
    emergency_contact_phone = factory.Faker('phone_number')
    preferences = factory.LazyFunction(lambda: {
        'language': 'es',
        'notifications': True,
        'theme': 'light'
    })