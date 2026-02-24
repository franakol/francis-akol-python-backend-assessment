"""API endpoints for file uploads."""

from typing import List, Optional

from app.services.file_storage import file_storage_service
from fastapi import APIRouter, File, Path, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/files", tags=["Files"])


class FileMetadata(BaseModel):
    """File metadata response."""

    filename: str
    original_filename: str
    path: str
    size: int
    content_type: str
    extension: str
    hash: str
    course_id: int
    uploaded_by: int
    uploaded_at: str
    url: str


class FileListItem(BaseModel):
    """File list item."""

    filename: str
    path: str
    size: int
    modified_at: str


@router.post("/{course_id}/upload", response_model=FileMetadata)
async def upload_file(
    course_id: int = Path(..., description="Course ID"),
    file: UploadFile = File(..., description="File to upload"),
    category: str = Query("materials", description="File category"),
    # In production, add proper auth dependency
    user_id: int = Query(
        1, description="User ID (temp - use auth in production)"
    ),
):
    """
    Upload a file for a course.

    Supports various file types including:
    - Documents: PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX, TXT, MD
    - Images: JPG, PNG, GIF, WEBP, SVG
    - Media: MP4, WEBM, MP3, WAV
    - Archives: ZIP, TAR, GZ

    Maximum file size: 50MB
    """
    return await file_storage_service.upload_file(
        file=file,
        course_id=course_id,
        user_id=user_id,
        category=category,
    )


@router.get("/{course_id}/{category}/{filename}")
async def download_file(
    course_id: int = Path(..., description="Course ID"),
    category: str = Path(..., description="File category"),
    filename: str = Path(..., description="Filename"),
):
    """Download a file."""
    file_path, content_type = await file_storage_service.get_file(
        course_id=course_id,
        category=category,
        filename=filename,
    )

    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=filename,
    )


@router.delete("/{course_id}/{category}/{filename}")
async def delete_file(
    course_id: int = Path(..., description="Course ID"),
    category: str = Path(..., description="File category"),
    filename: str = Path(..., description="Filename"),
):
    """Delete a file."""
    await file_storage_service.delete_file(
        course_id=course_id,
        category=category,
        filename=filename,
    )
    return {"message": "File deleted successfully"}


@router.get("/{course_id}", response_model=List[FileListItem])
async def list_files(
    course_id: int = Path(..., description="Course ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """List all files for a course."""
    return await file_storage_service.list_files(
        course_id=course_id,
        category=category,
    )
