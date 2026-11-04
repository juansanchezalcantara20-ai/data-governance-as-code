FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 GOVKIT_HOME=/app
RUN apt-get update && apt-get install -y --no-install-recommends make git && rm -rf /var/lib/apt/lists/*
COPY . .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .
# Reproduce the whole project: lint, validate governance, generate, run, verify, docs, tests.
CMD ["make", "all"]
