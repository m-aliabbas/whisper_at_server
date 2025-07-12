#!/bin/bash
# start_with_redis.sh

# Start Whisper service in the background
uvicorn server:app --host :: --port ${PORT:-9007} --workers ${WORKERS:-4} &

# Wait for Whisper to be ready
echo "Waiting for Whisper..."
until curl -f http://localhost:9007/health 2>/dev/null; do
  sleep 2
done
echo "Whisper ready!"

# Start Redis worker in foreground
python /app/worker.py
