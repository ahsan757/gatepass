from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

from fastapi import HTTPException

from ..utils.generate_qr import generate_qr_for_pass
from ..schemas.gatepass import GatePassCreate, GatePassFilter


def _new_gatepass_number(db):
    year = datetime.utcnow().year
    count = db["gatepasses"].count_documents({"year": year}) + 1
    return f"GP-{year}-{count:04d}"


def create_gatepass(db, hr_user_id: str, payload: GatePassCreate) -> Dict[str, Any]:
    from bson import ObjectId
    number = _new_gatepass_number(db)
    now = datetime.utcnow()
    qr_url = generate_qr_for_pass(number)

    doc = {
        "_id": uuid4().hex,
        "number": number,
        "person_name": payload.person_name,
        "description": payload.description,
        "created_by": hr_user_id,
        "is_returnable": payload.is_returnable,
        "status": "pending",
        "status_history": [
            {
                "status": "pending",
                "changed_at": now,
                "changed_by": hr_user_id,
            }
        ],
        "created_at": now,
        "approved_at": None,
        "exit_photo_id": None,
        "return_photo_id": None,
        "exit_time": None,
        "return_time": None,
        "qr_code_url": qr_url,
        "year": now.year,
    }
    db["gatepasses"].insert_one(doc)
    # Convert _id to string if MongoDB converted it to ObjectId
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


def _get_by_id(db, pass_id: str) -> Dict[str, Any]:
    # Try to find by _id as string first, then as ObjectId
    from bson import ObjectId
    doc = db["gatepasses"].find_one({"_id": pass_id})
    if not doc:
        # Try with ObjectId if pass_id is a valid ObjectId string
        try:
            doc = db["gatepasses"].find_one({"_id": ObjectId(pass_id)})
        except:
            pass
    if not doc:
        raise HTTPException(status_code=404, detail="Gate pass not found")
    # Convert _id to string if it's ObjectId
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


def _get_by_number(db, number: str) -> Dict[str, Any]:
    doc = db["gatepasses"].find_one({"number": number})
    if not doc:
        raise HTTPException(status_code=404, detail="Gate pass not found")
    # Convert _id to string if it's ObjectId
    from bson import ObjectId
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


def get_gatepass_by_id(db, pass_id: str) -> Dict[str, Any]:
    return _get_by_id(db, pass_id)


def get_gatepass_by_number(db, number: str) -> Dict[str, Any]:
    return _get_by_number(db, number)


def list_gatepasses(db, filter_obj: Optional[GatePassFilter] = None) -> List[Dict[str, Any]]:
    from bson import ObjectId
    query: Dict[str, Any] = {}
    if filter_obj:
        if filter_obj.status:
            query["status"] = filter_obj.status
        if filter_obj.created_by:
            query["created_by"] = filter_obj.created_by
    docs = list(db["gatepasses"].find(query).sort("created_at", -1))
    # Convert all ObjectId _id fields to strings
    for doc in docs:
        if isinstance(doc.get("_id"), ObjectId):
            doc["_id"] = str(doc["_id"])
    return docs


def _append_status_history(doc: Dict[str, Any], new_status: str, user_id: str):
    history = doc.get("status_history", [])
    history.append(
        {
            "status": new_status,
            "changed_at": datetime.utcnow(),
            "changed_by": user_id,
        }
    )
    doc["status_history"] = history


def approve_gatepass(db, pass_id: str, admin_user_id: str) -> Dict[str, Any]:
    from bson import ObjectId
    doc = _get_by_id(db, pass_id)
    if doc["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending passes can be approved")

    doc["status"] = "approved"
    doc["approved_at"] = datetime.utcnow()
    _append_status_history(doc, "approved", admin_user_id)
    
    # Use the document's _id for update (could be string or ObjectId)
    update_filter = {"_id": doc["_id"]} if isinstance(doc["_id"], ObjectId) else {"_id": doc["_id"]}
    # Remove _id from update data as it can't be updated
    update_data = {k: v for k, v in doc.items() if k != "_id"}
    db["gatepasses"].update_one(update_filter, {"$set": update_data})
    
    # Ensure _id is string in returned doc
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


def reject_gatepass(db, pass_id: str, admin_user_id: str) -> Dict[str, Any]:
    from bson import ObjectId
    doc = _get_by_id(db, pass_id)
    if doc["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending passes can be rejected")

    doc["status"] = "rejected"
    _append_status_history(doc, "rejected", admin_user_id)
    
    # Use the document's _id for update
    update_filter = {"_id": doc["_id"]}
    # Remove _id from update data as it can't be updated
    update_data = {k: v for k, v in doc.items() if k != "_id"}
    db["gatepasses"].update_one(update_filter, {"$set": update_data})
    
    # Ensure _id is string in returned doc
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


def update_on_exit(db, pass_number: str, photo_id: Optional[str], gate_user_id: str) -> Dict[str, Any]:
    from bson import ObjectId
    doc = _get_by_number(db, pass_number)
    if doc["status"] != "approved":
        raise HTTPException(status_code=400, detail="Only approved passes can be used for exit")

    now = datetime.utcnow()
    new_status = "pending_return" if doc.get("is_returnable") else "completed"

    doc["status"] = new_status
    doc["exit_time"] = now
    if photo_id:
        doc["exit_photo_id"] = photo_id
    _append_status_history(doc, new_status, gate_user_id)

    # Use the document's _id for update
    update_filter = {"_id": doc["_id"]}
    # Remove _id from update data as it can't be updated
    update_data = {k: v for k, v in doc.items() if k != "_id"}
    db["gatepasses"].update_one(update_filter, {"$set": update_data})
    
    # Ensure _id is string in returned doc
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


def update_on_return(db, pass_number: str, photo_id: Optional[str], gate_user_id: str) -> Dict[str, Any]:
    from bson import ObjectId
    doc = _get_by_number(db, pass_number)
    if doc["status"] != "pending_return":
        raise HTTPException(status_code=400, detail="Return only allowed for pending_return")

    now = datetime.utcnow()
    doc["status"] = "returned"
    doc["return_time"] = now
    if photo_id:
        doc["return_photo_id"] = photo_id
    _append_status_history(doc, "returned", gate_user_id)

    # Use the document's _id for update
    update_filter = {"_id": doc["_id"]}
    # Remove _id from update data as it can't be updated
    update_data = {k: v for k, v in doc.items() if k != "_id"}
    db["gatepasses"].update_one(update_filter, {"$set": update_data})
    
    # Ensure _id is string in returned doc
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc
