import io
import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.watermark import get_or_create_watermark, salon_logo_path
from app.schemas.watermark import WatermarkOut, WatermarkUpdate
from app.services.media_volume import commit_media_volume
from app.services import google_drive_media
from app.services.google_drive_media import GoogleDriveMediaError

router = APIRouter(prefix="/watermarks", tags=["watermarks"])
logger = logging.getLogger("makeupart.watermarks")


def _rollback_failed_logo_upload(
    target: Path,
    backup: Path,
    *,
    had_previous: bool,
    target_replaced: bool,
) -> bool:
    """Restore local and durable logo state after a failed replacement."""
    if not target_replaced:
        return True

    durable_required = (
        settings.REQUIRE_DURABLE_MEDIA
        or settings.ENVIRONMENT.lower() == "production"
    )
    try:
        if had_previous:
            if not backup.is_file():
                raise OSError("The previous salon logo backup is unavailable.")
            shutil.copy2(backup, target)
            persisted = google_drive_media.persist_media_file(target)
            if durable_required and not persisted:
                raise GoogleDriveMediaError(
                    "Could not confirm restoration of the previous logo in private storage."
                )
        else:
            # Keep a first-time logo on disk until remote cleanup has succeeded;
            # otherwise a failed cleanup could leave an unreferenced Drive copy.
            deleted = google_drive_media.delete_media_file(target)
            if durable_required and not deleted:
                raise GoogleDriveMediaError(
                    "Could not confirm cleanup of the failed logo upload in private storage."
                )
            target.unlink(missing_ok=True)

        commit_media_volume()
        return True
    except Exception:
        logger.exception("Failed to restore the prior salon-logo state after an upload error")
        return False


_MAX_LOGO_BYTES = 5 * 1024 * 1024
_MAX_LOGO_PIXELS = 25_000_000
_ALLOWED_LOGO_TYPES = {"image/png", "image/jpeg", "image/webp"}


def _logo_path(salon_id: uuid.UUID) -> Path:
    try:
        return salon_logo_path(str(salon_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Salon logo storage path failed tenant-isolation validation.",
        ) from exc


@router.get("/me", response_model=WatermarkOut)
def read_watermark(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WatermarkOut:
    watermark = get_or_create_watermark(db, current_user.salon)
    db.commit()
    db.refresh(watermark)
    return watermark


@router.patch("/me", response_model=WatermarkOut)
def update_watermark(
    watermark_in: WatermarkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> WatermarkOut:
    watermark = get_or_create_watermark(db, current_user.salon)
    for field, value in watermark_in.model_dump(exclude_unset=True).items():
        # Logo uploads must use the dedicated, validated binary upload route.
        if field != "logo_url":
            setattr(watermark, field, value)
    db.commit()
    db.refresh(watermark)
    return watermark


@router.post("/me/logo", response_model=WatermarkOut)
async def upload_watermark_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> WatermarkOut:
    if (file.content_type or "").lower() not in _ALLOWED_LOGO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Logo must be a PNG, JPEG, or WebP image.",
        )

    content = await file.read(_MAX_LOGO_BYTES + 1)
    if not content or len(content) > _MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Logo must be smaller than 5 MB.",
        )

    try:
        with Image.open(io.BytesIO(content)) as probe:
            width, height = probe.size
            if width <= 0 or height <= 0 or width * height > _MAX_LOGO_PIXELS:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Logo dimensions are too large.",
                )
            probe.verify()
        with Image.open(io.BytesIO(content)) as source:
            logo = ImageOps.exif_transpose(source).convert("RGBA")
    except HTTPException:
        raise
    except Image.DecompressionBombError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Logo dimensions are too large.",
        ) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded logo is not a valid image.",
        ) from exc

    target = _logo_path(current_user.salon_id)
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Salon logo storage path is not a regular file.",
        )

    temporary = target.with_name(f".logo-{uuid.uuid4().hex}.tmp")
    backup = target.with_name(f".logo-{uuid.uuid4().hex}.rollback")
    had_previous = target.is_file()
    target_replaced = False
    rollback_ok = True
    db_committed = False

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if had_previous:
            # Preserve the last known-good logo until cloud persistence and the
            # database update both succeed.
            shutil.copy2(target, backup)

        logo.save(temporary, format="PNG", optimize=True)
        os.replace(temporary, target)
        target_replaced = True

        persisted = google_drive_media.persist_media_file(target)
        durable_required = (
            settings.REQUIRE_DURABLE_MEDIA
            or settings.ENVIRONMENT.lower() == "production"
        )
        if durable_required and not persisted:
            raise GoogleDriveMediaError(
                "Private media storage did not confirm that the salon logo was saved."
            )
        commit_media_volume()

        watermark = get_or_create_watermark(db, current_user.salon)
        watermark.logo_url = "/api/v1/watermarks/me/logo"
        current_user.salon.logo_url = watermark.logo_url
        db.commit()
        db_committed = True
        db.refresh(watermark)
        return watermark
    except Exception as exc:
        if db_committed:
            # Storage and database have committed. Do not roll them back merely
            # because refreshing the response failed; a retry is idempotent.
            logger.exception("Salon logo was saved but the response could not be refreshed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="The logo was saved, but its response could not be refreshed. Reload the screen before retrying.",
            ) from exc

        db.rollback()
        rollback_ok = _rollback_failed_logo_upload(
            target,
            backup,
            had_previous=had_previous,
            target_replaced=target_replaced,
        )
        if not rollback_ok:
            detail = (
                "The logo upload failed and automatic restoration was incomplete. "
                "A recovery copy was retained where available; do not retry until storage is checked."
            )
        elif isinstance(exc, GoogleDriveMediaError):
            detail = "Private Google Drive storage could not confirm the upload. The previous logo was restored."
        elif isinstance(exc, OSError):
            detail = "Could not save the salon logo. The previous logo was restored."
        else:
            logger.exception("Unexpected salon logo upload failure")
            detail = "Could not save the salon logo. The previous logo was restored."

        error_status = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if isinstance(exc, GoogleDriveMediaError) or not rollback_ok
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=error_status, detail=detail) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove temporary salon-logo upload file")
        # Keep the previous image as a recovery artifact if restoration was not
        # fully confirmed. Otherwise remove the temporary backup.
        if backup.exists() and (rollback_ok or db_committed or not target_replaced):
            try:
                backup.unlink(missing_ok=True)
            except OSError:
                logger.exception("Could not remove temporary salon-logo rollback backup")



@router.get("/me/logo")
def read_watermark_logo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    watermark = get_or_create_watermark(db, current_user.salon)
    path = _logo_path(current_user.salon_id)
    if not watermark.logo_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon logo not found")
    if not path.is_file():
        try:
            restored = google_drive_media.ensure_local_file(path)
        except GoogleDriveMediaError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Private salon logo storage is temporarily unavailable.",
            ) from exc
        if not restored or not path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon logo not found")
        commit_media_volume()
    return FileResponse(path, media_type="image/png", filename="salon-logo.png")


@router.delete("/me/logo", response_model=WatermarkOut)
def delete_watermark_logo(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> WatermarkOut:
    path = _logo_path(current_user.salon_id)
    try:
        google_drive_media.delete_media_file(path)
    except GoogleDriveMediaError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not securely remove the salon logo from private Drive storage.",
        ) from exc
    path.unlink(missing_ok=True)
    commit_media_volume()

    watermark = get_or_create_watermark(db, current_user.salon)
    watermark.logo_url = None
    current_user.salon.logo_url = None
    db.commit()
    db.refresh(watermark)
    return watermark
