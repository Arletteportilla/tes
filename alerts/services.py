from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from alerts.models import Alert, AlertType, UserAlert
from pollination.models import PollinationRecord
from germination.models import GerminationRecord

User = get_user_model()


class AlertGeneratorService:
    """
    Service class for generating automatic alerts based on pollination and germination records.
    Implements the business logic for creating different types of alerts.
    """
    
    @staticmethod
    def create_weekly_alert(record, record_type='pollination'):
        """
        Create a weekly alert one week after a record is created.
        
        Args:
            record: PollinationRecord or GerminationRecord instance
            record_type: 'pollination' or 'germination'
        """
        try:
            alert_type = AlertType.objects.get(name='semanal')
        except AlertType.DoesNotExist:
            # Create default alert type if it doesn't exist
            alert_type = AlertType.objects.create(
                name='semanal',
                description='Alerta semanal de seguimiento de registros'
            )
        
        # Calculate scheduled date (one week after record creation)
        scheduled_date = record.created_at + timedelta(days=7)
        
        if record_type == 'pollination':
            title = f"Seguimiento semanal - Polinización {record.pollination_type.name}"
            message = (
                f"Ha pasado una semana desde la polinización de {record.mother_plant.full_scientific_name} "
                f"realizada el {record.pollination_date}. "
                f"Fecha estimada de maduración: {record.estimated_maturation_date}"
            )
            
            alert = Alert.objects.create(
                alert_type=alert_type,
                title=title,
                message=message,
                scheduled_date=scheduled_date,
                priority='medium',
                pollination_record=record
            )
        else:  # germination
            title = f"Seguimiento semanal - Germinación {record.plant.full_scientific_name}"
            message = (
                f"Ha pasado una semana desde la germinación de {record.plant.full_scientific_name} "
                f"realizada el {record.germination_date}. "
                f"Fecha estimada de trasplante: {record.estimated_transplant_date}"
            )
            
            alert = Alert.objects.create(
                alert_type=alert_type,
                title=title,
                message=message,
                scheduled_date=scheduled_date,
                priority='medium',
                germination_record=record
            )
        
        # Create user alert for the responsible user
        UserAlert.objects.create(
            user=record.responsible,
            alert=alert
        )
        
        return alert
    
    @staticmethod
    def create_preventive_alert(record, record_type='pollination'):
        """
        Create a preventive alert one week before the estimated date.
        
        Args:
            record: PollinationRecord or GerminationRecord instance
            record_type: 'pollination' or 'germination'
        """
        try:
            alert_type = AlertType.objects.get(name='preventiva')
        except AlertType.DoesNotExist:
            # Create default alert type if it doesn't exist
            alert_type = AlertType.objects.create(
                name='preventiva',
                description='Alerta preventiva antes de fechas importantes'
            )
        
        if record_type == 'pollination':
            if not record.estimated_maturation_date:
                return None
                
            # Calculate scheduled date (one week before estimated maturation)
            scheduled_date = timezone.make_aware(
                timezone.datetime.combine(
                    record.estimated_maturation_date - timedelta(days=7),
                    timezone.datetime.min.time()
                )
            )
            
            title = f"Alerta preventiva - Maduración próxima"
            message = (
                f"La polinización de {record.mother_plant.full_scientific_name} "
                f"está próxima a madurar. Fecha estimada: {record.estimated_maturation_date}. "
                f"Prepare los materiales necesarios para la cosecha."
            )
            
            alert = Alert.objects.create(
                alert_type=alert_type,
                title=title,
                message=message,
                scheduled_date=scheduled_date,
                priority='high',
                pollination_record=record
            )
        else:  # germination
            if not record.estimated_transplant_date:
                return None
                
            # Calculate scheduled date (one week before estimated transplant)
            scheduled_date = timezone.make_aware(
                timezone.datetime.combine(
                    record.estimated_transplant_date - timedelta(days=7),
                    timezone.datetime.min.time()
                )
            )
            
            title = f"Alerta preventiva - Trasplante próximo"
            message = (
                f"Las plántulas de {record.plant.full_scientific_name} "
                f"están próximas para trasplante. Fecha estimada: {record.estimated_transplant_date}. "
                f"Prepare los contenedores y sustrato necesarios."
            )
            
            alert = Alert.objects.create(
                alert_type=alert_type,
                title=title,
                message=message,
                scheduled_date=scheduled_date,
                priority='high',
                germination_record=record
            )
        
        # Create user alert for the responsible user
        UserAlert.objects.create(
            user=record.responsible,
            alert=alert
        )
        
        return alert
    
    @staticmethod
    def create_frequent_alerts(record, record_type='pollination'):
        """
        Create frequent alerts during the week of the estimated date.
        
        Args:
            record: PollinationRecord or GerminationRecord instance
            record_type: 'pollination' or 'germination'
        """
        try:
            alert_type = AlertType.objects.get(name='frecuente')
        except AlertType.DoesNotExist:
            # Create default alert type if it doesn't exist
            alert_type = AlertType.objects.create(
                name='frecuente',
                description='Alertas frecuentes durante fechas críticas'
            )
        
        alerts_created = []
        
        if record_type == 'pollination':
            if not record.estimated_maturation_date:
                return alerts_created
                
            estimated_date = record.estimated_maturation_date
            base_title = "Recordatorio diario - Maduración"
            base_message = f"Revise el estado de maduración de {record.mother_plant.full_scientific_name}"
            
        else:  # germination
            if not record.estimated_transplant_date:
                return alerts_created
                
            estimated_date = record.estimated_transplant_date
            base_title = "Recordatorio diario - Trasplante"
            base_message = f"Revise el estado de las plántulas de {record.plant.full_scientific_name}"
        
        # Create daily alerts for the week of the estimated date
        for days_offset in range(-3, 4):  # 3 days before to 3 days after
            alert_date = estimated_date + timedelta(days=days_offset)
            scheduled_datetime = timezone.make_aware(
                timezone.datetime.combine(alert_date, timezone.datetime.min.time().replace(hour=9))
            )
            
            if days_offset == 0:
                title = f"{base_title} - ¡HOY ES EL DÍA!"
                priority = 'urgent'
            elif days_offset < 0:
                title = f"{base_title} - Faltan {abs(days_offset)} días"
                priority = 'high'
            else:
                title = f"{base_title} - {days_offset} días de retraso"
                priority = 'urgent'
            
            message = f"{base_message}. Fecha estimada: {estimated_date}"
            
            if record_type == 'pollination':
                alert = Alert.objects.create(
                    alert_type=alert_type,
                    title=title,
                    message=message,
                    scheduled_date=scheduled_datetime,
                    priority=priority,
                    pollination_record=record
                )
            else:
                alert = Alert.objects.create(
                    alert_type=alert_type,
                    title=title,
                    message=message,
                    scheduled_date=scheduled_datetime,
                    priority=priority,
                    germination_record=record
                )
            
            # Create user alert for the responsible user
            UserAlert.objects.create(
                user=record.responsible,
                alert=alert
            )
            
            alerts_created.append(alert)
        
        return alerts_created
    
    @staticmethod
    def generate_all_alerts_for_record(record, record_type='pollination'):
        """
        Generate all types of alerts for a given record.
        
        Args:
            record: PollinationRecord or GerminationRecord instance
            record_type: 'pollination' or 'germination'
        """
        alerts_created = []
        
        # Create weekly alert
        weekly_alert = AlertGeneratorService.create_weekly_alert(record, record_type)
        if weekly_alert:
            alerts_created.append(weekly_alert)
        
        # Create preventive alert
        preventive_alert = AlertGeneratorService.create_preventive_alert(record, record_type)
        if preventive_alert:
            alerts_created.append(preventive_alert)
        
        # Create frequent alerts
        frequent_alerts = AlertGeneratorService.create_frequent_alerts(record, record_type)
        alerts_created.extend(frequent_alerts)
        
        return alerts_created
    
    @staticmethod
    def cleanup_expired_alerts():
        """
        Clean up expired alerts that are no longer relevant.
        This method should be called periodically via a cron job.
        """
        now = timezone.now()
        
        # Mark expired alerts as dismissed
        expired_alerts = Alert.objects.filter(
            expires_at__lt=now,
            status='pending'
        )
        
        for alert in expired_alerts:
            alert.mark_as_dismissed()
        
        return expired_alerts.count()
    
    @staticmethod
    def get_pending_alerts_for_user(user):
        """
        Get all pending alerts for a specific user.
        
        Args:
            user: User instance
            
        Returns:
            QuerySet of UserAlert instances
        """
        return UserAlert.objects.filter(
            user=user,
            is_read=False,
            is_dismissed=False,
            alert__status='pending'
        ).select_related('alert', 'alert__alert_type')
    
    @staticmethod
    def get_alerts_due_today():
        """
        Get all alerts that are scheduled for today.
        
        Returns:
            QuerySet of Alert instances
        """
        today = timezone.now().date()
        return Alert.objects.filter(
            scheduled_date__date=today,
            status='pending'
        ).select_related('alert_type')


class NotificationService:
    """
    Service class for handling in-app notifications.
    Provides methods for retrieving and managing user notifications.
    """
    
    @staticmethod
    def get_user_notifications(user, limit=None, unread_only=False):
        """
        Get notifications for a specific user.
        
        Args:
            user: User instance
            limit: Maximum number of notifications to return
            unread_only: If True, only return unread notifications
            
        Returns:
            QuerySet of UserAlert instances
        """
        queryset = UserAlert.objects.filter(user=user).select_related(
            'alert', 'alert__alert_type', 'alert__pollination_record', 'alert__germination_record'
        ).order_by('-alert__scheduled_date', '-alert__created_at')
        
        if unread_only:
            queryset = queryset.filter(is_read=False, is_dismissed=False)
        
        if limit:
            queryset = queryset[:limit]
            
        return queryset
    
    @staticmethod
    def get_notification_summary(user):
        """
        Get a summary of notifications for a user.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with notification counts and summary
        """
        user_alerts = UserAlert.objects.filter(user=user)
        
        total_count = user_alerts.count()
        unread_count = user_alerts.filter(is_read=False, is_dismissed=False).count()
        urgent_count = user_alerts.filter(
            is_read=False, 
            is_dismissed=False,
            alert__priority='urgent'
        ).count()
        high_priority_count = user_alerts.filter(
            is_read=False, 
            is_dismissed=False,
            alert__priority='high'
        ).count()
        
        # Get recent notifications (last 7 days)
        from django.utils import timezone
        from datetime import timedelta
        
        recent_cutoff = timezone.now() - timedelta(days=7)
        recent_count = user_alerts.filter(
            alert__created_at__gte=recent_cutoff
        ).count()
        
        return {
            'total_notifications': total_count,
            'unread_notifications': unread_count,
            'urgent_notifications': urgent_count,
            'high_priority_notifications': high_priority_count,
            'recent_notifications': recent_count,
            'has_urgent': urgent_count > 0,
            'has_unread': unread_count > 0
        }
    
    @staticmethod
    def mark_notification_as_read(user, alert_id):
        """
        Mark a specific notification as read for a user.
        
        Args:
            user: User instance
            alert_id: ID of the alert to mark as read
            
        Returns:
            Boolean indicating success
        """
        try:
            user_alert = UserAlert.objects.get(user=user, alert_id=alert_id)
            user_alert.mark_as_read()
            return True
        except UserAlert.DoesNotExist:
            return False
    
    @staticmethod
    def mark_notification_as_dismissed(user, alert_id):
        """
        Mark a specific notification as dismissed for a user.
        
        Args:
            user: User instance
            alert_id: ID of the alert to mark as dismissed
            
        Returns:
            Boolean indicating success
        """
        try:
            user_alert = UserAlert.objects.get(user=user, alert_id=alert_id)
            user_alert.mark_as_dismissed()
            return True
        except UserAlert.DoesNotExist:
            return False
    
    @staticmethod
    def mark_all_notifications_as_read(user):
        """
        Mark all notifications as read for a user.
        
        Args:
            user: User instance
            
        Returns:
            Number of notifications marked as read
        """
        unread_alerts = UserAlert.objects.filter(
            user=user, 
            is_read=False
        )
        
        count = 0
        for user_alert in unread_alerts:
            user_alert.mark_as_read()
            count += 1
            
        return count
    
    @staticmethod
    def get_notifications_by_type(user, alert_type_name):
        """
        Get notifications of a specific type for a user.
        
        Args:
            user: User instance
            alert_type_name: Name of the alert type ('semanal', 'preventiva', 'frecuente')
            
        Returns:
            QuerySet of UserAlert instances
        """
        return UserAlert.objects.filter(
            user=user,
            alert__alert_type__name=alert_type_name
        ).select_related('alert', 'alert__alert_type').order_by('-alert__scheduled_date')
    
    @staticmethod
    def get_notifications_by_priority(user, priority):
        """
        Get notifications of a specific priority for a user.
        
        Args:
            user: User instance
            priority: Priority level ('low', 'medium', 'high', 'urgent')
            
        Returns:
            QuerySet of UserAlert instances
        """
        return UserAlert.objects.filter(
            user=user,
            alert__priority=priority,
            is_dismissed=False
        ).select_related('alert', 'alert__alert_type').order_by('-alert__scheduled_date')
    
    @staticmethod
    def cleanup_old_notifications(user, days_old=30):
        """
        Clean up old notifications for a user.
        
        Args:
            user: User instance
            days_old: Number of days after which to clean up notifications
            
        Returns:
            Number of notifications cleaned up
        """
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days_old)
        
        old_notifications = UserAlert.objects.filter(
            user=user,
            created_at__lt=cutoff_date,
            is_read=True
        )
        
        count = old_notifications.count()
        old_notifications.delete()
        
        return count