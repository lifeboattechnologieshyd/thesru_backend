#!/bin/bash

set -e

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi


# Detect CPU cores cross-platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    CPU_CORES=$(grep -c ^processor /proc/cpuinfo)
elif [[ "$OSTYPE" == "darwin"* ]]; then
    CPU_CORES=$(sysctl -n hw.ncpu)
else
    CPU_CORES=1 # Default to 1 if unknown OS
fi


# Default values
PORT=8000
GUNICORN_WORKERS=${GUNICORN_WORKERS:-1}
GUNICORN_THREADS_PER_WORKER=${GUNICORN_THREADS_PER_WORKER:-8}
PROJECT_ROOT_DIR=${PROJECT_ROOT_DIR:-"/project"}
LOG_DIR=${LOG_DIR:-"/logs"}
DEPLOYMENT_MODE=${DEPLOYMENT_MODE:-"FULL"}


# Parse named arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port=*)
            PORT="${1#*=}"
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --gunicorn-workers=*)
            GUNICORN_WORKERS="${1#*=}"
            shift
            ;;
        --gunicorn-workers)
            GUNICORN_WORKERS="$2"
            shift 2
            ;;
        --gunicorn-threads-per-worker=*)
            GUNICORN_THREADS_PER_WORKER="${1#*=}"
            shift
            ;;
        --gunicorn-threads-per-worker)
            GUNICORN_THREADS_PER_WORKER="$2"
            shift 2
            ;;
        --project-root-dir=*)
            PROJECT_ROOT_DIR="${1#*=}"
            shift
            ;;
        --project-root-dir)
            PROJECT_ROOT_DIR="$2"
            shift 2
            ;;
        --log-dir=*)
            LOG_DIR="${1#*=}"
            shift
            ;;
        --log-dir)
            LOG_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--port=8000] [--gunicorn-workers=1] [--gunicorn-threads-per-worker=2] [--project-root-dir=/project] [--log-dir=/logs]"
            exit 0
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# Validate Port
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -le 0 ] || [ "$PORT" -gt 65535 ]; then
    echo "Invalid port: $PORT"
    exit 1
fi


echo "Starting services with configuration:"
echo "Port: $PORT"
echo "Gunicorn workers: $GUNICORN_WORKERS"
echo "Gunicorn threads per worker: $GUNICORN_THREADS_PER_WORKER"
echo "Project root directory: $PROJECT_ROOT_DIR"
echo "Log directory: $LOG_DIR"
echo "Deployment mode: $DEPLOYMENT_MODE"

# Running migrations and collecting static files
cd $PROJECT_ROOT_DIR
python manage.py migrate
python manage.py collectstatic --noinput


# Function to start cron safely across OS types
start_cron() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Detected macOS: Skipping cron daemon startup (macOS uses launchd instead)"
        return 0
    fi

    if command -v cron >/dev/null 2>&1; then
        echo "Starting cron using 'cron'..."
        cron
    elif command -v crond >/dev/null 2>&1; then
        echo "Starting cron using 'crond'..."
        crond
    elif [ -x /etc/init.d/cron ]; then
        echo "Starting cron using '/etc/init.d/cron'..."
        /etc/init.d/cron start
    else
        echo "Warning: Cron service not available on this system. Skipping cron startup."
    fi
}


# Start Alloy in the background
echo "Starting Alloy..."
alloy run --server.http.listen-addr=0.0.0.0:12345 --storage.path=/var/lib/alloy/data ${PROJECT_ROOT_DIR}/config.alloy &

# Store Alloy's PID
ALLOY_PID=$!

echo "Alloy started with PID: $ALLOY_PID"


# CRON deployment mode
if [ "$DEPLOYMENT_MODE" == "CRON" ]; then
    echo "Scheduling Cronjobs..."
    start_cron
    cd $PROJECT_ROOT_DIR
    python manage.py crontab add
    exec tail -f ${PROJECT_ROOT_DIR}${LOG_DIR}/django.log
fi


# API deployment mode
if [ "$DEPLOYMENT_MODE" == "API" ]; then
    echo "Starting Gunicorn..."
    cd $PROJECT_ROOT_DIR
    exec gunicorn \
        --bind 0.0.0.0:$PORT \
        --workers $GUNICORN_WORKERS \
        --threads $GUNICORN_THREADS_PER_WORKER \
        --worker-class gthread \
        --timeout 0 \
        --graceful-timeout 30 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 200 \
        --access-logfile '-' \
        --error-logfile '-' \
        --log-level info \
        config.wsgi:application
fi


# FULL deployment mode
if [ "$DEPLOYMENT_MODE" == "FULL" ]; then
    echo "Scheduling Cronjobs..."
    start_cron
    cd $PROJECT_ROOT_DIR
    python manage.py crontab add

    echo "Starting Gunicorn..."
    exec gunicorn \
        --bind 0.0.0.0:$PORT \
        --workers $GUNICORN_WORKERS \
        --threads $GUNICORN_THREADS_PER_WORKER \
        --worker-class gthread \
        --timeout 0 \
        --graceful-timeout 30 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 200 \
        --access-logfile '-' \
        --error-logfile '-' \
        --log-level info \
        config.wsgi:application
fi
