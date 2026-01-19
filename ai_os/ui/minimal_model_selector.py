import asyncio
import aiohttp
from typing import List, Optional
from dataclasses import dataclass

from textual.app import App
from textual.widgets import ListView, ListItem, Label, Static, Footer
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


class MinimalModelSelector(App[Optional[str]]):
    # NO CSS AT ALL - use textual defaults
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "select", "Select"),
        ("space", "select", "Select"),
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
        yield Static("=== MODEL SELECTOR ===")
        yield Static("[yellow]⚠️ AI-OS v2 uses Claude Code harness for execution[/yellow]", id="warning")
        yield Static("Current: NONE", id="current-display")
        yield Static("Search: ", id="search-display")
        yield ListView(id="model-list")
        yield Static("Loading models from OpenRouter...", id="status")
        yield Footer()
    
    async def on_mount(self):
        self.current_model = config_manager.get_current_model() or "NONE"
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
        current_display = self.query_one("#current-display")
        text = f"CURRENT MODEL: {current_model}"
        print(f"SETTING CURRENT: {text}")
        current_display.update(text)
    
    def watch_models(self, models: List[Model]):
        self.filtered_models = [m for m in models if m.matches(self.search_term)]
    
    def watch_search_term(self, search_term: str):
        self.filtered_models = [m for m in self.models if m.matches(search_term)]
        search_display = self.query_one("#search-display")
        text = f"SEARCH: [{search_term}]"
        print(f"SETTING SEARCH: {text}")
        search_display.update(text)
    
    def watch_filtered_models(self, filtered_models: List[Model]):
        self.call_later(self.update_model_list)
        if filtered_models:
            self.call_later(self.select_first_item)
    
    def watch_loading(self, loading: bool):
        status = self.query_one("#status")
        if loading:
            status.update("LOADING MODELS...")
        elif self.error:
            status.update(f"ERROR: {self.error}")
        else:
            status.update(f"LOADED {len(self.models)} MODELS")
    
    def watch_error(self, error: str):
        if error:
            status = self.query_one("#status")
            status.update(f"ERROR: {error}")
    
    async def update_model_list(self):
        model_list = self.query_one("#model-list")
        await model_list.clear()
        
        for i, model in enumerate(self.filtered_models):
            item = ListItem(Label(model.display_name()))
            item.data_model_id = model.id
            print(f"DEBUG LIST: Created item {i}: {model.display_name()} -> {model.id}")
            await model_list.append(item)
        print(f"DEBUG LIST: Added {len(self.filtered_models)} items to list")
    
    def select_first_item(self):
        model_list = self.query_one("#model-list")
        if model_list.children:
            model_list.highlighted = 0
            print(f"DEBUG SELECT_FIRST: highlighted index set to 0, child = {model_list.highlighted_child}")
    
    def on_key(self, event: Key):
        # Don't handle keys that are bound to actions
        if event.key in ["enter", "space", "escape", "up", "down", "f5"]:
            return
            
        if len(event.key) == 1 and event.key.isprintable():
            self.search_term += event.key
        elif event.key == "backspace":
            self.search_term = self.search_term[:-1]
        elif event.key == "ctrl+a" or event.key == "ctrl+u":
            self.search_term = ""
    
    def action_select(self):
        model_list = self.query_one("#model-list")
        print(f"DEBUG SELECT: highlighted_child = {model_list.highlighted_child}")
        if model_list.highlighted_child:
            print(f"DEBUG SELECT: has data_model_id = {hasattr(model_list.highlighted_child, 'data_model_id')}")
            if hasattr(model_list.highlighted_child, 'data_model_id'):
                model_id = model_list.highlighted_child.data_model_id
                print(f"DEBUG SELECT: model_id = {model_id}")
                config_manager.set_current_model(model_id)
                print(f"DEBUG SELECT: saved to config, exiting with {model_id}")
                self.exit(model_id)
            else:
                print("DEBUG SELECT: no data_model_id attribute")
        else:
            print("DEBUG SELECT: no highlighted_child")
    
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


def run_minimal_model_selector() -> Optional[str]:
    """Run the minimal model selector"""
    try:
        app = MinimalModelSelector()
        return app.run()
    except KeyboardInterrupt:
        return None
    except Exception:
        return None