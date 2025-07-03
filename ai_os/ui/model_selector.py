import asyncio
import aiohttp
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from rich.text import Text

from textual.app import App
from textual.widgets import Input, ListView, ListItem, Label, Static, Header, Footer
from textual.containers import Container
from textual.reactive import reactive
from textual.events import Key

from ai_os.utils.config import config_manager


@dataclass
class ModelData:
    """Simple model data with basic fields"""
    id: str
    name: str
    description: str = ""
    context_length: int = 0
    
    @classmethod
    def from_dict(cls, model_dict: Dict[str, Any]) -> 'ModelData':
        """Create ModelData from API response"""
        model_id = str(model_dict.get("id", "")).strip()
        if not model_id:
            raise ValueError("Model ID is required")
        
        name = str(model_dict.get("name", "")).strip()
        if not name:
            name = model_id  # Fallback to ID if name is missing
        
        description = str(model_dict.get("description", "")).strip()
        
        try:
            context_length = int(model_dict.get("context_length", 0))
        except (ValueError, TypeError):
            context_length = 0
        
        return cls(
            id=model_id,
            name=name,
            description=description,
            context_length=max(0, context_length)
        )
    
    def get_display_text(self) -> Text:
        """Get rich text for display in the list"""
        text = Text()
        text.append(self.name, style="bold")
        if self.context_length > 0:
            text.append(f" ({self.context_length:,} tokens)", style="dim")
        return text
    
    def get_detail_text(self) -> Text:
        """Get detailed info text"""
        text = Text()
        text.append(f"ID: {self.id}\n", style="dim")
        if self.description:
            text.append(f"Description: {self.description}\n")
        return text
    
    def matches_search(self, search_term: str) -> bool:
        """Check if model matches search term"""
        if not search_term:
            return True
        
        search_lower = search_term.lower()
        return (
            search_lower in self.name.lower() or
            search_lower in self.id.lower() or
            search_lower in self.description.lower()
        )


class ModelSelector(App[Optional[str]]):
    """Simple model selector app"""
    
    CSS = """
    Screen {
        layout: vertical;
        background: #1e1e1e;
        color: white;
    }
    
    #search-container {
        height: 3;
        border: thick #444444;
        background: #2a2a2a;
        padding: 0;
    }
    
    Input {
        height: 3;
        width: 100%;
        color: white !important;
        background: #2a2a2a !important;
        border: none;
        padding: 0 1;
    }
    
    Input:focus {
        color: white !important;
        background: #333333 !important;
        border: thick #0078d4;
    }
    
    #current-model {
        height: 3;
        border: thick #00aa00;
        background: #004400;
        padding: 0;
    }
    
    #current-model-display {
        height: 100%;
        width: 100%;
        color: #00ff00 !important;
        background: #004400 !important;
        text-style: bold;
        padding: 1;
        content-align: left middle;
    }
    
    #model-list-container {
        height: 60%;
        border: thick #444444;
        background: #1e1e1e;
    }
    
    #model-detail-container {
        height: 30%;
        border: thick #444444;
        background: #1e1e1e;
    }
    
    #loading {
        height: 100%;
        content-align: center middle;
        color: white;
    }
    
    #error {
        height: 100%;
        content-align: center middle;
        color: #ff4444;
    }
    """
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "select_model", "Select Model"),
        ("ctrl+c", "cancel", "Cancel"),
        ("f5", "refresh", "Refresh"),
    ]
    
    # Simple reactive properties
    models: reactive[List[ModelData]] = reactive([])
    filtered_models: reactive[List[ModelData]] = reactive([])
    current_model: reactive[Optional[str]] = reactive(None)
    search_term: reactive[str] = reactive("")
    is_loading: reactive[bool] = reactive(True)
    error_message: reactive[Optional[str]] = reactive(None)
    
    def __init__(self):
        super().__init__()
    
    def compose(self):
        """Compose the UI"""
        yield Header()
        
        # Current model display
        with Container(id="current-model"):
            self.current_model_label = Static(id="current-model-display")
            yield self.current_model_label
        
        # Search input
        with Container(id="search-container"):
            self.search_input = Input(placeholder="Type to search models...", value="")
            yield self.search_input
        
        # Model list
        with Container(id="model-list-container"):
            self.model_list = ListView(id="model-list")
            self.loading_display = Static("Loading models from OpenRouter...", id="loading")
            self.error_display = Static("", id="error")
            yield self.loading_display
            yield self.error_display
            yield self.model_list
        
        # Model detail
        with Container(id="model-detail-container"):
            self.model_detail = Static(id="model-detail")
            yield self.model_detail
        
        yield Footer()
    
    async def on_mount(self):
        """Initialize when mounted"""
        self.current_model = config_manager.get_current_model()
        self.search_input.focus()
        self._update_ui_state()
        await self._load_models()
    
    async def _load_models(self) -> None:
        """Load models from OpenRouter API"""
        try:
            self.is_loading = True
            self.error_message = None
            
            # Simple aiohttp call
            async with aiohttp.ClientSession() as session:
                async with session.get("https://openrouter.ai/api/v1/models") as response:
                    if response.status != 200:
                        raise Exception(f"API returned status {response.status}")
                    
                    data = await response.json()
                    models_data = data.get("data", [])
                    
                    models = []
                    for model_dict in models_data:
                        try:
                            model = ModelData.from_dict(model_dict)
                            models.append(model)
                        except ValueError:
                            continue  # Skip invalid models
                    
                    self.models = models
                    self.filtered_models = self._filter_models(models, self.search_term)
                    self.is_loading = False
                    
        except Exception as e:
            self.error_message = f"Failed to load models: {str(e)}"
            self.is_loading = False
    
    def _filter_models(self, models: List[ModelData], search_term: str) -> List[ModelData]:
        """Filter models by search term"""
        if not search_term:
            return models
        return [model for model in models if model.matches_search(search_term)]
    
    def _update_ui_state(self) -> None:
        """Update UI visibility based on current state"""
        if self.is_loading:
            self.loading_display.display = True
            self.error_display.display = False
            self.model_list.display = False
        elif self.error_message:
            self.loading_display.display = False
            self.error_display.display = True
            self.error_display.update(Text(self.error_message, style="red"))
            self.model_list.display = False
        else:
            self.loading_display.display = False
            self.error_display.display = False
            self.model_list.display = True
    
    def _update_current_model_display(self) -> None:
        """Update the current model display"""
        if self.current_model:
            # Use plain string instead of Rich Text to avoid styling conflicts
            display_text = f"Current Model: {self.current_model}"
            self.current_model_label.update(display_text)
        else:
            self.current_model_label.update("No model selected")
    
    def _sanitize_id(self, raw_id: str) -> str:
        """Sanitize ID for DOM usage - replace invalid chars with underscores"""
        if not raw_id:
            return "unknown"
        
        # Replace invalid characters (anything that's not alphanumeric, hyphen, or underscore) with underscores
        # This includes slashes, spaces, special characters, etc.
        sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '_', raw_id)
        
        # Replace consecutive separators with single underscore
        sanitized = re.sub(r'[-_]{2,}', '_', sanitized)
        
        # Ensure ID starts with letter or underscore (DOM requirement)
        if sanitized and not (sanitized[0].isalpha() or sanitized[0] == '_'):
            sanitized = f"model_{sanitized}"
        
        # Trim separators from ends
        sanitized = sanitized.strip('-_')
        
        # Ensure minimum length
        if not sanitized:
            return "unknown"
        
        return sanitized
    
    async def _update_model_list(self) -> None:
        """Update the model list display with proper clearing and DOM ID sanitization"""
        # CRITICAL: Clear the list first to prevent DuplicateIds
        await self.model_list.clear()
        
        for model in self.filtered_models:
            item = ListItem(Label(model.get_display_text()))
            # Use sanitized ID for DOM
            item.id = self._sanitize_id(model.id)
            # Store original model ID separately
            item.model_id = model.id
            await self.model_list.append(item)
    
    # Simple reactive updates
    def watch_models(self, models: List[ModelData]) -> None:
        self._update_current_model_display()
        self.filtered_models = self._filter_models(models, self.search_term)
    
    def watch_filtered_models(self, filtered_models: List[ModelData]) -> None:
        self.call_later(self._update_model_list)
    
    def watch_current_model(self, current_model: Optional[str]) -> None:
        self._update_current_model_display()
    
    def watch_search_term(self, search_term: str) -> None:
        self.filtered_models = self._filter_models(self.models, search_term)
    
    def watch_is_loading(self, is_loading: bool) -> None:
        self._update_ui_state()
    
    def watch_error_message(self, error_message: Optional[str]) -> None:
        self._update_ui_state()
    
    # Event handlers
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes"""
        self.search_term = event.value
    
    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle model selection in list"""
        if event.item and hasattr(event.item, 'model_id'):
            model_id = event.item.model_id
            model = next((m for m in self.models if m.id == model_id), None)
            if model:
                self.model_detail.update(model.get_detail_text())
    
    def on_key(self, event: Key) -> None:
        """Handle key events with proper focus management"""
        # Prevent typing from exiting the app
        if event.key == "escape":
            self.action_cancel()
            event.prevent_default()
        elif event.key == "enter":
            # Only select model if model list has focus, otherwise let input handle enter
            if self.model_list.has_focus:
                self.action_select_model()
                event.prevent_default()
            # If search input has focus, move focus to model list
            elif self.search_input.has_focus and self.filtered_models:
                self.model_list.focus()
                event.prevent_default()
        elif event.key == "f5":
            self.action_refresh()
            event.prevent_default()
        elif event.key in ("up", "down", "j", "k"):
            # Navigation keys should focus the list if not already focused
            if not self.model_list.has_focus and not self.search_input.has_focus:
                self.model_list.focus()
        # All other keys: let them bubble up normally for input handling
        # This prevents random key presses from exiting the app
    
    # Actions
    def action_select_model(self) -> None:
        """Select the highlighted model"""
        if not self.model_list.highlighted_child:
            return
        
        if not hasattr(self.model_list.highlighted_child, 'model_id'):
            return
        
        model_id = self.model_list.highlighted_child.model_id
        if not model_id:
            return
        
        try:
            config_manager.set_current_model(model_id)
            self.exit(model_id)
        except Exception as e:
            self.error_message = f"Failed to select model: {str(e)}"
    
    def action_cancel(self) -> None:
        """Cancel model selection"""
        self.exit(None)
    
    def action_refresh(self) -> None:
        """Refresh the model list"""
        # Use safe task creation
        try:
            # Reset state
            self.is_loading = True
            self.error_message = None
            self._update_ui_state()
            # Start loading
            asyncio.create_task(self._load_models())
        except Exception as e:
            self.error_message = f"Failed to start refresh: {str(e)}"


# Simple convenience functions
def run_model_selector() -> Optional[str]:
    """Run the model selector and return selected model ID"""
    try:
        app = ModelSelector()
        return asyncio.run(app.run_async())
    except KeyboardInterrupt:
        return None
    except Exception:
        return None