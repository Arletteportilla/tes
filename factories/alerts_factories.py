import factory
from datetime import datetime, timedelta
from django.utils import timezone
from alerts.models import AlertType, Alert, UserAlert
from .authentication_factories import CustomUserFactory
from .pollination_factories import PollinationRecordFactory
from .germination_factories import GerminationRecordFactory


class AlertTypeFactory(factory.django.DjangoModelFactory):
    """Factory for AlertType model."""
    
    class Meta:
        model = AlertType
        django_get_or_create = ('name',)
    
    name = factory.Iterator(['semanal', 'preventiva', 'frecuente'])
    description = factory.LazyAttribute(lambda obj: f"Descripción para alerta {obj.name}")
    is_active = True


class AlertFactory(factory.django.DjangoModelFactory):
    """Factory for Alert model."""
    
    class Meta:
        model = Alert
    
    alert_type = factory.SubFactory(AlertTypeFactory)
    title = factory.Faker('sentence', nb_words=6)
    message = factory.Faker('text', max_nb_chars=300)
    status = factory.Iterator(['pending', 'read', 'dismissed'])
    priority = factory.Iterator(['low', 'medium', 'high', 'urgent'])
    scheduled_date = factory.LazyFunction(lambda: timezone.now() + timedelta(days=3))
    expires_at = factory.LazyAttribute(lambda obj: obj.scheduled_date + timedelta(days=30))
    metadata = factory.LazyFunction(lambda: {
        'source': 'system',
        'auto_generated': True
    })


class PollinationAlertFactory(AlertFactory):
    """Factory for pollination-related alerts."""
    pollination_record = factory.SubFactory(PollinationRecordFactory)
    title = factory.LazyAttribute(lambda obj: f"Alerta de polinización - {obj.pollination_record.mother_plant.full_scientific_name}")
    message = factory.LazyAttribute(lambda obj: f"Revisar el estado de la polinización realizada el {obj.pollination_record.pollination_date}")


class GerminationAlertFactory(AlertFactory):
    """Factory for germination-related alerts."""
    germination_record = factory.SubFactory(GerminationRecordFactory)
    title = factory.LazyAttribute(lambda obj: f"Alerta de germinación - {obj.germination_record.plant.full_scientific_name}")
    message = factory.LazyAttribute(lambda obj: f"Revisar el estado de la germinación iniciada el {obj.germination_record.germination_date}")


class WeeklyAlertFactory(AlertFactory):
    """Factory for weekly alerts."""
    alert_type = factory.SubFactory(AlertTypeFactory, name='semanal')
    priority = 'medium'
    title = "Revisión semanal de registros"
    message = "Es momento de revisar el estado de tus registros de polinización y germinación"


class PreventiveAlertFactory(AlertFactory):
    """Factory for preventive alerts."""
    alert_type = factory.SubFactory(AlertTypeFactory, name='preventiva')
    priority = 'high'
    title = "Alerta preventiva"
    message = "Se acerca una fecha importante para uno de tus registros"


class FrequentAlertFactory(AlertFactory):
    """Factory for frequent alerts."""
    alert_type = factory.SubFactory(AlertTypeFactory, name='frecuente')
    priority = 'urgent'
    title = "Recordatorio frecuente"
    message = "Acción requerida para completar un proceso pendiente"


class UserAlertFactory(factory.django.DjangoModelFactory):
    """Factory for UserAlert model."""
    
    class Meta:
        model = UserAlert
    
    user = factory.SubFactory(CustomUserFactory)
    alert = factory.SubFactory(AlertFactory)
    is_read = False
    is_dismissed = False
    
    @factory.post_generation
    def set_read_status(obj, create, extracted, **kwargs):
        """Randomly set some alerts as read."""
        if not create:
            return
        
        # 30% chance of being read
        import random
        if random.random() < 0.3:
            obj.is_read = True
            obj.read_at = timezone.now() - timedelta(hours=random.randint(1, 24))
            obj.save()


class ReadUserAlertFactory(UserAlertFactory):
    """Factory for read user alerts."""
    is_read = True
    read_at = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=24))


class DismissedUserAlertFactory(UserAlertFactory):
    """Factory for dismissed user alerts."""
    is_dismissed = True
    dismissed_at = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=48))