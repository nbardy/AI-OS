import pytest
import sys
import os
from pathlib import Path
from PIL import Image # Assumed dependency for image processing

# Adjust sys.path to allow imports from parent directories
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# This placeholder assumes the function generate_and_save_checkerboard
# will be implemented in src/shader_generator.py
# It expects the function to take output_path, width, height, tile_size, and colors
try:
    from src.shader_generator import generate_and_save_checkerboard
except ImportError:
    pytest.fail("Could not import 'generate_and_save_checkerboard' from 'src/shader_generator.py'. "
                "Ensure the file and function exist.")

# Define expected colors and image properties for the checkerboard (assuming black and white)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
IMAGE_WIDTH = 256
IMAGE_HEIGHT = 256
TILE_SIZE = 32 # 8x8 tiles (256/32 = 8)

OUTPUT_DIR = Path("tmp")
OUTPUT_DIR.mkdir(exist_ok=True) # Ensure tmp directory exists for output
OUTPUT_IMAGE_PATH = OUTPUT_DIR / "checkerboard_test_image.png"

@pytest.fixture(scope="module", autouse=True)
def setup_teardown_image():
    """Fixture to ensure a fresh image is generated before tests and cleaned up after."""
    # Ensure the tmp directory exists and is empty of test images before running tests
    if OUTPUT_IMAGE_PATH.exists():
        OUTPUT_IMAGE_PATH.unlink()
    
    # Run the function to generate the image
    generate_and_save_checkerboard(
        output_path=OUTPUT_IMAGE_PATH,
        width=IMAGE_WIDTH,
        height=IMAGE_HEIGHT,
        tile_size=TILE_SIZE,
        color1=BLACK,
        color2=WHITE
    )
    
    assert OUTPUT_IMAGE_PATH.exists()
    yield # Yield control to tests
    
    # Clean up the generated image after tests
    if OUTPUT_IMAGE_PATH.exists():
        OUTPUT_IMAGE_PATH.unlink()

def get_pixel_color(image_path: Path, x: int, y: int):
    """Helper to get the RGB color of a pixel from an image file."""
    try:
        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
            return rgb_img.getpixel((x, y))
    except FileNotFoundError:
        pytest.fail(f"Image file not found at {image_path}")
    except Exception as e:
        pytest.fail(f"Error reading image or pixel at ({x},{y}): {e}")

def test_generated_image_exists():
    """Verify that the checkerboard image was generated."""
    assert OUTPUT_IMAGE_PATH.exists(), f"Image was not found at {OUTPUT_IMAGE_PATH}"
    assert OUTPUT_IMAGE_PATH.stat().st_size > 0, "Generated image file is empty."

def test_checkerboard_pattern_colors():
    """Verify specific pixel colors to ensure the checkerboard pattern."""
    
    # Test top-left quadrant pixels
    # (16, 16) should be BLACK (first tile)
    assert get_pixel_color(OUTPUT_IMAGE_PATH, 16, 16) == BLACK
    # (48, 16) should be WHITE (second tile in first row)
    assert get_pixel_color(OUTPUT_IMAGE_PATH, 48, 16) == WHITE
    # (16, 48) should be WHITE (first tile in second row)
    assert get_pixel_color(OUTPUT_IMAGE_PATH, 16, 48) == WHITE
    # (48, 48) should be BLACK (second tile in second row)
    assert get_pixel_color(OUTPUT_IMAGE_PATH, 48, 48) == BLACK

    # Test center pixels (assuming 256x256, so (128,128) is center)
    center_x = IMAGE_WIDTH // 2
    center_y = IMAGE_HEIGHT // 2
    # The tile at (center_x, center_y) for 256x256 image with 32x32 tiles
    # Pixel (128,128) is in tile (4,4) (0-indexed tiles)
    # Row 4, Col 4. (0,0) is BLACK. (0,1) is WHITE. (1,0) is WHITE. (1,1) is BLACK.
    # Tile (r,c) color depends on (r+c) % 2.
    # For (4,4), (4+4)%2 = 0, so it should be BLACK.
    assert get_pixel_color(OUTPUT_IMAGE_PATH, center_x, center_y) == BLACK
    
    # Test a pixel near the bottom right (e.g., in the last tile)
    last_tile_x = IMAGE_WIDTH - 16
    last_tile_y = IMAGE_HEIGHT - 16
    # Tile (7,7) (0-indexed). (7+7)%2 = 0, so it should be BLACK.
    assert get_pixel_color(OUTPUT_IMAGE_PATH, last_tile_x, last_tile_y) == BLACK

# Note: This test file requires the `Pillow` library (`pip install Pillow`)
# and a `src/shader_generator.py` file with the `generate_and_save_checkerboard` function.
# The `generate_and_save_checkerboard` function is expected to render a checkerboard
# and save it to the specified path, using the provided dimensions and colors.
# Example signature for the expected function:
# def generate_and_save_checkerboard(output_path: Path, width: int, height: int, tile_size: int, color1: tuple, color2: tuple):
#     # ... implementation ...