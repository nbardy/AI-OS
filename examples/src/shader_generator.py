from PIL import Image, ImageDraw
from pathlib import Path
from typing import Tuple

def generate_and_save_checkerboard(
    output_path: Path,
    width: int,
    height: int,
    tile_size: int,
    color1: Tuple[int, int, int],
    color2: Tuple[int, int, int]
) -> None:
    """
    Generates a checkerboard pattern image and saves it to the specified path.

    Args:
        output_path: The path where the image will be saved.
        width: The width of the image in pixels.
        height: The height of the image in pixels.
        tile_size: The size (width and height) of each square tile in pixels.
        color1: The RGB tuple for the first color (e.g., (0, 0, 0) for black).
        color2: The RGB tuple for the second color (e.g., (255, 255, 255) for white).
    """
    # Create a new RGB image with the specified dimensions
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)

    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            # Determine which color to use based on tile coordinates
            # (row_index + col_index) % 2 will alternate between 0 and 1
            # giving us the checkerboard pattern
            col_index = x // tile_size
            row_index = y // tile_size
            
            if (row_index + col_index) % 2 == 0:
                color = color1
            else:
                color = color2
            
            # Draw a rectangle for the current tile
            draw.rectangle([x, y, x + tile_size - 1, y + tile_size - 1], fill=color)

    # Ensure the output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the image
    img.save(output_path)

# Example Usage (for direct testing, not part of the main test function)
if __name__ == '__main__':
    OUTPUT_DIR = Path("tmp")
    OUTPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_IMAGE_PATH = OUTPUT_DIR / "example_checkerboard.png"
    
    generate_and_save_checkerboard(
        output_path=OUTPUT_IMAGE_PATH,
        width=512,
        height=512,
        tile_size=64,
        color1=(0, 0, 0),    # Black
        color2=(255, 255, 255) # White
    )
    print(f"Generated example checkerboard at {OUTPUT_IMAGE_PATH}")