#version 300 es
precision highp float;

uniform float u_time;
uniform vec2 u_resolution;

out vec4 gl_FragColor;

// Fractional Brownian Motion using layered sin/cos waves
float fbm(vec2 p, float time) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    float maxValue = 0.0;

    for(int i = 0; i < 5; i++) {
        // Rotate at different speeds per layer
        float angle = time * (0.3 + float(i) * 0.15);
        float c = cos(angle);
        float s = sin(angle);
        vec2 rotated = vec2(
            c * p.x - s * p.y,
            s * p.x + c * p.y
        );

        // Layer with different frequencies
        value += amplitude * sin(rotated.x * frequency + time * 0.5) * cos(rotated.y * frequency + time * 0.3);
        maxValue += amplitude;

        amplitude *= 0.5;
        frequency *= 2.0;
    }

    return value / maxValue;
}

// Domain warping: apply fbm to itself recursively
vec2 domainWarp(vec2 p, float time) {
    // First warp layer
    vec2 warped = p + vec2(
        fbm(p + time * 0.1, time),
        fbm(p + vec2(3.14, 2.71) + time * 0.12, time)
    );

    // Second warp layer for more complex patterns
    warped += vec2(
        fbm(warped + time * 0.15, time),
        fbm(warped + vec2(1.41, 1.73) + time * 0.18, time)
    ) * 0.5;

    return warped;
}

// Color gradient based on distance from warp centers
vec3 colorFromWarp(vec2 warpedPos, float distFromCenter) {
    // Create smooth gradients using sin functions
    vec3 color = vec3(0.0);

    // Primary gradient: shifts through hue space
    float hue = sin(warpedPos.x * 0.5) * 0.5 + 0.5;
    color += vec3(
        sin(hue * 3.14159) * 0.5 + 0.5,
        cos(hue * 3.14159 + 2.0) * 0.5 + 0.5,
        sin(hue * 3.14159 + 4.0) * 0.5 + 0.5
    );

    // Secondary gradient: based on distance
    float distGradient = sin(distFromCenter * 3.0 + u_time * 0.5) * 0.5 + 0.5;
    color = mix(color, vec3(distGradient), 0.3);

    // Tertiary gradient: interference pattern
    float interference = cos(warpedPos.y * 0.7) * sin(warpedPos.x * 0.7);
    color += vec3(interference * 0.3);

    return clamp(color, 0.0, 1.0);
}

void main() {
    // Normalize coordinates to [-1, 1] with aspect ratio correction
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec2 p = (uv - 0.5) * 2.0;
    p.x *= u_resolution.x / u_resolution.y;

    // Apply domain warping with time-based animation
    vec2 warpedPos = domainWarp(p, u_time);

    // Calculate distance from origin through the warped space
    float distFromCenter = length(warpedPos);

    // Create smooth distance-based color modulation
    float distFade = sin(distFromCenter * 2.0 - u_time * 0.7) * 0.5 + 0.5;

    // Get base color from warped position
    vec3 color = colorFromWarp(warpedPos, distFromCenter);

    // Apply distance fade and time-based brightness
    float brightness = 0.7 + 0.3 * sin(u_time * 0.3);
    color *= brightness * (1.0 - distFade * 0.4);

    // Add swirl effect through additional phase modulation
    float swirl = atan(warpedPos.y, warpedPos.x) + u_time * 0.2;
    color += vec3(sin(swirl) * 0.1, cos(swirl) * 0.1, sin(swirl + 1.0) * 0.1);

    gl_FragColor = vec4(color, 1.0);
}
