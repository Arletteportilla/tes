from django.db.models.signals import post_save
from django.dispatch import receiver
from pollination.models import PollinationRecord
from germination.models import GerminationRecord
from alerts.services import AlertGeneratorService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PollinationRecord)
def create_pollination_alerts(sender, instance, created, **kwargs):
    """
    Signal handler to create alerts when a new pollination record is created.
    
    Args:
        sender: The model class (PollinationRecord)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    if created:
        try:
            # Generate all types of alerts for the new pollination record
            alerts = AlertGeneratorService.generate_all_alerts_for_record(
                record=instance,
                record_type='pollination'
            )
            
            logger.info(
                f"Created {len(alerts)} alerts for pollination record {instance.id} "
                f"by user {instance.responsible.username}"
            )
            
        except Exception as e:
            logger.error(
                f"Error creating alerts for pollination record {instance.id}: {str(e)}"
            )


@receiver(post_save, sender=GerminationRecord)
def create_germination_alerts(sender, instance, created, **kwargs):
    """
    Signal handler to create alerts when a new germination record is created.
    
    Args:
        sender: The model class (GerminationRecord)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    if created:
        try:
            # Generate all types of alerts for the new germination record
            alerts = AlertGeneratorService.generate_all_alerts_for_record(
                record=instance,
                record_type='germination'
            )
            
            logger.info(
                f"Created {len(alerts)} alerts for germination record {instance.id} "
                f"by user {instance.responsible.username}"
            )
            
        except Exception as e:
            logger.error(
                f"Error creating alerts for germination record {instance.id}: {str(e)}"
            )