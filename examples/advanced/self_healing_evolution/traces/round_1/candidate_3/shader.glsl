#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

// Distance from point to line segment
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    float t = clamp(dot(p - a, ab) / dot(ab, ab), 0.0, 1.0);
    return length(p - (a + t * ab));
}

// HSV to RGB conversion
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    // Aspect-correct UV coordinates
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Generate 6 Hopf fibers in main (flat array: 6 fibers × 40 segments × 3 coords = 720 floats)
    float fiberData[720];

    // Two shell angles, three longitude rotations
    float shells[2];
    shells[0] = 0.7854; // pi/4
    shells[1] = 1.1781; // 3pi/8

    float longitudes[3];
    longitudes[0] = 0.0;
    longitudes[1] = 2.0944; // 2pi/3
    longitudes[2] = 4.1888; // 4pi/3

    // Fiber arrangement: 6 fibers as 3 longitude groups × 2 shells
    // Fiber 0: shell 0, long 0
    // Fiber 1: shell 1, long 0
    // Fiber 2: shell 0, long 1
    // Fiber 3: shell 1, long 1
    // Fiber 4: shell 0, long 2
    // Fiber 5: shell 1, long 2

    for (int f = 0; f < 6; f++) {
        int longIdx = f / 2;
        int shellIdx = f - longIdx * 2; // f % 2

        float phi = shells[shellIdx];
        float xi1 = longitudes[longIdx];

        float cph2 = cos(phi * 0.5);
        float sph2 = sin(phi * 0.5);

        for (int seg = 0; seg < 40; seg++) {
            float theta = float(seg) / 40.0 * 6.2832;
            float ct = cos(theta);
            float st = sin(theta);
            float ctx = cos(theta + xi1);
            float stx = sin(theta + xi1);

            // Hopf quaternion (MANDATORY form)
            vec4 q = vec4(cph2 * ct, cph2 * st, sph2 * ctx, sph2 * stx);

            // Stereographic projection with singularity protection
            vec3 p = q.xyz / (1.0 - q.w + 0.35);

            // Post-projection scale (MANDATORY 0.80-0.90)
            p *= 0.85;

            int idx = f * 120 + seg * 3;
            fiberData[idx] = p.x;
            fiberData[idx + 1] = p.y;
            fiberData[idx + 2] = p.z;
        }
    }

    // Camera setup: Y-offset orbit (MANDATORY, NOT spherical elevation)
    float angle = u_time * 0.25;
    float camDist = 4.5;
    vec3 camPos = vec3(camDist * cos(angle), 1.5, camDist * sin(angle));

    // Ray direction (look at origin)
    vec3 lookDir = normalize(-camPos);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), lookDir));
    vec3 up = cross(lookDir, right);
    vec3 rayDir = normalize(lookDir + uv.x * right + uv.y * up);

    // Ray marching with CHECK-before-STEP (MANDATORY)
    vec3 rayPos = camPos;
    float totalDensity = 0.0;
    vec3 colorAccum = vec3(0.0);
    float glowAccum = 0.0;

    // Triadic color palette
    vec3 fiberColors[6];
    fiberColors[0] = hsv2rgb(vec3(0.02, 0.95, 0.95));  // coral-red
    fiberColors[1] = hsv2rgb(vec3(0.02, 0.95, 0.95));
    fiberColors[2] = hsv2rgb(vec3(0.35, 0.95, 0.95));  // emerald-green
    fiberColors[3] = hsv2rgb(vec3(0.35, 0.95, 0.95));
    fiberColors[4] = hsv2rgb(vec3(0.72, 0.95, 0.95));  // violet-blue
    fiberColors[5] = hsv2rgb(vec3(0.72, 0.95, 0.95));

    for (int step = 0; step < 64; step++) {
        // CHECK distances at current rayPos FIRST (MANDATORY)
        float minDist = 10.0;

        for (int f = 0; f < 6; f++) {
            for (int seg = 0; seg < 40; seg++) {
                int idx = f * 120 + seg * 3;
                vec3 segA = vec3(fiberData[idx], fiberData[idx + 1], fiberData[idx + 2]);

                int nextSeg = seg + 1;
                if (nextSeg >= 40) nextSeg = 0; // Wrap to close the fiber

                int nextIdx = f * 120 + nextSeg * 3;
                vec3 segB = vec3(fiberData[nextIdx], fiberData[nextIdx + 1], fiberData[nextIdx + 2]);

                // Unsigned distance (MANDATORY)
                float dist = abs(distanceToSegment(rayPos, segA, segB));
                minDist = min(minDist, dist);

                // Tube radius 0.11 (PROVEN range 0.08-0.15)
                float tubeRadius = 0.11;

                // Phase-shifted glow (NOVEL feature)
                float thetaParam = float(seg) / 40.0 * 6.2832;
                float pulse = 0.7 + 0.3 * sin(thetaParam + float(f) * 1.047 + u_time * 2.0);

                // Quadratic density with pulse modulation
                float contrib = exp(-dist * dist * 50.0) * pulse;
                totalDensity += contrib;
                colorAccum += fiberColors[f] * contrib;

                // Glow halo at 1.5x tube radius (PROVEN)
                float glowRadius = tubeRadius * 1.5;
                if (dist < glowRadius) {
                    glowAccum += exp(-dist * 5.0) * 0.08 * pulse;
                }
            }
        }

        // THEN advance ray (check-before-step MANDATORY)
        rayPos += rayDir * 0.12;

        // Early exit if far from all geometry
        if (minDist > 2.0) break;
    }

    // Exponential alpha with transparency factor (PROVEN)
    float alpha = 1.0 - exp(-totalDensity * 4.5);
    alpha *= 0.85;

    // Normalize color accumulation
    vec3 finalColor = colorAccum / max(totalDensity, 0.001);

    // Add glow
    finalColor += vec3(glowAccum);

    // Dark background (PROVEN)
    vec3 bgColor = vec3(0.01, 0.01, 0.02);
    vec3 outputColor = mix(bgColor, finalColor, alpha);

    gl_FragColor = vec4(outputColor, 1.0);
}
