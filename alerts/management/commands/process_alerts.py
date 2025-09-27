from django.core.management.base import BaseCommand
from django.utils import timezone
from alerts.services import AlertGeneratorService
from alerts.tasks import cleanup_expired_alerts, process_due_alerts, generate_missing_alerts


class Command(BaseCommand):
    help = 'Process alerts: cleanup expired, process due alerts, and generate missing alerts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup-only',
            action='store_true',
            help='Only cleanup expired alerts',
        )
        parser.add_argument(
            '--process-only',
            action='store_true',
            help='Only process due alerts',
        )
        parser.add_argument(
            '--generate-missing',
            action='store_true',
            help='Generate missing alerts for existing records',
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run tasks asynchronously using Celery',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f'Starting alert processing at {timezone.now()}')
        )

        if options['async']:
            # Run tasks asynchronously using Celery
            if options['cleanup_only']:
                task = cleanup_expired_alerts.delay()
                self.stdout.write(f'Cleanup task queued: {task.id}')
            elif options['process_only']:
                task = process_due_alerts.delay()
                self.stdout.write(f'Process task queued: {task.id}')
            elif options['generate_missing']:
                task = generate_missing_alerts.delay()
                self.stdout.write(f'Generate missing task queued: {task.id}')
            else:
                # Queue all tasks
                cleanup_task = cleanup_expired_alerts.delay()
                process_task = process_due_alerts.delay()
                self.stdout.write(f'All tasks queued: cleanup={cleanup_task.id}, process={process_task.id}')
        else:
            # Run tasks synchronously
            if options['cleanup_only']:
                self._cleanup_expired_alerts()
            elif options['process_only']:
                self._process_due_alerts()
            elif options['generate_missing']:
                self._generate_missing_alerts()
            else:
                # Run all tasks
                self._cleanup_expired_alerts()
                self._process_due_alerts()

        self.stdout.write(
            self.style.SUCCESS(f'Alert processing completed at {timezone.now()}')
        )

    def _cleanup_expired_alerts(self):
        """Cleanup expired alerts synchronously"""
        try:
            expired_count = AlertGeneratorService.cleanup_expired_alerts()
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned up {expired_count} expired alerts')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error cleaning up expired alerts: {str(e)}')
            )

    def _process_due_alerts(self):
        """Process due alerts synchronously"""
        try:
            due_alerts = AlertGeneratorService.get_alerts_due_today()
            processed_count = due_alerts.count()
            
            for alert in due_alerts:
                self.stdout.write(f'Processing alert: {alert.title}')
            
            self.stdout.write(
                self.style.SUCCESS(f'Processed {processed_count} due alerts')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing due alerts: {str(e)}')
            )

    def _generate_missing_alerts(self):
        """Generate missing alerts synchronously"""
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
                self.stdout.write(f'Generated {len(alerts)} alerts for pollination record {record.id}')
            
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
                self.stdout.write(f'Generated {len(alerts)} alerts for germination record {record.id}')
            
            self.stdout.write(
                self.style.SUCCESS(f'Generated {generated_count} missing alerts')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error generating missing alerts: {str(e)}')
            )