import factory
from datetime import date, timedelta
from germination.models import SeedSource, GerminationCondition, GerminationRecord
from .authentication_factories import CustomUserFactory
from .pollination_factories import PlantFactory, PollinationRecordFactory


class SeedSourceFactory(factory.django.DjangoModelFactory):
    """Factory for SeedSource model."""
    
    class Meta:
        model = SeedSource
    
    name = factory.Faker('word')
    source_type = factory.Iterator(['Autopolinización', 'Sibling', 'Híbrido', 'Otra fuente'])
    description = factory.Faker('text', max_nb_chars=200)
    collection_date = factory.LazyFunction(lambda: date.today() - timedelta(days=30))
    is_active = True
    
    @factory.post_generation
    def set_source_details(obj, create, extracted, **kwargs):
        """Set source details based on source type."""
        if not create:
            return
        
        if obj.source_type in ['Autopolinización', 'Sibling', 'Híbrido'] and not obj.pollination_record:
            # Only create if not already provided
            obj.pollination_record = PollinationRecordFactory()
        elif obj.source_type == 'Otra fuente' and not obj.external_supplier:
            # External source
            from faker import Faker
            fake = Faker()
            obj.external_supplier = fake.company()
        
        obj.save()


class InternalSeedSourceFactory(SeedSourceFactory):
    """Factory for internal seed sources (from pollination records)."""
    source_type = factory.Iterator(['Autopolinización', 'Sibling', 'Híbrido'])
    pollination_record = factory.SubFactory(PollinationRecordFactory)
    external_supplier = ''


class ExternalSeedSourceFactory(SeedSourceFactory):
    """Factory for external seed sources."""
    source_type = 'Otra fuente'
    pollination_record = None
    external_supplier = factory.Faker('company')


class GerminationConditionFactory(factory.django.DjangoModelFactory):
    """Factory for GerminationCondition model."""
    
    class Meta:
        model = GerminationCondition
    
    climate = factory.Iterator(['Controlado', 'Invernadero', 'Exterior', 'Laboratorio'])
    substrate = factory.Iterator(['Turba', 'Perlita', 'Vermiculita', 'Corteza de pino', 'Musgo sphagnum', 'Mezcla personalizada'])
    location = factory.Faker('address')
    temperature = factory.Faker('pydecimal', left_digits=2, right_digits=1, min_value=18, max_value=28)
    humidity = factory.Faker('pyint', min_value=60, max_value=85)
    light_hours = factory.Faker('pyint', min_value=8, max_value=16)
    substrate_details = factory.Faker('text', max_nb_chars=150)
    notes = factory.Faker('text', max_nb_chars=100)


class GerminationRecordFactory(factory.django.DjangoModelFactory):
    """Factory for GerminationRecord model."""
    
    class Meta:
        model = GerminationRecord
    
    responsible = factory.SubFactory(CustomUserFactory)
    germination_date = factory.LazyFunction(lambda: date.today() - timedelta(days=15))
    plant = factory.SubFactory(PlantFactory)
    seed_source = factory.SubFactory(SeedSourceFactory)
    germination_condition = factory.SubFactory(GerminationConditionFactory)
    seeds_planted = factory.Faker('pyint', min_value=10, max_value=100)
    transplant_days = 90
    is_successful = None
    transplant_confirmed = False
    observations = factory.Faker('text', max_nb_chars=200)
    
    @factory.post_generation
    def set_germination_results(obj, create, extracted, **kwargs):
        """Set realistic germination results."""
        if not create:
            return
        
        # Set seedlings germinated as a percentage of seeds planted (50-90% success rate)
        import random
        success_rate = random.uniform(0.5, 0.9)
        obj.seedlings_germinated = int(obj.seeds_planted * success_rate)
        obj.save()


class SuccessfulGerminationRecordFactory(GerminationRecordFactory):
    """Factory for successful germination records."""
    is_successful = True
    transplant_confirmed = True
    transplant_confirmed_date = factory.LazyFunction(lambda: date.today() - timedelta(days=5))


class PendingGerminationRecordFactory(GerminationRecordFactory):
    """Factory for pending germination records (not yet transplanted)."""
    is_successful = None
    transplant_confirmed = False
    transplant_confirmed_date = None