# Bulk Certificate Generator

## Project Purpose
The Bulk Certificate Generator application is designed to process bulk requests for certificate generation, validate recipient information, generate individual certificates from predefined templates, and track job execution progress.

## Current Status: Phase 6 (Job Status & Retrieval APIs)
This codebase represents **Phase 6: Job Status & Certificate Retrieval APIs**.

It introduces:
- **Job Progress & Status API**: `GET /api/v1/jobs/{job_id}`
- **Job Certificates Listing API**: `GET /api/v1/jobs/{job_id}/certificates`
- **Certificate PDF Download API**: `GET /api/v1/certificates/{certificate_id}`
- **Path Traversal Security**: Strict validation enforcing that downloaded files reside inside `STORAGE_PATH`
- **On-the-Fly Progress Calculation**: Calculates `completed_count` (`success_count + failure_count`) and `progress_percentage` (`completed_count / total_count * 100`) dynamically from persisted counters.

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

### 3. Get Job Status & Progress
- **URL**: `GET /api/v1/jobs/{job_id}`
- **Response Body (HTTP 200 OK)**:
  ```json
  {
    "job_id": "7f3d9f34-8c1e-4e8d-9e21-123456789abc",
    "event_name": "Python Workshop",
    "event_date": "2026-10-07",
    "status": "PROCESSING",
    "total_count": 100,
    "success_count": 65,
    "failure_count": 2,
    "completed_count": 67,
    "progress_percentage": 67.0,
    "created_at": "2026-10-07T18:50:00Z",
    "completed_at": null
  }
  ```
- **Progress Formula**:
  - `completed_count = success_count + failure_count`
  - `progress_percentage = round((completed_count / total_count) * 100.0, 2)`
- **HTTP 404**: Returned if `job_id` does not exist.

### 4. List Job Certificates
- **URL**: `GET /api/v1/jobs/{job_id}/certificates`
- **Response Body (HTTP 200 OK)**:
  ```json
  {
    "job_id": "7f3d9f34-8c1e-4e8d-9e21-123456789abc",
    "certificates": [
      {
        "certificate_id": "74b00657-d1d7-4429-8c82-240c867e84ed",
        "recipient_name": "Barath Roshan",
        "recipient_email": "barath@example.com",
        "status": "SUCCESS",
        "error_message": null,
        "created_at": "2026-10-07T18:50:00Z",
        "completed_at": "2026-10-07T18:50:02Z"
      },
      {
        "certificate_id": "9b10a452-3e2b-4f11-8c90-112233445566",
        "recipient_name": "Arun Kumar",
        "recipient_email": "arun@example.com",
        "status": "FAILED",
        "error_message": "Certificate PDF generation failed",
        "created_at": "2026-10-07T18:50:00Z",
        "completed_at": "2026-10-07T18:50:03Z"
      }
    ]
  }
  ```
- **Ordering**: Returns certificate list in deterministic `created_at` ascending order.
- **HTTP 404**: Returned if `job_id` does not exist.

### 5. Download Certificate PDF
- **URL**: `GET /api/v1/certificates/{certificate_id}`
- **Response**: `200 OK` (`application/pdf`) with `Content-Disposition: attachment; filename="certificate-{id}.pdf"`
- **Availability Rules**:
  - Requires `status == SUCCESS`. Returns `400 Bad Request` if certificate is still `PENDING`, `PROCESSING`, or `FAILED`.
  - Path traversal checks enforce that the physical file resolves within `STORAGE_PATH` (`HTTP 403 Forbidden` on security violations).
  - Returns `500 Internal Server Error` if the physical file is missing on storage without leaking server directory paths.

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
