# Bulk Certificate Generator

## Project Purpose
The Bulk Certificate Generator application is designed to process bulk requests for certificate generation, validate recipient information, generate individual certificates from predefined templates, and track job execution progress.

## Current Status: Phase 1 (Foundation)
This codebase represents **Phase 1: Project Foundation**. It establishes the core FastAPI application setup, configuration management, and health verification endpoint.

> [!NOTE]
> Database models, background workers, certificate generation logic, and business APIs are out of scope for Phase 1 and will be introduced in future phases.

## Tech Stack
- **Python**: 3.12+
- **Framework**: FastAPI
- **ASGI Server**: Uvicorn
- **Configuration**: Pydantic Settings
- **Testing**: Pytest & HTTPX (TestClient)

## Setup Instructions

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
   Copy `.env.example` to `.env` if custom environment variables are required:
   ```bash
   cp .env.example .env
   ```

## Running the Application

Start the FastAPI server using Uvicorn:

```bash
uvicorn app.main:app --reload
```

The application will start at `http://127.0.0.1:8000`.

## Interactive API Documentation (Swagger)

Once the application is running, access the interactive Swagger UI at:
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
