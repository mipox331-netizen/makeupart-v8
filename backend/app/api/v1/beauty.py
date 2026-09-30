import os
import shutil
import uuid
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.crud.beauty_job import get_beauty_job, list_beauty_jobs
from app.core.config import settings
from app.crud.consent import get_active_consent
from app.db.session import get_db
from app.models.beauty_job import BeautyJob, BeautyJobStatus
from app.models.beauty_result import BeautyResult
from app.models.customer import Customer
from app.models.user import User
from app.schemas.beauty import (
    BeautyJobOut,
    BeautyProcessRequest,
    BeautyProcessResponse,
    BeautyUploadResponse,
)
from app.services.beauty import BeautyProvider, IdentityGuard, SkinToneMatcher

router = APIRouter(prefix="/beauty", tags=["beauty"])

ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _media_dirs(salon_id: uuid.UUID) -> tuple[Path, Path]:
    root = settings.media_root_path / "salons" / str(salon_id)
    input_dir = root / "inputs"
    output_dir = root / "outputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return input_dir, output_dir


def _safe_media_path(
    path: str,
    salon_id: uuid.UUID,
    *,
    error_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> Path:
    candidate = Path(path).resolve()
    root = (settings.media_root_path / "salons" / str(salon_id)).resolve()
    if candidate == root or root not in candidate.parents:
        raise HTTPException(status_code=error_status, detail="Media path is outside salon storage")
    return candidate


def _require_consent(
    db: Session,
    current_user: User,
    *,
    customer_id: uuid.UUID | None,
    consent_confirmed: bool,
) -> None:
    if not consent_confirmed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client consent is required before image processing",
        )
    if customer_id is None:
        return
    customer = db.get(Customer, customer_id)
    if customer is None or customer.salon_id != current_user.salon_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    if customer.consent_required and get_active_consent(db, current_user.salon_id, customer.id) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active customer consent is required before image processing",
        )


def _validate_uploaded_image(path: Path) -> None:
    try:
        raw = np.fromfile(path, dtype=np.uint8)
        image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not validate image data",
        ) from exc
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is not a valid image",
        )
    height, width = image.shape[:2]
    if height * width > settings.MAX_IMAGE_PIXELS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image dimensions are too large",
        )
    if not cv2.imwrite(str(path), image):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not normalize uploaded image",
        )


def _process_payload(
    payload: BeautyProcessRequest,
    provider: BeautyProvider,
    output_dir: Path,
) -> tuple[BeautyProcessResponse, str]:
    skin_matcher = SkinToneMatcher()
    identity_guard = IdentityGuard()
    attempt_intensity = float(payload.intensity)
    last_similarity = 0.0

    for _ in range(4):
        attempt_payload = payload.model_copy(update={"intensity": attempt_intensity})
        try:
            provider_options = {**attempt_payload.model_dump(), "output_dir": str(output_dir)}
            base_result = provider.process(attempt_payload.image_path, provider_options)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

        tone = skin_matcher.detect(attempt_payload.melanin_index)
        similarity = float(base_result["identity_similarity"])
        last_similarity = similarity
        accepted = identity_guard.validate(similarity, attempt_intensity)[1]
        if accepted:
            generated_output = Path(str(base_result["output_path"])).resolve()
        if output_dir.resolve() not in generated_output.parents:
            try:
                generated_output.unlink(missing_ok=True)
            except OSError:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Beauty provider generated media outside salon storage",
            )

            response = BeautyProcessResponse(
                identity_similarity=round(similarity, 4),
                skin_tone=tone["tone"],
                undertone=tone["undertone"],
                foundation_match=skin_matcher.recommend_foundation(
                    tone["tone"], tone["undertone"]
                ),
                intensity=round(attempt_intensity, 4),
                processed=bool(base_result["processed"]),
            )
            return response, str(generated_output)

        rejected_output = str(generated_output)
        if rejected_output:
            try:
                Path(rejected_output).unlink(missing_ok=True)
            except OSError:
                pass

        if attempt_intensity <= 0.05:
            break
        attempt_intensity = max(0.05, round(attempt_intensity * 0.65, 4))

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=(
            "Beauty processing could not satisfy the identity similarity threshold "
            f"(last_similarity={round(last_similarity, 4)})."
        ),
    )


@router.post("/process", response_model=BeautyProcessResponse, status_code=status.HTTP_200_OK)
def process_beauty(
    payload: BeautyProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BeautyProcessResponse:
    _require_consent(
        db,
        current_user,
        customer_id=None,
        consent_confirmed=payload.consent_confirmed,
    )
    input_dir, output_dir = _media_dirs(current_user.salon_id)
    input_path = Path(payload.image_path).resolve()
    if input_dir.resolve() not in input_path.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input image is outside salon storage",
        )
    if not input_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Input image not found")
    payload.image_path = str(input_path)

    response, output_path = _process_payload(payload, BeautyProvider(), output_dir)
    try:
        Path(output_path).unlink()
    except OSError:
        pass
    return response


@router.post("/process-upload", response_model=BeautyUploadResponse, status_code=status.HTTP_201_CREATED)
def process_beauty_upload(
    file: UploadFile = File(...),
    intensity: float = Query(default=0.7, ge=0.0, le=1.0),
    melanin_index: float = Query(default=2.0, ge=0.0, le=10.0),
    consent_confirmed: bool = Query(default=False),
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
    _require_consent(
        db,
        current_user,
        customer_id=customer_id,
        consent_confirmed=consent_confirmed,
    )

    input_dir, output_dir = _media_dirs(current_user.salon_id)
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

        _validate_uploaded_image(input_path)
        payload = BeautyProcessRequest(
            image_path=str(input_path),
            intensity=intensity,
            melanin_index=melanin_index,
            consent_confirmed=True,
        )
        response, generated_path = _process_payload(payload, BeautyProvider(), output_dir)
        generated_output = Path(generated_path).resolve()
        if output_dir.resolve() not in generated_output.parents:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Beauty provider generated media outside salon storage",
            )

        output_path = output_dir / f"{uuid.uuid4()}.png"
        shutil.move(generated_output, output_path)

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

        db.add(
            BeautyResult(
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
        )
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
        raise
    except Exception:
        db.rollback()
        for path in (input_path, output_path):
            if path:
                try:
                    path.unlink()
                except OSError:
                    pass
        raise


@router.get("/jobs", response_model=list[BeautyJobOut])
def list_job_records(
    customer_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[BeautyJob]:
    if customer_id is not None:
        customer = db.get(Customer, customer_id)
        if customer is None or customer.salon_id != current_user.salon_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return list_beauty_jobs(
        db,
        current_user.salon_id,
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/{job_id}", response_model=BeautyJobOut)
def read_job_record(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BeautyJob:
    job = get_beauty_job(db, current_user.salon_id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beauty job not found")
    return job


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

    path = _safe_media_path(stored_path, current_user.salon_id)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return FileResponse(path)
