#!/usr/bin/env python3
"""
Integration tests for the model selector system
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from aioresponses import aioresponses

from ai_os.ui.model_selector import (
    ModelSelector,
    ModelService,
    ModelData,
    select_model,
    run_model_selector
)
from ai_os.utils.config import ConfigManager


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_config_manager(temp_config_dir):
    """Create a test config manager with temporary directory"""
    config_manager = ConfigManager()
    config_manager.config_dir = temp_config_dir
    config_manager.config_file = temp_config_dir / "config.json"
    config_manager._config = {}
    return config_manager


@pytest.fixture
def sample_openrouter_response():
    """Sample OpenRouter API response"""
    return {
        "data": [
            {
                "id": "openai/gpt-4",
                "name": "GPT-4",
                "description": "Most capable GPT model",
                "context_length": 8192,
                "pricing": {"prompt": "0.000030", "completion": "0.000060"}
            },
            {
                "id": "anthropic/claude-3-sonnet",
                "name": "Claude-3 Sonnet",
                "description": "Anthropic's balanced model",
                "context_length": 200000,
                "pricing": {"prompt": "0.000015", "completion": "0.000075"}
            },
            {
                "id": "meta-llama/llama-2-70b",
                "name": "Llama-2 70B",
                "description": "Meta's large open source model",
                "context_length": 4096,
                "pricing": {"prompt": "0.000007", "completion": "0.000028"}
            }
        ]
    }


class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_model_service_workflow(self, test_config_manager, sample_openrouter_response):
        """Test complete model service workflow with real HTTP mocking"""
        with aioresponses() as m:
            # Mock the OpenRouter API response
            m.get(
                "https://openrouter.ai/api/v1/models",
                payload=sample_openrouter_response,
                status=200
            )
            
            # Create service with test config
            service = ModelService(test_config_manager)
            
            # Test fetching models
            models = await service.fetch_models()
            
            assert len(models) == 3
            assert models[0].id == "openai/gpt-4"
            assert models[1].id == "anthropic/claude-3-sonnet"
            assert models[2].id == "meta-llama/llama-2-70b"
            
            # Test setting current model
            service.set_current_model("openai/gpt-4")
            assert service.get_current_model() == "openai/gpt-4"
            
            # Test filtering
            filtered = service.filter_models(models, "claude")
            assert len(filtered) == 1
            assert filtered[0].id == "anthropic/claude-3-sonnet"
            
            # Test caching - second call shouldn't hit API
            cached_models = await service.fetch_models()
            assert cached_models == models
            
            # Only one API call should have been made
            assert len(m.requests) == 1
    
    @pytest.mark.asyncio
    async def test_model_selector_with_real_service(self, test_config_manager, sample_openrouter_response):
        """Test ModelSelector with real ModelService"""
        with aioresponses() as m:
            m.get(
                "https://openrouter.ai/api/v1/models",
                payload=sample_openrouter_response,
                status=200
            )
            
            service = ModelService(test_config_manager)
            selector = ModelSelector(service)
            
            # Mock UI components
            selector.current_model_label = Mock()
            selector.search_input = Mock()
            selector.model_list = Mock()
            selector.loading_display = Mock()
            selector.model_detail = Mock()
            selector.update_current_model_display = Mock()
            selector.update_model_list = Mock()
            
            # Test initialization
            await selector.on_mount()
            
            # Should have loaded models
            assert len(selector.models) == 3
            assert len(selector.filtered_models) == 3
            
            # Test search functionality
            selector.search_input.value = "gpt"
            await selector._debounced_search("gpt")
            
            # Should filter to GPT models
            assert len(selector.filtered_models) == 1
            assert selector.filtered_models[0].id == "openai/gpt-4"
    
    @pytest.mark.asyncio
    async def test_config_persistence(self, test_config_manager):
        """Test that configuration persists correctly"""
        # Initial state - no current model
        assert test_config_manager.get_current_model() is None
        
        # Set a model
        test_config_manager.set_current_model("openai/gpt-4")
        
        # Verify it's set
        assert test_config_manager.get_current_model() == "openai/gpt-4"
        
        # Verify file was created
        assert test_config_manager.config_file.exists()
        
        # Verify file contents
        with open(test_config_manager.config_file, 'r') as f:
            config_data = json.load(f)
        
        assert config_data["current_model"] == "openai/gpt-4"
        
        # Create new config manager instance to test persistence
        new_config_manager = ConfigManager()
        new_config_manager.config_dir = test_config_manager.config_dir
        new_config_manager.config_file = test_config_manager.config_file
        new_config_manager._load_config()
        
        # Should load the saved model
        assert new_config_manager.get_current_model() == "openai/gpt-4"


class TestErrorRecoveryScenarios:
    """Test error recovery and resilience scenarios"""
    
    @pytest.mark.asyncio
    async def test_network_failure_recovery(self, test_config_manager):
        """Test recovery from network failures"""
        service = ModelService(test_config_manager, max_retries=2, retry_delay=0.01)
        
        with aioresponses() as m:
            # First two calls fail, third succeeds
            m.get(
                "https://openrouter.ai/api/v1/models",
                exception=aiohttp.ClientError("Network error"),
                repeat=True
            )
            m.get(
                "https://openrouter.ai/api/v1/models",
                payload={"data": []},
                status=200
            )
            
            # Should eventually succeed after retries
            models = await service.fetch_models()
            assert models == []
    
    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, test_config_manager):
        """Test handling of malformed API responses"""
        service = ModelService(test_config_manager)
        
        with aioresponses() as m:
            # Return malformed response
            m.get(
                "https://openrouter.ai/api/v1/models",
                payload={"invalid": "response"},
                status=200
            )
            
            with pytest.raises(ValidationError):
                await service.fetch_models()
    
    @pytest.mark.asyncio
    async def test_partial_data_corruption(self, test_config_manager):
        """Test handling of partially corrupted model data"""
        service = ModelService(test_config_manager)
        
        corrupted_response = {
            "data": [
                {
                    "id": "openai/gpt-4",
                    "name": "GPT-4",
                    "description": "Valid model"
                },
                {
                    # Missing required ID field
                    "name": "Invalid Model",
                    "description": "Should be skipped"
                },
                {
                    "id": "anthropic/claude-3",
                    "name": "Claude-3",
                    "description": "Another valid model"
                }
            ]
        }
        
        with aioresponses() as m:
            m.get(
                "https://openrouter.ai/api/v1/models",
                payload=corrupted_response,
                status=200
            )
            
            models = await service.fetch_models()
            
            # Should return only valid models, skipping corrupted ones
            assert len(models) == 2
            assert models[0].id == "openai/gpt-4"
            assert models[1].id == "anthropic/claude-3"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, test_config_manager):
        """Test circuit breaker recovery after failures"""
        service = ModelService(test_config_manager)
        service.circuit_breaker.failure_threshold = 2
        service.circuit_breaker.recovery_timeout = 0.01
        
        with aioresponses() as m:
            # First two calls fail to open circuit breaker
            for _ in range(2):
                m.get(
                    "https://openrouter.ai/api/v1/models",
                    exception=aiohttp.ClientError("Network error")
                )
            
            # Cause failures to open circuit breaker
            for _ in range(2):
                with pytest.raises(NetworkError):
                    await service.fetch_models()
            
            # Circuit should be open
            assert service.circuit_breaker.state.value == "open"
            
            # Wait for recovery timeout
            await asyncio.sleep(0.02)
            
            # Add successful response
            m.get(
                "https://openrouter.ai/api/v1/models",
                payload={"data": []},
                status=200
            )
            
            # Should recover and work
            models = await service.fetch_models()
            assert models == []
            assert service.circuit_breaker.state.value == "closed"


class TestPerformanceScenarios:
    """Test performance-related scenarios"""
    
    @pytest.mark.asyncio
    async def test_large_model_dataset(self, test_config_manager):
        """Test handling of large model datasets"""
        # Create a large dataset
        large_response = {
            "data": [
                {
                    "id": f"provider/model-{i}",
                    "name": f"Model {i}",
                    "description": f"Description for model {i}" * 10,  # Long descriptions
                    "context_length": 4096,
                    "pricing": {"prompt": "0.000001", "completion": "0.000002"}
                }
                for i in range(1000)  # 1000 models
            ]
        }
        
        service = ModelService(test_config_manager)
        
        with aioresponses() as m:
            m.get(
                "https://openrouter.ai/api/v1/models",
                payload=large_response,
                status=200
            )
            
            # Should handle large datasets without issues
            models = await service.fetch_models()
            assert len(models) == 1000
            
            # Test filtering performance
            filtered = service.filter_models(models, "model-5")
            assert len(filtered) == 11  # model-5, model-50-59, model-500-509
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, test_config_manager, sample_openrouter_response):
        """Test concurrent API requests with caching"""
        service = ModelService(test_config_manager)
        
        with aioresponses() as m:
            m.get(
                "https://openrouter.ai/api/v1/models",
                payload=sample_openrouter_response,
                status=200
            )
            
            # Make multiple concurrent requests
            tasks = [service.fetch_models() for _ in range(10)]
            results = await asyncio.gather(*tasks)
            
            # All should return the same data
            for models in results:
                assert len(models) == 3
                assert models[0].id == "openai/gpt-4"
            
            # Only one API call should have been made due to caching
            assert len(m.requests) == 1
    
    @pytest.mark.asyncio
    async def test_unicode_handling(self, test_config_manager):
        """Test Unicode handling in model data"""
        unicode_response = {
            "data": [
                {
                    "id": "provider/模型",
                    "name": "测试模型",
                    "description": "Descripción con caractères especiales 🤖",
                    "context_length": 4096
                }
            ]
        }
        
        service = ModelService(test_config_manager)
        
        with aioresponses() as m:
            m.get(
                "https://openrouter.ai/api/v1/models",
                payload=unicode_response,
                status=200
            )
            
            models = await service.fetch_models()
            assert len(models) == 1
            
            model = models[0]
            assert model.id == "provider/模型"
            assert model.name == "测试模型"
            assert "🤖" in model.description
            
            # Test searching with Unicode
            filtered = service.filter_models(models, "测试")
            assert len(filtered) == 1
            
            filtered = service.filter_models(models, "🤖")
            assert len(filtered) == 1


class TestIntegrationWithExternalComponents:
    """Test integration with external components and edge cases"""
    
    def test_config_manager_file_permissions(self, temp_config_dir):
        """Test config manager with file permission issues"""
        config_manager = ConfigManager()
        config_manager.config_dir = temp_config_dir
        config_manager.config_file = temp_config_dir / "config.json"
        
        # Create file with restricted permissions
        config_manager.config_file.touch()
        config_manager.config_file.chmod(0o000)  # No permissions
        
        try:
            # Should handle permission errors gracefully
            config_manager.set_current_model("test-model")
            # Won't actually save, but shouldn't crash
        except PermissionError:
            # This is also acceptable behavior
            pass
        finally:
            # Restore permissions for cleanup
            config_manager.config_file.chmod(0o644)
    
    def test_config_manager_corrupted_file(self, temp_config_dir):
        """Test config manager with corrupted config file"""
        config_manager = ConfigManager()
        config_manager.config_dir = temp_config_dir
        config_manager.config_file = temp_config_dir / "config.json"
        
        # Create corrupted JSON file
        with open(config_manager.config_file, 'w') as f:
            f.write("{ invalid json content")
        
        # Should handle corrupted file gracefully
        config_manager._load_config()
        assert config_manager._config == {}
        
        # Should still be able to set values
        config_manager.set_current_model("test-model")
        assert config_manager.get_current_model() == "test-model"
    
    @pytest.mark.asyncio
    async def test_async_wrapper_functions(self, sample_openrouter_response):
        """Test the async wrapper functions"""
        with aioresponses() as m:
            m.get(
                "https://openrouter.ai/api/v1/models",
                payload=sample_openrouter_response,
                status=200
            )
            
            # Test select_model function
            with patch('ai_os.ui.model_selector.ModelSelector') as mock_selector_class:
                mock_selector = Mock()
                mock_selector.run_async = AsyncMock(return_value="selected-model")
                mock_selector_class.return_value = mock_selector
                
                result = await select_model()
                assert result == "selected-model"
                mock_selector_class.assert_called_once()
    
    def test_synchronous_wrapper(self, sample_openrouter_response):
        """Test synchronous wrapper function"""
        with aioresponses() as m:
            m.get(
                "https://openrouter.ai/api/v1/models",
                payload=sample_openrouter_response,
                status=200
            )
            
            # Test run_model_selector function
            with patch('ai_os.ui.model_selector.select_model') as mock_select:
                mock_select.return_value = AsyncMock(return_value="selected-model")()
                
                with patch('asyncio.run') as mock_run:
                    mock_run.return_value = "selected-model"
                    
                    result = run_model_selector()
                    assert result == "selected-model"
                    mock_run.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])