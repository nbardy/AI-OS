#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

const float PI = 3.14159265359;

// Distance from point p to line segment between a and b
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    vec3 ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    vec3 closest = a + t * ab;
    return length(p - closest);
}

// HSV to RGB conversion for vibrant colors
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    // Generate fiber data inside main (TIER 1)
    float fiberData[960];

    int idx = 0;
    float shellAngles[4] = float[4](PI/8.0, PI/4.0, 3.0*PI/8.0, PI/2.0);
    float rotations[2] = float[2](0.0, PI/2.0);

    // Generate 8 fibers (4 shells × 2 rotations)
    for (int shell = 0; shell < 4; shell++) {
        float shellEta = shellAngles[shell];
        float cosHalfEta = cos(shellEta * 0.5);
        float sinHalfEta = sin(shellEta * 0.5);

        for (int rot = 0; rot < 2; rot++) {
            float rotOffset = rotations[rot];

            // 40 segments per fiber
            for (int seg = 0; seg < 40; seg++) {
                float phi = (float(seg) / 40.0) * 2.0 * PI + rotOffset;
                float theta = phi;

                float cosTheta = cos(theta);
                float sinTheta = sin(theta);

                // Correct Hopf quaternion form (TIER 1)
                vec4 q = vec4(
                    cosHalfEta * cosTheta,
                    cosHalfEta * sinTheta,
                    sinHalfEta * cosTheta,
                    sinHalfEta * sinTheta
                );

                // Stereographic projection with singularity protection
                float denom = 1.0 / (1.0 - q.w + 0.35);
                vec3 p = vec3(q.x, q.y, q.z) * denom;

                // Post-projection scale to fill frame (TIER 1)
                p *= 0.85;

                fiberData[idx] = p.x;
                fiberData[idx + 1] = p.y;
                fiberData[idx + 2] = p.z;
                idx += 3;
            }
        }
    }

    // Camera setup - orbital at distance 4.5, elevation 1.5 (TIER 1 & TIER 2)
    float angle = u_time * 0.25;
    vec3 camPos = vec3(4.5 * cos(angle), 1.5, 4.5 * sin(angle));
    vec3 forward = normalize(-camPos);
    vec3 right = normalize(cross(forward, vec3(0.0, 1.0, 0.0)));
    vec3 up = cross(right, forward);

    // Aspect-corrected UV
    vec2 uv = (gl_FragCoord.xy / u_resolution.xy) * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);
    vec3 rayPos = camPos;

    // Ray marching state
    vec3 color = vec3(0.0);
    float opacity = 0.0;
    float stepSize = 0.09;
    float tubeRadius = 0.11;

    // Ray march: 100 steps (TIER 1: budget 100 × 0.09 = 9.0)
    for (int step = 0; step < 100; step++) {
        // Check all 8 fibers BEFORE stepping (TIER 1: check before step)
        for (int fiber = 0; fiber < 8; fiber++) {
            float minDist = 1000.0;

            // Check all 40 segments for this fiber
            for (int seg = 0; seg < 40; seg++) {
                int segIdx = (fiber * 40 + seg) * 3;
                int nextSegIdx = (fiber * 40 + ((seg + 1) % 40)) * 3;

                vec3 segStart = vec3(
                    fiberData[segIdx],
                    fiberData[segIdx + 1],
                    fiberData[segIdx + 2]
                );
                vec3 segEnd = vec3(
                    fiberData[nextSegIdx],
                    fiberData[nextSegIdx + 1],
                    fiberData[nextSegIdx + 2]
                );

                float dist = distanceToSegment(rayPos, segStart, segEnd);
                minDist = min(minDist, dist);
            }

            // Inside tube: add contribution (TIER 2)
            if (minDist < tubeRadius) {
                float normalizedDist = (tubeRadius - minDist) / tubeRadius;
                float density = normalizedDist * normalizedDist; // Quadratic
                float alpha = (1.0 - exp(-density * 4.5)) * 0.85; // Transparency factor

                // High saturation color (TIER 2: S=0.95, V=0.95)
                float hue = float(fiber) / 8.0;
                vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95));

                color += alpha * (1.0 - opacity) * fiberColor;
                opacity += alpha * (1.0 - opacity);
            }
            // Glow halo (TIER 2)
            else if (minDist < tubeRadius * 1.5) {
                float glowDist = minDist - tubeRadius;
                float glow = exp(-glowDist * 5.0) * 0.08;

                float hue = float(fiber) / 8.0;
                vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95));

                color += glow * (1.0 - opacity) * fiberColor;
            }
        }

        // NOW advance ray (TIER 1: step AFTER check)
        rayPos += rayDir * stepSize;

        if (opacity > 0.99) break;
    }

    // Dark background (TIER 2)
    vec3 finalColor = mix(vec3(0.02), color, opacity);

    gl_FragColor = vec4(finalColor, 1.0);
}
