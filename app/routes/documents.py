"""Document routes for Vellum application.

Handles document CRUD operations, version management, and comparison.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import delete as sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Document, DocumentVersion
from app.services import (
    check_significance,
    generate_diff_html,
    is_duplicate_content,
    send_notification,
)
from app.templates_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    """Render dashboard with list of all documents."""
    result = await db.execute(
        select(Document)
        .order_by(Document.created_at.desc())
        .options(selectinload(Document.versions))
    )
    documents = result.scalars().all()

    flash_messages = {
        "document_deleted": ("success", "Document deleted successfully.")
    }
    flash = request.query_params.get("flash")
    flash_message = flash_messages.get(flash) if flash else None

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "documents": documents,
            "flash_message": flash_message,
        },
    )


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
    db: AsyncSession = Depends(get_db),
):
    """Render document editor with version history."""
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.versions))
    )
    document = result.scalar_one_or_none()

    if not document:
        return RedirectResponse(url="/", status_code=303)

    flash_messages = {
        "no_changes": (
            "warning",
            "No changes detected. Content is identical to the latest version.",
        ),
        "version_saved": ("success", "New version saved successfully."),
        "title_updated": ("success", "Document title updated."),
    }
    flash = request.query_params.get("flash")
    flash_message = flash_messages.get(flash) if flash else None

    return templates.TemplateResponse(
        "editor.html",
        {
            "request": request,
            "document": document,
            "flash_message": flash_message,
        },
    )


@router.post("/documents/{document_id}/versions")
async def create_version(
    document_id: int,
    background_tasks: BackgroundTasks,
    content: str = Form(...),
    change_summary: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new version for a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        return RedirectResponse(url="/", status_code=303)

    is_duplicate = await is_duplicate_content(db, document_id, content)

    if is_duplicate:
        return RedirectResponse(
            url=f"/documents/{document_id}?flash=no_changes",
            status_code=303,
        )

    version_result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )
    last_version = version_result.scalar_one_or_none()
    next_version = (last_version.version_number + 1) if last_version else 1

    is_significant = False
    if last_version:
        is_significant = check_significance(last_version.content, content)

    version = DocumentVersion(
        document_id=document_id,
        version_number=next_version,
        content=content,
        change_summary=change_summary,
    )
    db.add(version)

    document.content = content

    await db.commit()

    if is_significant:
        background_tasks.add_task(send_notification, document.title, next_version)

    return RedirectResponse(
        url=f"/documents/{document_id}?flash=version_saved",
        status_code=303,
    )


@router.post("/documents/{document_id}")
async def update_document_metadata(
    document_id: int,
    request: Request,
    title: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Update document metadata (title) without creating a new version."""
    method_override = request.query_params.get("_method", "").upper()
    if method_override != "PATCH":
        return RedirectResponse(url=f"/documents/{document_id}", status_code=303)

    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        return RedirectResponse(url="/", status_code=303)

    document.title = title
    await db.commit()

    return RedirectResponse(
        url=f"/documents/{document_id}?flash=title_updated",
        status_code=303,
    )


@router.get("/documents/{document_id}/compare", response_class=HTMLResponse)
async def compare_versions(
    document_id: int,
    request: Request,
    v1: int | None = None,
    v2: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Compare two document versions and return an HTML diff table."""
    if not v1 or not v2:
        return Response(
            content="<p class='text-gray-500'>Please select two versions to compare.</p>"
        )

    result = await db.execute(
        select(DocumentVersion).where(DocumentVersion.id.in_([v1, v2]))
    )
    versions = result.scalars().all()

    if len(versions) != 2:
        raise HTTPException(status_code=404, detail="One or both versions not found")

    if (
        versions[0].document_id != document_id
        or versions[1].document_id != document_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Versions do not belong to the specified document",
        )

    version_map = {v.id: v for v in versions}
    content1 = version_map[v1].content
    content2 = version_map[v2].content
    version1_num = version_map[v1].version_number
    version2_num = version_map[v2].version_number

    diff_html = generate_diff_html(content1, content2)

    return templates.TemplateResponse(
        "_diff_result.html",
        {
            "request": request,
            "diff_html": diff_html,
            "version1": version1_num,
            "version2": version2_num,
        },
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and all its versions."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        return RedirectResponse(url="/", status_code=303)

    await db.execute(
        sql_delete(DocumentVersion).where(DocumentVersion.document_id == document_id)
    )
    await db.execute(sql_delete(Document).where(Document.id == document_id))
    await db.commit()

    return RedirectResponse(url="/?flash=document_deleted", status_code=303)
