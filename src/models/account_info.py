from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import time


@dataclass
class AccountInfo:
    email: str
    password: str

    account_id: str = field(
        default_factory=lambda: time.strftime("acct_%Y%m%d_%H%M%S")
    )

    pet_name: Optional[str] = None
    treasures: List[str] = field(default_factory=list)

    screenshot_path: Optional[str] = None
    pet_image_path: Optional[str] = None

    instance: Optional[str] = None
    found_time: datetime = field(default_factory=datetime.now)