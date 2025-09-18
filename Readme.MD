# Theatre API

A production-ready Django REST Framework (DRF) service for managing theatre domain entities (plays, actors, performances, halls/seats, images, bookings, etc.) with JWT authentication, OpenAPI documentation, Dockerized local setup, and CI-friendly testing.

---

## Table of Contents
- [Stack](#stack)
- [Quick Start (Docker)](#quick-start-docker)
- [Local Development (without Docker)](#local-development-without-docker)
- [Environment Variables](#environment-variables)
- [Database & Migrations](#database--migrations)
- [Create Superuser](#create-superuser)
- [Load Demo Data](#load-demo-data)
- [Run Tests & Lint](#run-tests--lint)
- [URLs & Docs](#urls--docs)
- [Auth (JWT)](#auth-jwt)
- [Pagination](#pagination)
- [Healthchecks](#healthchecks)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Makefile (optional)](#makefile-optional)
- [Troubleshooting](#troubleshooting)

---

## Stack
- **Python** 3.12+
- **Django** 5.x
- **Django REST Framework**
- **drf-spectacular** (OpenAPI 3 docs)
- **PostgreSQL** 15+
- **SimpleJWT** for access/refresh tokens
- **Docker / Docker Compose**
- **Whitenoise** for static files (optional)

---

## Quick Start (Docker)
Requirements: Docker Engine 24+, Docker Compose V2

```bash
# 1) Copy env template and adjust
cp .env.example .env  # if available

# 2) Build & start
docker compose up --build
# or detached
docker compose up -d --build

# 3) Apply migrations
docker compose exec app python manage.py migrate

# 4) Create superuser (see below)

# 5) Open documentation
#   Swagger UI:   http://localhost:8000/api/doc/swagger/
#   ReDoc:        http://localhost:8000/api/doc/redoc
```

**Default services:**
- **app** – Django API at `http://localhost:8000`
- **db** – PostgreSQL at `localhost:5432`

> If you see `password authentication failed for user` or `could not translate host name "db"` – check **.env** and ensure containers are running: `docker compose ps`.

---

## Local Development (without Docker)
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# set env vars (see .env.example) or use dotenv
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

---

## Environment Variables
Create `.env` in the project root. Example:

```dotenv
# Django
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
TIME_ZONE=Europe/Kyiv

# Database
POSTGRES_DB=theatre_db
POSTGRES_USER=theatre_user
POSTGRES_PASSWORD=theatre_pass
POSTGRES_HOST=db           # in Docker; use 127.0.0.1 for local dev
POSTGRES_PORT=5432
DATABASE_URL=postgres://theatre_user:theatre_pass@db:5432/theatre_db

# SimpleJWT
ACCESS_TOKEN_LIFETIME_MIN=30
REFRESH_TOKEN_LIFETIME_DAYS=7

# DRF
DEFAULT_PAGE_SIZE=10

# Static/Media
MEDIA_ROOT=media
MEDIA_URL=/media/
STATIC_URL=/static/
```

In `services/settings.py` ensure these values are loaded (via `os.environ` or `django-environ`). Also add `MEDIA_ROOT`/`MEDIA_URL` and mount a volume to `./media` in `docker-compose.yaml`.

---

## Database & Migrations
```bash
# create or modify models, then

docker compose exec app python manage.py makemigrations

docker compose exec app python manage.py migrate
```

---

## Create Superuser
Interactive:
```bash
docker compose exec app python manage.py createsuperuser
```

Non-interactive (CI/seed):
```bash
# set in .env
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=adminpass

# then run
docker compose exec app python manage.py createsuperuser --noinput
```

---

## Load Demo Data
Place fixtures (e.g. `theatre_test_data.json`) in the project root or app folder and run:
```bash
docker compose exec app python manage.py loaddata theatre_test_data.json
```
If you see errors like *no such column*:
1) Ensure migrations are applied; 2) Fixture fields match current models.

---

## Run Tests & Lint
```bash
# tests
docker compose exec app python manage.py test -v 2

# lint/format (optional)
pre-commit install
pre-commit run --all-files
```

---

## URLs & Docs
Main router in `services/urls.py`:
```py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/theatre/", include("theatre.urls", namespace="theatre")),
    path("api/user/", include("user.urls", namespace="user")),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/doc/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/doc/redoc", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- **Schema (JSON):** `/api/schema/`
- **Swagger UI:** `/api/doc/swagger/`
- **ReDoc:** `/api/doc/redoc`

---

## Auth (JWT)
The `user` app typically exposes:
- `POST /api/user/register/` – create account (if implemented)
- `POST /api/user/token/` – obtain access/refresh token pair
- `POST /api/user/token/refresh/` – refresh access token
- `GET  /api/user/me/` – retrieve/update current user (authenticated)

Example:
```bash
# obtain tokens
curl -X POST http://localhost:8000/api/user/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"adminpass"}'

# authorized request
curl http://localhost:8000/api/theatre/plays/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

You can refresh the access token multiple times while the refresh token is valid.

---

## Pagination
Global pagination in DRF settings:
```py
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(os.getenv("DEFAULT_PAGE_SIZE", 10)),
}
```

---

## Healthchecks
Add a lightweight endpoint or use DB check in a management command. Example path:
```
GET /health/  -> { "status": "ok" }
```
Use in `docker-compose.yaml` as a `healthcheck` for the app.

---

## Project Structure
```
py-theatre-api/
├─ media/
│  └─ uploads/
├─ services/
│  ├─ __init__.py
│  ├─ asgi.py
│  ├─ settings.py
│  ├─ urls.py
│  └─ wsgi.py
├─ static/
├─ templates/
├─ theatre/
│  ├─ management/
│  ├─ migrations/
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ filters.py
│  ├─ models.py
│  ├─ permissions.py
│  ├─ serializers.py
│  ├─ urls.py
│  ├─ utils.py
│  └─ views.py
├─ user/
│  ├─ migrations/
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ models.py
│  ├─ serializers.py
│  ├─ tests.py
│  ├─ urls.py
│  └─ views.py
├─ .dockerignore
├─ .env
├─ .flake8
├─ .gitignore
├─ docker-compose.yaml
├─ Dockerfile
├─ entrypoint.sh
├─ manage.py
├─ pyproject.toml
├─ README.md
├─ requirements.txt
└─ theatre_test_data.json
```

---

## API Reference
Adapt to your actual views and endpoints.

### Public
- `GET /api/theatre/plays/` – list plays
- `GET /api/theatre/plays/{id}/` – play details
- `GET /api/theatre/performances/` – list performances with optional date filters
- `GET /api/theatre/actors/` – list actors
- `GET /api/theatre/genres/` – list genres (if implemented)

### Authenticated
- `POST /api/theatre/plays/{id}/upload-image/` – upload play poster (multipart)
- `POST /api/theatre/bookings/` – create booking
- `GET  /api/theatre/bookings/mine/` – list user bookings

Media uploads:
- `MEDIA_ROOT=media`, files stored in `./media/uploads/` (configure in model/Storage)
- In production serve via CDN/web server; in development `static()` handles this.

---

## Makefile (optional)
```Makefile
.PHONY: up down build logs shell test lint fmt migrate makemigrations

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f app

shell:
	docker compose exec app python manage.py shell

test:
	docker compose exec app python manage.py test -v 2

migrate:
	docker compose exec app python manage.py migrate

makemigrations:
	docker compose exec app python manage.py makemigrations

superuser:
	docker compose exec app python manage.py createsuperuser
```

---

## Troubleshooting
**`FATAL:  role "theatre_user" does not exist`**
- Create the role in Postgres (or recreate container with correct `POSTGRES_USER`), or remove volume and rebuild after changing `.env`.

**`password authentication failed for user`**
- Ensure credentials in `.env` match Django and Postgres. If you changed them after first run, remove the DB volume: `docker compose down -v && docker compose up --build`.

**`could not translate host name "db"`**
- `db` hostname works inside Docker. For local (non-Docker) development use `127.0.0.1`.

**`Upload a valid image` in tests**
- Use valid image bytes (`SimpleUploadedFile` with a small PNG/JPEG). Ensure `Pillow` is installed.

**Swagger 404 or URL issues**
- Ensure `urlpatterns` is a flat list, and `DEFAULT_SCHEMA_CLASS` in `settings.py` is set to `drf_spectacular.openapi.AutoSchema`.

**Static/collectstatic in container**
- Not required for dev. For production/CI add: `python manage.py collectstatic --noinput` and serve via `whitenoise` or nginx.

