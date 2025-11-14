import os
import qrcode
from io import BytesIO
from pathlib import Path

from ..config import settings


def ensure_qr_dir() -> str:
    base = settings.MEDIA_ROOT
    qr_dir = os.path.join(base, settings.QR_DIR)
    os.makedirs(qr_dir, exist_ok=True)
    return qr_dir


def get_frontend_url():
    env = os.getenv("ENV", "dev")
    return os.getenv("PROD_NEXTJS_URL") if env == "prod" else os.getenv("DEV_NEXTJS_URL")


def generate_qr_for_pass(gatepass_id: str) -> str:
    base_url = get_frontend_url()
    final_url = f"{base_url}/gatepass?gid={gatepass_id}"

    qr_dir = ensure_qr_dir()
    
    # file path
    filename = f"{gatepass_id}.png"
    file_path = os.path.join(qr_dir, filename)

    # Generate QR and save to file
    qr = qrcode.make(final_url)
    qr.save(file_path)

    # Return string URL for frontend/media access
    return f"{base_url}/media/qr/{filename}"
