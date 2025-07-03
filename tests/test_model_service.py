#!/usr/bin/env python3
"""
Comprehensive unit tests for ModelService and related service classes
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import time
from typing import List, Dict, Any

from ai_os.ui.model_selector import (
    ModelService,
    ModelData,
    CircuitBreaker,
    CircuitBreakerState,
    ConfigService,
    ServiceError,
    NetworkError,
    ValidationError
)


class MockConfigService:
    """Mock configuration service for testing"""
    
    def __init__(self):
        self._current_model = None
    
    def get_current_model(self):
        return self._current_model
    
    def set_current_model(self, model_id: str):
        self._current_model = model_id


@pytest.fixture
def mock_config_service():
    """Fixture providing mock config service"""
    return MockConfigService()


@pytest.fixture
def sample_api_response():
    """Fixture providing sample API response data"""
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
                "id": "anthropic/claude-3",
                "name": "Claude-3",
                "description": "Anthropic's latest model",
                "context_length": 100000,
                "pricing": {"prompt": "0.000015", "completion": "0.000075"}
            },
            {
                "id": "invalid-model",  # This one should be skipped due to missing name
                "description": "Invalid model for testing"
            }
        ]
    }


@pytest.fixture
def model_service(mock_config_service):
    """Fixture providing ModelService instance"""
    return ModelService(
        config_service=mock_config_service,
        timeout=5.0,
        max_retries=2,
        retry_delay=0.1
    )


class TestCircuitBreaker:
    """Test cases for CircuitBreaker implementation"""
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
    
    def test_circuit_breaker_successful_call(self):
        """Test successful function call through circuit breaker"""
        cb = CircuitBreaker()
        
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
    
    def test_circuit_breaker_failure_handling(self):
        """Test circuit breaker failure handling"""
        cb = CircuitBreaker(failure_threshold=2, expected_exception=ValueError)
        
        def failing_func():
            raise ValueError("Test error")
        
        # First failure
        with pytest.raises(NetworkError):
            cb.call(failing_func)
        assert cb.failure_count == 1
        assert cb.state == CircuitBreakerState.CLOSED
        
        # Second failure - should open circuit
        with pytest.raises(NetworkError):
            cb.call(failing_func)
        assert cb.failure_count == 2
        assert cb.state == CircuitBreakerState.OPEN
    
    def test_circuit_breaker_open_state(self):
        """Test circuit breaker in open state"""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        def failing_func():
            raise ValueError("Test error")
        
        def success_func():
            return "success"
        
        # Cause failure to open circuit
        with pytest.raises(NetworkError):
            cb.call(failing_func)
        assert cb.state == CircuitBreakerState.OPEN
        
        # Should reject calls while open
        with pytest.raises(ServiceError, match="Circuit breaker is OPEN"):
            cb.call(success_func)
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout"""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        
        def failing_func():
            raise ValueError("Test error")
        
        def success_func():
            return "success"
        
        # Open the circuit
        with pytest.raises(NetworkError):
            cb.call(failing_func)
        assert cb.state == CircuitBreakerState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.02)
        
        # Should move to half-open and then closed on success
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_async_success(self):
        """Test successful async function call"""
        cb = CircuitBreaker()
        
        async def async_success():
            return "async_success"
        
        result = await cb.acall(async_success)
        assert result == "async_success"
        assert cb.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_async_failure(self):
        """Test async function failure handling"""
        cb = CircuitBreaker(failure_threshold=1, expected_exception=ValueError)
        
        async def async_failing():
            raise ValueError("Async test error")
        
        with pytest.raises(NetworkError):
            await cb.acall(async_failing)
        assert cb.state == CircuitBreakerState.OPEN


class TestModelService:
    """Test cases for ModelService class"""
    
    def test_model_service_initialization(self, mock_config_service):
        """Test ModelService initialization"""
        service = ModelService(
            config_service=mock_config_service,
            api_url="https://test.api/models",
            timeout=10.0,
            max_retries=5,
            retry_delay=2.0
        )
        
        assert service.config_service == mock_config_service
        assert service.api_url == "https://test.api/models"
        assert service.timeout == 10.0
        assert service.max_retries == 5
        assert service.retry_delay == 2.0
        assert service._models_cache is None
        assert service._cache_timestamp == 0.0
    
    def test_cache_validation(self, model_service):
        """Test cache validation logic"""
        # Initially no cache
        assert not model_service._is_cache_valid()
        
        # Set cache
        model_service._models_cache = []
        model_service._cache_timestamp = time.time()
        
        # Should be valid immediately
        assert model_service._is_cache_valid()
        
        # Invalidate cache
        model_service._invalidate_cache()
        assert not model_service._is_cache_valid()
        assert model_service._models_cache is None
        assert model_service._cache_timestamp == 0.0
    
    def test_cache_expiry(self, model_service):
        """Test cache expiry after TTL"""
        # Set cache with old timestamp
        model_service._models_cache = []
        model_service._cache_timestamp = time.time() - model_service._cache_ttl - 1
        
        # Should be expired
        assert not model_service._is_cache_valid()
    
    @pytest.mark.asyncio
    async def test_fetch_models_success(self, model_service, sample_api_response):
        """Test successful model fetching"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=sample_api_response)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            models = await model_service.fetch_models()
            
            # Should return valid models (invalid ones filtered out)
            assert len(models) == 2
            assert models[0].id == "openai/gpt-4"
            assert models[1].id == "anthropic/claude-3"
            
            # Cache should be populated
            assert model_service._models_cache == models
            assert model_service._cache_timestamp > 0
    
    @pytest.mark.asyncio
    async def test_fetch_models_network_error(self, model_service):
        """Test network error handling during fetch"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = aiohttp.ClientError("Network error")
            
            with pytest.raises(NetworkError):
                await model_service.fetch_models()
    
    @pytest.mark.asyncio
    async def test_fetch_models_http_error(self, model_service):
        """Test HTTP error handling"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 500
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(NetworkError, match="API returned status 500"):
                await model_service.fetch_models()
    
    @pytest.mark.asyncio
    async def test_fetch_models_invalid_response(self, model_service):
        """Test handling of invalid API response"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"invalid": "response"})
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(ValidationError, match="Invalid API response format"):
                await model_service.fetch_models()
    
    @pytest.mark.asyncio
    async def test_fetch_models_retry_logic(self, model_service):
        """Test retry logic on failure"""
        with patch('aiohttp.ClientSession') as mock_session:
            # First two calls fail, third succeeds
            responses = [
                aiohttp.ClientError("First failure"),
                aiohttp.ClientError("Second failure"),
                AsyncMock(status=200, json=AsyncMock(return_value={"data": []}))
            ]
            
            call_count = 0
            def mock_get(*args, **kwargs):
                nonlocal call_count
                if call_count < 2:
                    call_count += 1
                    raise responses[call_count - 1]
                else:
                    call_count += 1
                    return AsyncMock(__aenter__=AsyncMock(return_value=responses[2]))
            
            mock_session.return_value.__aenter__.return_value.get.side_effect = mock_get
            
            # Should eventually succeed after retries
            models = await model_service.fetch_models()
            assert models == []
            assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_fetch_models_max_retries_exceeded(self, model_service):
        """Test behavior when max retries are exceeded"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = aiohttp.ClientError("Persistent error")
            
            with pytest.raises(NetworkError):
                await model_service.fetch_models()
    
    @pytest.mark.asyncio
    async def test_fetch_models_from_cache(self, model_service):
        """Test fetching models from cache"""
        # Pre-populate cache
        cached_models = [
            ModelData.from_dict({"id": "cached-model", "name": "Cached Model"})
        ]
        model_service._models_cache = cached_models
        model_service._cache_timestamp = time.time()
        
        # Should return cached models without making API call
        with patch('aiohttp.ClientSession') as mock_session:
            models = await model_service.fetch_models()
            assert models == cached_models
            mock_session.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fetch_models_force_refresh(self, model_service, sample_api_response):
        """Test force refresh bypasses cache"""
        # Pre-populate cache
        cached_models = [
            ModelData.from_dict({"id": "cached-model", "name": "Cached Model"})
        ]
        model_service._models_cache = cached_models
        model_service._cache_timestamp = time.time()
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=sample_api_response)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            models = await model_service.fetch_models(force_refresh=True)
            
            # Should get fresh data, not cached
            assert len(models) == 2
            assert models[0].id == "openai/gpt-4"
            mock_session.assert_called_once()
    
    def test_get_current_model(self, model_service, mock_config_service):
        """Test getting current model"""
        mock_config_service.set_current_model("test-model")
        
        current = model_service.get_current_model()
        assert current == "test-model"
    
    def test_set_current_model_valid(self, model_service, mock_config_service):
        """Test setting valid current model"""
        model_service.set_current_model("openai/gpt-4")
        
        assert mock_config_service.get_current_model() == "openai/gpt-4"
    
    def test_set_current_model_invalid(self, model_service):
        """Test setting invalid current model"""
        with pytest.raises(ValidationError, match="Model ID must be a non-empty string"):
            model_service.set_current_model("")
        
        with pytest.raises(ValidationError, match="Model ID must be a non-empty string"):
            model_service.set_current_model(None)
        
        with pytest.raises(ValidationError, match="Model ID cannot be empty"):
            model_service.set_current_model("   ")
    
    def test_filter_models_empty_search(self, model_service):
        """Test filtering with empty search term"""
        models = [
            ModelData.from_dict({"id": "model1", "name": "Model 1"}),
            ModelData.from_dict({"id": "model2", "name": "Model 2"})
        ]
        
        filtered = model_service.filter_models(models, "")
        assert filtered == models
        
        filtered = model_service.filter_models(models, None)
        assert filtered == models
    
    def test_filter_models_with_search(self, model_service):
        """Test filtering with search term"""
        models = [
            ModelData.from_dict({"id": "openai/gpt-4", "name": "GPT-4"}),
            ModelData.from_dict({"id": "anthropic/claude", "name": "Claude"}),
            ModelData.from_dict({"id": "openai/gpt-3", "name": "GPT-3"})
        ]
        
        # Filter by provider
        filtered = model_service.filter_models(models, "openai")
        assert len(filtered) == 2
        assert all("openai" in model.id for model in filtered)
        
        # Filter by model name
        filtered = model_service.filter_models(models, "claude")
        assert len(filtered) == 1
        assert filtered[0].name == "Claude"
        
        # No matches
        filtered = model_service.filter_models(models, "nonexistent")
        assert len(filtered) == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, model_service):
        """Test circuit breaker integration with ModelService"""
        # Force circuit breaker to open by causing failures
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = aiohttp.ClientError("Network error")
            
            # Should exhaust retries and open circuit breaker
            with pytest.raises(NetworkError):
                await model_service.fetch_models()
            
            # Circuit breaker should now be open
            assert model_service.circuit_breaker.state == CircuitBreakerState.OPEN
            
            # Subsequent calls should fail immediately
            with pytest.raises(NetworkError):
                await model_service.fetch_models()


class TestModelServiceEdgeCases:
    """Test edge cases and concurrent behavior"""
    
    @pytest.mark.asyncio
    async def test_concurrent_fetch_requests(self, model_service, sample_api_response):
        """Test concurrent fetch requests"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=sample_api_response)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            # Launch multiple concurrent requests
            tasks = [model_service.fetch_models() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            # All should return the same data
            for models in results:
                assert len(models) == 2
                assert models[0].id == "openai/gpt-4"
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_config_service):
        """Test timeout handling"""
        service = ModelService(
            config_service=mock_config_service,
            timeout=0.001  # Very short timeout
        )
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Simulate slow response
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(0.1)
                return AsyncMock(status=200, json=AsyncMock(return_value={"data": []}))
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__ = slow_response
            
            with pytest.raises(NetworkError):
                await service.fetch_models()
    
    @pytest.mark.asyncio
    async def test_malformed_json_response(self, model_service):
        """Test handling of malformed JSON response"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(NetworkError):
                await model_service.fetch_models()
    
    def test_config_service_integration(self, mock_config_service):
        """Test integration with different config service implementations"""
        # Test with mock that raises exceptions
        class FailingConfigService:
            def get_current_model(self):
                raise RuntimeError("Config error")
            
            def set_current_model(self, model_id: str):
                raise RuntimeError("Config write error")
        
        failing_service = FailingConfigService()
        model_service = ModelService(failing_service)
        
        # Should handle config service errors gracefully
        with pytest.raises(RuntimeError):
            model_service.get_current_model()
        
        with pytest.raises(RuntimeError):
            model_service.set_current_model("test-model")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])