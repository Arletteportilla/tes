"""
Management command to check Celery worker status and manage Celery operations.

This command provides utilities for monitoring and managing Celery workers,
queues, and scheduled tasks.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from celery import current_app
import json


class Command(BaseCommand):
    help = 'Check Celery worker status and manage Celery operations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['status', 'workers', 'queues', 'scheduled', 'purge', 'test'],
            default='status',
            help='Action to perform',
        )
        parser.add_argument(
            '--queue',
            type=str,
            help='Specific queue to operate on',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information',
        )

    def handle(self, *args, **options):
        action = options['action']
        queue = options.get('queue')
        verbose = options.get('verbose', False)
        
        self.stdout.write(
            self.style.SUCCESS('=== Celery Management Console ===')
        )
        
        try:
            if action == 'status':
                self.show_status(verbose)
            elif action == 'workers':
                self.show_workers(verbose)
            elif action == 'queues':
                self.show_queues(verbose)
            elif action == 'scheduled':
                self.show_scheduled_tasks(verbose)
            elif action == 'purge':
                self.purge_queue(queue)
            elif action == 'test':
                self.test_celery()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error executing action {action}: {str(e)}')
            )

    def show_status(self, verbose=False):
        """Show overall Celery status"""
        self.stdout.write('\n=== Celery Status ===')
        
        try:
            # Check if Celery is configured
            broker_url = getattr(settings, 'CELERY_BROKER_URL', 'Not configured')
            result_backend = getattr(settings, 'CELERY_RESULT_BACKEND', 'Not configured')
            
            self.stdout.write(f'Broker URL: {broker_url}')
            self.stdout.write(f'Result Backend: {result_backend}')
            
            # Check worker connectivity
            inspect = current_app.control.inspect()
            
            # Get active workers
            active_workers = inspect.active()
            if active_workers:
                self.stdout.write(
                    self.style.SUCCESS(f'Active Workers: {len(active_workers)}')
                )
                if verbose:
                    for worker, tasks in active_workers.items():
                        self.stdout.write(f'  - {worker}: {len(tasks)} active tasks')
            else:
                self.stdout.write(
                    self.style.WARNING('No active workers found')
                )
            
            # Get registered tasks
            registered_tasks = inspect.registered()
            if registered_tasks:
                total_tasks = sum(len(tasks) for tasks in registered_tasks.values())
                self.stdout.write(f'Registered Tasks: {total_tasks}')
                
                if verbose:
                    for worker, tasks in registered_tasks.items():
                        self.stdout.write(f'  Worker {worker}:')
                        for task in sorted(tasks):
                            self.stdout.write(f'    - {task}')
            
            # Check scheduled tasks (beat)
            try:
                scheduled = inspect.scheduled()
                if scheduled:
                    total_scheduled = sum(len(tasks) for tasks in scheduled.values())
                    self.stdout.write(f'Scheduled Tasks: {total_scheduled}')
                else:
                    self.stdout.write('No scheduled tasks')
            except Exception:
                self.stdout.write(
                    self.style.WARNING('Could not retrieve scheduled tasks (beat may not be running)')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to get Celery status: {str(e)}')
            )

    def show_workers(self, verbose=False):
        """Show detailed worker information"""
        self.stdout.write('\n=== Celery Workers ===')
        
        try:
            inspect = current_app.control.inspect()
            
            # Get worker stats
            stats = inspect.stats()
            if not stats:
                self.stdout.write(
                    self.style.WARNING('No worker statistics available')
                )
                return
            
            for worker, worker_stats in stats.items():
                self.stdout.write(f'\nWorker: {worker}')
                self.stdout.write(f'  Status: {self.style.SUCCESS("Online")}')
                self.stdout.write(f'  Pool: {worker_stats.get("pool", {}).get("implementation", "Unknown")}')
                self.stdout.write(f'  Processes: {worker_stats.get("pool", {}).get("max-concurrency", "Unknown")}')
                self.stdout.write(f'  Load Average: {worker_stats.get("rusage", {}).get("utime", "Unknown")}')
                
                if verbose:
                    self.stdout.write(f'  Broker: {worker_stats.get("broker", {})}')
                    self.stdout.write(f'  Clock: {worker_stats.get("clock", "Unknown")}')
                    
                    # Show active tasks
                    active = inspect.active()
                    if active and worker in active:
                        active_tasks = active[worker]
                        self.stdout.write(f'  Active Tasks: {len(active_tasks)}')
                        for task in active_tasks:
                            self.stdout.write(f'    - {task.get("name", "Unknown")} [{task.get("id", "Unknown")}]')
                    
                    # Show reserved tasks
                    reserved = inspect.reserved()
                    if reserved and worker in reserved:
                        reserved_tasks = reserved[worker]
                        self.stdout.write(f'  Reserved Tasks: {len(reserved_tasks)}')
                        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to get worker information: {str(e)}')
            )

    def show_queues(self, verbose=False):
        """Show queue information"""
        self.stdout.write('\n=== Celery Queues ===')
        
        try:
            # Show configured queues
            task_queues = getattr(settings, 'CELERY_TASK_QUEUES', {})
            if task_queues:
                self.stdout.write('Configured Queues:')
                for queue_name, queue_config in task_queues.items():
                    self.stdout.write(f'  - {queue_name}')
                    if verbose:
                        self.stdout.write(f'    Exchange: {queue_config.get("exchange", "Unknown")}')
                        self.stdout.write(f'    Routing Key: {queue_config.get("routing_key", "Unknown")}')
            
            # Show active queues
            inspect = current_app.control.inspect()
            active_queues = inspect.active_queues()
            
            if active_queues:
                self.stdout.write('\nActive Queues:')
                for worker, queues in active_queues.items():
                    self.stdout.write(f'  Worker {worker}:')
                    for queue in queues:
                        self.stdout.write(f'    - {queue.get("name", "Unknown")}')
                        if verbose:
                            self.stdout.write(f'      Exchange: {queue.get("exchange", {}).get("name", "Unknown")}')
                            self.stdout.write(f'      Routing Key: {queue.get("routing_key", "Unknown")}')
            else:
                self.stdout.write(
                    self.style.WARNING('No active queues found')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to get queue information: {str(e)}')
            )

    def show_scheduled_tasks(self, verbose=False):
        """Show scheduled (beat) tasks"""
        self.stdout.write('\n=== Scheduled Tasks (Beat) ===')
        
        try:
            # Show configured beat schedule
            beat_schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
            if beat_schedule:
                self.stdout.write('Configured Scheduled Tasks:')
                for task_name, task_config in beat_schedule.items():
                    self.stdout.write(f'  - {task_name}')
                    self.stdout.write(f'    Task: {task_config.get("task", "Unknown")}')
                    self.stdout.write(f'    Schedule: {task_config.get("schedule", "Unknown")}')
                    
                    if verbose:
                        options = task_config.get('options', {})
                        if options:
                            self.stdout.write(f'    Options: {options}')
            else:
                self.stdout.write('No scheduled tasks configured')
            
            # Try to get runtime scheduled tasks
            inspect = current_app.control.inspect()
            try:
                scheduled = inspect.scheduled()
                if scheduled:
                    self.stdout.write('\nCurrently Scheduled Tasks:')
                    for worker, tasks in scheduled.items():
                        if tasks:
                            self.stdout.write(f'  Worker {worker}: {len(tasks)} tasks')
                            if verbose:
                                for task in tasks:
                                    self.stdout.write(f'    - {task.get("request", {}).get("task", "Unknown")}')
                else:
                    self.stdout.write('\nNo tasks currently scheduled')
            except Exception:
                self.stdout.write(
                    self.style.WARNING('\nCould not retrieve runtime scheduled tasks (beat may not be running)')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to get scheduled task information: {str(e)}')
            )

    def purge_queue(self, queue_name=None):
        """Purge tasks from queue"""
        if not queue_name:
            queue_name = 'default'
            
        self.stdout.write(f'\n=== Purging Queue: {queue_name} ===')
        
        try:
            # Confirm purge operation
            confirm = input(f'Are you sure you want to purge all tasks from queue "{queue_name}"? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Purge operation cancelled')
                return
            
            # Purge the queue
            result = current_app.control.purge()
            self.stdout.write(
                self.style.SUCCESS(f'Queue "{queue_name}" purged successfully')
            )
            
            if result:
                self.stdout.write(f'Purged tasks: {result}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to purge queue: {str(e)}')
            )

    def test_celery(self):
        """Test Celery by running a simple task"""
        self.stdout.write('\n=== Testing Celery ===')
        
        try:
            # Import and run debug task
            from sistema_polinizacion.celery import debug_task
            
            self.stdout.write('Sending test task...')
            result = debug_task.delay()
            
            self.stdout.write(f'Task ID: {result.id}')
            self.stdout.write('Waiting for result...')
            
            # Wait for result with timeout
            try:
                task_result = result.get(timeout=10)
                self.stdout.write(
                    self.style.SUCCESS(f'Task completed successfully: {task_result}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Task failed or timed out: {str(e)}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to test Celery: {str(e)}')
            )