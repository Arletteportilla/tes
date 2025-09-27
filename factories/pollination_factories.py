import factory
from datetime import date, timedelta
from pollination.models import Plant, PollinationType, ClimateCondition, PollinationRecord
from .authentication_factories import CustomUserFactory


class PlantFactory(factory.django.DjangoModelFactory):
    """Factory for Plant model."""
    
    class Meta:
        model = Plant
    
    genus = factory.Sequence(lambda n: f"Genus{n}")
    species = factory.Sequence(lambda n: f"species{n}")
    vivero = factory.Iterator(['Vivero Norte', 'Vivero Sur', 'Vivero Central', 'Vivero Este'])
    mesa = factory.Iterator(['Mesa A', 'Mesa B', 'Mesa C', 'Mesa D'])
    pared = factory.Sequence(lambda n: f"Pared {n}")
    is_active = True
    
    @factory.post_generation
    def format_names(obj, create, extracted, **kwargs):
        """Format genus and species names properly."""
        if not create:
            return
        
        obj.genus = obj.genus.capitalize()
        obj.species = obj.species.lower()
        obj.save()


class OrchidPlantFactory(PlantFactory):
    """Factory for Orchid plants with realistic names."""
    genus = factory.Iterator(['Cattleya', 'Phalaenopsis', 'Dendrobium', 'Oncidium'])
    species = factory.Sequence(lambda n: f"species{n}")
    pared = factory.Sequence(lambda n: f"OrchidPared {n}")


class PollinationTypeFactory(factory.django.DjangoModelFactory):
    """Factory for PollinationType model."""
    
    class Meta:
        model = PollinationType
        django_get_or_create = ('name',)
    
    name = factory.Iterator(['Self', 'Sibling', 'Híbrido'])
    description = factory.LazyAttribute(lambda obj: f"Descripción para {obj.name}")
    maturation_days = 120
    
    @factory.post_generation
    def set_type_properties(obj, create, extracted, **kwargs):
        """Set properties based on pollination type."""
        if not create:
            return
        
        if obj.name == 'Self':
            obj.requires_father_plant = False
            obj.allows_different_species = False
        elif obj.name == 'Sibling':
            obj.requires_father_plant = True
            obj.allows_different_species = False
        elif obj.name == 'Híbrido':
            obj.requires_father_plant = True
            obj.allows_different_species = True
        
        obj.save()


class ClimateConditionFactory(factory.django.DjangoModelFactory):
    """Factory for ClimateCondition model."""
    
    class Meta:
        model = ClimateCondition
    
    weather = factory.Iterator(['Soleado', 'Nublado', 'Lluvioso', 'Parcialmente nublado'])
    temperature = factory.Faker('pydecimal', left_digits=2, right_digits=1, min_value=15, max_value=35)
    humidity = factory.Faker('pyint', min_value=40, max_value=90)
    wind_speed = factory.Faker('pydecimal', left_digits=2, right_digits=1, min_value=0, max_value=20)
    notes = factory.Faker('text', max_nb_chars=100)


class PollinationRecordFactory(factory.django.DjangoModelFactory):
    """Factory for PollinationRecord model."""
    
    class Meta:
        model = PollinationRecord
    
    responsible = factory.SubFactory(CustomUserFactory)
    pollination_type = factory.SubFactory(PollinationTypeFactory)
    pollination_date = factory.LazyFunction(lambda: date.today() - timedelta(days=30))
    mother_plant = factory.SubFactory(PlantFactory)
    new_plant = factory.SubFactory(PlantFactory)
    climate_condition = factory.SubFactory(ClimateConditionFactory)
    capsules_quantity = factory.Faker('pyint', min_value=1, max_value=10)
    observations = factory.Faker('text', max_nb_chars=200)
    is_successful = None
    maturation_confirmed = False
    
    @factory.post_generation
    def set_father_plant(obj, create, extracted, **kwargs):
        """Set father plant based on pollination type."""
        if not create:
            return
        
        if obj.pollination_type.requires_father_plant:
            if obj.pollination_type.name == 'Sibling':
                # Same species for sibling pollination
                obj.father_plant = PlantFactory(
                    genus=obj.mother_plant.genus,
                    species=obj.mother_plant.species
                )
            else:  # Híbrido
                # Different species for hybrid
                obj.father_plant = PlantFactory()
        
        # Ensure new plant matches requirements
        if obj.pollination_type.name in ['Self', 'Sibling']:
            obj.new_plant.genus = obj.mother_plant.genus
            obj.new_plant.species = obj.mother_plant.species
            obj.new_plant.save()
        
        obj.save()


class SelfPollinationRecordFactory(PollinationRecordFactory):
    """Factory for Self pollination records."""
    pollination_type = factory.SubFactory(PollinationTypeFactory, name='Self')
    father_plant = None


class SiblingPollinationRecordFactory(PollinationRecordFactory):
    """Factory for Sibling pollination records."""
    pollination_type = factory.SubFactory(PollinationTypeFactory, name='Sibling')


class HybridPollinationRecordFactory(PollinationRecordFactory):
    """Factory for Hybrid pollination records."""
    pollination_type = factory.SubFactory(PollinationTypeFactory, name='Híbrido')