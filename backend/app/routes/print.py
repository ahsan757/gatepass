from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from reportlab.pdfgen import canvas
import os


from ..config import settings
from ..database import get_db
from ..services import gatepass_service

router = APIRouter(prefix="/media", tags=["media"])



@router.get("/gatepass/{pass_id}/print")
async def print_gatepass(pass_number: str, db=Depends(get_db)):
    """Generate and download a printable PDF for the selected gate pass."""

    gp = gatepass_service.get_gatepass_by_number(db, pass_number)
    if not gp:
        raise HTTPException(status_code=404, detail="Gate pass not found")
    
    # Ensure media folder exists
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    filename = f"{gp['number']}.pdf"
    file_path = os.path.join(settings.MEDIA_ROOT, filename)

    # Create PDF using reportlab
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
    if gp.get("approved_at"):
        c.drawString(100, 680, f"Approved At: {gp['approved_at'].strftime('%Y-%m-%d %H:%M:%S')}")

    # Include QR code if available (with gap after approved_at)
    if gp.get("qr_code_url"):
        # Extract pass number from gatepass
        pass_number = gp.get("number")
        qr_path = os.path.join(settings.MEDIA_ROOT, settings.QR_DIR, f"{pass_number}.png")
        if not os.path.exists(qr_path):
            # Try alternative path format
            qr_path = "." + gp["qr_code_url"] if gp["qr_code_url"].startswith("/") else gp["qr_code_url"]
        
        if os.path.exists(qr_path):
            # Add gap between approved_at and QR image (position QR code lower)
            c.drawImage(qr_path, 100, 560, width=150, height=150)
            c.drawString(100, 540, "Scan QR code at gate")

    c.showPage()
    c.save()

    return FileResponse(file_path, media_type="application/pdf", filename=filename)
