#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

// Constants - MINIMAL CHANGES: tube_radius 0.06->0.065, camera_y 1.5->1.3
const float TUBE_RADIUS = 0.065;
const float EPSILON = 0.15;
const float POST_PROJ_SCALE = 1.5;
const float CAMERA_DIST = 3.0;
const float CAMERA_Y = 1.3;
const float CAMERA_SPEED = 0.25;
const int NUM_FIBERS = 6;
const int SEGMENTS_PER_FIBER = 40;
const int RAY_STEPS = 48;
const float STEP_SIZE = 0.10;
const float PI = 3.14159265359;

// HSV to RGB conversion
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// Distance from point to line segment
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    vec3 ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    vec3 closest = a + t * ab;
    return length(p - closest);
}

void main() {
    // Aspect-corrected UV
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Generate fiber data: 6 fibers × 40 segments × 4 floats (x,y,z,hue) = 960 floats
    float fiberData[960];

    int idx = 0;
    for (int shellIdx = 0; shellIdx < 3; shellIdx++) {
        float phi = PI / 6.0 + float(shellIdx) * PI / 6.0; // π/6, π/3, π/2

        for (int rotIdx = 0; rotIdx < 2; rotIdx++) {
            float rotation = float(rotIdx) * PI / 2.0; // 0, π/2
            float hue = float(shellIdx) / 3.0 + float(rotIdx) / 6.0;

            for (int seg = 0; seg < SEGMENTS_PER_FIBER; seg++) {
                float theta = float(seg) * 2.0 * PI / float(SEGMENTS_PER_FIBER);

                // Hopf fibration quaternion
                float cp2 = cos(phi * 0.5);
                float sp2 = sin(phi * 0.5);
                vec4 q = vec4(
                    cp2 * cos(theta),
                    cp2 * sin(theta),
                    sp2 * cos(theta + rotation),
                    sp2 * sin(theta + rotation)
                );

                // Stereographic projection S3 -> R3
                vec3 pos = q.xyz / (1.0 - q.w + EPSILON);
                pos *= POST_PROJ_SCALE;

                // Store position and hue
                fiberData[idx++] = pos.x;
                fiberData[idx++] = pos.y;
                fiberData[idx++] = pos.z;
                fiberData[idx++] = hue;
            }
        }
    }

    // Camera setup (Y-offset orbital)
    float cameraAngle = u_time * CAMERA_SPEED;
    vec3 cameraPos = vec3(
        CAMERA_DIST * cos(cameraAngle),
        CAMERA_Y,
        CAMERA_DIST * sin(cameraAngle)
    );
    vec3 target = vec3(0.0);
    vec3 forward = normalize(target - cameraPos);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
    vec3 up = cross(forward, right);

    // Ray direction
    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);
    vec3 rayPos = cameraPos;

    // Ray march with per-step accumulation
    vec3 color = vec3(0.0);
    float accum = 0.0;

    for (int step = 0; step < RAY_STEPS && accum < 0.95; step++) {
        float minDist = 1000.0;
        float minHue = 0.0;

        // Check all fibers
        for (int fiber = 0; fiber < NUM_FIBERS; fiber++) {
            int baseIdx = fiber * SEGMENTS_PER_FIBER * 4;

            // Check all segments
            for (int seg = 0; seg < SEGMENTS_PER_FIBER; seg++) {
                int segIdx = baseIdx + seg * 4;
                vec3 a = vec3(fiberData[segIdx], fiberData[segIdx + 1], fiberData[segIdx + 2]);

                int nextSeg = (seg + 1) % SEGMENTS_PER_FIBER;
                int nextIdx = baseIdx + nextSeg * 4;
                vec3 b = vec3(fiberData[nextIdx], fiberData[nextIdx + 1], fiberData[nextIdx + 2]);

                float dist = distanceToSegment(rayPos, a, b);
                if (dist < minDist) {
                    minDist = dist;
                    minHue = fiberData[segIdx + 3];
                }
            }
        }

        // Solid tube density (nearest segment only)
        if (minDist < TUBE_RADIUS) {
            float density = (TUBE_RADIUS - minDist) / TUBE_RADIUS;
            float densitySq = density * density;
            float alpha = (1.0 - exp(-densitySq * 4.5)) * 0.85;
            vec3 fiberColor = hsv2rgb(vec3(minHue, 0.95, 0.95));
            color += fiberColor * alpha * (1.0 - accum);
            accum += alpha * (1.0 - accum);
        }

        // Glow halo at 1.5x radius
        float glowRadius = TUBE_RADIUS * 1.5;
        if (minDist < glowRadius) {
            float glowDist = minDist - TUBE_RADIUS;
            float glow = exp(-glowDist * 5.0) * 0.08;
            vec3 glowColor = hsv2rgb(vec3(minHue, 0.95, 0.95));
            color += glowColor * glow * (1.0 - accum);
            accum += glow * (1.0 - accum);
        }

        // Advance ray
        rayPos += rayDir * STEP_SIZE;
    }

    // Dark background
    color += vec3(0.02) * (1.0 - accum);

    gl_FragColor = vec4(color, 1.0);
}
