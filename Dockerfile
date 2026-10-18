FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /srv
COPY apps/api/pyproject.toml /srv/pyproject.toml
COPY apps/api/aura_api /srv/aura_api
RUN pip install --no-cache-dir . && useradd --create-home --uid 10001 aura
USER aura
EXPOSE 8000
CMD ["uvicorn", "aura_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
