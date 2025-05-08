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

class Patch(BaseModel):
    """Represents a set of file changes and summaries."""
    file_changes: Dict[str, str] # file_path -> new_full_content
    summaries: Dict[str, str] # file_path -> summary_of_change
