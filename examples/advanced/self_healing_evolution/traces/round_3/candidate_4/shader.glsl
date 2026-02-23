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
    vec3 ab = b - a;
    vec3 ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    vec3 closest = a + t * ab;
    return length(p - closest);
}

void main() {
    // Aspect-corrected UV (MANDATORY standard formula)
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Camera setup: orbital at distance 3.0, Y-offset 1.2, slow rotation
    float angle = u_time * 0.25;
    vec3 eye = vec3(3.0 * cos(angle), 1.2, 3.0 * sin(angle));
    vec3 center = vec3(0.0, 0.0, 0.0);
    vec3 up = vec3(0.0, 1.0, 0.0);

    // Camera basis
    vec3 forward = normalize(center - eye);
    vec3 right = normalize(cross(forward, up));
    vec3 newUp = cross(right, forward);

    // Ray through pixel
    vec3 rayDir = normalize(forward + uv.x * right + uv.y * newUp);
    vec3 rayPos = eye;

    // Dark background for maximum contrast
    vec3 bgColor = vec3(0.02);
    vec3 finalColor = bgColor;
    float finalAlpha = 0.0;

    // Generate 8 fiber geometries (960 floats total, at limit)
    // Family A (0-3): shell=π/4, rotations={0, π/2, π, 3π/2}, warm colors
    // Family B (4-7): shell=π/6, rotations={π/4, 3π/4, 5π/4, 7π/4}, cool colors

    float f0[120]; float f1[120]; float f2[120]; float f3[120];
    float f4[120]; float f5[120]; float f6[120]; float f7[120];

    // Shell angles
    float shells[2];
    shells[0] = 0.7854; // π/4 (Family A, inner)
    shells[1] = 0.5236; // π/6 (Family B, outer)

    // Rotation offsets
    float rotations[8];
    rotations[0] = 0.0;
    rotations[1] = 1.5708;      // π/2
    rotations[2] = 3.14159;     // π
    rotations[3] = 4.71239;     // 3π/2
    rotations[4] = 0.7854;      // π/4
    rotations[5] = 2.35619;     // 3π/4
    rotations[6] = 3.92699;     // 5π/4
    rotations[7] = 5.49779;     // 7π/4

    // Generate all 8 fibers
    for (int fiberIdx = 0; fiberIdx < 8; fiberIdx++) {
        float shell = (fiberIdx < 4) ? shells[0] : shells[1];
        float rotation = rotations[fiberIdx];

        for (int seg = 0; seg < 40; seg++) {
            float theta = float(seg) * 6.28318 / 40.0; // 2π/40

            // Hopf quaternion parameterization
            float phi_half = shell * 0.5;
            vec4 q = vec4(
                cos(phi_half) * cos(theta),
                cos(phi_half) * sin(theta),
                sin(phi_half) * cos(theta + rotation),
                sin(phi_half) * sin(theta + rotation)
            );

            // Stereographic projection S³→R³ with scale
            vec3 projected = q.xyz / (1.0 - q.w + 0.15) * 1.5;

            // Store in appropriate array
            int idx = seg * 3;
            if (fiberIdx == 0) {
                f0[idx] = projected.x; f0[idx+1] = projected.y; f0[idx+2] = projected.z;
            } else if (fiberIdx == 1) {
                f1[idx] = projected.x; f1[idx+1] = projected.y; f1[idx+2] = projected.z;
            } else if (fiberIdx == 2) {
                f2[idx] = projected.x; f2[idx+1] = projected.y; f2[idx+2] = projected.z;
            } else if (fiberIdx == 3) {
                f3[idx] = projected.x; f3[idx+1] = projected.y; f3[idx+2] = projected.z;
            } else if (fiberIdx == 4) {
                f4[idx] = projected.x; f4[idx+1] = projected.y; f4[idx+2] = projected.z;
            } else if (fiberIdx == 5) {
                f5[idx] = projected.x; f5[idx+1] = projected.y; f5[idx+2] = projected.z;
            } else if (fiberIdx == 6) {
                f6[idx] = projected.x; f6[idx+1] = projected.y; f6[idx+2] = projected.z;
            } else if (fiberIdx == 7) {
                f7[idx] = projected.x; f7[idx+1] = projected.y; f7[idx+2] = projected.z;
            }
        }
    }

    // Ray march: 46 steps, step size 0.10
    // Budget: 46 × 8 × 40 = 14,720 iterations < 15,000 limit
    float tubeRadius = 0.05;
    float stepSize = 0.10;
    vec3 glowAccum = vec3(0.0);

    for (int step = 0; step < 46; step++) {
        float globalMinDist = 1e10;
        int nearestFiber = 0;
        float depth = float(step) * stepSize;

        // Check distance to all 8 fibers at current rayPos (BEFORE advancing)
        for (int fiberIdx = 0; fiberIdx < 8; fiberIdx++) {
            float fiberMinDist = 1e10;

            // Check all 40 segments of this fiber
            for (int seg = 0; seg < 40; seg++) {
                int idx = seg * 3;
                int nextIdx = ((seg + 1) % 40) * 3;

                vec3 a, b;
                // Load segment endpoints
                if (fiberIdx == 0) {
                    a = vec3(f0[idx], f0[idx+1], f0[idx+2]);
                    b = vec3(f0[nextIdx], f0[nextIdx+1], f0[nextIdx+2]);
                } else if (fiberIdx == 1) {
                    a = vec3(f1[idx], f1[idx+1], f1[idx+2]);
                    b = vec3(f1[nextIdx], f1[nextIdx+1], f1[nextIdx+2]);
                } else if (fiberIdx == 2) {
                    a = vec3(f2[idx], f2[idx+1], f2[idx+2]);
                    b = vec3(f2[nextIdx], f2[nextIdx+1], f2[nextIdx+2]);
                } else if (fiberIdx == 3) {
                    a = vec3(f3[idx], f3[idx+1], f3[idx+2]);
                    b = vec3(f3[nextIdx], f3[nextIdx+1], f3[nextIdx+2]);
                } else if (fiberIdx == 4) {
                    a = vec3(f4[idx], f4[idx+1], f4[idx+2]);
                    b = vec3(f4[nextIdx], f4[nextIdx+1], f4[nextIdx+2]);
                } else if (fiberIdx == 5) {
                    a = vec3(f5[idx], f5[idx+1], f5[idx+2]);
                    b = vec3(f5[nextIdx], f5[nextIdx+1], f5[nextIdx+2]);
                } else if (fiberIdx == 6) {
                    a = vec3(f6[idx], f6[idx+1], f6[idx+2]);
                    b = vec3(f6[nextIdx], f6[nextIdx+1], f6[nextIdx+2]);
                } else if (fiberIdx == 7) {
                    a = vec3(f7[idx], f7[idx+1], f7[idx+2]);
                    b = vec3(f7[nextIdx], f7[nextIdx+1], f7[nextIdx+2]);
                }

                float dist = distanceToSegment(rayPos, a, b);
                fiberMinDist = min(fiberMinDist, dist);
            }

            // Track global minimum across all fibers
            if (fiberMinDist < globalMinDist) {
                globalMinDist = fiberMinDist;
                nearestFiber = fiberIdx;
            }
        }

        // Render nearest fiber only (solid tube density)
        if (globalMinDist < tubeRadius) {
            float d = max(0.0, (tubeRadius - globalMinDist) / tubeRadius);
            d = d * d; // Quadratic density

            // Color by fiber family
            vec3 color;
            if (nearestFiber < 4) {
                // Family A: warm ruby-coral (hue 0.02-0.11)
                float hue = 0.02 + float(nearestFiber) * 0.03;
                color = hsv2rgb(vec3(hue, 0.95, 0.95));
            } else {
                // Family B: cool teal-sapphire (hue 0.52-0.61)
                float hue = 0.52 + float(nearestFiber - 4) * 0.03;
                color = hsv2rgb(vec3(hue, 0.95, 0.95));
            }

            // Gentle depth brightness
            color *= mix(0.85, 1.0, exp(-0.03 * depth));

            // Exponential alpha
            float alpha = 1.0 - exp(-d * 4.5);

            // Accumulate with transparency
            finalColor += color * alpha * (1.0 - finalAlpha);
            finalAlpha += alpha * (1.0 - finalAlpha) * 0.85;
        }

        // Glow halo at 1.5× tube radius
        if (globalMinDist >= tubeRadius && globalMinDist < tubeRadius * 1.5) {
            float glowDist = globalMinDist - tubeRadius;
            float glowIntensity = exp(-glowDist * 5.0) * 0.08;

            vec3 glowColor;
            if (nearestFiber < 4) {
                float hue = 0.02 + float(nearestFiber) * 0.03;
                glowColor = hsv2rgb(vec3(hue, 0.95, 0.95));
            } else {
                float hue = 0.52 + float(nearestFiber - 4) * 0.03;
                glowColor = hsv2rgb(vec3(hue, 0.95, 0.95));
            }

            glowAccum += glowColor * glowIntensity * (1.0 - finalAlpha);
        }

        // Early exit if opaque
        if (finalAlpha > 0.98) break;

        // Advance ray (AFTER checking)
        rayPos += rayDir * stepSize;
    }

    // Final composite
    finalColor = mix(bgColor, finalColor, finalAlpha);
    finalColor += glowAccum;

    gl_FragColor = vec4(finalColor, 1.0);
}
