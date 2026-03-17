# Vellum - Smart Legal Document Manager

A modern web application for managing legal documents with intelligent version control, duplicate detection, and side-by-side version comparison.

## Images
![Homepage](res/1.webp)
![Editor](res/2.webp)
![Version_Control](res/3.webp)

## Features

- **Document Management**: Create, edit, and delete legal documents with metadata tracking
- **Version Control**: Automatic versioning with change summaries and duplicate detection
- **Smart Duplicate Detection**: SHA-256 hashing prevents saving identical versions
- **Significance Checking**: Ignores whitespace-only changes for meaningful version tracking
- **Version Comparison**: Side-by-side diff view with HTMX-powered dynamic loading
- **Background Notifications**: Console logging for significant document changes
- **Modern UI**: Built with Tailwind CSS, HTMX, and Google Fonts

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite with SQLAlchemy 2.0 Async (aiosqlite driver)
- **Frontend**: Jinja2 Templates + HTMX + Tailwind CSS
- **Fonts**: Inter (UI) + JetBrains Mono (code)

## Installation

```bash
# Install dependencies
uv sync

# Run the application
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Development

```bash
# Run with auto-reload
uv run uvicorn app.main:app --reload

# Test imports
uv run python -c "from app.main import app; print('OK')"
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard with document list |
| POST | `/documents` | Create new document |
| GET | `/documents/{id}` | Document editor page |
| POST | `/documents/{id}` | Update document title (with `?_method=PATCH`) |
| POST | `/documents/{id}/versions` | Save new version |
| DELETE | `/documents/{id}` | Delete document |
| GET | `/documents/{id}/compare?v1={id}&v2={id}` | Version comparison |
| GET | `/health` | Health check |

