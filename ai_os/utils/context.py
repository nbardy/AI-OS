from typing import List, Literal, Dict
from pathlib import Path
import os
import subprocess

from ai_os.core.models import Context, Message, KnownFileData


request_format = """
<CONTEXT START>
Below if context  information to assist with the requests.
All files are the current version
Chat history refers to the conversation between the user and the assistant.

[FILE CONTEXT]
{file_context}
[FILE CONTEXT END]

[CHAT HISTORY]
{chat_history}
[CHAT HISTORY END]
<CONTEXT END>
"""

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
                except Exception as e:
                    print(f"[Warning] Could not read file {f} during git repo load: {e}")
            return files_to_add
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def get_llm_payload(self, user_prompt: str, include_history_count: int = 10) -> List[Message]:
        # Gather file context
        file_context_content = ""
        included_files_count = 0
        for path, data in self._context.known_files.items():
            if data.include_in_prompt:
                file_context_content += f"## File: {str(path)}\n```\n{data.content}\n```\n\n"
                included_files_count += 1
        
        if not included_files_count:
            file_context_content = "No files included in context."

        # Gather chat history
        chat_history_content = ""
        # Ensure we only take the specified number of messages from the end
        actual_history_count = int(include_history_count)
        start_index = max(0, len(self._context.messages) - actual_history_count)
        relevant_history = self._context.messages[start_index:]

        if relevant_history:
            for msg in relevant_history:
                # Simple representation for the context string
                chat_history_content += f"{msg.role}: {msg.content}\n" 
        else:
            chat_history_content = "No chat history provided."

        # Format the system message using the template
        system_content = request_format.format(
            file_context=file_context_content.strip(), 
            chat_history=chat_history_content.strip()
        )

        # Construct the final payload
        payload_messages = [
            Message(role="system", content=system_content),
            Message(role="user", content=user_prompt)
        ]

        return payload_messages

context_manager = ContextManager() 