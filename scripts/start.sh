#!/bin/bash

# Start FastAPI in the background
echo "Starting FastAPI on port 8000..."
uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# Start Streamlit in the foreground
# Streamlit will use the PORT environment variable if provided, or default to 8501
export PORT=${PORT:-8501}
echo "Starting Streamlit on port $PORT..."
streamlit run scripts/chat_ui.py --server.port $PORT --server.address 0.0.0.0
