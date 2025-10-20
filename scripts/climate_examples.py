#!/usr/bin/env python
"""
Ejemplos de uso del nuevo sistema de clima simplificado.
Muestra cómo crear registros de polinización y germinación con los nuevos códigos de clima.
"""

import os
import sys
import django
from datetime import date

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_polinizacion.settings')
django.setup()

from pollination.models import Plant, PollinationType, PollinationRecord
from core.models import ClimateCondition
from germination.models import SeedSource, GerminationSetup, GerminationRecord
from authentication.models import CustomUser, Role


def create_example_data():
    """Create example data using the new climate system."""
    
    print("🌱 Creando datos de ejemplo con el nuevo sistema de clima...")
    
    # Create user and role
    role, _ = Role.objects.get_or_create(name='Polinizador')
    user, _ = CustomUser.objects.get_or_create(
        username='ejemplo_user',
        defaults={
            'email': 'ejemplo@test.com',
            'role': role
        }
    )
    
    # Create plants
    mother_plant, _ = Plant.objects.get_or_create(
        genus='Orchidaceae',
        species='cattleya',
        vivero='Vivero Principal',
        mesa='Mesa 1',
        pared='Norte'
    )
    
    father_plant, _ = Plant.objects.get_or_create(
        genus='Orchidaceae',
        species='cattleya',
        vivero='Vivero Principal',
        mesa='Mesa 2',
        pared='Sur'
    )
    
    new_plant, _ = Plant.objects.get_or_create(
        genus='Orchidaceae',
        species='cattleya',
        vivero='Vivero Propagación',
        mesa='Mesa A',
        pared='Este'
    )
    
    # Create pollination type
    pollination_type, _ = PollinationType.objects.get_or_create(
        name='Sibling',
        defaults={
            'description': 'Polinización entre hermanos',
            'maturation_days': 120
        }
    )
    
    print("📊 Ejemplos de condiciones climáticas:")
    
    # Example 1: Cold climate for mountain species
    cold_climate, _ = ClimateCondition.objects.get_or_create(
        climate='C',
        defaults={
            'notes': 'Clima frío para especies de montaña'
        }
    )
    print(f"  ❄️  {cold_climate.get_climate_display()} ({cold_climate.temperature_range}): {cold_climate.description}")
    
    # Example 2: Intermediate climate (most common)
    intermediate_climate, _ = ClimateCondition.objects.get_or_create(
        climate='I',
        defaults={
            'notes': 'Clima intermedio estándar'
        }
    )
    print(f"  🌤️  {intermediate_climate.get_climate_display()} ({intermediate_climate.temperature_range}): {intermediate_climate.description}")
    
    # Example 3: Warm climate for tropical species
    warm_climate, _ = ClimateCondition.objects.get_or_create(
        climate='W',
        defaults={
            'notes': 'Clima caliente para especies tropicales'
        }
    )
    print(f"  🔥 {warm_climate.get_climate_display()} ({warm_climate.temperature_range}): {warm_climate.description}")
    
    # Create pollination record example
    pollination_record, created = PollinationRecord.objects.get_or_create(
        responsible=user,
        pollination_type=pollination_type,
        pollination_date=date.today(),
        mother_plant=mother_plant,
        father_plant=father_plant,
        new_plant=new_plant,
        climate_condition=intermediate_climate,
        capsules_quantity=5,
        defaults={
            'observations': 'Ejemplo de polinización con clima intermedio'
        }
    )
    
    if created:
        print(f"\n✅ Registro de polinización creado:")
        print(f"   Tipo: {pollination_record.pollination_type.get_name_display()}")
        print(f"   Clima: {pollination_record.climate_condition.get_climate_display()}")
        print(f"   Fecha: {pollination_record.pollination_date}")
        print(f"   Maduración estimada: {pollination_record.estimated_maturation_date}")
    
    # Create seed source
    seed_source, _ = SeedSource.objects.get_or_create(
        name='Semillas de ejemplo',
        source_type='Otra fuente',
        defaults={
            'external_supplier': 'Proveedor de ejemplo',
            'description': 'Semillas para demostración'
        }
    )
    
    # Create germination setups for different climates
    germination_setups = []
    
    for climate_code in ['IC', 'I', 'IW']:
        climate_condition = ClimateCondition.objects.get(climate=climate_code)
        setup, _ = GerminationSetup.objects.get_or_create(
            climate_condition=climate_condition,
            defaults={
                'setup_notes': f'Configuración climática {climate_code} para germinación de ejemplo'
            }
        )
        germination_setups.append(setup)
    
    print(f"\n🌱 Configuraciones de germinación creadas:")
    for setup in germination_setups:
        print(f"   {setup.climate_display} ({setup.temperature_range})")
    
    # Create germination record example
    germination_record, created = GerminationRecord.objects.get_or_create(
        responsible=user,
        germination_date=date.today(),
        plant=new_plant,
        seed_source=seed_source,
        germination_setup=germination_setups[1],  # Intermediate climate
        seeds_planted=50,
        seedlings_germinated=42,
        defaults={
            'observations': 'Ejemplo de germinación con clima intermedio'
        }
    )
    
    if created:
        print(f"\n✅ Registro de germinación creado:")
        print(f"   Planta: {germination_record.plant.full_scientific_name}")
        print(f"   Clima: {germination_record.germination_setup.climate_display}")
        print(f"   Tasa de germinación: {germination_record.germination_rate()}%")
        print(f"   Trasplante estimado: {germination_record.estimated_transplant_date}")


def show_climate_options():
    """Show all available climate options."""
    print("\n🌡️  Opciones de clima disponibles:")
    print("=" * 50)
    
    from pollination.models import ClimateCondition
    
    for code, name in ClimateCondition.CLIMATE_CHOICES:
        # Create a temporary instance to get properties
        temp_climate = ClimateCondition(climate=code)
        print(f"  {code:2} | {name:18} | {temp_climate.temperature_range:8} | {temp_climate.description}")
    
    print("=" * 50)


def show_usage_examples():
    """Show API usage examples."""
    print("\n📡 Ejemplos de uso de API:")
    print("=" * 40)
    
    print("\n1. Crear condición climática para polinización:")
    print("""
POST /api/pollination/climate-conditions/
{
    "climate": "I",
    "notes": "Condiciones estándar para Cattleya"
}
    """)
    
    print("\n2. Crear registro de polinización:")
    print("""
POST /api/pollination/records/
{
    "pollination_type": 1,
    "pollination_date": "2024-01-15",
    "mother_plant": 1,
    "father_plant": 2,
    "new_plant": 3,
    "climate_condition": 3,
    "capsules_quantity": 5
}
    """)
    
    print("\n3. Crear condición de germinación:")
    print("""
POST /api/germination/conditions/
{
    "climate": "IW",
    "substrate": "Corteza de pino",
    "location": "Invernadero 2"
}
    """)
    
    print("\n4. Crear registro de germinación:")
    print("""
POST /api/germination/records/
{
    "germination_date": "2024-01-20",
    "plant": 1,
    "seed_source": 1,
    "germination_condition": 4,
    "seeds_planted": 50,
    "seedlings_germinated": 42
}
    """)


if __name__ == '__main__':
    print("🌿 Sistema de Clima Simplificado - Ejemplos de Uso")
    print("=" * 60)
    
    show_climate_options()
    create_example_data()
    show_usage_examples()
    
    print("\n✨ ¡Ejemplos completados exitosamente!")
    print("\nPara más información, consulta: docs/CLIMATE_SYSTEM_UPDATE.md")