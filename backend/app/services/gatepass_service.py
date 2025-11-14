from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

from fastapi import HTTPException
from bson import ObjectId

from ..utils.generate_qr import generate_qr_for_pass
from ..schemas.gatepass import GatePassCreate, GatePassFilter


# -----------------------------
# Helpers
# -----------------------------

def _normalize_id(doc: Dict[str, Any]):
    """Ensure _id is always a string for API responses."""
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


def _new_gatepass_number(db):
    year = datetime.utcnow().year
    count = db["gatepasses"].count_documents({"year": year}) + 1
    return f"GP-{year}-{count:04d}"


def _find_gatepass(db, query: Dict[str, Any]):
    """Unified fetch function supporting both string and ObjectId."""
    doc = db["gatepasses"].find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Gate pass not found")
    return _normalize_id(doc)


def _append_status_history(doc: Dict[str, Any], new_status: str, user_id: str):
    doc.setdefault("status_history", []).append({
        "status": new_status,
        "changed_at": datetime.utcnow(),
        "changed_by": user_id,
    })


def _update_doc(db, doc: Dict[str, Any]):
    """Safely update doc using correct filter."""
    raw_id = doc["_id"]
    filter_id = ObjectId(raw_id) if ObjectId.is_valid(raw_id) else raw_id

    update_data = {k: v for k, v in doc.items() if k != "_id"}
    db["gatepasses"].update_one({"_id": filter_id}, {"$set": update_data})
    return doc


# -----------------------------
# CRUD functions
# -----------------------------

def create_gatepass(db, hr_user_id: str, payload: GatePassCreate) -> Dict[str, Any]:
    number = _new_gatepass_number(db)
    now = datetime.utcnow()

    doc = {
        "_id": uuid4().hex,  # Always store _id as string. Avoid mixing ObjectId and strings.
        "number": number,
        "person_name": payload.person_name,
        "description": payload.description,
        "created_by": hr_user_id,
        "is_returnable": payload.is_returnable,
        "status": "pending",
        "status_history": [{
            "status": "pending",
            "changed_at": now,
            "changed_by": hr_user_id,
        }],
        "created_at": now,
        "approved_at": None,
        "exit_photo_id": None,
        "return_photo_id": None,
        "exit_time": None,
        "return_time": None,
        "qr_code_url": generate_qr_for_pass(number),
        "year": now.year,
    }

    db["gatepasses"].insert_one(doc)
    return doc


def get_gatepass_by_id(db, pass_id: str):
    query = {"_id": pass_id}

    if ObjectId.is_valid(pass_id):
        doc = db["gatepasses"].find_one({"_id": ObjectId(pass_id)}) or db["gatepasses"].find_one(query)
    else:
        doc = db["gatepasses"].find_one(query)

    if not doc:
        raise HTTPException(status_code=404, detail="Gate pass not found")

    return _normalize_id(doc)


def get_gatepass_by_number(db, number: str):
    return _find_gatepass(db, {"number": number})


def list_gatepasses(db, filter_obj: Optional[GatePassFilter] = None):
    query = {}

    if filter_obj:
        if filter_obj.status:
            query["status"] = filter_obj.status
        if filter_obj.created_by:
            query["created_by"] = filter_obj.created_by

    docs = list(db["gatepasses"].find(query).sort("created_at", -1))
    return [_normalize_id(doc) for doc in docs]


# -----------------------------
# Workflow Updates
# -----------------------------

def approve_gatepass(db, pass_number: str, admin_user_id: str):
    doc = get_gatepass_by_number(db, pass_number)

    if doc["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending passes can be approved")

    doc["status"] = "approved"
    doc["approved_at"] = datetime.utcnow()

    _append_status_history(doc, "approved", admin_user_id)
    return _update_doc(db, doc)


def reject_gatepass(db, pass_number: str, admin_user_id: str):
    doc = get_gatepass_by_number(db, pass_number)

    if doc["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending passes can be rejected")

    doc["status"] = "rejected"
    _append_status_history(doc, "rejected", admin_user_id)

    return _update_doc(db, doc)


def update_on_exit(db, pass_number: str, photo_id: Optional[str], gate_user_id: str):
    doc = get_gatepass_by_number(db, pass_number)

    if doc["status"] != "approved":
        raise HTTPException(status_code=400, detail="Only approved passes can be used for exit")

    now = datetime.utcnow()
    doc["exit_time"] = now
    if photo_id:
        doc["exit_photo_id"] = photo_id

    new_status = "pending_return" if doc["is_returnable"] else "completed"
    doc["status"] = new_status

    _append_status_history(doc, new_status, gate_user_id)

    return _update_doc(db, doc)


def update_on_return(db, pass_number: str, photo_id: Optional[str], gate_user_id: str):
    doc = get_gatepass_by_number(db, pass_number)

    if doc["status"] != "pending_return":
        raise HTTPException(status_code=400, detail="Return only allowed for pending_return")

    now = datetime.utcnow()
    doc["return_time"] = now
    if photo_id:
        doc["return_photo_id"] = photo_id

    doc["status"] = "returned"
    _append_status_history(doc, "returned", gate_user_id)

    return _update_doc(db, doc)
