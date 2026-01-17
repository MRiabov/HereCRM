#!/bin/bash
set -e

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Determine which service to start
SERVICE=${1:-api}

if [ "$SERVICE" = "api" ]; then
    echo "Starting FastAPI API..."
    exec uvicorn src.main:app --host 0.0.0.0 --port 8000
elif [ "$SERVICE" = "ui" ]; then
    echo "Starting Streamlit UI..."
    exec streamlit run scripts/chat_ui.py --server.address 0.0.0.0
else
    echo "Unknown service: $SERVICE"
    echo "Usage: $0 [api|ui]"
    exit 1
fi
