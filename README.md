# Vaani Backend

A FastAPI-based backend service for book authors' text autocomplete functionality.

## Setup

1. Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
# Edit .env with your values
```

2. Build and run with Docker Compose:

```bash
docker-compose up --build
```

3. Apply database migrations:

```bash
# Inside the container
docker-compose exec server alembic upgrade head

# Or locally (with .venv active)
alembic upgrade head
```

The API will be available at `http://localhost:80` or simply `http://localhost`

## Database Migrations

```bash
# Create new migration after schema changes
alembic revision --autogenerate -m "description"

# Apply pending migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Default Settings

After setting up the database, initialize the application's default settings:

```bash
# Inside the container
docker-compose exec server python scripts/create_default_settings.py

# Or locally (with .venv active)
python scripts/create_default_settings.py
```

This script creates the necessary AI model settings with default values for scene generation, chapter content, and other features.

## API Documentation

- Interactive API docs (Swagger UI): `http://localhost/docs`
- Alternative API docs (ReDoc): `http://localhost/redoc`
