from django.db import models
from django.conf import settings
from core.models import BaseModel


class AlertType(BaseModel):
    """
    Model to define different types of alerts in the system.
    Types include: semanal, preventiva, frecuente
    """
    TYPE_CHOICES = [
        ('semanal', 'Semanal'),
        ('preventiva', 'Preventiva'),
        ('frecuente', 'Frecuente'),
    ]
    
    name = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        unique=True,
        help_text="Tipo de alerta en el sistema"
    )
    description = models.TextField(
        help_text="Descripción detallada del tipo de alerta"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si el tipo de alerta está activo"
    )
    
    class Meta:
        verbose_name = "Tipo de Alerta"
        verbose_name_plural = "Tipos de Alerta"
        ordering = ['name']
    
    def __str__(self):
        return self.get_name_display()


class Alert(BaseModel):
    """
    Model for alerts generated automatically in the system.
    Alerts are created based on pollination and germination records.
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('read', 'Leída'),
        ('dismissed', 'Descartada'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ]
    
    alert_type = models.ForeignKey(
        AlertType,
        on_delete=models.CASCADE,
        related_name='alerts',
        help_text="Tipo de alerta"
    )
    title = models.CharField(
        max_length=200,
        help_text="Título de la alerta"
    )
    message = models.TextField(
        help_text="Mensaje detallado de la alerta"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Estado actual de la alerta"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text="Prioridad de la alerta"
    )
    scheduled_date = models.DateTimeField(
        help_text="Fecha programada para mostrar la alerta"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de expiración de la alerta"
    )
    
    # References to related records
    pollination_record = models.ForeignKey(
        'pollination.PollinationRecord',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts',
        help_text="Registro de polinización relacionado"
    )
    germination_record = models.ForeignKey(
        'germination.GerminationRecord',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts',
        help_text="Registro de germinación relacionado"
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadatos adicionales de la alerta en formato JSON"
    )
    
    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ['-scheduled_date', '-priority']
        indexes = [
            models.Index(fields=['status', 'scheduled_date']),
            models.Index(fields=['alert_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    def is_expired(self):
        """
        Check if the alert has expired.
        """
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def mark_as_read(self):
        """
        Mark the alert as read.
        """
        self.status = 'read'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_as_dismissed(self):
        """
        Mark the alert as dismissed.
        """
        self.status = 'dismissed'
        self.save(update_fields=['status', 'updated_at'])


class UserAlert(BaseModel):
    """
    Model to manage the relationship between users and alerts.
    Allows for user-specific alert management and tracking.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_alerts',
        help_text="Usuario que recibe la alerta"
    )
    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name='user_alerts',
        help_text="Alerta asignada al usuario"
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Indica si el usuario ha leído la alerta"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora en que se leyó la alerta"
    )
    is_dismissed = models.BooleanField(
        default=False,
        help_text="Indica si el usuario ha descartado la alerta"
    )
    dismissed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora en que se descartó la alerta"
    )
    
    class Meta:
        verbose_name = "Alerta de Usuario"
        verbose_name_plural = "Alertas de Usuario"
        unique_together = ['user', 'alert']
        ordering = ['-alert__scheduled_date']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'is_dismissed']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.alert.title}"
    
    def mark_as_read(self):
        """
        Mark the user alert as read and update timestamp.
        """
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])
            
            # Also update the main alert status if needed
            self.alert.mark_as_read()
    
    def mark_as_dismissed(self):
        """
        Mark the user alert as dismissed and update timestamp.
        """
        if not self.is_dismissed:
            from django.utils import timezone
            self.is_dismissed = True
            self.dismissed_at = timezone.now()
            self.save(update_fields=['is_dismissed', 'dismissed_at', 'updated_at'])
            
            # Also update the main alert status if needed
            self.alert.mark_as_dismissed()
