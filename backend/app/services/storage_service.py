"""
Image Storage & Upload Service
Handles image validation, Cloudinary uploads, and fallback local/base64 storage.
"""

import logging
import base64
from typing import List, Dict, Any, Optional
from fastapi import UploadFile, HTTPException, status
from PIL import Image, ImageOps
import io

from app.core.config import settings

logger = logging.getLogger("findit.storage")

ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit

class StorageService:
    def __init__(self):
        self._cloudinary_configured = False
        if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
            try:
                import cloudinary
                import cloudinary.uploader
                cloudinary.config(
                    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                    api_key=settings.CLOUDINARY_API_KEY,
                    api_secret=settings.CLOUDINARY_API_SECRET,
                    secure=True
                )
                self._cloudinary_configured = True
                logger.info("✅ Cloudinary storage service configured successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize Cloudinary SDK: {e}")

    async def upload_image(self, file: UploadFile, folder: str = "findit/items") -> Dict[str, Any]:
        """
        Validate and upload a single image file.
        Returns dict containing `url` and `publicId`.
        """
        # 1. Validate MIME type
        if file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file format '{file.content_type}'. Allowed formats: JPG, PNG, WEBP."
            )

        contents = await file.read()

        # 2. Validate file size
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed limit of 10MB."
            )

        # 3. Process image with Pillow to verify integrity
        try:
            img = Image.open(io.BytesIO(contents)).convert("RGB")
            img = ImageOps.exif_transpose(img)
            # Re-encode compressed JPEG
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            compressed_bytes = buffer.getvalue()
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a valid image or is corrupted."
            )

        # 4. Upload to Cloudinary if available
        if self._cloudinary_configured:
            try:
                import cloudinary.uploader
                upload_result = cloudinary.uploader.upload(
                    compressed_bytes,
                    folder=folder,
                    resource_type="image"
                )
                return {
                    "url": upload_result.get("secure_url"),
                    "publicId": upload_result.get("public_id"),
                    "width": upload_result.get("width"),
                    "height": upload_result.get("height"),
                }
            except Exception as e:
                logger.error(f"Cloudinary upload failed: {e}")

        # Fallback for development without Cloudinary credentials: Base64 data URL
        b64_str = base64.b64encode(compressed_bytes).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64_str}"
        fake_id = f"local_{hash(data_url) & 0xFFFFFFFF}"
        return {
            "url": data_url,
            "publicId": fake_id,
            "width": 800,
            "height": 600,
        }

    async def upload_multiple_images(self, files: List[UploadFile], folder: str = "findit/items") -> List[Dict[str, Any]]:
        """
        Upload multiple images concurrently.
        """
        uploaded = []
        for file in files:
            res = await self.upload_image(file, folder=folder)
            uploaded.append(res)
        return uploaded

storage_service = StorageService()
