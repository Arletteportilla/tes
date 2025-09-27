from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Role, UserProfile


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Admin configuration for Role model.
    """
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['name', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Permisos', {
            'fields': ('permissions',),
            'classes': ('collapse',)
        }),
        ('Información de Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class UserProfileInline(admin.StackedInline):
    """
    Inline admin for UserProfile.
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil'
    fields = [
        'department', 'position', 'bio', 'avatar',
        'birth_date', 'address', 'emergency_contact_name',
        'emergency_contact_phone', 'preferences'
    ]


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin configuration for CustomUser model.
    """
    inlines = [UserProfileInline]
    
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'role', 'employee_id', 'is_active', 'date_joined'
    ]
    list_filter = [
        'role', 'is_active', 'is_staff', 'is_superuser',
        'date_joined', 'last_login'
    ]
    search_fields = [
        'username', 'first_name', 'last_name', 'email',
        'employee_id', 'phone_number'
    ]
    ordering = ['username']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('role', 'employee_id', 'phone_number')
        }),
        ('Información de Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('role', 'employee_id', 'phone_number', 'email')
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for UserProfile model.
    """
    list_display = [
        'user', 'department', 'position', 'created_at'
    ]
    list_filter = ['department', 'position', 'created_at']
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'department', 'position'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Información Profesional', {
            'fields': ('department', 'position', 'bio', 'avatar')
        }),
        ('Información Personal', {
            'fields': ('birth_date', 'address'),
            'classes': ('collapse',)
        }),
        ('Contacto de Emergencia', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone'),
            'classes': ('collapse',)
        }),
        ('Preferencias', {
            'fields': ('preferences',),
            'classes': ('collapse',)
        }),
        ('Información de Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
