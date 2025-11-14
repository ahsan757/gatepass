from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from reportlab.pdfgen import canvas
import os

from ..database import get_db
from ..schemas.gatepass import GatePassOut, StatusHistoryItem
from ..services import admin_service, gatepass_service
from ..config import settings

router = APIRouter(prefix="/admin", tags=["admin"])

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


@router.get("/gatepass/pending", response_model=List[GatePassOut])
async def pending_gatepasses(db=Depends(get_db)):
    docs = admin_service.get_pending_gatepasses(db)
    return [serialize_gatepass(d) for d in docs]


@router.get("/gatepass/{pass_number}", response_model=GatePassOut)
async def get_gatepass_detail(pass_id: str, db=Depends(get_db)):
    """
    Get gatepass details by ID.
    Admin can view any gatepass details.
    """
    doc = gatepass_service.get_gatepass_by_number(db, pass_id)
    return serialize_gatepass(doc)


@router.post("/gatepass/{pass_number}/approve", response_model=GatePassOut)
async def approve_gatepass(pass_number: str, db=Depends(get_db)):
    doc = admin_service.approve_gatepass(db, pass_number, SYSTEM_USER_ID)
    return serialize_gatepass(doc)


@router.post("/gatepass/{pass_number}/reject", response_model=GatePassOut)
async def reject_gatepass(pass_number: str, db=Depends(get_db)):
    doc = admin_service.reject_gatepass(db, pass_number, SYSTEM_USER_ID)
    return serialize_gatepass(doc)


@router.get("/gatepass/all", response_model=List[GatePassOut])
async def all_gatepasses(
    status: str | None = None,
    db=Depends(get_db),
):
    docs = admin_service.list_all_gatepasses(db, status)
    return [serialize_gatepass(d) for d in docs]


@router.get("/gatepass/{pass_number}/print")
async def print_gatepass(pass_number: str, db=Depends(get_db)):
    """
    Print gatepass as PDF (with QR code).
    Admin can print approved gatepasses.
    """
    gp = gatepass_service.get_gatepass_by_number(db, pass_number)

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    filename = f"{gp['number']}.pdf"
    file_path = os.path.join(settings.MEDIA_ROOT, filename)

    c = canvas.Canvas(file_path)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 800, f"Gate Pass: {gp['number']}")
    c.setFont("Helvetica", 12)
    c.drawString(100, 780, f"Name: {gp['person_name']}")
    c.drawString(100, 760, f"Description: {gp['description']}")
    c.drawString(100, 740, f"Status: {gp['status']}")
    c.drawString(100, 720, f"Type: {'Returnable' if gp.get('is_returnable') else 'Non-Returnable'}")
    c.drawString(100, 700, f"Created At: {gp['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")

    # Add approved_at if available
    current_y = 680
    if gp.get("approved_at"):
        c.drawString(100, current_y, f"Approved At: {gp['approved_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        current_y -= 40  # extra space before QR

    # Include QR code if available (with gap after approved_at)
    if gp.get("qr_code_url"):
        # Extract pass number from gatepass
        pass_number = gp.get("number")
        qr_path = os.path.join(settings.MEDIA_ROOT, settings.QR_DIR, f"{pass_number}.png")
        if not os.path.exists(qr_path):
            # Try alternative path format
            qr_path = "." + gp["qr_code_url"] if gp["qr_code_url"].startswith("/") else gp["qr_code_url"]

        if os.path.exists(qr_path):
            # Draw QR code lower to create space
            qr_y = current_y - 150  # QR height
            c.drawImage(qr_path, 100, qr_y, width=150, height=150)
            c.drawString(100, qr_y - 20, "Scan QR code at gate")

    c.showPage()
    c.save()

    return FileResponse(file_path, media_type="application/pdf", filename=filename)
