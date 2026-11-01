# Use official Python image as base
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose the port Cloud Run will use
ENV PORT=8080
EXPOSE 8080

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install gunicorn

# Copy project files
COPY . /app/

# Provide a default DJANGO_SECRET_KEY for build-time steps
ARG DJANGO_SECRET_KEY=django-insecure-buildkey
ENV DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}

# Collect static files if you use Django staticfiles
RUN python manage.py collectstatic --noinput

# Run Gunicorn, binding to the port from $PORT
CMD ["sh", "-c", "gunicorn interpascend1_1.wsgi:application --bind 0.0.0.0:$PORT --log-level info"]
