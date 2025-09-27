from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta
from django.utils import timezone
from factories import (
    RoleFactory, CustomUserFactory, UserProfileFactory,
    OrchidPlantFactory, PollinationTypeFactory, ClimateConditionFactory,
    SelfPollinationRecordFactory, SiblingPollinationRecordFactory, HybridPollinationRecordFactory,
    SeedSourceFactory, GerminationConditionFactory, GerminationRecordFactory,
    AlertTypeFactory, PollinationAlertFactory, GerminationAlertFactory, UserAlertFactory,
    ReportTypeFactory, CompletedReportFactory
)


class Command(BaseCommand):
    help = 'Create demonstration data with realistic scenarios for the pollination and germination system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing demo data before creating new data'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing demo data...'))
            self.clear_demo_data()

        with transaction.atomic():
            self.stdout.write(self.style.SUCCESS('Creating demonstration data...'))
            
            # Create base types
            self.create_base_types()
            
            # Create demo users
            users = self.create_demo_users()
            
            # Create demo plants (orchids)
            plants = self.create_demo_plants()
            
            # Create demo pollination records
            pollination_records = self.create_demo_pollination_records(users, plants)
            
            # Create demo germination records
            germination_records = self.create_demo_germination_records(users, plants, pollination_records)
            
            # Create demo alerts
            self.create_demo_alerts(users, pollination_records, germination_records)
            
            # Create demo reports
            self.create_demo_reports(users)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created demonstration data:\n'
                    f'- {len(users)} demo users with different roles\n'
                    f'- {len(plants)} orchid plants\n'
                    f'- {len(pollination_records)} pollination records\n'
                    f'- {len(germination_records)} germination records\n'
                    f'- Demo alerts and reports\n\n'
                    f'Demo users created:\n'
                    f'- maria.polinizadora (password: demo123) - Polinizador role\n'
                    f'- carlos.germinador (password: demo123) - Germinador role\n'
                    f'- ana.secretaria (password: demo123) - Secretaria role\n'
                    f'- admin.sistema (password: demo123) - Administrador role'
                )
            )

    def clear_demo_data(self):
        """Clear existing demo data."""
        from authentication.models import CustomUser, UserProfile
        from pollination.models import Plant, PollinationRecord, ClimateCondition
        from germination.models import GerminationRecord, SeedSource, GerminationCondition
        from alerts.models import Alert, UserAlert
        from reports.models import Report
        
        # Clear demo data (keep base types)
        UserAlert.objects.all().delete()
        Alert.objects.all().delete()
        Report.objects.all().delete()
        GerminationRecord.objects.all().delete()
        PollinationRecord.objects.all().delete()
        SeedSource.objects.all().delete()
        GerminationCondition.objects.all().delete()
        ClimateCondition.objects.all().delete()
        Plant.objects.all().delete()
        UserProfile.objects.all().delete()
        CustomUser.objects.filter(is_superuser=False).delete()
        
        self.stdout.write(self.style.SUCCESS('Demo data cleared successfully'))

    def create_base_types(self):
        """Create base types and configurations."""
        # Create roles
        RoleFactory(name='Polinizador')
        RoleFactory(name='Germinador')
        RoleFactory(name='Secretaria')
        RoleFactory(name='Administrador')
        
        # Create pollination types
        PollinationTypeFactory(name='Self')
        PollinationTypeFactory(name='Sibling')
        PollinationTypeFactory(name='Híbrido')
        
        # Create alert types
        AlertTypeFactory(name='semanal')
        AlertTypeFactory(name='preventiva')
        AlertTypeFactory(name='frecuente')
        
        # Create report types
        ReportTypeFactory(name='pollination')
        ReportTypeFactory(name='germination')
        ReportTypeFactory(name='statistical')
        
        self.stdout.write(self.style.SUCCESS('Base types created'))

    def create_demo_users(self):
        """Create demo users with realistic profiles."""
        users = []
        
        # Polinizador user
        maria = CustomUserFactory(
            username='maria.polinizadora',
            email='maria@example.com',
            first_name='María',
            last_name='González',
            employee_id='POL001',
            role__name='Polinizador'
        )
        maria.set_password('demo123')
        maria.save()
        
        UserProfileFactory(
            user=maria,
            department='Laboratorio de Polinización',
            position='Especialista en Polinización',
            bio='Especialista con 5 años de experiencia en polinización de orquídeas'
        )
        users.append(maria)
        
        # Germinador user
        carlos = CustomUserFactory(
            username='carlos.germinador',
            email='carlos@example.com',
            first_name='Carlos',
            last_name='Rodríguez',
            employee_id='GER001',
            role__name='Germinador'
        )
        carlos.set_password('demo123')
        carlos.save()
        
        UserProfileFactory(
            user=carlos,
            department='Laboratorio de Germinación',
            position='Técnico en Germinación',
            bio='Técnico especializado en germinación in vitro de orquídeas'
        )
        users.append(carlos)
        
        # Secretaria user
        ana = CustomUserFactory(
            username='ana.secretaria',
            email='ana@example.com',
            first_name='Ana',
            last_name='Martínez',
            employee_id='SEC001',
            role__name='Secretaria'
        )
        ana.set_password('demo123')
        ana.save()
        
        UserProfileFactory(
            user=ana,
            department='Administración',
            position='Asistente Administrativa',
            bio='Encargada del soporte administrativo y gestión de registros'
        )
        users.append(ana)
        
        # Administrador user
        admin = CustomUserFactory(
            username='admin.sistema',
            email='admin@example.com',
            first_name='Administrador',
            last_name='Sistema',
            employee_id='ADM001',
            role__name='Administrador'
        )
        admin.set_password('demo123')
        admin.save()
        
        UserProfileFactory(
            user=admin,
            department='Sistemas',
            position='Administrador del Sistema',
            bio='Administrador general del sistema con acceso completo'
        )
        users.append(admin)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(users)} demo users'))
        return users

    def create_demo_plants(self):
        """Create demo orchid plants with realistic data."""
        plants = []
        
        # Create specific orchid varieties
        orchid_data = [
            ('Cattleya', 'trianae', 'Vivero Norte', 'Mesa A', 'Pared 1'),
            ('Cattleya', 'mossiae', 'Vivero Norte', 'Mesa A', 'Pared 2'),
            ('Phalaenopsis', 'amabilis', 'Vivero Sur', 'Mesa B', 'Pared 1'),
            ('Phalaenopsis', 'schilleriana', 'Vivero Sur', 'Mesa B', 'Pared 2'),
            ('Dendrobium', 'nobile', 'Vivero Central', 'Mesa C', 'Pared 1'),
            ('Dendrobium', 'phalaenopsis', 'Vivero Central', 'Mesa C', 'Pared 2'),
            ('Oncidium', 'flexuosum', 'Vivero Este', 'Mesa D', 'Pared 1'),
            ('Oncidium', 'sphacelatum', 'Vivero Este', 'Mesa D', 'Pared 2'),
            ('Cattleya', 'warscewiczii', 'Vivero Norte', 'Mesa A', 'Pared 3'),
            ('Phalaenopsis', 'equestris', 'Vivero Sur', 'Mesa B', 'Pared 3'),
        ]
        
        for genus, species, vivero, mesa, pared in orchid_data:
            plant = OrchidPlantFactory(
                genus=genus,
                species=species,
                vivero=vivero,
                mesa=mesa,
                pared=pared
            )
            plants.append(plant)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(plants)} demo orchid plants'))
        return plants

    def create_demo_pollination_records(self, users, plants):
        """Create demo pollination records with realistic scenarios."""
        records = []
        maria = next(u for u in users if u.username == 'maria.polinizadora')
        
        # Create climate conditions
        sunny_climate = ClimateConditionFactory(
            weather='Soleado',
            temperature=25.5,
            humidity=65,
            wind_speed=2.3,
            notes='Condiciones ideales para polinización'
        )
        
        cloudy_climate = ClimateConditionFactory(
            weather='Nublado',
            temperature=22.0,
            humidity=75,
            wind_speed=1.8,
            notes='Condiciones estables, buena humedad'
        )
        
        # Self pollination - Cattleya trianae
        cattleya_mother = next(p for p in plants if p.genus == 'Cattleya' and p.species == 'trianae')
        cattleya_new = next(p for p in plants if p.genus == 'Cattleya' and p.species == 'mossiae')
        
        self_record = SelfPollinationRecordFactory(
            responsible=maria,
            mother_plant=cattleya_mother,
            new_plant=cattleya_new,
            climate_condition=sunny_climate,
            pollination_date=date.today() - timedelta(days=45),
            capsules_quantity=3,
            observations='Primera autopolinización de la temporada. Planta madre en excelente estado.'
        )
        records.append(self_record)
        
        # Sibling pollination - Phalaenopsis
        phal_mother = next(p for p in plants if p.genus == 'Phalaenopsis' and p.species == 'amabilis')
        phal_father = next(p for p in plants if p.genus == 'Phalaenopsis' and p.species == 'schilleriana')
        phal_new = next(p for p in plants if p.genus == 'Phalaenopsis' and p.species == 'equestris')
        
        sibling_record = SiblingPollinationRecordFactory(
            responsible=maria,
            mother_plant=phal_mother,
            father_plant=phal_father,
            new_plant=phal_new,
            climate_condition=cloudy_climate,
            pollination_date=date.today() - timedelta(days=30),
            capsules_quantity=5,
            observations='Cruce entre hermanos de la misma progenie. Ambas plantas madres saludables.'
        )
        records.append(sibling_record)
        
        # Hybrid pollination - Dendrobium x Oncidium
        dendro_mother = next(p for p in plants if p.genus == 'Dendrobium' and p.species == 'nobile')
        oncidium_father = next(p for p in plants if p.genus == 'Oncidium' and p.species == 'flexuosum')
        hybrid_new = next(p for p in plants if p.genus == 'Dendrobium' and p.species == 'phalaenopsis')
        
        hybrid_record = HybridPollinationRecordFactory(
            responsible=maria,
            mother_plant=dendro_mother,
            father_plant=oncidium_father,
            new_plant=hybrid_new,
            climate_condition=sunny_climate,
            pollination_date=date.today() - timedelta(days=60),
            capsules_quantity=2,
            observations='Hibridación experimental entre géneros diferentes. Monitorear desarrollo.'
        )
        records.append(hybrid_record)
        
        # Recent pollination for alerts
        recent_record = SelfPollinationRecordFactory(
            responsible=maria,
            mother_plant=next(p for p in plants if p.genus == 'Cattleya' and p.species == 'warscewiczii'),
            new_plant=cattleya_mother,
            climate_condition=sunny_climate,
            pollination_date=date.today() - timedelta(days=7),
            capsules_quantity=4,
            observations='Polinización reciente para generar alertas de seguimiento.'
        )
        records.append(recent_record)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(records)} demo pollination records'))
        return records

    def create_demo_germination_records(self, users, plants, pollination_records):
        """Create demo germination records."""
        records = []
        carlos = next(u for u in users if u.username == 'carlos.germinador')
        
        # Create germination conditions
        controlled_condition = GerminationConditionFactory(
            climate='Controlado',
            substrate='Musgo sphagnum',
            location='Laboratorio - Cámara 1',
            temperature=24.0,
            humidity=80,
            light_hours=12,
            substrate_details='Musgo sphagnum esterilizado con perlita 70:30',
            notes='Condiciones controladas ideales para germinación'
        )
        
        greenhouse_condition = GerminationConditionFactory(
            climate='Invernadero',
            substrate='Mezcla personalizada',
            location='Invernadero 2 - Sección A',
            temperature=26.5,
            humidity=75,
            light_hours=14,
            substrate_details='Corteza de pino, turba y vermiculita 40:30:30',
            notes='Ambiente de invernadero con control parcial'
        )
        
        # Germination from pollination record
        seed_source_internal = SeedSourceFactory(
            name='Semillas Cattleya trianae - Autopolinización',
            source_type='Autopolinización',
            pollination_record=pollination_records[0],
            description='Semillas obtenidas de la autopolinización de Cattleya trianae'
        )
        
        germination1 = GerminationRecordFactory(
            responsible=carlos,
            plant=pollination_records[0].mother_plant,
            seed_source=seed_source_internal,
            germination_condition=controlled_condition,
            germination_date=date.today() - timedelta(days=20),
            seeds_planted=50,
            seedlings_germinated=38,
            transplant_days=90,
            observations='Excelente tasa de germinación. Plántulas desarrollándose bien.'
        )
        records.append(germination1)
        
        # External seed source germination
        seed_source_external = SeedSourceFactory(
            name='Semillas Phalaenopsis comerciales',
            source_type='Otra fuente',
            external_supplier='Orquídeas del Valle S.A.',
            description='Semillas comerciales de Phalaenopsis híbridas'
        )
        
        germination2 = GerminationRecordFactory(
            responsible=carlos,
            plant=next(p for p in plants if p.genus == 'Phalaenopsis'),
            seed_source=seed_source_external,
            germination_condition=greenhouse_condition,
            germination_date=date.today() - timedelta(days=35),
            seeds_planted=75,
            seedlings_germinated=52,
            transplant_days=85,
            observations='Semillas comerciales con buena viabilidad. Crecimiento uniforme.'
        )
        records.append(germination2)
        
        # Recent germination for alerts
        recent_germination = GerminationRecordFactory(
            responsible=carlos,
            plant=next(p for p in plants if p.genus == 'Dendrobium'),
            seed_source=seed_source_internal,
            germination_condition=controlled_condition,
            germination_date=date.today() - timedelta(days=5),
            seeds_planted=30,
            seedlings_germinated=22,
            transplant_days=95,
            observations='Germinación reciente para seguimiento y alertas.'
        )
        records.append(recent_germination)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(records)} demo germination records'))
        return records

    def create_demo_alerts(self, users, pollination_records, germination_records):
        """Create demo alerts for users."""
        maria = next(u for u in users if u.username == 'maria.polinizadora')
        carlos = next(u for u in users if u.username == 'carlos.germinador')
        
        # Pollination alerts
        for record in pollination_records[:2]:  # First 2 records
            alert = PollinationAlertFactory(
                pollination_record=record,
                title=f'Revisar polinización - {record.mother_plant.full_scientific_name}',
                message=f'Es momento de revisar el estado de la polinización realizada el {record.pollination_date}',
                scheduled_date=timezone.now() + timedelta(days=1),
                priority='medium'
            )
            UserAlertFactory(user=maria, alert=alert)
        
        # Germination alerts
        for record in germination_records[:2]:  # First 2 records
            alert = GerminationAlertFactory(
                germination_record=record,
                title=f'Revisar germinación - {record.plant.full_scientific_name}',
                message=f'Verificar el progreso de la germinación iniciada el {record.germination_date}',
                scheduled_date=timezone.now() + timedelta(hours=12),
                priority='high'
            )
            UserAlertFactory(user=carlos, alert=alert)
        
        self.stdout.write(self.style.SUCCESS('Created demo alerts'))

    def create_demo_reports(self, users):
        """Create demo reports."""
        admin = next(u for u in users if u.username == 'admin.sistema')
        
        # Pollination report
        poll_report = CompletedReportFactory(
            title='Reporte Mensual de Polinización - Septiembre 2024',
            report_type__name='pollination',
            generated_by=admin,
            parameters={
                'date_from': '2024-09-01',
                'date_to': '2024-09-30',
                'pollination_types': ['Self', 'Sibling', 'Híbrido'],
                'include_charts': True,
                'group_by': 'species'
            },
            file_path='reports/pollination_monthly_sep2024.pdf',
            file_size=2048576  # 2MB
        )
        
        # Germination report
        germ_report = CompletedReportFactory(
            title='Análisis de Germinación - Tercer Trimestre 2024',
            report_type__name='germination',
            generated_by=admin,
            parameters={
                'date_from': '2024-07-01',
                'date_to': '2024-09-30',
                'include_success_rates': True,
                'include_charts': True,
                'group_by': 'genus'
            },
            file_path='reports/germination_q3_2024.pdf',
            file_size=1536000  # 1.5MB
        )
        
        # Statistical report
        stat_report = CompletedReportFactory(
            title='Reporte Estadístico Consolidado - 2024',
            report_type__name='statistical',
            generated_by=admin,
            parameters={
                'date_from': '2024-01-01',
                'date_to': '2024-09-30',
                'include_pollination': True,
                'include_germination': True,
                'include_trends': True,
                'include_charts': True
            },
            file_path='reports/statistical_2024.pdf',
            file_size=4194304  # 4MB
        )
        
        self.stdout.write(self.style.SUCCESS('Created demo reports'))