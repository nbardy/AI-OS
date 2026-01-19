#!/usr/bin/env python3
"""
Enhanced test script to verify config management and system integration
"""

import sys
import time
from pathlib import Path

# Add the ai_os package to the path
sys.path.insert(0, str(Path(__file__).parent))

from ai_os.utils.config import config_manager

def test_basic_functionality():
    """Test basic config management functionality"""
    print("=" * 50)
    print("Testing Basic Config Management")
    print("=" * 50)
    
    # Test getting current model
    current = config_manager.get_current_model()
    print(f"✓ Current model: {current or 'None'}")
    
    # Test setting a model
    test_model = "openai/gpt-4"
    print(f"✓ Setting model to: {test_model}")
    success = config_manager.set_current_model(test_model)
    print(f"✓ Set operation successful: {success}")
    
    # Test getting it back
    retrieved = config_manager.get_current_model()
    print(f"✓ Retrieved model: {retrieved}")
    
    # Verify they match
    assert retrieved == test_model, f"Model mismatch: {retrieved} != {test_model}"
    print("✓ Model persistence verified")
    
    # Test config file location
    print(f"✓ Config file: {config_manager.config_file}")
    print(f"✓ Config exists: {config_manager.config_file.exists()}")

def test_advanced_features():
    """Test advanced config features"""
    print("\n" + "=" * 50)
    print("Testing Advanced Config Features")
    print("=" * 50)
    
    # Test nested configuration
    print("✓ Testing nested configuration...")
    success = config_manager.set_nested("api_settings.timeout_seconds", 45)
    print(f"✓ Set nested value successful: {success}")
    
    timeout = config_manager.get_nested("api_settings.timeout_seconds")
    print(f"✓ Retrieved nested value: {timeout}")
    assert timeout == 45, f"Nested value mismatch: {timeout} != 45"
    
    # Test default values
    default_val = config_manager.get_nested("nonexistent.key", "default_value")
    print(f"✓ Default value handling: {default_val}")
    assert default_val == "default_value", "Default value not returned"
    
    # Test model caching
    print("✓ Testing model caching...")
    test_models = [
        {"id": "openai/gpt-4", "name": "GPT-4", "description": "Advanced model"},
        {"id": "anthropic/claude-3", "name": "Claude 3", "description": "Anthropic model"}
    ]
    
    success = config_manager.set_cached_models(test_models)
    print(f"✓ Cache models successful: {success}")
    
    cached = config_manager.get_cached_models()
    print(f"✓ Retrieved {len(cached)} cached models")
    assert len(cached) == 2, f"Cache size mismatch: {len(cached)} != 2"
    
    # Test cache validity
    is_valid = config_manager.is_model_cache_valid()
    print(f"✓ Cache is valid: {is_valid}")
    assert is_valid, "Cache should be valid immediately after setting"
    
    # Test model validation
    valid = config_manager.validate_model_id("openai/gpt-4")
    invalid = config_manager.validate_model_id("nonexistent/model")
    print(f"✓ Valid model check: {valid}")
    print(f"✓ Invalid model check: {invalid}")
    assert valid and not invalid, "Model validation failed"

def test_error_handling():
    """Test error handling and edge cases"""
    print("\n" + "=" * 50)
    print("Testing Error Handling")
    print("=" * 50)
    
    # Test invalid model IDs
    print("✓ Testing invalid model ID handling...")
    result1 = config_manager.set_current_model("")
    result2 = config_manager.set_current_model(None)
    print(f"✓ Empty string rejected: {not result1}")
    print(f"✓ None value rejected: {not result2}")
    assert not result1 and not result2, "Invalid model IDs should be rejected"
    
    # Test configuration export/import
    print("✓ Testing config export/import...")
    original = config_manager.export_config()
    print(f"✓ Exported config with {len(original)} keys")
    
    # Modify and reimport
    original["test_key"] = "test_value"
    success = config_manager.import_config(original)
    print(f"✓ Import successful: {success}")
    
    test_val = config_manager.get("test_key")
    print(f"✓ Imported value: {test_val}")
    assert test_val == "test_value", "Import/export failed"

def test_performance():
    """Test performance characteristics"""
    print("\n" + "=" * 50)
    print("Testing Performance")
    print("=" * 50)
    
    # Test large config operations
    print("✓ Testing performance with large dataset...")
    
    start_time = time.time()
    for i in range(100):
        config_manager.set(f"perf_test_{i}", f"value_{i}")
    set_time = time.time() - start_time
    print(f"✓ Set 100 values in {set_time:.3f} seconds")
    
    start_time = time.time()
    for i in range(100):
        val = config_manager.get(f"perf_test_{i}")
        assert val == f"value_{i}", f"Performance test failed at {i}"
    get_time = time.time() - start_time
    print(f"✓ Retrieved 100 values in {get_time:.3f} seconds")
    
    # Clean up performance test data
    for i in range(100):
        config_manager._config.pop(f"perf_test_{i}", None)
    config_manager._save_config()

def display_config_content():
    """Display current configuration content"""
    print("\n" + "=" * 50)
    print("Current Configuration Content")
    print("=" * 50)
    
    if config_manager.config_file.exists():
        with open(config_manager.config_file, 'r') as f:
            content = f.read()
        print(content)
    else:
        print("Config file does not exist")

def main():
    """Run all tests"""
    print("AI-OS Configuration Management Test Suite")
    print("Running comprehensive tests...\n")
    
    try:
        test_basic_functionality()
        test_advanced_features()
        test_error_handling()
        test_performance()
        display_config_content()
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("Config management system is working correctly.")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("=" * 50)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)