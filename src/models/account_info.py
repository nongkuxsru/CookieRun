from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class AccountInfo:
    email: str
    password: str
    account_id: str

    pet_name: Optional[str] = None
    treasures: List[str] = field(default_factory=list)

    screenshot_path: Optional[str] = None
    pet_image_path: Optional[str] = None

    instance: Optional[str] = None
    found_time: datetime = field(default_factory=datetime.now)