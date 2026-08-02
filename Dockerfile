FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY config ./config
COPY registries ./registries
COPY data/snapshots ./data/snapshots
COPY app.py ./

RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.address=0.0.0.0"]
