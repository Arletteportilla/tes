#!/bin/bash

# Celery Management Script for Sistema de Polinización y Germinación
# This script provides utilities for managing Celery workers, beat, and monitoring

set -e

# Configuration
PROJECT_NAME="sistema_polinizacion"
CELERY_APP="sistema_polinizacion"
LOG_DIR="logs"
PID_DIR="pids"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure directories exist
mkdir -p $LOG_DIR $PID_DIR

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Function to check if process is running
is_running() {
    local pidfile=$1
    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pidfile"
            return 1
        fi
    fi
    return 1
}

# Function to start Celery worker
start_worker() {
    local queue=${1:-"default"}
    local concurrency=${2:-4}
    local pidfile="$PID_DIR/celery_worker_${queue}.pid"
    local logfile="$LOG_DIR/celery_worker_${queue}.log"
    
    if is_running "$pidfile"; then
        print_warning "Celery worker for queue '$queue' is already running"
        return 0
    fi
    
    print_status "Starting Celery worker for queue '$queue'..."
    
    celery -A $CELERY_APP worker \
        --loglevel=info \
        --concurrency=$concurrency \
        --queues=$queue \
        --pidfile="$pidfile" \
        --logfile="$logfile" \
        --detach
    
    if is_running "$pidfile"; then
        print_status "Celery worker for queue '$queue' started successfully"
    else
        print_error "Failed to start Celery worker for queue '$queue'"
        return 1
    fi
}

# Function to start Celery beat
start_beat() {
    local pidfile="$PID_DIR/celery_beat.pid"
    local logfile="$LOG_DIR/celery_beat.log"
    
    if is_running "$pidfile"; then
        print_warning "Celery beat is already running"
        return 0
    fi
    
    print_status "Starting Celery beat..."
    
    celery -A $CELERY_APP beat \
        --loglevel=info \
        --pidfile="$pidfile" \
        --logfile="$logfile" \
        --detach
    
    if is_running "$pidfile"; then
        print_status "Celery beat started successfully"
    else
        print_error "Failed to start Celery beat"
        return 1
    fi
}

# Function to start Flower monitoring
start_flower() {
    local port=${1:-5555}
    local pidfile="$PID_DIR/celery_flower.pid"
    local logfile="$LOG_DIR/celery_flower.log"
    
    if is_running "$pidfile"; then
        print_warning "Celery flower is already running"
        return 0
    fi
    
    print_status "Starting Celery flower on port $port..."
    
    celery -A $CELERY_APP flower \
        --port=$port \
        --pidfile="$pidfile" \
        --logfile="$logfile" \
        --detach
    
    if is_running "$pidfile"; then
        print_status "Celery flower started successfully on http://localhost:$port"
    else
        print_error "Failed to start Celery flower"
        return 1
    fi
}

# Function to stop service
stop_service() {
    local service=$1
    local pidfile="$PID_DIR/celery_${service}.pid"
    
    if ! is_running "$pidfile"; then
        print_warning "Celery $service is not running"
        return 0
    fi
    
    local pid=$(cat "$pidfile")
    print_status "Stopping Celery $service (PID: $pid)..."
    
    kill -TERM "$pid"
    
    # Wait for graceful shutdown
    local count=0
    while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 30 ]; do
        sleep 1
        count=$((count + 1))
    done
    
    if ps -p "$pid" > /dev/null 2>&1; then
        print_warning "Graceful shutdown failed, forcing kill..."
        kill -KILL "$pid"
    fi
    
    rm -f "$pidfile"
    print_status "Celery $service stopped"
}

# Function to show status
show_status() {
    print_header "Celery Services Status"
    
    # Check worker status
    for pidfile in $PID_DIR/celery_worker_*.pid; do
        if [ -f "$pidfile" ]; then
            local queue=$(basename "$pidfile" .pid | sed 's/celery_worker_//')
            if is_running "$pidfile"; then
                local pid=$(cat "$pidfile")
                print_status "Worker ($queue): Running (PID: $pid)"
            else
                print_error "Worker ($queue): Not running"
            fi
        fi
    done
    
    # Check beat status
    local beat_pidfile="$PID_DIR/celery_beat.pid"
    if is_running "$beat_pidfile"; then
        local pid=$(cat "$beat_pidfile")
        print_status "Beat: Running (PID: $pid)"
    else
        print_error "Beat: Not running"
    fi
    
    # Check flower status
    local flower_pidfile="$PID_DIR/celery_flower.pid"
    if is_running "$flower_pidfile"; then
        local pid=$(cat "$flower_pidfile")
        print_status "Flower: Running (PID: $pid)"
    else
        print_error "Flower: Not running"
    fi
    
    # Show Celery inspect info
    print_header "Celery Cluster Status"
    celery -A $CELERY_APP inspect active 2>/dev/null || print_warning "No active workers found"
}

# Function to restart all services
restart_all() {
    print_header "Restarting All Celery Services"
    
    # Stop all services
    for pidfile in $PID_DIR/celery_*.pid; do
        if [ -f "$pidfile" ]; then
            local service=$(basename "$pidfile" .pid | sed 's/celery_//')
            stop_service "$service"
        fi
    done
    
    # Wait a moment
    sleep 2
    
    # Start services
    start_worker "default" 4
    start_worker "alerts" 2
    start_worker "reports" 2
    start_worker "system" 1
    start_beat
    start_flower
}

# Function to purge all queues
purge_queues() {
    print_warning "This will purge ALL tasks from ALL queues!"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        print_status "Purging all queues..."
        celery -A $CELERY_APP purge -f
        print_status "All queues purged"
    else
        print_status "Purge cancelled"
    fi
}

# Function to show logs
show_logs() {
    local service=${1:-"worker_default"}
    local logfile="$LOG_DIR/celery_${service}.log"
    
    if [ -f "$logfile" ]; then
        tail -f "$logfile"
    else
        print_error "Log file not found: $logfile"
        print_status "Available log files:"
        ls -la $LOG_DIR/celery_*.log 2>/dev/null || print_warning "No log files found"
    fi
}

# Main script logic
case "${1:-help}" in
    start)
        case "${2:-all}" in
            worker)
                start_worker "${3:-default}" "${4:-4}"
                ;;
            beat)
                start_beat
                ;;
            flower)
                start_flower "${3:-5555}"
                ;;
            all)
                start_worker "default" 4
                start_worker "alerts" 2
                start_worker "reports" 2
                start_worker "system" 1
                start_beat
                start_flower
                ;;
            *)
                print_error "Unknown service: $2"
                exit 1
                ;;
        esac
        ;;
    stop)
        case "${2:-all}" in
            worker)
                stop_service "worker_${3:-default}"
                ;;
            beat)
                stop_service "beat"
                ;;
            flower)
                stop_service "flower"
                ;;
            all)
                for pidfile in $PID_DIR/celery_*.pid; do
                    if [ -f "$pidfile" ]; then
                        local service=$(basename "$pidfile" .pid | sed 's/celery_//')
                        stop_service "$service"
                    fi
                done
                ;;
            *)
                print_error "Unknown service: $2"
                exit 1
                ;;
        esac
        ;;
    restart)
        restart_all
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    purge)
        purge_queues
        ;;
    test)
        print_status "Testing Celery configuration..."
        python manage.py celery_status --action=test
        ;;
    help|*)
        print_header "Celery Manager - Sistema de Polinización y Germinación"
        echo "Usage: $0 {start|stop|restart|status|logs|purge|test} [service] [options]"
        echo ""
        echo "Commands:"
        echo "  start [service]     Start Celery service(s)"
        echo "    - worker [queue] [concurrency]  Start worker for specific queue"
        echo "    - beat                          Start beat scheduler"
        echo "    - flower [port]                 Start flower monitoring"
        echo "    - all                           Start all services"
        echo ""
        echo "  stop [service]      Stop Celery service(s)"
        echo "    - worker [queue]                Stop worker for specific queue"
        echo "    - beat                          Stop beat scheduler"
        echo "    - flower                        Stop flower monitoring"
        echo "    - all                           Stop all services"
        echo ""
        echo "  restart             Restart all services"
        echo "  status              Show status of all services"
        echo "  logs [service]      Show logs for service (default: worker_default)"
        echo "  purge               Purge all queues (removes all pending tasks)"
        echo "  test                Test Celery configuration"
        echo ""
        echo "Examples:"
        echo "  $0 start worker alerts 2    # Start alerts worker with 2 processes"
        echo "  $0 stop worker default       # Stop default worker"
        echo "  $0 logs beat                 # Show beat logs"
        echo "  $0 status                    # Show all services status"
        ;;
esac