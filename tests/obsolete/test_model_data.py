#!/usr/bin/env python3
"""
Comprehensive unit tests for ModelData and related classes
"""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch
import unicodedata

from ai_os.ui.model_selector import (
    ModelData,
    ModelPricing,
    ValidationError,
    DOMSanitizer
)


class TestModelPricing:
    """Test cases for ModelPricing data class"""
    
    def test_default_pricing(self):
        """Test default pricing values"""
        pricing = ModelPricing()
        assert pricing.prompt == 0.0
        assert pricing.completion == 0.0
    
    def test_explicit_pricing(self):
        """Test explicit pricing values"""
        pricing = ModelPricing(prompt=0.001, completion=0.002)
        assert pricing.prompt == 0.001
        assert pricing.completion == 0.002
    
    def test_from_dict_valid(self):
        """Test creating pricing from valid dictionary"""
        pricing_dict = {"prompt": "0.001", "completion": "0.002"}
        pricing = ModelPricing.from_dict(pricing_dict)
        assert pricing.prompt == 0.001
        assert pricing.completion == 0.002
    
    def test_from_dict_missing_completion(self):
        """Test creating pricing with missing completion"""
        pricing_dict = {"prompt": "0.001"}
        pricing = ModelPricing.from_dict(pricing_dict)
        assert pricing.prompt == 0.001
        assert pricing.completion == 0.0
    
    def test_from_dict_invalid_values(self):
        """Test creating pricing with invalid values"""
        pricing_dict = {"prompt": "invalid", "completion": "also_invalid"}
        pricing = ModelPricing.from_dict(pricing_dict)
        assert pricing.prompt == 0.0
        assert pricing.completion == 0.0
    
    def test_from_dict_not_dict(self):
        """Test creating pricing from non-dictionary"""
        pricing = ModelPricing.from_dict("not_a_dict")
        assert pricing.prompt == 0.0
        assert pricing.completion == 0.0
    
    def test_from_dict_empty_dict(self):
        """Test creating pricing from empty dictionary"""
        pricing = ModelPricing.from_dict({})
        assert pricing.prompt == 0.0
        assert pricing.completion == 0.0
    
    def test_from_dict_numeric_values(self):
        """Test creating pricing from numeric values"""
        pricing_dict = {"prompt": 0.001, "completion": 0.002}
        pricing = ModelPricing.from_dict(pricing_dict)
        assert pricing.prompt == 0.001
        assert pricing.completion == 0.002


class TestModelData:
    """Test cases for ModelData class"""
    
    def test_from_dict_valid_minimal(self):
        """Test creating ModelData with minimal valid data"""
        model_dict = {"id": "test-model", "name": "Test Model"}
        model = ModelData.from_dict(model_dict)
        
        assert model.id == "test-model"
        assert model.name == "Test Model"
        assert model.description == ""
        assert model.context_length == 0
        assert isinstance(model.pricing, ModelPricing)
    
    def test_from_dict_valid_complete(self):
        """Test creating ModelData with complete valid data"""
        model_dict = {
            "id": "test-model",
            "name": "Test Model",
            "description": "A test model for testing",
            "context_length": 4096,
            "pricing": {"prompt": "0.001", "completion": "0.002"}
        }
        model = ModelData.from_dict(model_dict)
        
        assert model.id == "test-model"
        assert model.name == "Test Model"
        assert model.description == "A test model for testing"
        assert model.context_length == 4096
        assert model.pricing.prompt == 0.001
        assert model.pricing.completion == 0.002
    
    def test_from_dict_missing_id(self):
        """Test creating ModelData without ID raises ValidationError"""
        model_dict = {"name": "Test Model"}
        with pytest.raises(ValidationError, match="Model ID is required"):
            ModelData.from_dict(model_dict)
    
    def test_from_dict_empty_id(self):
        """Test creating ModelData with empty ID raises ValidationError"""
        model_dict = {"id": "", "name": "Test Model"}
        with pytest.raises(ValidationError, match="Model ID is required"):
            ModelData.from_dict(model_dict)
    
    def test_from_dict_whitespace_id(self):
        """Test creating ModelData with whitespace-only ID raises ValidationError"""
        model_dict = {"id": "   ", "name": "Test Model"}
        with pytest.raises(ValidationError, match="Model ID is required"):
            ModelData.from_dict(model_dict)
    
    def test_from_dict_missing_name_uses_id(self):
        """Test that missing name falls back to ID"""
        model_dict = {"id": "test-model"}
        model = ModelData.from_dict(model_dict)
        assert model.name == "test-model"
    
    def test_from_dict_empty_name_uses_id(self):
        """Test that empty name falls back to ID"""
        model_dict = {"id": "test-model", "name": ""}
        model = ModelData.from_dict(model_dict)
        assert model.name == "test-model"
    
    def test_from_dict_whitespace_name_uses_id(self):
        """Test that whitespace-only name falls back to ID"""
        model_dict = {"id": "test-model", "name": "   "}
        model = ModelData.from_dict(model_dict)
        assert model.name == "test-model"
    
    def test_from_dict_invalid_context_length(self):
        """Test handling of invalid context length values"""
        test_cases = [
            ("string", 0),
            (-100, 0),
            (None, 0),
            ([], 0),
            ({}, 0),
            ("123", 123),
            (123.5, 123),
        ]
        
        for invalid_value, expected in test_cases:
            model_dict = {"id": "test", "name": "test", "context_length": invalid_value}
            model = ModelData.from_dict(model_dict)
            assert model.context_length == expected, f"Failed for value: {invalid_value}"
    
    def test_from_dict_not_dict_raises_error(self):
        """Test that non-dictionary input raises ValidationError"""
        with pytest.raises(ValidationError, match="Model data must be a dictionary"):
            ModelData.from_dict("not_a_dict")
        
        with pytest.raises(ValidationError, match="Model data must be a dictionary"):
            ModelData.from_dict(None)
        
        with pytest.raises(ValidationError, match="Model data must be a dictionary"):
            ModelData.from_dict([])
    
    def test_get_display_text_basic(self):
        """Test basic display text generation"""
        model_dict = {"id": "test-model", "name": "Test Model"}
        model = ModelData.from_dict(model_dict)
        
        text = model.get_display_text()
        assert "Test Model" in str(text)
    
    def test_get_display_text_with_context_length(self):
        """Test display text with context length"""
        model_dict = {
            "id": "test-model",
            "name": "Test Model",
            "context_length": 4096
        }
        model = ModelData.from_dict(model_dict)
        
        text = model.get_display_text()
        text_str = str(text)
        assert "Test Model" in text_str
        assert "4,096 tokens" in text_str
    
    def test_get_detail_text_minimal(self):
        """Test detail text with minimal data"""
        model_dict = {"id": "test-model", "name": "Test Model"}
        model = ModelData.from_dict(model_dict)
        
        text = model.get_detail_text()
        text_str = str(text)
        assert "ID: test-model" in text_str
    
    def test_get_detail_text_complete(self):
        """Test detail text with complete data"""
        model_dict = {
            "id": "test-model",
            "name": "Test Model",
            "description": "A test model",
            "context_length": 4096,
            "pricing": {"prompt": "0.001", "completion": "0.002"}
        }
        model = ModelData.from_dict(model_dict)
        
        text = model.get_detail_text()
        text_str = str(text)
        assert "ID: test-model" in text_str
        assert "Description: A test model" in text_str
        assert "$0.001000 prompt" in text_str
        assert "$0.002000 completion" in text_str
    
    def test_matches_search_case_insensitive(self):
        """Test search matching is case insensitive"""
        model_dict = {
            "id": "OpenAI/GPT-4",
            "name": "GPT-4",
            "description": "Advanced language model"
        }
        model = ModelData.from_dict(model_dict)
        
        assert model.matches_search("gpt")
        assert model.matches_search("GPT")
        assert model.matches_search("openai")
        assert model.matches_search("OPENAI")
        assert model.matches_search("advanced")
        assert model.matches_search("LANGUAGE")
    
    def test_matches_search_empty_term(self):
        """Test that empty search term matches all models"""
        model_dict = {"id": "test-model", "name": "Test Model"}
        model = ModelData.from_dict(model_dict)
        
        assert model.matches_search("")
        assert model.matches_search(None)
    
    def test_matches_search_no_match(self):
        """Test search with no matches"""
        model_dict = {"id": "test-model", "name": "Test Model"}
        model = ModelData.from_dict(model_dict)
        
        assert not model.matches_search("nonexistent")
        assert not model.matches_search("xyz123")
    
    def test_unicode_handling(self):
        """Test proper Unicode handling in model data"""
        model_dict = {
            "id": "test-model",
            "name": "Test Modèl with ünïcode",
            "description": "Descripción con caractères especiales 🤖"
        }
        model = ModelData.from_dict(model_dict)
        
        assert model.name == "Test Modèl with ünïcode"
        assert model.description == "Descripción con caractères especiales 🤖"
        
        # Test search with Unicode
        assert model.matches_search("modèl")
        assert model.matches_search("descripción")
        assert model.matches_search("🤖")


class TestDOMSanitizer:
    """Test cases for DOMSanitizer utility class"""
    
    def test_sanitize_basic_id(self):
        """Test sanitizing basic model IDs"""
        assert DOMSanitizer.sanitize_id("openai/gpt-4") == "openai_gpt_4"
        assert DOMSanitizer.sanitize_id("anthropic/claude-3") == "anthropic_claude_3"
        assert DOMSanitizer.sanitize_id("simple-model") == "simple_model"
    
    def test_sanitize_special_characters(self):
        """Test sanitizing IDs with special characters"""
        assert DOMSanitizer.sanitize_id("model@domain.com") == "model_domain_com"
        assert DOMSanitizer.sanitize_id("model#123") == "model_123"
        assert DOMSanitizer.sanitize_id("model$%^&*()") == "model_"
    
    def test_sanitize_consecutive_separators(self):
        """Test handling of consecutive separators"""
        assert DOMSanitizer.sanitize_id("model___test") == "model_test"
        assert DOMSanitizer.sanitize_id("model---test") == "model_test"
        assert DOMSanitizer.sanitize_id("model_-_-_test") == "model_test"
    
    def test_sanitize_leading_number(self):
        """Test handling of IDs starting with numbers"""
        assert DOMSanitizer.sanitize_id("123-model") == "model_123_model"
        assert DOMSanitizer.sanitize_id("9gpt-4") == "model_9gpt_4"
    
    def test_sanitize_empty_or_invalid(self):
        """Test handling of empty or invalid IDs"""
        assert DOMSanitizer.sanitize_id("") == "unknown"
        assert DOMSanitizer.sanitize_id("   ") == "unknown"
        assert DOMSanitizer.sanitize_id("---") == "unknown"
        assert DOMSanitizer.sanitize_id("___") == "unknown"
    
    def test_sanitize_unicode(self):
        """Test sanitizing Unicode characters"""
        assert DOMSanitizer.sanitize_id("modèl-tëst") == "mod_l_t_st"
        assert DOMSanitizer.sanitize_id("模型-测试") == "model____"
    
    def test_sanitize_edge_cases(self):
        """Test edge cases for ID sanitization"""
        # Very long ID
        long_id = "a" * 1000
        result = DOMSanitizer.sanitize_id(long_id)
        assert len(result) <= 1000
        assert result.startswith("a")
        
        # Mixed valid and invalid characters
        assert DOMSanitizer.sanitize_id("valid_123-test@invalid") == "valid_123_test_invalid"


@pytest.fixture
def sample_model_data():
    """Fixture providing sample model data for tests"""
    return {
        "id": "openai/gpt-4",
        "name": "GPT-4",
        "description": "Most capable GPT model",
        "context_length": 8192,
        "pricing": {
            "prompt": "0.000030",
            "completion": "0.000060"
        }
    }


@pytest.fixture
def invalid_model_data_cases():
    """Fixture providing various invalid model data cases"""
    return [
        # Missing required fields
        {},
        {"name": "Test"},
        {"id": "", "name": "Test"},
        
        # Invalid types
        "not_a_dict",
        None,
        [],
        
        # Invalid field values
        {"id": None, "name": "Test"},
        {"id": 123, "name": "Test"},
        {"id": "test", "name": None},
    ]


class TestModelDataEdgeCases:
    """Test edge cases and error conditions for ModelData"""
    
    def test_extremely_large_context_length(self):
        """Test handling of extremely large context lengths"""
        model_dict = {
            "id": "test-model",
            "name": "Test Model",
            "context_length": 999999999999  # Very large number
        }
        model = ModelData.from_dict(model_dict)
        # Should handle large numbers gracefully
        assert isinstance(model.context_length, int)
        assert model.context_length >= 0
    
    def test_very_long_strings(self):
        """Test handling of very long strings"""
        long_description = "A" * 10000
        model_dict = {
            "id": "test-model",
            "name": "Test Model",
            "description": long_description
        }
        model = ModelData.from_dict(model_dict)
        # Should handle long strings without crashing
        assert len(model.description) <= 10000
    
    def test_special_pricing_values(self):
        """Test handling of special pricing values"""
        test_cases = [
            {"prompt": float('inf'), "completion": 0.001},
            {"prompt": float('-inf'), "completion": 0.001},
            {"prompt": float('nan'), "completion": 0.001},
            {"prompt": None, "completion": None},
        ]
        
        for pricing_dict in test_cases:
            model_dict = {
                "id": "test-model",
                "name": "Test Model",
                "pricing": pricing_dict
            }
            # Should not crash, even with special float values
            model = ModelData.from_dict(model_dict)
            assert isinstance(model.pricing, ModelPricing)
    
    def test_concurrent_model_creation(self):
        """Test that ModelData creation is thread-safe"""
        import threading
        import time
        
        model_dict = {
            "id": "test-model",
            "name": "Test Model",
            "description": "Concurrent test model"
        }
        
        results = []
        errors = []
        
        def create_model():
            try:
                model = ModelData.from_dict(model_dict.copy())
                results.append(model)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads creating models concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_model)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(errors) == 0
        assert len(results) == 10
        
        # All results should be equivalent
        for model in results:
            assert model.id == "test-model"
            assert model.name == "Test Model"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])