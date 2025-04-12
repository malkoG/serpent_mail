# Use the official Python image from the Docker Hub
FROM python:3.13-slim

ARG DJANGO_SETTINGS_MODULE

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install Node.js and npm
RUN apt-get update && apt-get install -y nodejs npm

# Set the working directory
WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock /app/

COPY README.md /app

# Copy the package folder so that Poetry can find it during install
COPY serpent_mail /app/serpent_mail

RUN pip install uv

# Copy the project files
COPY . /app/

# Expose the port the app runs on
EXPOSE 8000

ENV DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE

# Run the application
CMD ["sh", "-c", "uv run python manage.py migrate && uv run python manage.py runserver 0.0.0.0:8000"]
