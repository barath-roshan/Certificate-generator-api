# Bulk Certificate Generator API

High-performance asynchronous backend API built with FastAPI, PostgreSQL, SQLAlchemy 2.x, and ReportLab for bulk certificate generation, real-time progress tracking, and secure PDF delivery.

---

## 1. Project Overview

The **Bulk Certificate Generator API** enables organizations and event hosts to generate personalized PDF certificates for multiple recipients in a single bulk request. 

### Key Highlights
- **Single Bulk Request**: Accepts event details and recipient lists in one HTTP payload, eliminating the need for single-recipient polling requests.
- **Asynchronous Execution**: Offloads PDF rendering to background worker tasks using FastAPI `BackgroundTasks`.
- **Fault Isolation**: Individual certificate generation failures are isolated so remaining certificates in the batch complete successfully.
- **Secure Retrieval**: Streams generated PDFs directly while enforcing path containment security against traversal attacks.

---

## 2. Tech Stack

- **Framework**: FastAPI (Python 3.12+)
- **Database**: PostgreSQL
- **ORM & Migrations**: SQLAlchemy 2.x & Alembic
- **Database Driver**: Psycopg 3 (`psycopg[binary]`)
- **Validation**: Pydantic v2 & `email-validator`
- **PDF Engine**: ReportLab
- **Testing**: Pytest & HTTPX (`TestClient`)
- **Server**: Uvicorn

---

## 3. Project Features

- **Bulk Job Processing**: Submits bulk requests atomically and returns `HTTP 202 Accepted`.
- **Input Validation**: Validates strings, emails, dates, empty recipient lists, and configurable maximum recipient limits.
- **Independent PDF Rendering**: Pure Python PDF engine generating vector-quality PDF certificates.
- **Failure Isolation**: Per-recipient exception handling ensures one failed PDF does not halt batch execution.
- **Real-Time Progress Tracking**: Calculates dynamic completion counts and progress percentages.
- **Secure PDF Delivery**: Streams `application/pdf` binary files with path security checks.

---

## 4. Setup Instructions

### Prerequisites
- **Python**: 3.12+
- **PostgreSQL**: 15+ running locally or remotely

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/barath-roshan/Certificate-generator-api.git
cd Certificate-generator-api

python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the project root based on `.env.example`:
```env
APP_NAME="Bulk Certificate Generator"
APP_VERSION="0.1.0"
ENVIRONMENT="development"
DATABASE_URL="postgresql+psycopg://postgres:password@localhost:5432/certificate_db"
MAX_RECIPIENTS=1000
STORAGE_PATH="storage"
```

### 4. Database Setup & Migrations
Create the PostgreSQL database and run Alembic migrations:
```sql
CREATE DATABASE certificate_db;
```
```bash
alembic upgrade head
```

---

## 5. Running the Application

Start the Uvicorn development server:
```bash
uvicorn app.main:app --reload
```
- **Local Application URL**: `http://127.0.0.1:8000`
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 6. Running Tests

Execute the full automated test suite using Pytest:
```bash
pytest
```
### Test Coverage
- **API Endpoints**: Input validation, job creation, status metrics, and certificate retrieval.
- **Database Integration**: Model schemas, relationships, cascades, and transaction boundaries.
- **PDF Generation**: Template rendering, output path handling, and file integrity.
- **Worker & Failure Isolation**: Asynchronous execution, counter correctness, and duplicate worker safety.
- **Security**: Path traversal rejection (`HTTP 403`) and OpenAPI schema compliance.

---

## 7. Submit a Certificate Generation Request

**Endpoint**: `POST /api/v1/jobs`

### Request Body
```json
{
  "event_name": "Annual Tech Conference 2026",
  "event_date": "2026-10-08",
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

### Response (`HTTP 202 Accepted`)
```json
{
  "job_id": "7f3d9f34-8c1e-4e8d-9e21-123456789abc",
  "status": "PENDING",
  "total_count": 2
}
```
*The job is recorded atomically and background processing begins immediately.*

---

## 8. Check Job Progress

**Endpoint**: `GET /api/v1/jobs/{job_id}`

### Response (`HTTP 200 OK`)
```json
{
  "job_id": "7f3d9f34-8c1e-4e8d-9e21-123456789abc",
  "event_name": "Annual Tech Conference 2026",
  "event_date": "2026-10-08",
  "status": "COMPLETED",
  "total_count": 2,
  "success_count": 2,
  "failure_count": 0,
  "completed_count": 2,
  "progress_percentage": 100.0,
  "created_at": "2026-10-08T01:00:00Z",
  "completed_at": "2026-10-08T01:00:02Z"
}
```

### Supported Job Statuses
- `PENDING`: Initial recorded state.
- `PROCESSING`: Background worker actively generating PDFs.
- `COMPLETED`: All recipient certificates successfully generated.
- `COMPLETED_WITH_ERRORS`: Job finished, but one or more certificates failed.
- `FAILED`: Unrecoverable infrastructure or job-level error.

---

## 9. Retrieve Generated Certificates

### 1. List Certificates for a Job
**Endpoint**: `GET /api/v1/jobs/{job_id}/certificates`  
Returns recipient names, emails, statuses (`SUCCESS` / `FAILED`), and error messages.

### 2. Download Certificate PDF
**Endpoint**: `GET /api/v1/certificates/{certificate_id}`  
Downloads the binary PDF file (`Content-Type: application/pdf`) when status is `SUCCESS`. Returns `HTTP 400` if not yet generated or failed.

---

## 10. API Summary

| Method | Endpoint | Purpose | Status Code |
|---|---|---|---|
| `GET` | `/health` | Application health check | `200 OK` |
| `POST` | `/api/v1/jobs` | Submit bulk certificate generation job | `202 Accepted` |
| `GET` | `/api/v1/jobs/{job_id}` | Get job progress counters and status | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}/certificates` | List job certificates and status | `200 OK` |
| `GET` | `/api/v1/certificates/{certificate_id}` | Download generated certificate PDF | `200 OK` |

---

## 11. Important Design Decisions

- **Bulk Processing Architecture**: Single bulk HTTP request avoids client request overhead and allows background processing.
- **FastAPI BackgroundTasks**: Light-weight, built-in task execution without requiring complex external message queues.
- **Failure Isolation**: Per-certificate try-catch blocks prevent a single bad record from crashing the entire batch.
- **Dedicated Worker Sessions**: The worker opens an independent `SessionLocal()` session and commits per certificate, preventing long-running DB locks during PDF generation.
- **Derived Progress**: Progress metrics are dynamically calculated from `success_count + failure_count`, avoiding stale redundant progress state.
- **Path Security**: Enforces `pathlib.Path.resolve().relative_to()` to prevent directory traversal attacks.
- **Modular Design**: Clear separation between routes, services, models, schemas, workers, and PDF rendering engines.
