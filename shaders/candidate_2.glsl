#version 300 es
precision highp float;

// Animation time
uniform float u_time;
// Screen resolution for aspect ratio
uniform vec2 u_resolution;

// Output color
out vec4 gl_FragColor;

// Convert HSV to RGB
vec3 hsv2rgb(vec3 hsv) {
    float h = hsv.x;
    float s = hsv.y;
    float v = hsv.z;

    float c = v * s;
    float x = c * (1.0 - mod(h * 6.0, 2.0) - 1.0);
    float m = v - c;

    vec3 rgb;
    if (h < 1.0/6.0) rgb = vec3(c, x, 0.0);
    else if (h < 2.0/6.0) rgb = vec3(x, c, 0.0);
    else if (h < 3.0/6.0) rgb = vec3(0.0, c, x);
    else if (h < 4.0/6.0) rgb = vec3(0.0, x, c);
    else if (h < 5.0/6.0) rgb = vec3(x, 0.0, c);
    else rgb = vec3(c, 0.0, x);

    return rgb + m;
}

void main() {
    // Normalize coordinates to [-1, 1] with aspect ratio correction
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    uv = uv * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    // Convert to polar coordinates
    float r = length(uv);
    float theta = atan(uv.y, uv.x);

    // Normalize angle to [0, 1]
    float normalizedTheta = (theta + 3.14159265) / (2.0 * 3.14159265);

    // Apply layered counter-rotating spirals with distortion
    float spiral1 = sin(theta * 3.0 + u_time * 1.5) * 0.2;
    float spiral2 = sin(theta * 5.0 - u_time * 2.3) * 0.15;
    float spiral3 = sin(theta * 7.0 + u_time * 0.8) * 0.1;

    // Combine spirals for radial distortion
    float distortedR = r + spiral1 + spiral2 + spiral3;

    // Add radial pulsation for additional dynamism
    distortedR += sin(r * 4.0 - u_time) * 0.05;

    // Clamp to prevent negative radius
    distortedR = max(distortedR, 0.0);

    // Create ripple effect from center
    float ripple = sin(distortedR * 10.0 - u_time * 2.0) * 0.5 + 0.5;

    // Map to HSV color space
    float hue = normalizedTheta + sin(distortedR * 2.0 + u_time) * 0.1;
    hue = mod(hue, 1.0);

    // Saturation based on distance and ripple effect
    float saturation = 0.7 + 0.3 * sin(distortedR * 3.0 + u_time * 0.5);
    saturation = clamp(saturation, 0.0, 1.0);

    // Value (brightness) with falloff and animation
    float brightness = 1.0 / (1.0 + distortedR * distortedR);
    brightness *= ripple;
    brightness = pow(brightness, 0.6);

    // Create rainbow vortex effect by combining multiple hue layers
    float hueShift = sin(r * 2.0 + u_time * 0.3) * 0.05;
    hue += hueShift;
    hue = mod(hue, 1.0);

    // Convert HSV to RGB
    vec3 hsv = vec3(hue, saturation, brightness);
    vec3 rgb = hsv2rgb(hsv);

    // Add subtle glow at center
    float glow = exp(-distortedR * distortedR * 2.0);
    rgb += vec3(0.1, 0.05, 0.15) * glow;

    // Output with full opacity
    gl_FragColor = vec4(rgb, 1.0);
}
