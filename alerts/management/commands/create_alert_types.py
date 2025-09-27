from django.core.management.base import BaseCommand
from alerts.models import AlertType


class Command(BaseCommand):
    help = 'Create default alert types for the system'

    def handle(self, *args, **options):
        alert_types = [
            {
                'name': 'semanal',
                'description': 'Alerta semanal para seguimiento de registros una semana después de su creación'
            },
            {
                'name': 'preventiva',
                'description': 'Alerta preventiva que se envía una semana antes de fechas importantes como maduración o trasplante'
            },
            {
                'name': 'frecuente',
                'description': 'Alertas frecuentes (diarias) durante la semana de fechas críticas como maduración o trasplante'
            }
        ]

        created_count = 0
        updated_count = 0

        for alert_type_data in alert_types:
            alert_type, created = AlertType.objects.get_or_create(
                name=alert_type_data['name'],
                defaults={
                    'description': alert_type_data['description'],
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created alert type: {alert_type.name}')
                )
            else:
                # Update description if it has changed
                if alert_type.description != alert_type_data['description']:
                    alert_type.description = alert_type_data['description']
                    alert_type.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Updated alert type: {alert_type.name}')
                    )
                else:
                    self.stdout.write(f'Alert type already exists: {alert_type.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Alert types processing completed. '
                f'Created: {created_count}, Updated: {updated_count}'
            )
        )