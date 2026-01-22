"""
Shader renderer using moderngl for headless GLSL rendering.
"""

import moderngl
from PIL import Image
from pathlib import Path


def render_shader(shader_path: str, output_path: str, width: int = 512, height: int = 512, time: float = 1.0) -> bool:
    """
    Render a GLSL fragment shader to an image.

    Args:
        shader_path: Path to .glsl/.frag file
        output_path: Path for output .png file
        width: Image width
        height: Image height
        time: Value for u_time uniform

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read shader
        shader_code = Path(shader_path).read_text()

        # Clean up shader for moderngl compatibility
        # Remove #version directives (moderngl adds its own)
        lines = shader_code.split('\n')
        lines = [l for l in lines if not l.strip().startswith('#version')]
        lines = [l for l in lines if not l.strip().startswith('precision ')]

        # Replace gl_FragColor with fragColor
        shader_code = '\n'.join(lines)
        shader_code = shader_code.replace('gl_FragColor', 'fragColor')

        # Add output declaration if not present
        if 'out vec4 fragColor' not in shader_code:
            shader_code = 'out vec4 fragColor;\n' + shader_code

        # Add version
        shader_code = '#version 330\n' + shader_code

        # Create context
        ctx = moderngl.create_standalone_context()

        vert = """
#version 330
in vec2 in_vert;
void main() {
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

        prog = ctx.program(vertex_shader=vert, fragment_shader=shader_code)

        # Fullscreen quad (-1,-1) to (1,1)
        import struct
        vertices = struct.pack('8f', -1, -1, 1, -1, -1, 1, 1, 1)
        vbo = ctx.buffer(vertices)
        vao = ctx.simple_vertex_array(prog, vbo, 'in_vert')

        # Framebuffer
        fbo = ctx.framebuffer(color_attachments=[ctx.texture((width, height), 4)])
        fbo.use()

        # Set uniforms
        if 'u_resolution' in prog:
            prog['u_resolution'] = (float(width), float(height))
        if 'u_time' in prog:
            prog['u_time'] = time

        # Render
        ctx.clear(0.0, 0.0, 0.0, 1.0)
        vao.render(moderngl.TRIANGLE_STRIP)

        # Save
        data = fbo.read(components=4)
        img = Image.frombytes('RGBA', (width, height), data)
        img = img.transpose(Image.FLIP_TOP_BOTTOM)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)

        return True

    except Exception as e:
        print(f"Render error: {e}")
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        success = render_shader(sys.argv[1], sys.argv[2])
        sys.exit(0 if success else 1)
    else:
        print("Usage: python shader_renderer.py <shader.glsl> <output.png>")
