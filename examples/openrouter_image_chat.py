#!/usr/bin/env python3
"""
Example of using OpenRouter with images via OpenAI-compatible format.

This demonstrates how to:
1. Send images as base64-encoded data
2. Send images as URLs
3. Mix text and images in conversations
"""

import os
import base64
import httpx
from pathlib import Path
from ai_os.core.models import Message, TextContent, ImageContent
from ai_os.core.chat import chat_completion


def encode_image(image_path: str) -> str:
    """Encode image file to base64 string"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')


def example_base64_image():
    """Example: Send a local image as base64 to OpenRouter"""
    print("=== Example 1: Base64 Image ===")
    
    # For demo, we'll create a simple test image
    # In real use, you'd load an actual image file
    image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    messages = [
        Message(
            role="user",
            content=[
                TextContent(type="text", text="What do you see in this image?"),
                ImageContent(
                    type="image_url",
                    image_url={"url": f"data:image/png;base64,{image_base64}"}
                )
            ]
        )
    ]
    
    # Use a vision-capable model
    model = "openai/gpt-4-vision-preview"
    
    print(f"Sending image to {model}...")
    for chunk in chat_completion(messages, model=model):
        print(chunk, end='', flush=True)
    print("\n")


def example_url_image():
    """Example: Send an image URL to OpenRouter"""
    print("=== Example 2: URL Image ===")
    
    messages = [
        Message(
            role="user",
            content=[
                TextContent(type="text", text="Can you describe this chart?"),
                ImageContent(
                    type="image_url",
                    image_url={"url": "https://example.com/chart.png"}
                )
            ]
        )
    ]
    
    model = "anthropic/claude-3-opus"  # Claude 3 also supports vision
    
    print(f"Sending image URL to {model}...")
    for chunk in chat_completion(messages, model=model):
        print(chunk, end='', flush=True)
    print("\n")


def example_multiple_images():
    """Example: Send multiple images in one message"""
    print("=== Example 3: Multiple Images ===")
    
    messages = [
        Message(
            role="user",
            content=[
                TextContent(type="text", text="Compare these two images:"),
                ImageContent(
                    type="image_url",
                    image_url={"url": "https://example.com/image1.jpg"}
                ),
                ImageContent(
                    type="image_url",
                    image_url={"url": "https://example.com/image2.jpg"}
                ),
                TextContent(type="text", text="What are the main differences?")
            ]
        )
    ]
    
    model = "openai/gpt-4-vision-preview"
    
    print(f"Sending multiple images to {model}...")
    for chunk in chat_completion(messages, model=model):
        print(chunk, end='', flush=True)
    print("\n")


def example_conversation_with_images():
    """Example: Multi-turn conversation with images"""
    print("=== Example 4: Conversation with Images ===")
    
    messages = [
        Message(role="system", content="You are a helpful image analysis assistant."),
        Message(
            role="user",
            content=[
                TextContent(type="text", text="I'm going to show you some images. First, what's this?"),
                ImageContent(
                    type="image_url",
                    image_url={"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="}
                )
            ]
        ),
        Message(role="assistant", content="This appears to be a very small image, possibly a single pixel or a placeholder image. The base64 data suggests it's a minimal PNG file."),
        Message(role="user", content="Good observation! Can you tell me more about the PNG format?")
    ]
    
    model = "openai/gpt-4-vision-preview"
    
    print(f"Continuing conversation with {model}...")
    for chunk in chat_completion(messages, model=model):
        print(chunk, end='', flush=True)
    print("\n")


def example_with_local_file(image_path: str):
    """Example: Load and send a local image file"""
    print(f"=== Example 5: Local File: {image_path} ===")
    
    if not Path(image_path).exists():
        print(f"Image file not found: {image_path}")
        return
    
    # Encode the image
    image_base64 = encode_image(image_path)
    
    # Detect image format from extension
    ext = Path(image_path).suffix.lower()
    mime_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg', 
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }.get(ext, 'image/jpeg')
    
    messages = [
        Message(
            role="user",
            content=[
                TextContent(type="text", text="Please analyze this image in detail:"),
                ImageContent(
                    type="image_url",
                    image_url={"url": f"data:{mime_type};base64,{image_base64}"}
                )
            ]
        )
    ]
    
    model = "openai/gpt-4-vision-preview"
    
    print(f"Sending {image_path} to {model}...")
    for chunk in chat_completion(messages, model=model):
        print(chunk, end='', flush=True)
    print("\n")


if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: Please set OPENROUTER_API_KEY environment variable")
        print("Get your API key from: https://openrouter.ai/keys")
        exit(1)
    
    # Run examples
    try:
        example_base64_image()
        example_url_image()
        example_multiple_images()
        example_conversation_with_images()
        
        # If you have a local image file, uncomment and modify:
        # example_with_local_file("/path/to/your/image.jpg")
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nNote: Vision support depends on the model. Models that support images include:")
    print("- openai/gpt-4-vision-preview")
    print("- anthropic/claude-3-opus")
    print("- anthropic/claude-3-sonnet")
    print("- google/gemini-pro-vision")
    print("\nCheck OpenRouter docs for the latest vision-capable models.")