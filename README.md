# Django CRM

[![CI](https://github.com/ChakerChourouk/Django-CRM/actions/workflows/ci.yml/badge.svg)](https://github.com/ChakerChourouk/Django-CRM/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Django 5.2](https://img.shields.io/badge/django-5.2-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-red.svg)](https://www.django-rest-framework.org/)
[![Live Demo](https://img.shields.io/badge/demo-Railway-blueviolet.svg)](https://web-production-8332.up.railway.app)

A full-featured **Customer Relationship Management** system built with Django, MySQL, and Django REST Framework. Provides both a web interface and a RESTful API for managing customer records with authentication, search, pagination, and CRUD operations.

### Live Demo: [web-production-8332.up.railway.app](https://web-production-8332.up.railway.app)

---

## Screenshots

### Add a New Record
![Add Record](images/add%20.png)

### Record Detail — Update & Delete
![Update and Delete Record](images/delete%20update.png)

---

## Features

- **Authentication** — Registration, login, logout with Django's auth system
- **CRUD Operations** — Create, read, update, and delete customer records
- **Search & Filter** — Search records by name, email, phone, or city
- **Pagination** — Server-side pagination for efficient data browsing
- **REST API** — Full CRUD API powered by Django REST Framework
- **Admin Dashboard** — Customized Django admin with filters and search
- **Responsive UI** — Bootstrap 5 for mobile-friendly design
- **Security** — CSRF protection, POST-only deletes, env-based secrets, production hardening
- **Docker Support** — Containerized with Docker Compose (Django + MySQL)
- **CI/CD** — Automated testing via GitHub Actions
- **Extensión forense** — Auditoría de cambios con contexto de solicitud, consulta de solo lectura y scripts de preservación SHA-256. Ver [guía de uso](docs/forense.md).

---

## Tech Stack

| Layer       | Technology                         |
|-------------|------------------------------------|
| Backend     | Python 3.12, Django 5.2            |
| API         | Django REST Framework 3.15         |
| Database    | MySQL 8.0                          |
| Frontend    | Django Templates, Bootstrap 5      |
| DevOps      | Docker, Docker Compose, GitHub Actions |
| Server      | Gunicorn (production)              |

---

## Project Structure

```
Django-CRM/
├── dcrm/                       # Project configuration
│   ├── settings/
│   │   ├── base.py             # Shared settings
│   │   ├── dev.py              # Development overrides
│   │   └── prod.py             # Production (HTTPS, HSTS, etc.)
│   ├── urls.py
│   └── wsgi.py
├── website/                    # Main application
│   ├── models.py               # Record model with validators
│   ├── views.py                # Web views with auth decorators
│   ├── forms.py                # SignUp + AddRecord forms
│   ├── serializers.py          # DRF serializers
│   ├── api_views.py            # DRF viewsets
│   ├── api_urls.py             # API router
│   ├── admin.py                # Customized admin
│   ├── tests.py                # 20+ unit & integration tests
│   └── templates/website/      # Namespaced templates
├── .env.example                # Environment template
├── .github/workflows/ci.yml   # GitHub Actions pipeline
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── manage.py
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- MySQL 8.0+
- pip

### 1. Clone & install

```bash
git clone https://github.com/ChakerChourouk/Django-CRM.git
cd Django-CRM
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your database credentials and secret key
```

### 3. Set up database

```sql
CREATE DATABASE elderco CHARACTER SET utf8mb4;
```

### 4. Run migrations & start

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser.

---

## Docker

```bash
# Copy and configure environment
cp .env.example .env

# Build and start containers
docker compose up --build -d

# Run migrations inside container
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

App available at **http://localhost:8000/**

---

## API Reference

All endpoints require authentication (session-based).

| Method   | Endpoint              | Description           |
|----------|-----------------------|-----------------------|
| `GET`    | `/api/records/`       | List all records      |
| `POST`   | `/api/records/`       | Create a record       |
| `GET`    | `/api/records/{id}/`  | Retrieve a record     |
| `PUT`    | `/api/records/{id}/`  | Update a record       |
| `PATCH`  | `/api/records/{id}/`  | Partial update        |
| `DELETE` | `/api/records/{id}/`  | Delete a record       |

### Example: Create a record

```bash
curl -X POST http://localhost:8000/api/records/ \
  -H "Content-Type: application/json" \
  -b "sessionid=<your-session-id>" \
  -d '{
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane@example.com",
    "phone": "+11234567890",
    "address": "456 Oak Ave",
    "city": "Portland",
    "state": "OR",
    "zipcode": "97201"
  }'
```

---

## Running Tests

```bash
python manage.py test website --verbosity=2
```

Tests cover:
- Model creation and validation
- Authentication (login, logout, registration)
- CRUD views (create, read, update, delete)
- Search and pagination
- REST API endpoints
- Permission enforcement

---

## Deployment (Railway)

This app is deployed on [Railway](https://railway.app) with PostgreSQL.

**Live URL:** [web-production-8332.up.railway.app](https://web-production-8332.up.railway.app)

To deploy your own instance:

1. Fork this repo
2. Create a new project on [Railway](https://railway.app) and connect your GitHub repo
3. Add a **PostgreSQL** database to the project
4. Set environment variables:
   | Variable | Value |
   |---|---|
   | `DJANGO_SETTINGS_MODULE` | `dcrm.settings.prod` |
   | `SECRET_KEY` | *(generate a random key)* |
   | `ALLOWED_HOSTS` | `.railway.app` |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
5. Railway auto-deploys on every push. Migrations run automatically via the `release` command in the Procfile.
6. Create a superuser via the Railway **Shell** tab:
   ```bash
   python manage.py createsuperuser
   ```

---

## License

This project is open source and available under the [MIT License](LICENSE).

