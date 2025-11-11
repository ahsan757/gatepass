from typing import Literal

GatePassStatus = Literal[
    "pending",
    "approved",
    "rejected",
    "pending_return",
    "completed",
    "returned",
]

PhotoType = Literal["exit", "return"]
