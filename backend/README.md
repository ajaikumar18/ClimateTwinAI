# ClimateTwin AI — Backend

This is the FastAPI backend for the **ClimateTwin AI** platform — an AI-powered Digital Twin of India's Climate.

## Quick Start

```bash
# 1. Create & activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure environment variables
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# 4. Run the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application factory
│   ├── ai/                      # AI/ML model integration
│   ├── api/
│   │   └── v1/
│   │       ├── router.py        # V1 router aggregator
│   │       └── endpoints/
│   │           └── health.py    # Health-check endpoints
│   ├── core/
│   │   ├── config.py            # Pydantic settings
│   │   ├── cors.py              # CORS middleware config
│   │   └── logging.py           # Structured logging setup
│   ├── database/
│   │   ├── base.py              # SQLAlchemy declarative base
│   │   └── session.py           # Async engine & session
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic request/response schemas
│   │   └── health.py
│   ├── services/                # Business logic layer
│   └── utils/                   # Shared helpers
├── .env.example
├── requirements.txt
└── README.md
```

## API Docs

Once the server is running:

| Resource  | URL                                     |
|-----------|-----------------------------------------|
| Swagger   | http://localhost:8000/api/v1/docs        |
| ReDoc     | http://localhost:8000/api/v1/redoc       |
| OpenAPI   | http://localhost:8000/api/v1/openapi.json|
| Health    | http://localhost:8000/api/v1/health      |
| Health+DB | http://localhost:8000/api/v1/health/db   |

## Environment Variables

See [`.env.example`](.env.example) for a full list of configurable variables.
