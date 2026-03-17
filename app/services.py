import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DocumentVersion


def hash_content(content: str) -> str:
    """Create SHA-256 hash of text content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def is_duplicate_content(
    db: AsyncSession,
    document_id: int,
    new_content: str
) -> bool:
    """
    Check if new content is a duplicate of the latest version.
    
    Compares the hash of the new content with the hash of the most recent version.
    Returns True if content is identical (duplicate), False otherwise.
    """
    new_hash = hash_content(new_content)
    
    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )
    latest_version = result.scalar_one_or_none()
    
    if latest_version is None:
        return False
    
    latest_hash = hash_content(latest_version.content)
    return new_hash == latest_hash
