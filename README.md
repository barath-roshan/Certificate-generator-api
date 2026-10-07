# Bulk Certificate Generator

## Project Purpose
The Bulk Certificate Generator application is designed to process bulk requests for certificate generation, validate recipient information, generate individual certificates from predefined templates, and track job execution progress.

## Current Status: Phase 4 (Certificate PDF Generator)
This codebase represents **Phase 4: Standalone Certificate PDF Generator**.

It introduces:
- **Standalone PDF Generator Module** (`app/generators/pdf_generator.py`) using ReportLab
- **Clean Input Data Structure** (`CertificateData` dataclass)
- **Predefined Professional Certificate Template** (Landscape A4, double decorative border, typography, formatted dates, and signature lines)
- **Deterministic Storage Pattern** (`storage/certificates/{job_id}/{certificate_id}.pdf`)
- **Independent Test Suite** (`tests/test_pdf_generator.py`)

> [!NOTE]
> PDF generation is currently an independent component and is decoupled from HTTP API routes and database transactions. Bulk job background processing integration will occur in a later phase.

## Tech Stack
- **Python**: 3.12+
- **Framework**: FastAPI
- **PDF Engine**: ReportLab
- **ASGI Server**: Uvicorn
- **ORM**: SQLAlchemy 2.x
- **Database Driver**: Psycopg 3 (`psycopg[binary]`)
- **Database Migrations**: Alembic
- **Validation**: Pydantic v2 & Email Validator
- **Configuration**: Pydantic Settings
- **Testing**: Pytest & HTTPX (TestClient)

## Certificate Generator & Storage Architecture

### 1. Certificate Template Design
The PDF generator renders a professional A4 landscape certificate containing:
- Double border frame (Navy `#1A365D` outer line & Gold `#D69E2E` inner line)
- Header: **CERTIFICATE OF PARTICIPATION**
- Presentation: **This certificate is proudly presented to `<RECIPIENT NAME>`**
- Event Context: **for successfully participating in `<EVENT NAME>`**
- Date: Human-readable deterministic format (e.g. `07 October 2026`)
- Footer: Unique Certificate ID (`Certificate ID: <UUID>`) & Signature section

### 2. Local Storage Structure
Certificates are generated locally under the configured storage root:
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
