FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from listener folder
COPY listener/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy listener python scripts
COPY listener/ .

CMD ["python", "listener.py"]
