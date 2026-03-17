from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document, DocumentVersion
from app.services import hash_content, is_duplicate_content
from app.templates_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    """Render dashboard with list of all documents."""
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    documents = result.scalars().all()
    return templates.TemplateResponse("index.html", {"request": request, "documents": documents})


@router.post("/documents")
async def create_document(title: str = Form(...), db: AsyncSession = Depends(get_db)):
    """Create a new document and redirect to editor."""
    document = Document(title=title)
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return RedirectResponse(url=f"/documents/{document.id}", status_code=303)


@router.get("/documents/{document_id}", response_class=HTMLResponse)
async def get_document(
    request: Request,
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Render document editor with version history."""
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        return RedirectResponse(url="/", status_code=303)

    # Map flash messages to user-friendly text
    flash_messages = {
        "no_changes": ("warning", "No changes detected. Content is identical to the latest version."),
        "version_saved": ("success", "New version saved successfully."),
        "title_updated": ("success", "Document title updated.")
    }
    flash = request.query_params.get("flash")
    flash_message = flash_messages.get(flash) if flash else None

    return templates.TemplateResponse("editor.html", {
        "request": request,
        "document": document,
        "flash_message": flash_message
    })


@router.post("/documents/{document_id}/versions")
async def create_version(
    document_id: int,
    request: Request,
    content: str = Form(...),
    change_summary: str | None = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Create a new version for a document."""
    # Get the document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        return RedirectResponse(url="/", status_code=303)

    # Check for duplicate content
    is_duplicate = await is_duplicate_content(db, document_id, content)
    
    if is_duplicate:
        # No changes detected, redirect back with flash message
        return RedirectResponse(
            url=f"/documents/{document_id}?flash=no_changes",
            status_code=303
        )

    # Calculate next version number
    version_result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
    )
    last_version = version_result.scalar_one_or_none()
    next_version = (last_version.version_number + 1) if last_version else 1

    # Create new version
    version = DocumentVersion(
        document_id=document_id,
        version_number=next_version,
        content=content,
        change_summary=change_summary
    )
    db.add(version)

    # Update document content
    document.content = content

    await db.commit()

    return RedirectResponse(
        url=f"/documents/{document_id}?flash=version_saved",
        status_code=303
    )


@router.post("/documents/{document_id}")
async def update_document_metadata(
    document_id: int,
    request: Request,
    title: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Update document metadata (title) without creating a new version."""
    # Support method override via query parameter
    method_override = request.query_params.get("_method", "").upper()
    if method_override != "PATCH":
        # This is a regular POST, not a method override
        return RedirectResponse(url=f"/documents/{document_id}", status_code=303)
    
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        return RedirectResponse(url="/", status_code=303)

    document.title = title
    await db.commit()

    return RedirectResponse(
        url=f"/documents/{document_id}?flash=title_updated",
        status_code=303
    )
