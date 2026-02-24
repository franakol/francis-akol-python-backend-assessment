"""File storage service for handling course materials and uploads."""

import hashlib
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from app.core.config import settings
from fastapi import HTTPException, UploadFile


class FileStorageService:
    """Service for handling file uploads and storage."""

    ALLOWED_EXTENSIONS = {
        "pdf",
        "doc",
        "docx",
        "ppt",
        "pptx",
        "xls",
        "xlsx",
        "txt",
        "md",
        "csv",
        "json",
        "jpg",
        "jpeg",
        "png",
        "gif",
        "webp",
        "svg",
        "mp4",
        "webm",
        "mp3",
        "wav",
        "zip",
        "tar",
        "gz",
    }

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    def __init__(self):
        self.storage_path = Path(settings.FILE_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    def _validate_file(self, file: UploadFile) -> Tuple[str, str]:
        """
        Validate uploaded file.

        Returns:
            Tuple of (extension, content_type)

        Raises:
            HTTPException if validation fails
        """
        # Check filename
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # Check extension
        extension = self._get_file_extension(file.filename)
        if extension not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{extension}' not allowed. Allowed: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}",
            )

        return extension, file.content_type or "application/octet-stream"

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename with UUID prefix."""
        extension = self._get_file_extension(original_filename)
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(
            c
            for c in original_filename.rsplit(".", 1)[0]
            if c.isalnum() or c in "-_"
        )[:50]
        return f"{timestamp}_{unique_id}_{safe_name}.{extension}"

    def _get_file_hash(self, content: bytes) -> str:
        """Calculate SHA256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    async def upload_file(
        self,
        file: UploadFile,
        course_id: int,
        user_id: int,
        category: str = "materials",
    ) -> dict:
        """
        Upload a file for a course.

        Args:
            file: Uploaded file
            course_id: ID of the course
            user_id: ID of the uploading user
            category: File category (materials, thumbnails, etc.)

        Returns:
            Dict with file metadata
        """
        # Validate file
        extension, content_type = self._validate_file(file)

        # Read file content
        content = await file.read()

        # Check file size
        if len(content) > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {self.MAX_FILE_SIZE // (1024*1024)}MB",
            )

        # Generate unique filename
        unique_filename = self._generate_unique_filename(file.filename)

        # Create directory structure
        file_dir = self.storage_path / str(course_id) / category
        file_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = file_dir / unique_filename
        with open(file_path, "wb") as f:
            f.write(content)

        # Calculate hash
        file_hash = self._get_file_hash(content)

        return {
            "filename": unique_filename,
            "original_filename": file.filename,
            "path": str(file_path.relative_to(self.storage_path)),
            "size": len(content),
            "content_type": content_type,
            "extension": extension,
            "hash": file_hash,
            "course_id": course_id,
            "uploaded_by": user_id,
            "uploaded_at": datetime.utcnow().isoformat(),
            "url": f"/api/v1/files/{course_id}/{category}/{unique_filename}",
        }

    async def get_file(
        self, course_id: int, category: str, filename: str
    ) -> Tuple[Path, str]:
        """
        Get a file path and content type.

        Returns:
            Tuple of (file_path, content_type)
        """
        file_path = self.storage_path / str(course_id) / category / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Determine content type
        extension = self._get_file_extension(filename)
        content_types = {
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "mp4": "video/mp4",
            "mp3": "audio/mpeg",
        }
        content_type = content_types.get(extension, "application/octet-stream")

        return file_path, content_type

    async def delete_file(
        self, course_id: int, category: str, filename: str
    ) -> bool:
        """Delete a file."""
        file_path = self.storage_path / str(course_id) / category / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        os.remove(file_path)
        return True

    async def list_files(
        self, course_id: int, category: Optional[str] = None
    ) -> list:
        """List all files for a course."""
        course_dir = self.storage_path / str(course_id)

        if not course_dir.exists():
            return []

        files = []
        search_path = course_dir / category if category else course_dir

        if not search_path.exists():
            return []

        for file_path in search_path.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(self.storage_path)
                files.append(
                    {
                        "filename": file_path.name,
                        "path": str(rel_path),
                        "size": file_path.stat().st_size,
                        "modified_at": datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        ).isoformat(),
                    }
                )

        return files


# Singleton instance
file_storage_service = FileStorageService()
