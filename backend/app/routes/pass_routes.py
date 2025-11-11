from typing import List
from fastapi import APIRouter, Depends

from ..database import get_db
from ..schemas.gatepass import GatePassOut, StatusHistoryItem, GatePassFilter
from ..services import gatepass_service

router = APIRouter(prefix="/pass", tags=["gatepass"])


def serialize_gatepass(doc) -> GatePassOut:
    # Convert ObjectId to string for JSON serialization
    from bson import ObjectId
    doc_id = str(doc["_id"]) if isinstance(doc["_id"], ObjectId) else doc["_id"]
    created_by = str(doc["created_by"]) if isinstance(doc["created_by"], ObjectId) else doc["created_by"]
    
    return GatePassOut(
        id=doc_id,
        number=doc["number"],
        person_name=doc["person_name"],
        description=doc["description"],
        created_by=created_by,
        is_returnable=doc["is_returnable"],
        status=doc["status"],
        status_history=[
            StatusHistoryItem(
                status=h["status"],
                changed_at=h["changed_at"],
                changed_by=str(h["changed_by"]) if isinstance(h.get("changed_by"), ObjectId) else h["changed_by"],
            )
            for h in doc.get("status_history", [])
        ],
        created_at=doc["created_at"],
        approved_at=doc.get("approved_at"),
        exit_photo_id=doc.get("exit_photo_id"),
        return_photo_id=doc.get("return_photo_id"),
        exit_time=doc.get("exit_time"),
        return_time=doc.get("return_time"),
        qr_code_url=doc.get("qr_code_url"),
    )


@router.get("/list", response_model=List[GatePassOut])
async def list_passes(
    status: str | None = None,
    db=Depends(get_db),
):
    filter_obj = GatePassFilter(status=status)
    docs = gatepass_service.list_gatepasses(db, filter_obj)
    return [serialize_gatepass(d) for d in docs]
