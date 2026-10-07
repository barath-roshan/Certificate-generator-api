# Bulk Certificate Generator

## Project Purpose
The Bulk Certificate Generator application is designed to process bulk requests for certificate generation, validate recipient information, generate individual certificates from predefined templates, and track job execution progress.

## Current Status: Phase 5 (Background Bulk Processing)
This codebase represents **Phase 5: Background Certificate Processing**.

It introduces:
- **Background Worker Module** (`app/workers/certificate_worker.py`)
- **FastAPI BackgroundTasks Integration** (asynchronous job scheduling on `POST /api/v1/jobs`)
- **Fault Isolation Engine**: Single certificate failures do not halt batch processing
- **Independent Database Session Strategy**: Workers instantiate dedicated database sessions via `SessionLocal`
- **Granular Progress Counters & Status Tracking**: Updates job status to `PROCESSING`, `COMPLETED`, or `COMPLETED_WITH_ERRORS`

> [!NOTE]
> `FastAPI BackgroundTasks` is an in-process, non-durable task execution choice for this assignment. Production deployments handling large-scale asynchronous distributed queues can be upgraded to Celery/Redis/RabbitMQ in future architecture phases.

## Tech Stack
- **Python**: 3.12+
- **Framework**: FastAPI (BackgroundTasks)
- **PDF Engine**: ReportLab
- **ASGI Server**: Uvicorn
- **ORM**: SQLAlchemy 2.x
- **Database Driver**: Psycopg 3 (`psycopg[binary]`)
- **Database Migrations**: Alembic
- **Validation**: Pydantic v2 & Email Validator
- **Configuration**: Pydantic Settings
- **Testing**: Pytest & HTTPX (TestClient)

## Background Processing Architecture

### 1. Processing Lifecycle
1. **API Job Submission (`POST /api/v1/jobs`)**:
   - Validates Pydantic request body.
   - Atomically commits `GenerationJob` and `Certificate` records in `PENDING` state.
   - Schedules `process_job(job_id)` via `background_tasks.add_task()`.
   - Returns `HTTP 202 Accepted` immediately.

2. **Worker Execution (`app/workers/certificate_worker.py`)**:
   - Opens a dedicated, isolated database session.
   - Updates `GenerationJob.status = PROCESSING`.
   - Processes each `Certificate` record individually:
     - Marks certificate `PROCESSING`.
     - Calls PDF generator to render ReportLab PDF (`storage/certificates/{job_id}/{certificate_id}.pdf`).
     - On Success: Marks certificate `SUCCESS`, records `file_path`, increments `success_count`.
     - On Failure: Catches exception, marks certificate `FAILED`, records safe `error_message`, increments `failure_count`, and continues processing remaining certificates.
   - Calculates final job state:
     - `COMPLETED` if all certificates succeed (`failure_count == 0`).
     - `COMPLETED_WITH_ERRORS` if any certificate fails.

### 2. Local Storage Structure
Certificates are generated under:
```
storage/
└── certificates/
    └── {job_id}/
        └── {certificate_id}.pdf
```

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

## Setup & Local Configuration

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
   STORAGE_PATH="storage"
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

Execute the full test suite using `pytest`:

```bash
pytest
```
