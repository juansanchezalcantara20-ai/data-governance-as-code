FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 GOVKIT_HOME=/app
RUN apt-get update && apt-get install -y --no-install-recommends make && rm -rf /var/lib/apt/lists/*
COPY . .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .
EXPOSE 8501
# Reproduce the project, then serve the UI if present.
CMD ["sh", "-c", "make validate generate run && if [ -f app/app.py ]; then streamlit run app/app.py --server.address=0.0.0.0 --server.headless=true; fi"]
