"""Result type for ops layer."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Result:
    success: bool = True
    data: Any = None
    message: str = ""


EmptyResult = Result()
