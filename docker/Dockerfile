FROM python:3.13-slim

WORKDIR /app

# Installa uv
RUN pip install --no-cache-dir uv

# Copia dipendenze e installa
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copia sorgenti
COPY rules/ rules/
COPY src/ src/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
