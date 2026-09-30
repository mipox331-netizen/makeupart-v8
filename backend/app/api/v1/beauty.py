import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.db.session import get_db
from app.models.beauty_job import BeautyJob, BeautyJobStatus
from app.models.beauty_result import BeautyResult
from app.models.user import User
from app.schemas.beauty import (
    BeautyProcessRequest,
    BeautyProcessResponse,
    BeautyUploadResponse,
)
from app.services.beauty import BeautyProvider, IdentityGuard, SkinToneMatcher

router = APIRouter(prefix="/beauty", tags=["beauty"])

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _media_dirs() -> tuple[Path, Path]:
    root = settings.media_root_path
    input_dir = root / "inputs"
    output_dir = root / "outputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return input_dir, output_dir


def _safe_output_path(path: str) -> Path:
    candidate = Path(path).resolve()
    root = settings.media_root_path
    if root not in candidate.parents:
        raise HTTPException(status_code=500, detail="Stored media path is outside media storage")
    return candidate


def _process_payload(
    payload: BeautyProcessRequest,
    provider: BeautyProvider,
) -> tuple[BeautyProcessResponse, str]:
    skin_matcher = SkinToneMatcher()
    identity_guard = IdentityGuard()
    try:
        base_result = provider.process(payload.image_path, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    tone = skin_matcher.detect(payload.melanin_index)
    similarity = float(base_result["identity_similarity"])
    final_intensity, accepted = identity_guard.validate(similarity, float(payload.intensity))
    if not accepted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Beauty processing could not satisfy the identity similarity threshold.",
        )
    response = BeautyProcessResponse(
        identity_similarity=round(similarity, 4),
        skin_tone=tone["tone"],
        undertone=tone["undertone"],
        foundation_match=skin_matcher.recommend_foundation(tone["tone"], tone["undertone"]),
        intensity=round(final_intensity, 4),
        processed=bool(base_result["processed"]),
    )
    return response, str(base_result["output_path"])


@router.post("/process", response_model=BeautyProcessResponse, status_code=status.HTTP_200_OK)
def process_beauty(
    payload: BeautyProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BeautyProcessResponse:
    del db, current_user
    response, output_path = _process_payload(payload, BeautyProvider())
    try:
        os.unlink(output_path)
    except OSError:
        pass
    return response


@router.post("/process-upload", response_model=BeautyUploadResponse, status_code=status.HTTP_201_CREATED)
def process_beauty_upload(
    file: UploadFile = File(...),
    intensity: float = Query(default=0.7, ge=0.0, le=1.0),
    melanin_index: float = Query(default=2.0, ge=0.0, le=10.0),
    customer_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BeautyUploadResponse:
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, and WebP images are supported.",
        )

    input_dir, output_dir = _media_dirs()
    input_path = input_dir / f"{uuid.uuid4()}{extension}"
    output_path: Path | None = None

    try:
        total = 0
        with input_path.open("wb") as destination:
            while chunk := file.file.read(1024 * 1024):
                total += len(chunk)
                if total > settings.MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Image exceeds the {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
                    )
                destination.write(chunk)

        payload = BeautyProcessRequest(
            image_path=str(input_path),
            intensity=intensity,
            melanin_index=melanin_index,
        )
        response, generated_path = _process_payload(payload, BeautyProvider())

        output_path = output_dir / f"{uuid.uuid4()}.png"
        shutil.move(generated_path, output_path)

        job = BeautyJob(
            salon_id=current_user.salon_id,
            customer_id=customer_id,
            status=BeautyJobStatus.COMPLETED,
            selected_makeup="AI beauty enhancement",
            intensity=response.intensity,
            shade=response.foundation_match,
            before_image_url=f"/api/v1/beauty/jobs/{{job_id}}/image?kind=before",
            after_image_url=f"/api/v1/beauty/jobs/{{job_id}}/image?kind=after",
            input_file_path=str(input_path),
            output_file_path=str(output_path),
        )
        db.add(job)
        db.flush()

        job.before_image_url = f"/api/v1/beauty/jobs/{job.id}/image?kind=before"
        job.after_image_url = f"/api/v1/beauty/jobs/{job.id}/image?kind=after"

        result = BeautyResult(
            salon_id=current_user.salon_id,
            beauty_job_id=job.id,
            before_image_url=job.before_image_url,
            after_image_url=job.after_image_url,
            identity_similarity=response.identity_similarity,
            skin_tone=response.skin_tone,
            undertone=response.undertone,
            foundation_match=response.foundation_match,
            watermark_applied=False,
        )
        db.add(result)
        db.commit()

        return BeautyUploadResponse(
            **response.model_dump(),
            job_id=job.id,
            before_image_url=job.before_image_url,
            after_image_url=job.after_image_url,
        )
    except HTTPException:
        db.rollback()
        for path in (input_path, output_path):
            if path:
                try:
                    path.unlink()
                except OSError:
                    pass
        if output_path:
            try:
                Path(str(input_path) + ".output").unlink()
            except OSError:
                pass
        raise
    except Exception:
        db.rollback()
        for path in (input_path, output_path):
            if path:
                try:
                    path.unlink()
                except OSError:
                    pass
        try:
            Path(str(input_path) + ".output").unlink()
        except OSError:
            pass
        raise


@router.get("/jobs/{job_id}/image")
def get_job_image(
    job_id: uuid.UUID,
    kind: str = Query(..., pattern=r"^(before|after)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    job = db.get(BeautyJob, job_id)
    if job is None or job.salon_id != current_user.salon_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beauty job not found")

    stored_path = job.input_file_path if kind == "before" else job.output_file_path
    if not stored_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    path = _safe_output_path(stored_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return FileResponse(path)
