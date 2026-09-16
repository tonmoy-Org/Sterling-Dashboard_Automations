FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=3000 \
    TZ=America/Los_Angeles

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium

COPY . /app/

EXPOSE 3000

CMD ["python", "run_standalone.py", "--live", "--days", "30", "--loop", "--port", "3000"]
