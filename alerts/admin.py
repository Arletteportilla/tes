from django.contrib import admin
from django.utils.html import format_html
from alerts.models import AlertType, Alert, UserAlert


@admin.register(AlertType)
class AlertTypeAdmin(admin.ModelAdmin):
    """Admin configuration for AlertType model"""
    
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'name', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """Admin configuration for Alert model"""
    
    list_display = [
        'title', 'alert_type', 'status', 'priority', 'scheduled_date', 
        'related_record', 'is_expired', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'alert_type', 'scheduled_date', 
        'created_at', 'expires_at'
    ]
    search_fields = ['title', 'message']
    readonly_fields = ['created_at', 'updated_at', 'is_expired']
    date_hierarchy = 'scheduled_date'
    ordering = ['-scheduled_date', '-created_at']
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('alert_type', 'title', 'message', 'status', 'priority')
        }),
        ('Scheduling', {
            'fields': ('scheduled_date', 'expires_at', 'is_expired')
        }),
        ('Related Records', {
            'fields': ('pollination_record', 'germination_record'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def related_record(self, obj):
        """Display related record information"""
        if obj.pollination_record:
            return format_html(
                '<a href="/admin/pollination/pollinationrecord/{}/change/">Polinización #{}</a>',
                obj.pollination_record.id,
                obj.pollination_record.id
            )
        elif obj.germination_record:
            return format_html(
                '<a href="/admin/germination/germinationrecord/{}/change/">Germinación #{}</a>',
                obj.germination_record.id,
                obj.germination_record.id
            )
        return '-'
    related_record.short_description = 'Registro Relacionado'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'alert_type', 'pollination_record', 'germination_record'
        )


@admin.register(UserAlert)
class UserAlertAdmin(admin.ModelAdmin):
    """Admin configuration for UserAlert model"""
    
    list_display = [
        'user', 'alert_title', 'alert_type', 'alert_priority', 
        'is_read', 'is_dismissed', 'read_at', 'created_at'
    ]
    list_filter = [
        'is_read', 'is_dismissed', 'alert__priority', 'alert__alert_type',
        'read_at', 'dismissed_at', 'created_at'
    ]
    search_fields = ['user__username', 'user__email', 'alert__title']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Alert', {
            'fields': ('user', 'alert')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'is_dismissed', 'dismissed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def alert_title(self, obj):
        """Display alert title"""
        return obj.alert.title
    alert_title.short_description = 'Título de Alerta'
    
    def alert_type(self, obj):
        """Display alert type"""
        return obj.alert.alert_type.get_name_display()
    alert_type.short_description = 'Tipo de Alerta'
    
    def alert_priority(self, obj):
        """Display alert priority with color coding"""
        priority = obj.alert.priority
        colors = {
            'urgent': '#dc3545',  # Red
            'high': '#fd7e14',    # Orange
            'medium': '#ffc107',  # Yellow
            'low': '#28a745'      # Green
        }
        color = colors.get(priority, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.alert.get_priority_display()
        )
    alert_priority.short_description = 'Prioridad'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'user', 'alert', 'alert__alert_type'
        )
    
    actions = ['mark_as_read', 'mark_as_dismissed']
    
    def mark_as_read(self, request, queryset):
        """Admin action to mark selected user alerts as read"""
        count = 0
        for user_alert in queryset:
            if not user_alert.is_read:
                user_alert.mark_as_read()
                count += 1
        
        self.message_user(
            request,
            f'{count} alertas marcadas como leídas.'
        )
    mark_as_read.short_description = 'Marcar como leídas'
    
    def mark_as_dismissed(self, request, queryset):
        """Admin action to mark selected user alerts as dismissed"""
        count = 0
        for user_alert in queryset:
            if not user_alert.is_dismissed:
                user_alert.mark_as_dismissed()
                count += 1
        
        self.message_user(
            request,
            f'{count} alertas marcadas como descartadas.'
        )
    mark_as_dismissed.short_description = 'Marcar como descartadas'
