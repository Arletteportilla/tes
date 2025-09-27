from django.core.management.base import BaseCommand
from django.db import transaction
from factories import (
    RoleFactory, CustomUserFactory, UserProfileFactory,
    PlantFactory, OrchidPlantFactory, PollinationTypeFactory, ClimateConditionFactory,
    SelfPollinationRecordFactory, SiblingPollinationRecordFactory, HybridPollinationRecordFactory,
    SeedSourceFactory, GerminationConditionFactory, GerminationRecordFactory,
    AlertTypeFactory, PollinationAlertFactory, GerminationAlertFactory, UserAlertFactory,
    ReportTypeFactory, CompletedReportFactory, PollinationReportFactory
)


class Command(BaseCommand):
    help = 'Populate database with test data using factories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users to create (default: 10)'
        )
        parser.add_argument(
            '--plants',
            type=int,
            default=50,
            help='Number of plants to create (default: 50)'
        )
        parser.add_argument(
            '--pollinations',
            type=int,
            default=30,
            help='Number of pollination records to create (default: 30)'
        )
        parser.add_argument(
            '--germinations',
            type=int,
            default=25,
            help='Number of germination records to create (default: 25)'
        )
        parser.add_argument(
            '--alerts',
            type=int,
            default=40,
            help='Number of alerts to create (default: 40)'
        )
        parser.add_argument(
            '--reports',
            type=int,
            default=15,
            help='Number of reports to create (default: 15)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data before creating new data'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing test data...'))
            self.clear_test_data()

        with transaction.atomic():
            self.stdout.write(self.style.SUCCESS('Creating test data...'))
            
            # Create base types first
            self.create_base_types()
            
            # Create users and profiles
            users = self.create_users(options['users'])
            
            # Create plants
            plants = self.create_plants(options['plants'])
            
            # Create pollination records
            pollination_records = self.create_pollination_records(options['pollinations'], users, plants)
            
            # Create germination records
            germination_records = self.create_germination_records(options['germinations'], users, plants)
            
            # Create alerts
            self.create_alerts(options['alerts'], users, pollination_records, germination_records)
            
            # Create reports
            self.create_reports(options['reports'], users)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created test data:\n'
                    f'- {len(users)} users\n'
                    f'- {len(plants)} plants\n'
                    f'- {len(pollination_records)} pollination records\n'
                    f'- {len(germination_records)} germination records\n'
                    f'- {options["alerts"]} alerts\n'
                    f'- {options["reports"]} reports'
                )
            )

    def clear_test_data(self):
        """Clear existing test data."""
        from authentication.models import CustomUser, Role, UserProfile
        from pollination.models import Plant, PollinationType, ClimateCondition, PollinationRecord
        from germination.models import SeedSource, GerminationCondition, GerminationRecord
        from alerts.models import AlertType, Alert, UserAlert
        from reports.models import ReportType, Report
        
        # Clear in reverse dependency order
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
        CustomUser.objects.filter(is_superuser=False).delete()  # Keep superusers
        
        self.stdout.write(self.style.SUCCESS('Test data cleared successfully'))

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

    def create_users(self, count):
        """Create users with different roles."""
        users = []
        
        # Create users with different roles (distribute evenly)
        role_distribution = {
            'Polinizador': count // 4,
            'Germinador': count // 4,
            'Secretaria': count // 4,
            'Administrador': count - (3 * (count // 4))  # Remaining users
        }
        
        for role_name, role_count in role_distribution.items():
            for i in range(role_count):
                user = CustomUserFactory(role__name=role_name)
                UserProfileFactory(user=user)
                users.append(user)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(users)} users'))
        return users

    def create_plants(self, count):
        """Create plants with realistic orchid names."""
        plants = []
        
        # Create mix of regular plants and orchids
        orchid_count = count // 2
        regular_count = count - orchid_count
        
        # Create orchid plants
        for i in range(orchid_count):
            plants.append(OrchidPlantFactory())
        
        # Create regular plants
        for i in range(regular_count):
            plants.append(PlantFactory())
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(plants)} plants'))
        return plants

    def create_pollination_records(self, count, users, plants):
        """Create pollination records with different types."""
        records = []
        
        # Distribute pollination types
        self_count = count // 3
        sibling_count = count // 3
        hybrid_count = count - (self_count + sibling_count)
        
        # Create self pollination records
        for i in range(self_count):
            records.append(SelfPollinationRecordFactory(responsible=users[i % len(users)]))
        
        # Create sibling pollination records
        for i in range(sibling_count):
            records.append(SiblingPollinationRecordFactory(responsible=users[i % len(users)]))
        
        # Create hybrid pollination records
        for i in range(hybrid_count):
            records.append(HybridPollinationRecordFactory(responsible=users[i % len(users)]))
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(records)} pollination records'))
        return records

    def create_germination_records(self, count, users, plants):
        """Create germination records."""
        records = []
        
        for i in range(count):
            records.append(GerminationRecordFactory(
                responsible=users[i % len(users)],
                plant=plants[i % len(plants)]
            ))
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(records)} germination records'))
        return records

    def create_alerts(self, count, users, pollination_records, germination_records):
        """Create alerts related to records."""
        alert_count = 0
        
        # Create pollination alerts
        pollination_alert_count = count // 3
        for i in range(min(pollination_alert_count, len(pollination_records))):
            alert = PollinationAlertFactory(pollination_record=pollination_records[i])
            UserAlertFactory(user=pollination_records[i].responsible, alert=alert)
            alert_count += 1
        
        # Create germination alerts
        germination_alert_count = count // 3
        for i in range(min(germination_alert_count, len(germination_records))):
            alert = GerminationAlertFactory(germination_record=germination_records[i])
            UserAlertFactory(user=germination_records[i].responsible, alert=alert)
            alert_count += 1
        
        # Create general alerts for remaining count
        remaining_alerts = count - alert_count
        for i in range(remaining_alerts):
            alert = PollinationAlertFactory()
            UserAlertFactory(user=users[i % len(users)], alert=alert)
            alert_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {alert_count} alerts'))

    def create_reports(self, count, users):
        """Create reports of different types."""
        # Filter admin users for report generation
        admin_users = [user for user in users if user.role and user.role.name == 'Administrador']
        if not admin_users:
            # Create at least one admin user if none exist
            admin_users = [CustomUserFactory(role__name='Administrador')]
        
        report_count = 0
        
        # Distribute report types
        pollination_count = count // 3
        germination_count = count // 3
        statistical_count = count - (pollination_count + germination_count)
        
        # Create pollination reports
        for i in range(pollination_count):
            PollinationReportFactory(generated_by=admin_users[i % len(admin_users)])
            report_count += 1
        
        # Create germination reports
        for i in range(germination_count):
            CompletedReportFactory(
                report_type__name='germination',
                generated_by=admin_users[i % len(admin_users)]
            )
            report_count += 1
        
        # Create statistical reports
        for i in range(statistical_count):
            CompletedReportFactory(
                report_type__name='statistical',
                generated_by=admin_users[i % len(admin_users)]
            )
            report_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {report_count} reports'))