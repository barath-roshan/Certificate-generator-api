# Bulk Certificate Generator

## Overview
The **Bulk Certificate Generator** is a robust backend application built with FastAPI, PostgreSQL, SQLAlchemy 2.x, and ReportLab. It allows event organizers and institutions to submit bulk certificate generation jobs, validate recipient data, asynchronously render PDF certificates in the background, track execution status and real-time progress counters, and securely retrieve generated certificates.

## Features
- **Bulk Job Creation**: Accepts bulk recipient lists alongside event information in a single atomic request (returns `HTTP 202 Accepted`).
- **Comprehensive Validation**: Validates recipient names, email addresses, event metadata, date format, non-empty recipient lists, and configurable recipient batch limits.
- **Asynchronous Processing**: Renders PDF certificates in the background via FastAPI `BackgroundTasks` without holding open HTTP connections.
- **Independent PDF Generator**: Pure Python PDF rendering engine powered by ReportLab with custom borders, dynamic headers, participant credentials, and verification IDs.
- **Strict Failure Isolation**: Exception during one certificate generation does not halt processing for remaining certificates in the batch.
- **Real-time Progress & Status Metrics**: Tracks job-level states (`PENDING`, `PROCESSING`, `COMPLETED`, `COMPLETED_WITH_ERRORS`, `FAILED`) and dynamic completion percentages derived directly from persisted counters.
- **Secure File Retrieval**: Path traversal protection enforcing that all downloaded PDF files strictly reside within the configured storage directory root.

## Architecture

```text
Client
  |
  v
FastAPI App (POST /api/v1/jobs)
  |
  +--> PostgreSQL DB (Atomically persists GenerationJob & Certificates in PENDING state)
  |
  +--> FastAPI BackgroundTasks
          |
          v
     Certificate Worker (Independent DB Session)
          |
          +--> Renders PDFs individually via ReportLab Generator
          |
          +--> Updates individual Certificate & Job counter records
          |
          v
     PDF Storage (storage/certificates/<job_id>/<certificate_id>.pdf)
```

1. The client submits one bulk job containing event details and recipient information.
2. FastAPI validates the request using Pydantic schemas.
3. The job and recipient certificate records are persisted atomically in `PENDING` state within PostgreSQL.
4. An HTTP `202 Accepted` response with the `job_id` is immediately returned to the client.
5. A background worker creates its own database session and processes each certificate independently.
6. Progress metrics (`total_count`, `success_count`, `failure_count`) and individual certificate statuses (`SUCCESS` or `FAILED`) are persisted.
7. Clients poll status endpoints and download generated PDFs via secure file retrieval routes.

## Tech Stack
- **Language**: Python 3.12+
- **API Framework**: FastAPI
- **ASGI Server**: Uvicorn
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy 2.x
- **Database Driver**: Psycopg 3 (`psycopg[binary]`)
- **Database Migrations**: Alembic
- **Validation**: Pydantic v2 & `email-validator`
- **Configuration**: Pydantic Settings
- **PDF Engine**: ReportLab
- **Testing**: Pytest & HTTPX (`TestClient`)

## Project Structure
```text
Certificate-generator-api/
├── alembic/
│   ├── versions/
│   │   └── 001_initial_tables.py
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── certificates.py
│   │       ├── health.py
│   │       └── jobs.py
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   ├── generators/
│   │   └── pdf_generator.py
│   ├── models/
│   │   ├── certificate.py
│   │   ├── enums.py
│   │   └── job.py
│   ├── schemas/
│   │   ├── certificate.py
│   │   └── job.py
│   ├── services/
│   │   ├── certificate_service.py
│   │   └── job_service.py
│   ├── workers/
│   │   └── certificate_worker.py
│   └── main.py
├── storage/
│   └── certificates/
├── tests/
│   ├── test_database.py
│   ├── test_health.py
│   ├── test_jobs.py
│   ├── test_pdf_generator.py
│   ├── test_phase6_retrieval.py
│   └── test_workers.py
├── .env.example
├── .gitignore
├── alembic.ini
├── pytest.ini
├── requirements.txt
└── README.md
```

## Prerequisites
- **Python**: 3.12 or higher
- **PostgreSQL**: Local instance or accessible remote database server

## Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/barath-roshan/Certificate-generator-api.git
   cd Certificate-generator-api
   ```

2. **Create and activate virtual environment**:
   ```bash
   # On Windows (PowerShell):
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # On Linux / macOS:
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Environment Variables
Create a `.env` file in the root directory by copying `.env.example`:

```bash
cp .env.example .env
```

Configure your environment settings:

```env
APP_NAME="Bulk Certificate Generator"
APP_VERSION="0.1.0"
ENVIRONMENT="development"
DATABASE_URL="postgresql+psycopg://username:password@localhost:5432/certificate_db"
MAX_RECIPIENTS=1000
STORAGE_PATH="storage"
```

## Database Setup

1. **Create PostgreSQL Database**:
   ```sql
   CREATE DATABASE certificate_db;
   ```

2. **Apply Database Migrations**:
   Run Alembic to apply migrations and initialize database tables:
   ```bash
   alembic upgrade head
   ```

## Running the Application
Start the Uvicorn development server:

```bash
uvicorn app.main:app --reload
```

The application runs at `http://127.0.0.1:8000`. Interactive documentation is available at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## API Endpoints

| Method | Endpoint | Description | Expected Status |
|---|---|---|---|
| `GET` | `/health` | Application health check | `200 OK` |
| `POST` | `/api/v1/jobs` | Submit bulk certificate generation job | `202 Accepted` |
| `GET` | `/api/v1/jobs/{job_id}` | Get job progress counters and status | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}/certificates` | List job certificates and status | `200 OK` |
| `GET` | `/api/v1/certificates/{certificate_id}` | Download generated certificate PDF | `200 OK` |

## Example Request

**Endpoint**: `POST /api/v1/jobs`

```json
{
  "event_name": "Annual Developer Conference 2026",
  "event_date": "2026-10-15",
  "recipients": [
    {
      "name": "Alice Johnson",
      "email": "alice@example.com"
    },
    {
      "name": "Bob Smith",
      "email": "bob@example.com"
    }
  ]
}
```

**Response** (`HTTP 202 Accepted`):

```json
{
  "job_id": "7f3d9f34-8c1e-4e8d-9e21-123456789abc",
  "status": "PENDING",
  "total_count": 2
}
```

## Checking Job Progress

**Endpoint**: `GET /api/v1/jobs/7f3d9f34-8c1e-4e8d-9e21-123456789abc`

**Response** (`HTTP 200 OK`):

```json
{
  "job_id": "7f3d9f34-8c1e-4e8d-9e21-123456789abc",
  "event_name": "Annual Developer Conference 2026",
  "event_date": "2026-10-15",
  "status": "COMPLETED",
  "total_count": 2,
  "success_count": 2,
  "failure_count": 0,
  "completed_count": 2,
  "progress_percentage": 100.0,
  "created_at": "2026-10-08T00:00:00Z",
  "completed_at": "2026-10-08T00:00:02Z"
}
```

### Job Statuses
- `PENDING`: Initial state when job is recorded.
- `PROCESSING`: Background worker actively generating certificates.
- `COMPLETED`: All certificates generated successfully.
- `COMPLETED_WITH_ERRORS`: Job finished, but one or more certificates failed.
- `FAILED`: Unrecoverable infrastructure or job-level error.

## Retrieving Certificates

1. **List certificates for a job**:
   `GET /api/v1/jobs/{job_id}/certificates`

   **Response** (`HTTP 200 OK`):
   ```json
   {
     "job_id": "7f3d9f34-8c1e-4e8d-9e21-123456789abc",
     "certificates": [
       {
         "certificate_id": "74b00657-d1d7-4429-8c82-240c867e84ed",
         "recipient_name": "Alice Johnson",
         "recipient_email": "alice@example.com",
         "status": "SUCCESS",
         "error_message": null,
         "created_at": "2026-10-08T00:00:00Z",
         "completed_at": "2026-10-08T00:00:01Z"
       }
     ]
   }
   ```

2. **Download PDF file**:
   `GET /api/v1/certificates/74b00657-d1d7-4429-8c82-240c867e84ed`
   - Returns binary PDF (`Content-Type: application/pdf`).
   - Downloads are only allowed for certificates in `SUCCESS` status.

## Running Tests
Run the comprehensive test suite with `pytest`:

```bash
pytest
```

The test suite consists of 34 unit and integration tests covering database models, API endpoint validation, worker processing, failure isolation, PDF rendering, and path security.

## Certificate Storage
Generated certificates are stored on disk under the configured root directory:

```text
storage/
└── certificates/
    └── <job_id>/
        └── <certificate_id>.pdf
```

The database stores relative storage file paths. The retrieval service resolves target paths using `pathlib.Path.resolve()` and verifies that resolved paths remain within the configured `STORAGE_PATH` root directory.

## Failure Handling
- **Individual Certificate Isolation**: Processing each recipient is wrapped in an isolated exception block. An error generating one recipient's PDF logs the failure, updates that certificate to `FAILED`, increments `failure_count`, and continues processing remaining recipients.
- **Final Status Determination**: If all certificates succeed, job status becomes `COMPLETED`. If at least one recipient fails, job status becomes `COMPLETED_WITH_ERRORS`.
- **Database Safety**: Worker functions execute with explicit transaction rollback handling to ensure invalid partial states are never committed.

## Design Decisions
- **FastAPI BackgroundTasks**: Selected to handle background PDF generation without introducing heavy external message queues (like Celery/Redis) while meeting all assignment processing requirements.
- **Dedicated Worker Session**: The background worker explicitly opens and closes its own SQLAlchemy session (`SessionLocal()`), preventing request-scoped session leakage.
- **Derived Progress Metrics**: Progress percentages and `completed_count` are derived dynamically (`success_count + failure_count`), avoiding redundant state duplication in the database schema.
- **Path Security**: Resolves file paths strictly and rejects path traversal attempts with `HTTP 403 Forbidden`.

## Limitations
- **In-Process Worker Execution**: FastAPI `BackgroundTasks` executes inside the API worker process. If the server process restarts while a job is running, in-flight background tasks may be interrupted.
- **Local Filesystem Storage**: PDF files are saved to the server's local storage directory rather than cloud object storage (e.g., AWS S3).

## Future Improvements
- Integrate a distributed task queue (e.g., Celery with Redis/RabbitMQ) for multi-worker scaling and queue durability.
- Add cloud object storage backends (AWS S3 / Google Cloud Storage) for scalable certificate storage.
- Support zip archive batch downloads for completed jobs.
