from typing import Literal, List, Dict
from pydantic import BaseModel
from pathlib import Path

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    # files field removed - content injected

class KnownFileData(BaseModel):
    path: Path
    content: str
    include_in_prompt: bool = True

class Context(BaseModel):
    messages: List[Message] = []
    known_files: Dict[Path, KnownFileData] = {}
