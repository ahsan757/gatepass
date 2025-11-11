from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from datetime import datetime

from ..utils.photo_upload import save_photo_file
from . import gatepass_service


async def process_exit_scan(db, pass_number: str, file: UploadFile, gate_user_id: str) -> Dict[str, Any]:
    """
    Process exit scan: validate gatepass, save photo, and update status.
    Only approved gatepasses can be used for exit.
    Photo is required and will be stored in database with gatepass linkage.
    """
    from bson import ObjectId
    
    # Get gatepass by number
    gp = gatepass_service.get_gatepass_by_number(db, pass_number)
    
    # Validate gatepass is approved
    if gp["status"] != "approved":
        raise HTTPException(
            status_code=400, 
            detail=f"Gatepass {pass_number} is not approved. Current status: {gp['status']}"
        )

    # Save photo (required)
    filename = await save_photo_file(file)
    gatepass_id = gp["_id"]
    
    # Ensure gatepass_id is in correct format for MongoDB
    if not isinstance(gatepass_id, ObjectId):
        try:
            gatepass_id = ObjectId(gatepass_id) if len(str(gatepass_id)) == 24 else gatepass_id
        except:
            pass
    
    photo_record = {
        "photo_id": filename,
        "gatepass_id": gatepass_id,
        "file_url": f"/media/photo/{filename}",
        "type": "exit",
        "captured_at": datetime.utcnow(),
        "captured_by": gate_user_id,
        "pass_number": pass_number,  # Store pass number for easy reference
    }
    
    db["photos"].insert_one(photo_record)
    
    # Convert ObjectId to string if needed
    if isinstance(photo_record.get("gatepass_id"), ObjectId):
        photo_record["gatepass_id"] = str(photo_record["gatepass_id"])
    if "_id" in photo_record and isinstance(photo_record["_id"], ObjectId):
        photo_record["_id"] = str(photo_record["_id"])
    
    photo_id = filename

    # Update gatepass status using pass number
    return gatepass_service.update_on_exit(db, pass_number, photo_id, gate_user_id)


async def process_return_scan(db, pass_number: str, file: UploadFile, gate_user_id: str) -> Dict[str, Any]:
    """
    Process return scan: validate gatepass, save photo, and update status.
    Only returnable gatepasses with status 'pending_return' can be returned.
    Photo is required and will be stored in database with gatepass linkage.
    """
    from bson import ObjectId
    
    # Get gatepass by number
    gp = gatepass_service.get_gatepass_by_number(db, pass_number)
    
    # Validate gatepass is returnable and in pending_return status
    if not gp.get("is_returnable", False):
        raise HTTPException(
            status_code=400,
            detail=f"Gatepass {pass_number} is not returnable"
        )
    
    if gp["status"] != "pending_return":
        raise HTTPException(
            status_code=400,
            detail=f"Gatepass {pass_number} cannot be returned. Current status: {gp['status']}"
        )

    # Save photo (required)
    filename = await save_photo_file(file)
    gatepass_id = gp["_id"]
    
    # Ensure gatepass_id is in correct format for MongoDB
    if not isinstance(gatepass_id, ObjectId):
        try:
            gatepass_id = ObjectId(gatepass_id) if len(str(gatepass_id)) == 24 else gatepass_id
        except:
            pass
    
    photo_record = {
        "photo_id": filename,
        "gatepass_id": gatepass_id,
        "file_url": f"/media/photo/{filename}",
        "type": "return",
        "captured_at": datetime.utcnow(),
        "captured_by": gate_user_id,
        "pass_number": pass_number,  # Store pass number for easy reference
    }
    
    db["photos"].insert_one(photo_record)
    
    # Convert ObjectId to string if needed
    if isinstance(photo_record.get("gatepass_id"), ObjectId):
        photo_record["gatepass_id"] = str(photo_record["gatepass_id"])
    if "_id" in photo_record and isinstance(photo_record["_id"], ObjectId):
        photo_record["_id"] = str(photo_record["_id"])
    
    photo_id = filename

    # Update gatepass status using pass number
    return gatepass_service.update_on_return(db, pass_number, photo_id, gate_user_id)

