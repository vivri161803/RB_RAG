# Stage 1: Builder
FROM python:3.13-slim AS builder

WORKDIR /app

# Installa uv
RUN pip install --no-cache-dir uv

# Variabili d'ambiente per uv per compilare bytecode ed evitare link
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copia solo i file delle dipendenze
COPY pyproject.toml uv.lock ./

# Installa le dipendenze in un virtual environment separato senza installare il progetto root
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: Runtime
FROM python:3.13-slim

# Crea utente e gruppo non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Installa dipendenze di sistema minime se necessarie (es. curl per l'healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copia il virtual environment dal builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copia le sorgenti con i giusti permessi
COPY --chown=appuser:appuser rules/ rules/
COPY --chown=appuser:appuser src/ src/

# Aggiungi il venv al PATH in modo da poter usare uvicorn direttamente
ENV PATH="/app/.venv/bin:$PATH"

# Cambia l'utente in uno non privilegiato
USER appuser

EXPOSE 8000

# Esegui uvicorn direttamente tramite il venv
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
