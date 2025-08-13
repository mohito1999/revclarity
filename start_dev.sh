#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Function to handle cleanup
cleanup() {
    echo "Stopping services..."
    # Stop the background jobs
    if kill $FRONTEND_PID; then
        echo "Frontend stopped."
    fi
    if kill $BACKEND_PID; then
        echo "Backend server stopped."
    fi
    if kill $CELERY_PID; then
        echo "Celery worker stopped."
    fi
    # Stop docker-compose
    docker-compose down
    echo "All services stopped."
}

# Trap SIGINT (Ctrl+C) and call the cleanup function
trap cleanup SIGINT

# 1. Start Docker containers
echo "Starting Docker containers..."
docker-compose up -d
echo "Docker containers started."

# 2. Start Frontend
echo "Starting frontend..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

# 3. Start Backend Server
echo "Starting backend server..."
(cd backend && source venv/bin/activate && uvicorn app.main:app --reload) &
BACKEND_PID=$!

# 4. Start Celery Worker
echo "Starting Celery worker..."
(cd backend && source venv/bin/activate && celery -A app.celery_worker worker --loglevel=info) &
CELERY_PID=$!

echo "All services are running."
echo "Frontend PID: $FRONTEND_PID"
echo "Backend server PID: $BACKEND_PID"
echo "Celery worker PID: $CELERY_PID"
echo "Press Ctrl+C to stop all services."

# Wait for all background processes to complete
wait $FRONTEND_PID
wait $BACKEND_PID
wait $CELERY_PID
