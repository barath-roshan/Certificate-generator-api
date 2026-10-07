# Bulk Certificate Generator

## Project Purpose
The Bulk Certificate Generator application is designed to process bulk requests for certificate generation, validate recipient information, generate individual certificates from predefined templates, and track job execution progress.

## Current Status: Phase 3 (Bulk Job Creation API)
This codebase represents **Phase 3: Job Creation API**.

It introduces:
- **Pydantic Validation Schemas** (`RecipientCreate`, `GenerationJobCreate`, `GenerationJobResponse`)
- **Configurable Recipient Limits** (`MAX_RECIPIENTS`)
- **Service Layer** (`app/services/job_service.py`) for atomic database transactions
- **API Endpoint**: `POST /api/v1/jobs` returning HTTP 202 Accepted with generated `job_id`

> [!NOTE]
> PDF generation (ReportLab) and background task processing (Celery/Workers) remain out of scope for Phase 3 and will be introduced in subsequent phases.

## Tech Stack
- **Python**: 3.12+
- **Framework**: FastAPI
- **ASGI Server**: Uvicorn
- **ORM**: SQLAlchemy 2.x
- **Database Driver**: Psycopg 3 (`psycopg[binary]`)
- **Database Migrations**: Alembic
- **Validation**: Pydantic v2 & Email Validator
- **Configuration**: Pydantic Settings
- **Testing**: Pytest & HTTPX (TestClient)

## API Endpoints

### 1. Health Check
- **URL**: `GET /health`
- **Response**: `{"status": "ok"}`

### 2. Create Bulk Certificate Generation Job
- **URL**: `POST /api/v1/jobs`
- **Status Code**: `202 Accepted`
- **Request Body**:
  ```json
  {
    "event_name": "Python Workshop",
    "event_date": "2026-10-07",
    "recipients": [
      {
        "name": "Barath Roshan",
        "email": "barath@example.com"
      },
      {
        "name": "Arun Kumar",
        "email": "arun@example.com"
      }
    ]
  }
  ```
- **Response Body**:
  ```json
  {
    "job_id": "7f3d9f34-8c1e-4e8d-9e21-123456789abc",
    "status": "PENDING",
    "total_count": 2
  }
  ```

## Setup & Local Database Configuration

1. **Clone the repository**:
   ```bash
   git clone https://github.com/barath-roshan/Certificate-generator-api.git
   cd Certificate-generator-api
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Set configuration in `.env`:
   ```env
   DATABASE_URL="postgresql+psycopg://postgres:your_password@localhost:5432/certificate_db"
   MAX_RECIPIENTS=1000
   ```

5. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

## Running the Application

Start the FastAPI server using Uvicorn:

```bash
uvicorn app.main:app --reload
```

The application will start at `http://127.0.0.1:8000`.

## Interactive API Documentation (Swagger)

Access the interactive Swagger UI at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Running Tests

Execute the test suite using `pytest`:

```bash
pytest
```
