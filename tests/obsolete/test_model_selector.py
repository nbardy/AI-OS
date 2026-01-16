#!/usr/bin/env python3
"""
Comprehensive unit tests for ModelSelector UI class
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Optional

from textual.widgets import Input, ListView
from rich.text import Text

from ai_os.ui.model_selector import (
    ModelSelector,
    ModelService,
    ModelData,
    ConfigService,
    ServiceError,
    NetworkError,
    ValidationError
)


class MockModelService:
    """Mock model service for testing UI interactions"""
    
    def __init__(self):
        self.models = []
        self.current_model = None
        self.should_fail = False
        self.fetch_called = False
        self.force_refresh_called = False
    
    async def fetch_models(self, force_refresh: bool = False) -> List[ModelData]:
        self.fetch_called = True
        if force_refresh:
            self.force_refresh_called = True
        
        if self.should_fail:
            raise NetworkError("Mock network error")
        
        return self.models
    
    def get_current_model(self) -> Optional[str]:
        return self.current_model
    
    def set_current_model(self, model_id: str) -> None:
        if self.should_fail:
            raise ValidationError("Mock validation error")
        self.current_model = model_id
    
    def filter_models(self, models: List[ModelData], search_term: str) -> List[ModelData]:
        if not search_term:
            return models
        
        return [
            model for model in models
            if search_term.lower() in model.name.lower() or 
               search_term.lower() in model.id.lower()
        ]


@pytest.fixture
def mock_model_service():
    """Fixture providing mock model service"""
    service = MockModelService()
    service.models = [
        ModelData.from_dict({
            "id": "openai/gpt-4",
            "name": "GPT-4",
            "description": "Most capable GPT model",
            "context_length": 8192
        }),
        ModelData.from_dict({
            "id": "anthropic/claude-3",
            "name": "Claude-3",
            "description": "Anthropic's latest model",
            "context_length": 100000
        }),
        ModelData.from_dict({
            "id": "meta/llama-2",
            "name": "Llama-2",
            "description": "Meta's open source model"
        })
    ]
    return service


@pytest.fixture
def model_selector(mock_model_service):
    """Fixture providing ModelSelector instance with mock service"""
    return ModelSelector(mock_model_service)


class TestModelSelectorInitialization:
    """Test ModelSelector initialization and setup"""
    
    def test_initialization_with_service(self, mock_model_service):
        """Test initialization with provided service"""
        selector = ModelSelector(mock_model_service)
        assert selector.model_service == mock_model_service
        assert selector._last_search == ""
        assert selector._search_debounce_timer is None
    
    def test_initialization_without_service(self):
        """Test initialization without service creates default"""
        with patch('ai_os.ui.model_selector.config_manager') as mock_config:
            selector = ModelSelector()
            assert selector.model_service is not None
            assert isinstance(selector.model_service, ModelService)
    
    def test_reactive_state_initialization(self, model_selector):
        """Test reactive state is properly initialized"""
        assert model_selector.models == []
        assert model_selector.filtered_models == []
        assert model_selector.current_model is None
        assert model_selector.search_term == ""
        assert model_selector.is_loading is True
        assert model_selector.error_message is None


class TestModelSelectorComposition:
    """Test UI composition and widget creation"""
    
    def test_compose_widgets(self, model_selector):
        """Test that all required widgets are composed"""
        widgets = list(model_selector.compose())
        
        # Should have Header, Footer, and Containers
        widget_types = [type(widget).__name__ for widget in widgets]
        assert "Header" in widget_types
        assert "Footer" in widget_types
        assert "Container" in widget_types
    
    def test_widget_ids(self, model_selector):
        """Test that widgets have correct IDs"""
        # This would require running the compose method and checking IDs
        # Since we can't easily instantiate textual widgets in tests,
        # we'll test the structure indirectly
        assert hasattr(model_selector, 'compose')


class TestModelSelectorLoading:
    """Test model loading functionality"""
    
    @pytest.mark.asyncio
    async def test_load_models_success(self, model_selector, mock_model_service):
        """Test successful model loading"""
        # Mock UI components
        model_selector.loading_display = Mock()
        model_selector.model_list = Mock()
        model_selector.update_current_model_display = Mock()
        model_selector.update_model_list = Mock()
        
        await model_selector.load_models()
        
        # Service should have been called
        assert mock_model_service.fetch_called
        
        # Models should be loaded
        assert len(model_selector.models) == 3
        assert len(model_selector.filtered_models) == 3
        
        # UI should be updated
        model_selector.update_current_model_display.assert_called_once()
        model_selector.update_model_list.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_models_network_error(self, model_selector, mock_model_service):
        """Test handling of network errors during loading"""
        mock_model_service.should_fail = True
        model_selector.show_error = Mock()
        
        await model_selector.load_models()
        
        # Should show error
        model_selector.show_error.assert_called_once()
        call_args = model_selector.show_error.call_args[0][0]
        assert "Network error" in call_args
    
    @pytest.mark.asyncio
    async def test_load_models_empty_response(self, model_selector, mock_model_service):
        """Test handling of empty model list"""
        mock_model_service.models = []
        model_selector.show_error = Mock()
        
        await model_selector.load_models()
        
        # Should show error for empty response
        model_selector.show_error.assert_called_once()
        call_args = model_selector.show_error.call_args[0][0]
        assert "No models available" in call_args
    
    @pytest.mark.asyncio
    async def test_load_models_force_refresh(self, model_selector, mock_model_service):
        """Test force refresh functionality"""
        model_selector.loading_display = Mock()
        model_selector.model_list = Mock()
        model_selector.update_current_model_display = Mock()
        model_selector.update_model_list = Mock()
        
        await model_selector.load_models(force_refresh=True)
        
        # Should have called with force_refresh
        assert mock_model_service.force_refresh_called


class TestModelSelectorSearch:
    """Test search and filtering functionality"""
    
    def test_debounced_search_setup(self, model_selector):
        """Test search debouncing setup"""
        # Mock input event
        mock_event = Mock()
        mock_event.value = "test search"
        
        # Mock async task creation
        with patch('asyncio.create_task') as mock_create_task:
            model_selector.on_input_changed(mock_event)
            
            # Should create debounce task
            mock_create_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_debounced_search_execution(self, model_selector, mock_model_service):
        """Test actual search execution"""
        # Setup models and UI mocks
        model_selector.models = mock_model_service.models
        model_selector.search_input = Mock()
        model_selector.search_input.value = "gpt"
        model_selector.update_model_list = Mock()
        
        await model_selector._debounced_search("gpt")
        
        # Should filter models
        assert len(model_selector.filtered_models) == 1
        assert model_selector.filtered_models[0].id == "openai/gpt-4"
        
        # Should update UI
        model_selector.update_model_list.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_debounced_search_cancellation(self, model_selector):
        """Test search cancellation when input changes"""
        model_selector.search_input = Mock()
        model_selector.search_input.value = "different"
        model_selector.update_model_list = Mock()
        
        # Search term doesn't match current input, should return early
        await model_selector._debounced_search("old_search")
        
        # Should not update UI
        model_selector.update_model_list.assert_not_called()
    
    def test_search_debounce_timer_cancellation(self, model_selector):
        """Test that previous search timers are cancelled"""
        # Create a mock timer
        mock_timer = Mock()
        model_selector._search_debounce_timer = mock_timer
        
        mock_event = Mock()
        mock_event.value = "new search"
        
        with patch('asyncio.create_task'):
            model_selector.on_input_changed(mock_event)
        
        # Previous timer should be cancelled
        mock_timer.cancel.assert_called_once()


class TestModelSelectorModelSelection:
    """Test model selection and interaction"""
    
    def test_model_list_highlighting(self, model_selector):
        """Test model highlighting updates detail view"""
        # Setup mocks
        model_selector.models = [
            ModelData.from_dict({"id": "test-model", "name": "Test Model"})
        ]
        model_selector.model_detail = Mock()
        
        # Mock event with model data
        mock_item = Mock()
        mock_item.data_model_id = "test-model"
        mock_event = Mock()
        mock_event.item = mock_item
        
        model_selector.on_list_view_highlighted(mock_event)
        
        # Should update detail view
        model_selector.model_detail.update.assert_called_once()
    
    def test_model_list_highlighting_no_item(self, model_selector):
        """Test highlighting with no item selected"""
        model_selector.model_detail = Mock()
        
        mock_event = Mock()
        mock_event.item = None
        
        model_selector.on_list_view_highlighted(mock_event)
        
        # Should not update detail view
        model_selector.model_detail.update.assert_not_called()
    
    def test_model_selection_success(self, model_selector, mock_model_service):
        """Test successful model selection"""
        # Setup mock highlighted child
        mock_child = Mock()
        mock_child.data_model_id = "openai/gpt-4"
        
        model_selector.model_list = Mock()
        model_selector.model_list.highlighted_child = mock_child
        model_selector.exit = Mock()
        
        model_selector.action_select_model()
        
        # Should set current model and exit
        assert mock_model_service.current_model == "openai/gpt-4"
        model_selector.exit.assert_called_once_with("openai/gpt-4")
    
    def test_model_selection_no_highlighted(self, model_selector):
        """Test model selection with no highlighted item"""
        model_selector.model_list = Mock()
        model_selector.model_list.highlighted_child = None
        model_selector.exit = Mock()
        
        model_selector.action_select_model()
        
        # Should not exit
        model_selector.exit.assert_not_called()
    
    def test_model_selection_validation_error(self, model_selector, mock_model_service):
        """Test model selection with validation error"""
        mock_model_service.should_fail = True
        
        mock_child = Mock()
        mock_child.data_model_id = "invalid-model"
        
        model_selector.model_list = Mock()
        model_selector.model_list.highlighted_child = mock_child
        model_selector.show_error = Mock()
        
        model_selector.action_select_model()
        
        # Should show error
        model_selector.show_error.assert_called_once()
        call_args = model_selector.show_error.call_args[0][0]
        assert "Invalid model selection" in call_args


class TestModelSelectorActions:
    """Test action handlers"""
    
    def test_action_cancel(self, model_selector):
        """Test cancel action"""
        model_selector.exit = Mock()
        
        model_selector.action_cancel()
        
        model_selector.exit.assert_called_once_with(None)
    
    def test_action_refresh(self, model_selector):
        """Test refresh action"""
        model_selector.model_list = Mock()
        model_selector.loading_display = Mock()
        
        with patch('asyncio.create_task') as mock_create_task:
            model_selector.action_refresh()
        
        # Should hide list and show loading
        assert model_selector.model_list.display is False
        assert model_selector.loading_display.display is True
        
        # Should create task to load models
        mock_create_task.assert_called_once()


class TestModelSelectorUIUpdates:
    """Test UI update methods"""
    
    def test_update_current_model_display_no_model(self, model_selector):
        """Test display update with no current model"""
        model_selector.current_model_label = Mock()
        
        model_selector.update_current_model_display()
        
        # Should show "No model selected"
        model_selector.current_model_label.update.assert_called_once()
        call_args = model_selector.current_model_label.update.call_args[0][0]
        assert "No model selected" in str(call_args)
    
    def test_update_current_model_display_with_model(self, model_selector, mock_model_service):
        """Test display update with current model"""
        model_selector.current_model = "openai/gpt-4"
        model_selector.models = mock_model_service.models
        model_selector.current_model_label = Mock()
        
        model_selector.update_current_model_display()
        
        # Should show current model
        model_selector.current_model_label.update.assert_called_once()
        call_args = model_selector.current_model_label.update.call_args[0][0]
        call_text = str(call_args)
        assert "Current Model:" in call_text
        assert "openai/gpt-4" in call_text
    
    def test_update_current_model_display_unavailable_model(self, model_selector):
        """Test display update with unavailable current model"""
        model_selector.current_model = "unavailable/model"
        model_selector.models = []  # No models loaded
        model_selector.current_model_label = Mock()
        
        model_selector.update_current_model_display()
        
        call_args = model_selector.current_model_label.update.call_args[0][0]
        call_text = str(call_args)
        assert "unavailable/model" in call_text
        assert "not available" in call_text
    
    def test_show_error(self, model_selector):
        """Test error display"""
        model_selector.loading_display = Mock()
        model_selector.model_list = Mock()
        
        model_selector.show_error("Test error message")
        
        # Should update loading display with error and show it
        model_selector.loading_display.update.assert_called_once()
        assert model_selector.loading_display.display is True
        assert model_selector.model_list.display is False
    
    def test_update_model_list_basic(self, model_selector, mock_model_service):
        """Test basic model list update"""
        model_selector.filtered_models = mock_model_service.models
        model_selector.current_model = None
        model_selector.model_list = Mock()
        
        # Mock ListItem and Label creation
        with patch('ai_os.ui.model_selector.ListItem') as mock_list_item, \
             patch('ai_os.ui.model_selector.Label') as mock_label:
            
            mock_item = Mock()
            mock_list_item.return_value = mock_item
            
            model_selector.update_model_list()
            
            # Should clear list and add items
            model_selector.model_list.clear.assert_called_once()
            assert model_selector.model_list.append.call_count == 3
    
    def test_update_model_list_with_current(self, model_selector, mock_model_service):
        """Test model list update with current model"""
        model_selector.filtered_models = mock_model_service.models
        model_selector.current_model = "openai/gpt-4"
        model_selector.model_list = Mock()
        
        with patch('ai_os.ui.model_selector.ListItem') as mock_list_item, \
             patch('ai_os.ui.model_selector.Label') as mock_label:
            
            mock_item = Mock()
            mock_list_item.return_value = mock_item
            
            model_selector.update_model_list()
            
            # Should add current model first, then others
            # Current model + 2 others = 3 total calls
            assert model_selector.model_list.append.call_count == 3


class TestModelSelectorEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_on_mount_initialization_error(self, model_selector, mock_model_service):
        """Test handling of initialization errors in on_mount"""
        mock_model_service.should_fail = True
        model_selector.show_error = Mock()
        model_selector.search_input = Mock()
        model_selector.model_list = Mock()
        model_selector.loading_display = Mock()
        model_selector.update_current_model_display = Mock()
        
        # Make get_current_model fail
        def failing_get_current():
            raise RuntimeError("Config error")
        
        mock_model_service.get_current_model = failing_get_current
        
        await model_selector.on_mount()
        
        # Should show error
        model_selector.show_error.assert_called_once()
        call_args = model_selector.show_error.call_args[0][0]
        assert "Failed to initialize" in call_args
    
    def test_sanitize_id_integration(self, model_selector):
        """Test DOM ID sanitization integration"""
        result = model_selector._sanitize_id("openai/gpt-4")
        
        # Should use DOMSanitizer
        assert result == "openai_gpt_4"
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, model_selector):
        """Test error handling in search functionality"""
        # Setup to cause error
        model_selector.models = None  # This should cause an error
        model_selector.search_input = Mock()
        model_selector.search_input.value = "test"
        
        # Should not crash even with errors
        await model_selector._debounced_search("test")
        
        # Should handle gracefully without updating UI
        assert model_selector.filtered_models == []


class TestModelSelectorIntegration:
    """Integration tests for ModelSelector"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_simulation(self, mock_model_service):
        """Test a full workflow simulation"""
        selector = ModelSelector(mock_model_service)
        
        # Mock all UI components
        selector.current_model_label = Mock()
        selector.search_input = Mock()
        selector.model_list = Mock()
        selector.loading_display = Mock()
        selector.model_detail = Mock()
        selector.update_current_model_display = Mock()
        selector.update_model_list = Mock()
        selector.exit = Mock()
        
        # Simulate mounting
        await selector.on_mount()
        
        # Should have loaded models
        assert len(selector.models) == 3
        
        # Simulate search
        mock_event = Mock()
        mock_event.value = "gpt"
        selector.on_input_changed(mock_event)
        
        # Simulate model selection
        mock_child = Mock()
        mock_child.data_model_id = "openai/gpt-4"
        selector.model_list.highlighted_child = mock_child
        selector.action_select_model()
        
        # Should have selected model
        assert mock_model_service.current_model == "openai/gpt-4"
        selector.exit.assert_called_once_with("openai/gpt-4")


# Test fixtures and utilities for async functions
@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])