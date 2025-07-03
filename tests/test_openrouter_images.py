import os
import base64
import pytest
from unittest.mock import patch, MagicMock
from ai_os.core.models import Message, TextContent, ImageContent
from ai_os.core.chat import chat_completion


def test_message_with_image_content():
    """Test that Message model supports OpenAI-style image content"""
    # Test with text content
    text_msg = Message(
        role="user",
        content="What's in this image?"
    )
    assert text_msg.content == "What's in this image?"
    
    # Test with multimodal content (text + image)
    multimodal_msg = Message(
        role="user",
        content=[
            TextContent(type="text", text="What's in this image?"),
            ImageContent(
                type="image_url",
                image_url={"url": "data:image/jpeg;base64,/9j/4AAQ..."}
            )
        ]
    )
    assert len(multimodal_msg.content) == 2
    assert multimodal_msg.content[0].text == "What's in this image?"
    assert multimodal_msg.content[1].image_url["url"].startswith("data:image")


def test_message_with_url_image():
    """Test Message with URL-based image"""
    msg = Message(
        role="user",
        content=[
            TextContent(type="text", text="Analyze this chart"),
            ImageContent(
                type="image_url", 
                image_url={"url": "https://example.com/chart.png"}
            )
        ]
    )
    assert msg.content[1].image_url["url"] == "https://example.com/chart.png"


@patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"})
@patch("httpx.Client")
def test_chat_completion_with_images(mock_client_class):
    """Test that chat_completion properly sends image content to OpenRouter"""
    # Setup mock
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = [
        'data: {"choices":[{"delta":{"content":"I see an image"}}]}',
        'data: [DONE]'
    ]
    mock_response.raise_for_status = MagicMock()
    mock_client.stream.return_value.__enter__.return_value = mock_response
    
    # Create message with image
    messages = [
        Message(
            role="user",
            content=[
                TextContent(type="text", text="What do you see?"),
                ImageContent(
                    type="image_url",
                    image_url={"url": "data:image/png;base64,iVBORw0KGg..."}
                )
            ]
        )
    ]
    
    # Call chat_completion
    result = list(chat_completion(messages, model="openai/gpt-4-vision-preview"))
    
    # Verify the request
    mock_client.stream.assert_called_once_with(
        "POST",
        "/chat/completions",
        json={
            "model": "openai/gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What do you see?"},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGg..."}}
                    ]
                }
            ],
            "stream": True
        }
    )
    
    assert result == ["I see an image"]


def test_serialize_mixed_messages():
    """Test serialization of messages with both string and multimodal content"""
    messages = [
        Message(role="system", content="You are a helpful assistant"),
        Message(
            role="user",
            content=[
                TextContent(type="text", text="What's this?"),
                ImageContent(type="image_url", image_url={"url": "https://example.com/img.jpg"})
            ]
        ),
        Message(role="assistant", content="Let me analyze that image...")
    ]
    
    # Test model_dump() serialization
    serialized = [msg.model_dump() for msg in messages]
    
    assert serialized[0] == {"role": "system", "content": "You are a helpful assistant"}
    assert serialized[1] == {
        "role": "user",
        "content": [
            {"type": "text", "text": "What's this?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/img.jpg"}}
        ]
    }
    assert serialized[2] == {"role": "assistant", "content": "Let me analyze that image..."}