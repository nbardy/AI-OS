#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

const float PI = 3.14159265359;
const float EPSILON = 0.15;
const float SCALE = 1.5;

// HSV to RGB conversion
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// Hopf fibration: S³ → R³ via stereographic projection
vec3 hopf(float theta, float phi, float rot) {
    float cp = cos(phi * 0.5);
    float sp = sin(phi * 0.5);
    float ct = cos(theta);
    float st = sin(theta);
    float ctr = cos(theta + rot);
    float str = sin(theta + rot);

    vec4 q = vec4(cp * ct, cp * st, sp * ctr, sp * str);
    return q.xyz / (1.0 - q.w + EPSILON);
}

// Point to line segment distance
float segDist(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    vec3 ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    return length(ap - ab * t);
}

// Camera matrix
mat3 lookAt(vec3 eye, vec3 target, vec3 up) {
    vec3 zaxis = normalize(target - eye);
    vec3 xaxis = normalize(cross(up, zaxis));
    vec3 yaxis = cross(zaxis, xaxis);
    return mat3(xaxis, yaxis, zaxis);
}

void main() {
    // Standard UV
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Orbital camera (Y-offset, never overhead)
    float angle = u_time * 0.25;
    vec3 eye = vec3(3.0 * cos(angle), 1.4, 3.0 * sin(angle));
    vec3 target = vec3(0.0);
    mat3 cam = lookAt(eye, target, vec3(0.0, 1.0, 0.0));
    vec3 rayDir = normalize(cam * vec3(uv, 1.5));

    // Generate 8 fibers: 2 shells × 4 rotations
    // Shell angles: pi/6, pi/3 (wider spacing, distinct radii)
    // Rotations: 0, pi/4, pi/2, 3pi/4 (shows linking)
    float fibers[960]; // 8 fibers × 40 segments × 3 coords = 960

    int idx = 0;
    for (int fiberIdx = 0; fiberIdx < 8; fiberIdx++) {
        int shellIdx = fiberIdx / 4;
        int rotIdx = fiberIdx - shellIdx * 4;

        float phi = (shellIdx == 0) ? PI / 6.0 : PI / 3.0;
        float rot = float(rotIdx) * PI * 0.25;

        for (int seg = 0; seg < 40; seg++) {
            float theta = float(seg) * 2.0 * PI / 40.0;
            vec3 p = hopf(theta, phi, rot) * SCALE;
            fibers[idx++] = p.x;
            fibers[idx++] = p.y;
            fibers[idx++] = p.z;
        }
    }

    // Ray march with front-to-back accumulation
    vec3 color = vec3(0.0);
    float accum = 0.0;
    const float tubeRadius = 0.08;
    const float glowRadius = 0.12; // 1.5× tube radius

    for (int step = 0; step < 64; step++) {
        vec3 pos = eye + rayDir * (float(step) * 0.10);

        for (int fiberIdx = 0; fiberIdx < 8; fiberIdx++) {
            // Determine fiber color (warm/cool split by shell)
            int shellIdx = fiberIdx / 4;
            float hue = (shellIdx == 0) ? 15.0 / 360.0 : 200.0 / 360.0;
            vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95));

            // Find minimum distance to this fiber
            float minDist = 1e10;
            int baseIdx = fiberIdx * 120; // 40 segments × 3 coords

            for (int seg = 0; seg < 40; seg++) {
                int idx1 = baseIdx + seg * 3;
                int idx2 = baseIdx + ((seg + 1) % 40) * 3;

                vec3 a = vec3(fibers[idx1], fibers[idx1 + 1], fibers[idx1 + 2]);
                vec3 b = vec3(fibers[idx2], fibers[idx2 + 1], fibers[idx2 + 2]);

                float d = segDist(pos, a, b);
                minDist = min(minDist, d);
            }

            // Solid tube density (nearest segment only)
            float density = max(0.0, (tubeRadius - minDist) / tubeRadius);

            // Glow halo (structurally necessary to cover ray march gaps)
            float glowDist = max(0.0, minDist - tubeRadius);
            float glow = exp(-glowDist * 5.0) * 0.08;

            // Combine density and glow
            float totalDensity = density * density + glow;
            float alpha = (1.0 - exp(-totalDensity * 4.5)) * 0.85;

            // Per-step front-to-back accumulation (MANDATORY)
            color += fiberColor * alpha * (1.0 - accum);
            accum += alpha * (1.0 - accum);
        }

        // Early exit optimization
        if (accum > 0.99) break;
    }

    // Dark background
    vec3 bg = vec3(0.02);
    color = mix(bg, color, min(accum, 1.0));

    gl_FragColor = vec4(color, 1.0);
}
