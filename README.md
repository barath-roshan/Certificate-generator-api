# Bulk Certificate Generator

## Project Purpose
The Bulk Certificate Generator application is designed to process bulk requests for certificate generation, validate recipient information, generate individual certificates from predefined templates, and track job execution progress.

## Current Status: Phase 2 (PostgreSQL & Persistence Layer)
This codebase represents **Phase 2: PostgreSQL Database Integration and SQLAlchemy Persistence Foundation**.

It introduces:
- **PostgreSQL Database Support**
- **SQLAlchemy 2.x Declarative Models** (`GenerationJob` and `Certificate`)
- **Alembic Database Migrations**
- **Database Dependency Injection** (`get_db`)

> [!NOTE]
> Background job processing, PDF generation (ReportLab), and public certificate generation API endpoints remain out of scope for Phase 2 and will be introduced in subsequent phases.

## Tech Stack
- **Python**: 3.12+
- **Framework**: FastAPI
- **ASGI Server**: Uvicorn
- **ORM**: SQLAlchemy 2.x
- **Database Driver**: Psycopg 3 (`psycopg[binary]`)
- **Database Migrations**: Alembic
- **Configuration**: Pydantic Settings
- **Testing**: Pytest & HTTPX (TestClient)

## Database Architecture

### Models & Relationships

1. **`GenerationJob` (`generation_jobs`)**:
   - `id`: UUID (Primary Key)
   - `event_name`: String (Required)
   - `event_date`: Date (Optional)
   - `status`: JobStatus Enum (`PENDING`, `PROCESSING`, `COMPLETED`, `COMPLETED_WITH_ERRORS`, `FAILED`)
   - `total_count`, `success_count`, `failure_count`: Integers
   - `created_at`, `completed_at`: Timestamps with timezone

2. **`Certificate` (`certificates`)**:
   - `id`: UUID (Primary Key)
   - `job_id`: UUID (Foreign Key -> `generation_jobs.id`, ON DELETE CASCADE, Indexed)
   - `recipient_name`: String (Required)
   - `recipient_email`: String (Required)
   - `status`: CertificateStatus Enum (`PENDING`, `PROCESSING`, `SUCCESS`, `FAILED`, Indexed)
   - `file_path`: String (Optional)
   - `error_message`: String (Optional)
   - `created_at`, `completed_at`: Timestamps with timezone

- **Relationship**: `GenerationJob 1 ---- N Certificate` (`job.certificates` and `certificate.job`).

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
   Set `DATABASE_URL` in `.env` to point to your local PostgreSQL instance:
   ```env
   DATABASE_URL="postgresql+psycopg://postgres:your_password@localhost:5432/certificate_db"
   ```

5. **Local PostgreSQL Setup**:
   Create local PostgreSQL database:
   ```sql
   CREATE DATABASE certificate_db;
   ```

6. **Run Database Migrations**:
   Initialize and apply Alembic schema migrations:
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

## Health Endpoint

- **URL**: `GET /health`
- **Response**: `{"status": "ok"}`

## Running Tests

Execute the test suite using `pytest`:

```bash
pytest
```
