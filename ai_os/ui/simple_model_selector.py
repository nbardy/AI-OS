import asyncio
import aiohttp
from typing import List, Optional
from dataclasses import dataclass

from textual.app import App
from textual.widgets import ListView, ListItem, Label, Static, Footer
from textual.containers import Container
from textual.reactive import reactive
from textual.events import Key

from ai_os.utils.config import config_manager


@dataclass
class Model:
    id: str
    name: str
    context_length: int = 0
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Model':
        return cls(
            id=data.get("id", ""),
            name=data.get("name", data.get("id", "")),
            context_length=int(data.get("context_length", 0))
        )
    
    def display_name(self) -> str:
        if self.context_length > 0:
            return f"{self.name} ({self.context_length:,} tokens)"
        return self.name
    
    def matches(self, search: str) -> bool:
        if not search:
            return True
        search = search.lower()
        return search in self.name.lower() or search in self.id.lower()


class SimpleModelSelector(App[Optional[str]]):
    CSS = """
    Screen {
        background: #2b2b2b;
        color: #ffffff;
    }
    
    #header {
        height: 3;
        background: #404040;
        color: #ffffff;
        text-align: center;
        padding: 1;
        border-bottom: solid #666666;
    }
    
    #current-model {
        height: 3;
        background: #1a4d1a;
        color: #ffffff !important;
        padding: 1;
        text-align: left;
        border-bottom: solid #333333;
    }
    
    #search-display {
        height: 3;
        background: #333333;
        color: #ffffff !important;
        padding: 1;
        border: solid #0078d4;
        text-align: left;
    }
    
    Static {
        color: #ffffff !important;
    }
    
    #models {
        background: #2b2b2b;
        color: #ffffff;
        border: solid #555555;
    }
    
    ListView {
        background: #2b2b2b;
        color: #ffffff;
    }
    
    ListItem {
        background: #2b2b2b;
        color: #ffffff;
        padding: 0 1;
    }
    
    ListItem:hover {
        background: #404040;
    }
    
    ListItem.-highlighted {
        background: #0078d4;
        color: #ffffff;
    }
    
    #loading {
        text-align: center;
        padding: 10;
        color: #888888;
    }
    
    #error {
        text-align: center;
        padding: 10;
        color: #ff6666;
    }
    """
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "select", "Select"),
        ("f5", "refresh", "Refresh"),
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
    ]
    
    models: reactive[List[Model]] = reactive([])
    filtered_models: reactive[List[Model]] = reactive([])
    current_model: reactive[str] = reactive("")
    search_term: reactive[str] = reactive("")
    loading: reactive[bool] = reactive(True)
    error: reactive[str] = reactive("")
    
    def compose(self):
        yield Static("Model Selector", id="header")
        yield Static("", id="current-model")
        yield Static("Search: ", id="search-display")
        with Container(id="models"):
            yield ListView(id="model-list")
            yield Static("Loading models...", id="loading")
            yield Static("", id="error")
        yield Footer()
    
    async def on_mount(self):
        self.current_model = config_manager.get_current_model() or "None"
        await self.load_models()
    
    async def load_models(self):
        try:
            self.loading = True
            self.error = ""
            
            async with aiohttp.ClientSession() as session:
                async with session.get("https://openrouter.ai/api/v1/models") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = []
                        for item in data.get("data", []):
                            try:
                                model = Model.from_dict(item)
                                if model.id and model.name:
                                    models.append(model)
                            except:
                                continue
                        self.models = models
                        self.loading = False
                    else:
                        self.error = f"Failed to load models (HTTP {response.status})"
                        self.loading = False
        except Exception as e:
            self.error = f"Error: {str(e)}"
            self.loading = False
    
    def watch_current_model(self, current_model: str):
        current_display = self.query_one("#current-model")
        text = f"Current Model: {current_model}"
        print(f"DEBUG: Setting current model text to: {text}")  # Debug
        current_display.update(text)
    
    def watch_models(self, models: List[Model]):
        self.filtered_models = [m for m in models if m.matches(self.search_term)]
    
    def watch_search_term(self, search_term: str):
        self.filtered_models = [m for m in self.models if m.matches(search_term)]
        # Update search display
        search_display = self.query_one("#search-display")
        text = f"Search: {search_term}"
        print(f"DEBUG: Setting search text to: {text}")  # Debug
        search_display.update(text)
    
    def watch_filtered_models(self, filtered_models: List[Model]):
        self.update_model_list()
        # Auto-select first item
        if filtered_models:
            self.call_later(self.select_first_item)
    
    def watch_loading(self, loading: bool):
        loading_widget = self.query_one("#loading")
        loading_widget.display = loading
        
        model_list = self.query_one("#model-list")
        model_list.display = not loading and not self.error
    
    def watch_error(self, error: str):
        error_widget = self.query_one("#error")
        error_widget.update(error)
        error_widget.display = bool(error)
        
        model_list = self.query_one("#model-list")
        model_list.display = not self.loading and not error
    
    def update_model_list(self):
        model_list = self.query_one("#model-list")
        model_list.clear()
        
        for model in self.filtered_models:
            item = ListItem(Label(model.display_name()))
            item.data_model_id = model.id
            model_list.append(item)
    
    def select_first_item(self):
        model_list = self.query_one("#model-list")
        if model_list.children:
            model_list.highlighted = 0
    
    def on_key(self, event: Key):
        # Handle typing for search
        if len(event.key) == 1 and event.key.isprintable():
            self.search_term += event.key
        elif event.key == "backspace":
            self.search_term = self.search_term[:-1]
        elif event.key == "ctrl+a" or event.key == "ctrl+u":
            self.search_term = ""
    
    def on_list_view_highlighted(self, event: ListView.Highlighted):
        # Could show model details here if needed
        pass
    
    def action_select(self):
        model_list = self.query_one("#model-list")
        if model_list.highlighted_child and hasattr(model_list.highlighted_child, 'data_model_id'):
            model_id = model_list.highlighted_child.data_model_id
            config_manager.set_current_model(model_id)
            self.exit(model_id)
    
    def action_cancel(self):
        self.exit(None)
    
    def action_refresh(self):
        asyncio.create_task(self.load_models())
    
    def action_cursor_up(self):
        model_list = self.query_one("#model-list")
        if model_list.children and model_list.highlighted is not None:
            new_index = max(0, model_list.highlighted - 1)
            model_list.highlighted = new_index
    
    def action_cursor_down(self):
        model_list = self.query_one("#model-list")
        if model_list.children and model_list.highlighted is not None:
            new_index = min(len(model_list.children) - 1, model_list.highlighted + 1)
            model_list.highlighted = new_index


def run_simple_model_selector() -> Optional[str]:
    """Run the simple model selector"""
    try:
        app = SimpleModelSelector()
        return app.run()
    except KeyboardInterrupt:
        return None
    except Exception:
        return None