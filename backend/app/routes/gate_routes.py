from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from ..database import get_db
from ..services import gate_service, gatepass_service
from ..schemas.gatepass import GatePassOut, StatusHistoryItem

router = APIRouter(prefix="/gate", tags=["gate"])

# Default system user ID (no authentication required)
SYSTEM_USER_ID = "system"


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


@router.post("/scan-exit", response_model=GatePassOut)
async def scan_exit(
    pass_number: str = Form(...),
    file: UploadFile = File(...),
    db=Depends(get_db),
):
    """
    Scan QR code at gate exit.
    - Requires pass_number (e.g., GP-2024-0001) and photo file
    - Validates gatepass is approved
    - Uploads and stores person's photo in database with gatepass linkage
    - Updates gatepass status to 'pending_return' (if returnable) or 'completed' (if not)
    """
    doc = await gate_service.process_exit_scan(db, pass_number, file, SYSTEM_USER_ID)
    return serialize_gatepass(doc)


@router.post("/scan-return", response_model=GatePassOut)
async def scan_return(
    pass_number: str = Form(...),
    file: UploadFile = File(...),
    db=Depends(get_db),
):
    """
    Scan QR code at gate return (for returnable gatepasses only).
    - Requires pass_number (e.g., GP-2024-0001) and photo file
    - Validates gatepass is returnable and in 'pending_return' status
    - Uploads and stores person's photo in database with gatepass linkage
    - Updates gatepass status to 'returned'
    """
    doc = await gate_service.process_return_scan(db, pass_number, file, SYSTEM_USER_ID)
    return serialize_gatepass(doc)


@router.get("/gatepass/number/{pass_number}", response_model=GatePassOut)
async def get_gatepass_by_number(pass_number: str, db=Depends(get_db)):
    """
    Get gatepass details by pass number (e.g., GP-2024-0001).
    Use this endpoint when scanning QR code which contains the pass number.
    """
    doc = gatepass_service.get_gatepass_by_number(db, pass_number)
    return serialize_gatepass(doc)


@router.get("/gatepass/id/{pass_number}", response_model=GatePassOut)
async def get_gatepass_by_number(pass_number: str, db=Depends(get_db)):
    """
    Get gatepass details by pass ID.
    Use this endpoint when you have the gatepass ID.
    """
    doc = gatepass_service.get_gatepass_by_number(db, pass_number)
    return serialize_gatepass(doc)


@router.get("/photos/{pass_number}")
async def get_gatepass_photos(pass_number: str, db=Depends(get_db)):
    """
    Get all photos associated with a gatepass by pass number.
    Returns exit and return photos with their details.
    """
    from bson import ObjectId
    
    # Query photos by pass_number (since we store pass_number in photo records)
    photos = list(db["photos"].find({"pass_number": pass_number}).sort("captured_at", -1))
    
    # Convert ObjectId to string for JSON serialization
    result = []
    for photo in photos:
        photo_dict = {
            "photo_id": photo.get("photo_id"),
            "gatepass_id": str(photo.get("gatepass_id")) if isinstance(photo.get("gatepass_id"), ObjectId) else photo.get("gatepass_id"),
            "file_url": photo.get("file_url"),
            "type": photo.get("type"),
            "captured_at": photo.get("captured_at"),
            "captured_by": photo.get("captured_by"),
            "pass_number": photo.get("pass_number"),
        }
        if "_id" in photo:
            photo_dict["_id"] = str(photo["_id"]) if isinstance(photo["_id"], ObjectId) else photo["_id"]
        result.append(photo_dict)
    
    return {"pass_number": pass_number, "photos": result, "total": len(result)}
