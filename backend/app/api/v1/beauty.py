from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.beauty import BeautyProcessRequest, BeautyProcessResponse
from app.services.beauty import BeautyProvider, IdentityGuard, SkinToneMatcher

router = APIRouter(prefix="/beauty", tags=["beauty"])


@router.post("/process", response_model=BeautyProcessResponse, status_code=status.HTTP_200_OK)
def process_beauty(
    payload: BeautyProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BeautyProcessResponse:
    del db
    provider = BeautyProvider()
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
    return BeautyProcessResponse(
        identity_similarity=round(similarity, 4),
        skin_tone=tone["tone"],
        undertone=tone["undertone"],
        foundation_match=skin_matcher.recommend_foundation(tone["tone"], tone["undertone"]),
        intensity=round(final_intensity, 4),
        processed=base_result["processed"],
    )
