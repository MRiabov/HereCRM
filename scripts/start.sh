#!/bin/bash
# Local Development Startup Script
# Starts both Backend and Frontend for local testing.

# Start FastAPI in the background
echo "Starting FastAPI on port 8000..."
uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# Wait for FastAPI to start (max 30 seconds)
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null; then
        echo "Backend is ready!"
        break
    fi
    sleep 1
done

# Start Streamlit in the foreground
# Streamlit will use the PORT environment variable if provided, or default to 8501
export PORT=${PORT:-8501}
echo "Starting Streamlit on port $PORT..."
streamlit run scripts/chat_ui.py --server.port $PORT --server.address 0.0.0.0
