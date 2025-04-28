from typing import List, Literal, Dict
from pathlib import Path
import os
import subprocess

from ai_os.core.models import Context, Message, KnownFileData

class ContextManager:
    def __init__(self):
        self._context = Context()

    def add_message(self, role: Literal["user", "assistant", "system"], content: str):
        self._context.messages.append(Message(role=role, content=content))

    def add_known_file(self, path: Path, content: str):
        self._context.known_files[path] = KnownFileData(path=path, content=content)

    def toggle_path(self, path: Path, include: bool = None):
        if path in self._context.known_files:
            data = self._context.known_files[path]
            data.include_in_prompt = include if include is not None else not data.include_in_prompt

    def get_known_files(self) -> Dict[Path, KnownFileData]:
        return self._context.known_files

    def get_messages(self) -> List[Message]:
        return self._context.messages

    def load_git_repo(self):
        try:
            result = subprocess.run(
                ['git', 'ls-files'],
                capture_output=True,
                text=True,
                check=True,
                cwd=os.getcwd()
            )
            files_to_add = [Path(p.strip()) for p in result.stdout.splitlines() if p.strip()]
            for f in files_to_add:
                try:
                    content = f.read_text()
                    self.add_known_file(path=f, content=content)
                except Exception:
                    pass
            return files_to_add
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def get_llm_payload(self, user_prompt: str, include_history_count: int = 10) -> List[Message]:
        payload_messages: List[Message] = []

        file_context_content = ""
        for path, data in self._context.known_files.items():
            if data.include_in_prompt:
                file_context_content += f"## File: {str(path)}\n```\n{data.content}\n```\n\n"

        if file_context_content:
            payload_messages.append(Message(role="system", content="[CONTEXT START]\n" + file_context_content.strip() + "\n[CONTEXT END]"))

        chat_history_only = [
            msg for msg in self._context.messages
            if not msg.content.strip().startswith("[CONTEXT START]")
        ]

        if chat_history_only:
            history_before_current_prompt = chat_history_only[:-1]
            payload_messages.extend(history_before_current_prompt[-include_history_count:])

        if self._context.messages:
            last_msg = self._context.messages[-1]
            if last_msg.role == "user" and last_msg.content == user_prompt:
                payload_messages.append(last_msg)
            else:
                payload_messages.append(Message(role="user", content=user_prompt))

        if payload_messages and payload_messages[0].role == "assistant":
            payload_messages.insert(0, Message(role="system", content="Continuing conversation."))

        return payload_messages

context_manager = ContextManager() 