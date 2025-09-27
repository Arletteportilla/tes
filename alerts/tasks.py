from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from alerts.services import AlertGeneratorService
from alerts.models import Alert, UserAlert
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_alerts():
    """
    Celery task to clean up expired alerts.
    This task should be run periodically (e.g., daily).
    """
    try:
        expired_count = AlertGeneratorService.cleanup_expired_alerts()
        logger.info(f"Cleaned up {expired_count} expired alerts")
        return f"Successfully cleaned up {expired_count} expired alerts"
    except Exception as e:
        logger.error(f"Error cleaning up expired alerts: {str(e)}")
        raise


@shared_task
def process_due_alerts():
    """
    Celery task to process alerts that are due today.
    This task should be run multiple times per day (e.g., every hour).
    """
    try:
        due_alerts = AlertGeneratorService.get_alerts_due_today()
        processed_count = 0
        
        for alert in due_alerts:
            # Here you could add additional processing logic
            # For example, sending email notifications, push notifications, etc.
            logger.info(f"Processing due alert: {alert.title}")
            processed_count += 1
        
        logger.info(f"Processed {processed_count} due alerts")
        return f"Successfully processed {processed_count} due alerts"
    except Exception as e:
        logger.error(f"Error processing due alerts: {str(e)}")
        raise


@shared_task
def generate_missing_alerts():
    """
    Celery task to generate missing alerts for existing records.
    This is useful for backfilling alerts or handling edge cases.
    """
    try:
        from pollination.models import PollinationRecord
        from germination.models import GerminationRecord
        
        generated_count = 0
        
        # Check for pollination records without alerts
        pollination_records_without_alerts = PollinationRecord.objects.filter(
            alerts__isnull=True
        ).distinct()
        
        for record in pollination_records_without_alerts:
            alerts = AlertGeneratorService.generate_all_alerts_for_record(
                record=record,
                record_type='pollination'
            )
            generated_count += len(alerts)
            logger.info(f"Generated {len(alerts)} alerts for pollination record {record.id}")
        
        # Check for germination records without alerts
        germination_records_without_alerts = GerminationRecord.objects.filter(
            alerts__isnull=True
        ).distinct()
        
        for record in germination_records_without_alerts:
            alerts = AlertGeneratorService.generate_all_alerts_for_record(
                record=record,
                record_type='germination'
            )
            generated_count += len(alerts)
            logger.info(f"Generated {len(alerts)} alerts for germination record {record.id}")
        
        logger.info(f"Generated {generated_count} missing alerts")
        return f"Successfully generated {generated_count} missing alerts"
    except Exception as e:
        logger.error(f"Error generating missing alerts: {str(e)}")
        raise


@shared_task
def send_daily_alert_summary(user_id):
    """
    Celery task to send daily alert summary to a specific user.
    
    Args:
        user_id: ID of the user to send the summary to
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.get(id=user_id)
        pending_alerts = AlertGeneratorService.get_pending_alerts_for_user(user)
        
        if pending_alerts.exists():
            # Here you would implement the actual notification sending
            # For now, we'll just log the summary
            alert_count = pending_alerts.count()
            high_priority_count = pending_alerts.filter(alert__priority='high').count()
            urgent_count = pending_alerts.filter(alert__priority='urgent').count()
            
            logger.info(
                f"Daily summary for {user.username}: "
                f"{alert_count} pending alerts "
                f"({urgent_count} urgent, {high_priority_count} high priority)"
            )
            
            return f"Sent daily summary to {user.username}: {alert_count} alerts"
        else:
            logger.info(f"No pending alerts for {user.username}")
            return f"No pending alerts for {user.username}"
            
    except Exception as e:
        logger.error(f"Error sending daily alert summary to user {user_id}: {str(e)}")
        raise


@shared_task
def auto_dismiss_old_alerts():
    """
    Celery task to automatically dismiss very old alerts that are no longer relevant.
    This helps keep the alert system clean and focused on current issues.
    """
    try:
        # Auto-dismiss alerts older than 30 days that are still pending
        cutoff_date = timezone.now() - timedelta(days=30)
        
        old_alerts = Alert.objects.filter(
            created_at__lt=cutoff_date,
            status='pending'
        )
        
        dismissed_count = 0
        for alert in old_alerts:
            alert.mark_as_dismissed()
            dismissed_count += 1
        
        logger.info(f"Auto-dismissed {dismissed_count} old alerts")
        return f"Successfully auto-dismissed {dismissed_count} old alerts"
    except Exception as e:
        logger.error(f"Error auto-dismissing old alerts: {str(e)}")
        raise


@shared_task
def generate_alert_statistics():
    """
    Celery task to generate statistics about alert usage and effectiveness.
    This can be used for monitoring and improving the alert system.
    """
    try:
        from django.db.models import Count, Q
        
        # Calculate various statistics
        total_alerts = Alert.objects.count()
        pending_alerts = Alert.objects.filter(status='pending').count()
        read_alerts = Alert.objects.filter(status='read').count()
        dismissed_alerts = Alert.objects.filter(status='dismissed').count()
        
        # Alert type distribution
        alert_type_stats = Alert.objects.values('alert_type__name').annotate(
            count=Count('id')
        )
        
        # Priority distribution
        priority_stats = Alert.objects.values('priority').annotate(
            count=Count('id')
        )
        
        # User engagement stats
        user_alert_stats = UserAlert.objects.values('user__username').annotate(
            total_alerts=Count('id'),
            read_alerts=Count('id', filter=Q(is_read=True)),
            dismissed_alerts=Count('id', filter=Q(is_dismissed=True))
        )
        
        stats = {
            'total_alerts': total_alerts,
            'pending_alerts': pending_alerts,
            'read_alerts': read_alerts,
            'dismissed_alerts': dismissed_alerts,
            'alert_type_distribution': list(alert_type_stats),
            'priority_distribution': list(priority_stats),
            'user_engagement': list(user_alert_stats)
        }
        
        logger.info(f"Generated alert statistics: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Error generating alert statistics: {str(e)}")
        raise