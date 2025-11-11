import os
import qrcode

from ..config import settings


def ensure_qr_dir() -> str:
    base = settings.MEDIA_ROOT
    qr_dir = os.path.join(base, settings.QR_DIR)
    os.makedirs(qr_dir, exist_ok=True)
    return qr_dir


def generate_qr_for_pass(pass_number: str) -> str:
    """
    Generate QR code for a gate pass number.
    Returns the URL path to access the QR code image.
    """
    qr_dir = ensure_qr_dir()
    filename = f"{pass_number}.png"
    file_path = os.path.join(qr_dir, filename)

    # Generate QR code with the pass number
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(pass_number)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(file_path)

    # Return URL path that matches the QR route
    return f"/qr/{pass_number}"
