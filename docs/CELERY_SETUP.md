# Celery Configuration Guide

## Overview

This document describes the Celery configuration for the Sistema de Polinización y Germinación project. Celery is used for handling asynchronous tasks including alert generation, report processing, and system maintenance.

## Architecture

### Components

1. **Celery Worker**: Processes asynchronous tasks
2. **Celery Beat**: Schedules periodic tasks
3. **Redis**: Message broker and result backend
4. **Flower**: Web-based monitoring tool

### Queues

The system uses multiple queues for task organization:

- `default`: General purpose tasks
- `alerts`: Alert generation and processing
- `reports`: Report generation and export
- `system`: System maintenance tasks

## Installation

### Prerequisites

1. **Redis Server**: Required as message broker
   ```bash
   # Windows (using Chocolatey)
   choco install redis-64
   
   # Or download from: https://github.com/microsoftarchive/redis/releases
   ```

2. **Python Dependencies**: Install from requirements.txt
   ```bash
   pip install -r requirements.txt
   ```

### Environment Configuration

Add the following variables to your `.env` file:

```env
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=False
CELERY_WORKER_PREFETCH_MULTIPLIER=1
```

## Running Celery Services

### Option 1: Using Management Scripts

#### Windows
```cmd
# Start all services
scripts\celery_manager.bat start all

# Start specific services
scripts\celery_manager.bat start worker default 4
scripts\celery_manager.bat start beat
scripts\celery_manager.bat start flower

# Check status
scripts\celery_manager.bat status

# View logs
scripts\celery_manager.bat logs worker_default
```

#### Linux/Mac
```bash
# Make script executable
chmod +x scripts/celery_manager.sh

# Start all services
./scripts/celery_manager.sh start all

# Start specific services
./scripts/celery_manager.sh start worker default 4
./scripts/celery_manager.sh start beat
./scripts/celery_manager.sh start flower

# Check status
./scripts/celery_manager.sh status
```

### Option 2: Manual Commands

#### Start Worker
```bash
celery -A sistema_polinizacion worker --loglevel=info --concurrency=4
```

#### Start Beat Scheduler
```bash
celery -A sistema_polinizacion beat --loglevel=info
```

#### Start Flower Monitoring
```bash
celery -A sistema_polinizacion flower --port=5555
```

### Option 3: Docker Compose

```bash
# Start all Celery services with Docker
docker-compose -f docker-compose.celery.yml up -d

# View logs
docker-compose -f docker-compose.celery.yml logs -f

# Stop services
docker-compose -f docker-compose.celery.yml down
```

## Scheduled Tasks

The system includes several periodic tasks:

### Alert Tasks
- **Process Alerts**: Every hour at minute 0
- **Weekly Alerts**: Monday at 8:00 AM
- **Preventive Alerts**: Daily at 9:00 AM
- **Frequent Alerts**: Daily at 10:00 AM
- **Cleanup Old Alerts**: Sunday at 2:00 AM

### System Tasks
- **Health Check**: Daily at 6:00 AM
- **Log Cleanup**: Configurable retention period
- **Database Backup**: Configurable schedule

## Monitoring

### Flower Web Interface

Access the Flower monitoring interface at: http://localhost:5555

Features:
- Real-time task monitoring
- Worker status and statistics
- Task history and results
- Queue management

### Django Admin Integration

Celery Beat schedules can be managed through Django admin when using `django-celery-beat`.

### Management Commands

#### Check Celery Status
```bash
python manage.py celery_status --action=status --verbose
```

#### Test Celery Configuration
```bash
python manage.py celery_status --action=test
```

#### Check Settings Configuration
```bash
python manage.py check_settings --environment=development --verbose
```

## Task Development

### Creating New Tasks

1. **Define Task in App**:
   ```python
   # alerts/tasks.py
   from celery import shared_task
   
   @shared_task(bind=True, max_retries=3)
   def process_alert(self, alert_id):
       try:
           # Task logic here
           return {"status": "success", "alert_id": alert_id}
       except Exception as exc:
           raise self.retry(exc=exc, countdown=60)
   ```

2. **Add to Beat Schedule** (if periodic):
   ```python
   # sistema_polinizacion/celery.py
   app.conf.beat_schedule.update({
       'my-periodic-task': {
           'task': 'alerts.tasks.process_alert',
           'schedule': crontab(minute=0),  # Every hour
           'args': (123,)  # Task arguments
       }
   })
   ```

3. **Configure Task Routing**:
   ```python
   # sistema_polinizacion/celery.py
   app.conf.task_routes.update({
       'alerts.tasks.*': {'queue': 'alerts'},
   })
   ```

### Task Best Practices

1. **Use `bind=True`** for retry functionality
2. **Set `max_retries`** to prevent infinite loops
3. **Use exponential backoff** for retries
4. **Log task execution** for debugging
5. **Handle exceptions gracefully**
6. **Keep tasks idempotent** when possible

## Troubleshooting

### Common Issues

#### 1. Redis Connection Error
```
Error: Redis connection failed
```
**Solution**: Ensure Redis server is running
```bash
# Windows
redis-server

# Linux/Mac
sudo systemctl start redis
```

#### 2. No Active Workers
```
Warning: No active workers found
```
**Solution**: Start Celery worker
```bash
celery -A sistema_polinizacion worker --loglevel=info
```

#### 3. Tasks Not Executing
**Check**:
1. Worker is running and connected
2. Task is properly registered
3. Queue routing is correct
4. No syntax errors in task code

#### 4. Beat Not Scheduling Tasks
**Check**:
1. Celery beat is running
2. Beat schedule is properly configured
3. Database migrations are applied (for django-celery-beat)

### Debugging Commands

#### Inspect Active Tasks
```bash
celery -A sistema_polinizacion inspect active
```

#### Inspect Registered Tasks
```bash
celery -A sistema_polinizacion inspect registered
```

#### Inspect Scheduled Tasks
```bash
celery -A sistema_polinizacion inspect scheduled
```

#### Purge All Queues
```bash
celery -A sistema_polinizacion purge
```

### Log Files

Celery logs are stored in the `logs/` directory:
- `celery_worker_default.log`: Default worker logs
- `celery_worker_alerts.log`: Alerts worker logs
- `celery_beat.log`: Beat scheduler logs
- `celery_flower.log`: Flower monitoring logs

## Production Deployment

### Systemd Services (Linux)

Create systemd service files for production deployment:

#### Worker Service
```ini
# /etc/systemd/system/celery-worker.service
[Unit]
Description=Celery Worker
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
EnvironmentFile=/path/to/.env
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/celery -A sistema_polinizacion worker --detach --pidfile=/var/run/celery/worker.pid --logfile=/var/log/celery/worker.log --loglevel=info
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Beat Service
```ini
# /etc/systemd/system/celery-beat.service
[Unit]
Description=Celery Beat
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
EnvironmentFile=/path/to/.env
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/celery -A sistema_polinizacion beat --detach --pidfile=/var/run/celery/beat.pid --logfile=/var/log/celery/beat.log --loglevel=info
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

### Process Management

#### Supervisor Configuration
```ini
# /etc/supervisor/conf.d/celery.conf
[program:celery-worker]
command=/path/to/venv/bin/celery -A sistema_polinizacion worker --loglevel=info
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600

[program:celery-beat]
command=/path/to/venv/bin/celery -A sistema_polinizacion beat --loglevel=info
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat.log
autostart=true
autorestart=true
startsecs=10
```

## Security Considerations

1. **Redis Security**: Configure Redis authentication and network restrictions
2. **Task Validation**: Validate all task inputs
3. **Resource Limits**: Set appropriate task time limits and memory limits
4. **Monitoring**: Monitor task execution and system resources
5. **Error Handling**: Don't expose sensitive information in error messages

## Performance Optimization

1. **Worker Concurrency**: Adjust based on CPU cores and task types
2. **Prefetch Multiplier**: Set to 1 for long-running tasks
3. **Task Routing**: Use separate queues for different task types
4. **Result Backend**: Consider disabling if results aren't needed
5. **Connection Pooling**: Configure Redis connection pooling

## Backup and Recovery

1. **Redis Persistence**: Configure Redis RDB and AOF persistence
2. **Task State**: Important tasks should be idempotent
3. **Monitoring**: Set up alerts for worker failures
4. **Graceful Shutdown**: Use proper signal handling for worker shutdown