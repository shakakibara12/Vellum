from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document, DocumentVersion
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
async def get_document(request: Request, document_id: int, db: AsyncSession = Depends(get_db)):
    """Render document editor with version history."""
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("editor.html", {
        "request": request,
        "document": document
    })


@router.post("/documents/{document_id}/versions")
async def create_version(
    document_id: int,
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
    
    return RedirectResponse(url=f"/documents/{document_id}", status_code=303)
