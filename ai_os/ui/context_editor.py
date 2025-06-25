from typing import Dict, List
from pathlib import Path
from rich.text import Text

# Import Textual components
from textual.app import App, ComposeResult
# Import TreeNode from textual.widgets.tree for clarity and compatibility
# In newer Textual versions, TreeNode might be directly in textual.widgets.tree
from textual.widgets import Header, Footer, Tree, Static
from textual.widgets.tree import TreeNode # Explicitly import TreeNode

from textual.containers import Container

# Import the global context_manager instance
from ai_os.utils.context import context_manager
# Import commands which now operate on the context_manager
from ai_os.core import commands
# Import necessary types from models
from ai_os.core.models import KnownFileData

# --- Textual Context Editor App ---

class ContextFileTreeNodeData:
    """Data attached to a Textual Tree node for context files."""
    def __init__(self, path: Path, is_dir: bool, include_status: bool = False):
        self.path = path
        self.is_dir = is_dir
        self.include_status = include_status

# Helper function to structure flat file list into a tree hierarchy
def build_file_tree_data(files: Dict[Path, KnownFileData]):
    """Builds a nested dictionary representation of the file tree."""
    tree_data = {}
    for path, data in files.items():
        # The path loaded from git ls-files is already relative to the repo root
        # We don't need a separate method to get the relative path; the path object itself is it.
        # relative_path = context_manager.get_relative_path(path) # REMOVE THIS LINE
        relative_path = path # Use the path directly
        # if relative_path is None: # This check is no longer needed if path is always valid
        #     continue
        parts = relative_path.parts
        current_level = tree_data
        for i, part in enumerate(parts):
            is_dir = (i < len(parts) - 1)
            # Use (part, is_dir) as the key to distinguish files/dirs with same name
            key = (part, is_dir)
            if key not in current_level:
                # Store the full original path (which is relative to repo root) in the data for dirs/files
                # For directories, we just need the relative path constructed from parts
                current_full_path_relative = Path(*parts[:i+1])
                current_level[key] = {} if is_dir else data # Store the KnownFileData for files, dict for dirs
            current_level = current_level[key]
    return tree_data


# Helper function to populate a Textual Tree widget from tree data
def populate_textual_tree(parent_node: TreeNode[ContextFileTreeNodeData], tree_data: dict, current_path_parts: list = []):
    """Recursively populates a Textual Tree widget starting from a parent node."""
    # Sort keys: directories first, then files, both alphabetically
    sorted_keys = sorted(tree_data.keys(), key=lambda x: (not x[1], x[0]))

    for key in sorted_keys:
        part, is_dir = key
        node_data_or_dict = tree_data[key]
        new_path_parts = current_path_parts + [part]
        # Construct the relative path for display/node data
        full_path_relative = Path(*new_path_parts)

        if is_dir:
            # Calculate folder status (ON/OFF/MIXED)
            folder_status = get_folder_status(full_path_relative)
            status_style = "green" if folder_status == "ON" else ("red" if folder_status == "OFF" else "yellow")
            
            dir_label = Text(part)
            if folder_status != "NONE":
                dir_label.append(f" ({folder_status})", style=f"dim {status_style}")
            
            # Always add to the parent_node passed to the function
            dir_node = parent_node.add( # Use parent_node.add
                dir_label,
                allow_expand=True,
                # Store the relative path for the directory node data
                data=ContextFileTreeNodeData(path=full_path_relative, is_dir=True)
            )
            if node_data_or_dict: # Only recurse if directory has content
                # Pass the new dir_node as the parent for the recursive call
                populate_textual_tree(dir_node, node_data_or_dict, new_path_parts)
        else:
            file_data: KnownFileData = node_data_or_dict # node_data_or_dict is the KnownFileData for files
            status_text = "ON" if file_data.include_in_prompt else "OFF"
            status_style = "green" if file_data.include_in_prompt else "red"
            node_label = Text(str(Path(part).name)) # Use only the final part (filename) for display
            node_label.append(f" ({status_text})", style=f"dim {status_style}")

            # Store the *original* Path from KnownFileData for the file node data
            # This is the actual path relative to the repo root needed for toggling
            # Always add to the parent_node passed to the function
            parent_node.add_leaf( # Use parent_node.add_leaf
                node_label,
                data=ContextFileTreeNodeData(path=file_data.path, is_dir=False, include_status=file_data.include_in_prompt)
            )


def get_folder_status(folder_path: Path) -> str:
    """Get the status of a folder: ON (all files on), OFF (all files off), MIXED (some on/some off), NONE (no files)"""
    files = context_manager.get_known_files()
    folder_str = str(folder_path)
    
    # Find all files that are in this folder (including subdirectories)
    folder_files = []
    for path, data in files.items():
        path_str = str(path)
        # Check if this file is within the folder
        if path_str.startswith(folder_str + "/") or path == folder_path:
            folder_files.append(data)
    
    if not folder_files:
        return "NONE"
    
    on_count = sum(1 for data in folder_files if data.include_in_prompt)
    
    if on_count == 0:
        return "OFF"
    elif on_count == len(folder_files):
        return "ON"
    else:
        return "MIXED"


def get_files_in_folder(folder_path: Path) -> List[Path]:
    """Get all file paths that are within the given folder path (including subdirectories)"""
    files = context_manager.get_known_files()
    folder_str = str(folder_path)
    
    result = []
    for path in files.keys():
        path_str = str(path)
        # Check if this file is within the folder
        if path_str.startswith(folder_str + "/"):
            result.append(path)
    
    return result


class ContextEditorApp(App[None]):
    """Textual App for editing the context file tree."""
    CSS = """
    Screen {
        layout: vertical;
    }
    #help-container {
        height: 3;
        border: thick $panel;
        background: $surface;
    }
    #file-tree-container {
        border: thick $panel;
        height: 55%;
    }
    #message-history-container {
        border: thick $panel;
        height: 40%;
    }
    #message-history {
        overflow-y: auto; /* Apply scroll only to the Static widget */
        height: 100%; /* Make Static fill its container */
        width: 100%;
    }
    """

    BINDINGS = [
        ("space", "toggle_include", "Toggle Include"),
        ("q", "quit_editor", "Quit"),
        ("escape", "quit_editor", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the Textual UI."""
        yield Header()
        
        # Add help text container
        with Container(id="help-container"):
            help_text = Static("Press [bold cyan]SPACE[/bold cyan] to toggle files/folders ON/OFF. Folders show [green]ON[/green]/[red]OFF[/red]/[yellow]MIXED[/yellow] status. Toggle folder to change all contents.")
            yield help_text
        
        with Container(id="file-tree-container"):
            # The Tree widget itself is the root
            self.file_tree_widget: Tree[ContextFileTreeNodeData] = Tree("Git Tracked Files")
            self.file_tree_widget.show_root = False # Hide the root label itself
            self.file_tree_widget.id = "file-tree"
            yield self.file_tree_widget

        with Container(id="message-history-container"):
            self.history_label = Static(id="message-history")
            yield self.history_label

        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.update_file_tree()
        self.update_message_history()
        self.file_tree_widget.focus() # Set focus to the tree

    def update_file_tree(self):
        """Update the file tree display."""
        files = context_manager.get_known_files()
        tree_data = build_file_tree_data(files)

        self.file_tree_widget.clear()
        # Pass the widget's root node as the initial parent
        populate_textual_tree(self.file_tree_widget.root, tree_data)
        # Expand the first level of directories automatically
        if self.file_tree_widget.root.children:
            # Expand immediate children if they are directories
            for node in self.file_tree_widget.root.children:
                 if node.data and node.data.is_dir:
                     node.expand() # Expand the node itself, not all children of root
            # Also expand the root node itself so its children become visible
            self.file_tree_widget.root.expand()


    def update_message_history(self):
        """Update the message history display."""
        messages = context_manager.get_messages()
        history_text = Text()
        # Show last 10 non-context messages
        chat_history_only = [
            msg for msg in messages
            if msg.role != "system" or not msg.content.strip().startswith("[CONTEXT START]")
        ][-10:] # Get last 10 user/assistant messages (and system messages not starting with CONTEXT)


        if not chat_history_only:
            history_text.append("History is empty.", style="dim")
        else:
            for msg in chat_history_only:
                # Skip the large context message content
                if msg.role == "system" and msg.content.strip().startswith("[CONTEXT START]"):
                     history_text.append("[SYSTEM] Context loaded.\n", style="bold dim")
                     continue

                role_color = "blue" if msg.role == "assistant" else ("green" if msg.role == "user" else "yellow")
                history_text.append(f"[{msg.role.upper()}] ", style=f"bold {role_color}")
                # Only show the first line and truncate if long
                content_preview = msg.content.split('\n')[0]
                history_text.append(content_preview[:100] + ('...' if len(content_preview) > 100 else '') + '\n') # Increased preview length

        self.history_label.update(history_text)

    def action_toggle_include(self):
        """Toggle inclusion status of the selected file or folder."""
        selected_node: TreeNode[ContextFileTreeNodeData] | None = self.file_tree_widget.cursor_node
        
        if not selected_node or not selected_node.data or not isinstance(selected_node.data, ContextFileTreeNodeData):
            return
            
        target_path = selected_node.data.path
        
        if selected_node.data.is_dir:
            # Handle folder toggling
            folder_files = get_files_in_folder(target_path)
            if not folder_files:
                return  # No files in folder
                
            folder_status = get_folder_status(target_path)
            
            # Determine new state: if MIXED or ON, turn everything OFF; if OFF, turn everything ON  
            if folder_status == "OFF":
                new_state = True  # Turn everything ON
            else:  # folder_status is "ON" or "MIXED"
                new_state = False  # Turn everything OFF
            
            # Toggle all files in the folder
            for file_path in folder_files:
                current_state = context_manager.get_known_files()[file_path].include_in_prompt
                if current_state != new_state:
                    context_manager.toggle_path(file_path)
        else:
            # Handle individual file toggling
            commands.toggle_context_file(str(target_path))

        # Remember cursor position and expansion state
        cursor_path_relative = selected_node.data.path
        expanded_paths = {node.data.path for node in self.file_tree_widget.walk_expanded() if node.data and node.data.is_dir}

        # Refresh the tree display to show the change
        self.update_file_tree()

        # Try to restore expansion state and cursor position
        self.file_tree_widget.root.collapse_all() # Start collapsed

        # Restore expansion state
        for node in self.file_tree_widget.walk_nodes():
             if node.data and node.data.is_dir and node.data.path in expanded_paths:
                  node.expand()

        # Find and select the node again by path
        for node in self.file_tree_widget.walk_nodes():
            if node.data and node.data.path == cursor_path_relative:
                 self.file_tree_widget.cursor = node.id
                 self.file_tree_widget.scroll_to_node(node) # Ensure cursor is visible
                 node.select() # Ensure the node is selected
                 break # Found and restored cursor

    def action_quit_editor(self):
        """Quit the context editor."""
        self.exit()

# If you wanted to run the editor standalone for testing:
# Needs context_manager initialized appropriately if run standalone
# if __name__ == "__main__":
#     from ai_os.utils.context import initialize_context_dev # Example init
#     initialize_context_dev()
#     ContextEditorApp().run() 