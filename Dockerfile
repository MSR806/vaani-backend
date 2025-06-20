FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    nginx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Configure nginx
RUN rm -f /etc/nginx/sites-enabled/default
COPY service.nginx /etc/nginx/sites-enabled/ecs-vaani
RUN mkdir -p /run/gunicorn

COPY . .

EXPOSE 80

CMD ["/bin/bash", "init.sh"]
