from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class StatusHistoryItem(BaseModel):
    status: str
    changed_at: datetime
    changed_by: str


class GatePassCreate(BaseModel):
    person_name: str
    description: str
    is_returnable: bool = False


class GatePassOut(BaseModel):
    id: str
    number: str
    person_name: str
    description: str
    created_by: str
    is_returnable: bool
    status: str
    status_history: List[StatusHistoryItem] = []
    created_at: datetime
    approved_at: Optional[datetime] = None
    exit_photo_id: Optional[str] = None
    return_photo_id: Optional[str] = None
    exit_time: Optional[datetime] = None
    return_time: Optional[datetime] = None
    qr_code_url: Optional[str] = None

    class Config:
        from_attributes = True


class GatePassFilter(BaseModel):
    status: Optional[str] = None
    created_by: Optional[str] = None


class GatePassScanExit(BaseModel):
    pass_number: str


class GatePassScanReturn(BaseModel):
    pass_number: str


class PhotoInfo(BaseModel):
    photo_id: str
    gatepass_id: str
    file_url: str
    type: str  # "exit" or "return"
    captured_at: datetime
    captured_by: str
    pass_number: Optional[str] = None
