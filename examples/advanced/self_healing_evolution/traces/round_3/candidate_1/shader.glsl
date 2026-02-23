#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

// Constants
const float TUBE_RADIUS = 0.06;
const float EPSILON = 0.15;
const float POST_PROJ_SCALE = 1.5;
const float CAMERA_DIST = 3.0;
const float CAMERA_Y = 1.5;
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
                float theta = rotation + (float(seg) / float(SEGMENTS_PER_FIBER)) * 2.0 * PI;

                // Hopf fibration parametrization in S³
                float cos_phi_2 = cos(phi / 2.0);
                float sin_phi_2 = sin(phi / 2.0);
                float cos_theta = cos(theta);
                float sin_theta = sin(theta);

                vec4 q = vec4(
                    cos_phi_2 * cos_theta,
                    cos_phi_2 * sin_theta,
                    sin_phi_2 * cos_theta,
                    sin_phi_2 * sin_theta
                );

                // Stereographic projection S³ → R³
                vec3 projected = q.xyz / (1.0 - q.w + EPSILON);

                // Scale up
                projected *= POST_PROJ_SCALE;

                // Store in flat array
                fiberData[idx] = projected.x;
                fiberData[idx + 1] = projected.y;
                fiberData[idx + 2] = projected.z;
                fiberData[idx + 3] = hue;
                idx += 4;
            }
        }
    }

    // Camera setup (Y-offset orbit)
    float angle = u_time * CAMERA_SPEED;
    vec3 camPos = vec3(CAMERA_DIST * cos(angle), CAMERA_Y, CAMERA_DIST * sin(angle));
    vec3 camTarget = vec3(0.0, 0.0, 0.0);
    vec3 camUp = vec3(0.0, 1.0, 0.0);

    // View matrix
    vec3 camZ = normalize(camTarget - camPos);
    vec3 camX = normalize(cross(camUp, camZ));
    vec3 camY = cross(camZ, camX);

    // Ray direction
    vec3 rayDir = normalize(uv.x * camX + uv.y * camY + 2.0 * camZ);
    vec3 rayPos = camPos;

    // Ray marching
    vec3 accumulatedColor = vec3(0.0);
    float accumulatedAlpha = 0.0;

    for (int step = 0; step < RAY_STEPS; step++) {
        float minDist = 1000.0;
        float closestHue = 0.0;

        // Check distance to all fiber segments
        for (int fiberIdx = 0; fiberIdx < NUM_FIBERS; fiberIdx++) {
            int baseIdx = fiberIdx * SEGMENTS_PER_FIBER * 4;

            for (int seg = 0; seg < SEGMENTS_PER_FIBER; seg++) {
                int segIdx = baseIdx + seg * 4;
                int nextSeg = (seg + 1) % SEGMENTS_PER_FIBER;
                int nextIdx = baseIdx + nextSeg * 4;

                vec3 segStart = vec3(
                    fiberData[segIdx],
                    fiberData[segIdx + 1],
                    fiberData[segIdx + 2]
                );
                vec3 segEnd = vec3(
                    fiberData[nextIdx],
                    fiberData[nextIdx + 1],
                    fiberData[nextIdx + 2]
                );

                float dist = distanceToSegment(rayPos, segStart, segEnd);

                if (dist < minDist) {
                    minDist = dist;
                    closestHue = fiberData[segIdx + 3];
                }
            }
        }

        // Solid tube density (only if within tube radius)
        if (minDist < TUBE_RADIUS) {
            float density = (TUBE_RADIUS - minDist) / TUBE_RADIUS;
            density = density * density; // Quadratic

            // Exponential alpha
            float alpha = (1.0 - exp(-density * 4.5)) * 0.85;

            // Color from hue
            vec3 fiberColor = hsv2rgb(vec3(closestHue, 0.95, 0.95));

            // Accumulate with transparency
            accumulatedColor += fiberColor * alpha * (1.0 - accumulatedAlpha);
            accumulatedAlpha += alpha * (1.0 - accumulatedAlpha);
        }

        // Glow halo at 1.5× tube radius
        float glowRadius = TUBE_RADIUS * 1.5;
        if (minDist < glowRadius && minDist >= TUBE_RADIUS) {
            float glowDist = (minDist - TUBE_RADIUS) / (glowRadius - TUBE_RADIUS);
            float glowIntensity = exp(-glowDist * 5.0) * 0.08;

            vec3 glowColor = hsv2rgb(vec3(closestHue, 0.95, 0.95));
            accumulatedColor += glowColor * glowIntensity * (1.0 - accumulatedAlpha);
        }

        // Early exit if fully opaque
        if (accumulatedAlpha > 0.99) break;

        // Advance ray
        rayPos += rayDir * STEP_SIZE;
    }

    // Blend with dark background
    vec3 backgroundColor = vec3(0.02);
    vec3 finalColor = mix(backgroundColor, accumulatedColor, accumulatedAlpha);

    gl_FragColor = vec4(finalColor, 1.0);
}
