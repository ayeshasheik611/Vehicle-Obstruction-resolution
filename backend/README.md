# FreeWay Community Backend API

Privacy-focused vehicle blocking resolution system backend built with FastAPI.

## Features

- User authentication with JWT tokens
- Automatic License Plate Recognition (ALPR)
- Push notifications via Firebase Cloud Messaging
- Rate limiting and abuse prevention
- PostgreSQL database with connection pooling
- Redis caching for performance
- Comprehensive audit logging

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Firebase project with Cloud Messaging enabled

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Set up the database:
```bash
# Create PostgreSQL database
createdb freeway_db

# Run migrations
alembic upgrade head
```

5. Start Redis:
```bash
redis-server
```

6. Run the development server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/     # API endpoint handlers
│   ├── core/
│   │   ├── config.py         # Configuration settings
│   │   ├── database.py       # Database setup
│   │   └── redis.py          # Redis setup
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # Business logic
│   └── utils/                # Utility functions
├── alembic/                  # Database migrations
├── tests/                    # Test suite
├── main.py                   # Application entry point
└── requirements.txt          # Python dependencies
```

## Testing

Run tests with pytest:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

## License

Proprietary - All rights reserved
