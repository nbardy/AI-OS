#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

// HSV to RGB conversion
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// Distance from point to line segment
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 pa = p - a;
    vec3 ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h);
}

void main() {
    // Standard UV with aspect correction
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Camera setup: Y-offset orbit (NOT spherical coordinates)
    float angle = u_time * 0.25;
    float dist = 4.5;
    vec3 camera = vec3(dist * cos(angle), 1.5, dist * sin(angle));
    vec3 target = vec3(0.0, 0.0, 0.0);

    // Camera basis vectors
    vec3 forward = normalize(target - camera);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
    vec3 up = cross(forward, right);

    // Ray direction
    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);
    vec3 rayPos = camera;

    // Generate fiber data inside main() - MANDATORY
    // 8 fibers (4 shells × 2 rotations) × 40 segments × 3 coords = 960 floats
    float fiberData[960];
    int idx = 0;

    // 4 shell angles × 2 rotation offsets
    float shells[4];
    shells[0] = 3.14159265 / 8.0;      // π/8
    shells[1] = 3.14159265 / 4.0;      // π/4
    shells[2] = 3.14159265 * 3.0 / 8.0; // 3π/8
    shells[3] = 3.14159265 / 2.0;      // π/2

    float rotations[2];
    rotations[0] = 0.0;
    rotations[1] = 3.14159265 / 2.0;   // π/2

    // Generate all 8 fibers
    for (int shell = 0; shell < 4; shell++) {
        for (int rot = 0; rot < 2; rot++) {
            float phi = shells[shell];
            float rotation = rotations[rot];

            // Generate 40 segments per fiber
            for (int seg = 0; seg < 40; seg++) {
                float theta = rotation + float(seg) * 6.28318530 / 40.0;

                // MANDATORY Hopf quaternion formula
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

                // Direct S³→R³ stereographic projection with singularity protection
                vec3 p = q.xyz / (1.0 - q.w + 0.35);

                // Post-projection scale
                p *= 0.85;

                // Store in flat array
                fiberData[idx] = p.x; idx++;
                fiberData[idx] = p.y; idx++;
                fiberData[idx] = p.z; idx++;
            }
        }
    }

    // Ray marching parameters
    float tubeRadius = 0.11;
    float stepSize = 0.10;
    int maxSteps = 48;  // GPU budget: 48×8×40 = 15,360 iterations/pixel

    vec3 color = vec3(0.02);  // Dark background
    float totalAlpha = 0.0;

    // Ray march
    for (int step = 0; step < 48; step++) {
        if (step >= maxSteps) break;

        float minDistAll = 1000.0;
        int closestFiber = -1;

        // Check all 8 fibers
        for (int fiber = 0; fiber < 8; fiber++) {
            float minDist = 1000.0;

            // Check all 40 segments in this fiber
            for (int seg = 0; seg < 40; seg++) {
                int baseIdx = (fiber * 40 + seg) * 3;
                vec3 a = vec3(fiberData[baseIdx], fiberData[baseIdx+1], fiberData[baseIdx+2]);

                int nextSeg = (seg + 1) % 40;
                int nextIdx = (fiber * 40 + nextSeg) * 3;
                vec3 b = vec3(fiberData[nextIdx], fiberData[nextIdx+1], fiberData[nextIdx+2]);

                float d = distanceToSegment(rayPos, a, b);
                minDist = min(minDist, d);
            }

            if (minDist < minDistAll) {
                minDistAll = minDist;
                closestFiber = fiber;
            }
        }

        // Only closest fiber contributes (NEVER sum all)
        if (minDistAll < tubeRadius && closestFiber >= 0) {
            // Solid tube density (NOT hollow shell)
            float density = (tubeRadius - minDistAll) / tubeRadius;
            density = density * density;  // Quadratic

            // Fiber color (8 distinct hues)
            float hue = float(closestFiber) / 8.0;
            vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95));

            // Exponential alpha
            float alpha = 1.0 - exp(-density * 4.5);
            alpha *= 0.85;  // Transparency factor for overlap

            // Blend
            color = mix(color, fiberColor, alpha * (1.0 - totalAlpha));
            totalAlpha += alpha * (1.0 - totalAlpha);
        }

        // Glow halo at 1.5× tube radius
        float glowRadius = tubeRadius * 1.5;
        if (minDistAll < glowRadius) {
            float glowDist = minDistAll - tubeRadius;
            if (glowDist > 0.0) {
                float glowIntensity = exp(-glowDist * 5.0) * 0.08;
                float hue = float(closestFiber) / 8.0;
                vec3 glowColor = hsv2rgb(vec3(hue, 0.95, 0.95));
                color += glowColor * glowIntensity * (1.0 - totalAlpha);
            }
        }

        // Early exit if opaque
        if (totalAlpha > 0.99) break;

        // Advance ray (AFTER checks)
        rayPos += rayDir * stepSize;
    }

    gl_FragColor = vec4(color, 1.0);
}
