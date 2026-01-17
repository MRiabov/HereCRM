FROM astral/uv:python3.12-bookworm-slim

# Set the working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a single image
ENV UV_LINK_MODE=copy

# Install dependencies first for better caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application
COPY src ./src
COPY scripts ./scripts
RUN chmod +x scripts/start.sh

# Place uv on the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Create data directory for volume mount
RUN mkdir -p /app/data && chmod 777 /app/data
VOLUME /app/data

# Expose FastAPI port
EXPOSE 8000

# Command to run FastAPI
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
