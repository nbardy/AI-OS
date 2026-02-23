#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

// Distance from point to line segment
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    vec3 ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    return length(ap - ab * t);
}

// HSV to RGB conversion
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    // Fiber data array - MUST be inside main()
    float fiberData[960]; // 8 fibers × 40 points × 3 coords

    // Configuration
    float shells[4];
    shells[0] = 0.39269908; // π/8
    shells[1] = 0.78539816; // π/4
    shells[2] = 1.17809725; // 3π/8
    shells[3] = 1.57079633; // π/2

    float rotations[2];
    rotations[0] = 0.0;
    rotations[1] = 1.57079633; // π/2

    int segments = 40;
    float tubeRadius = 0.11;
    float postScale = 0.85;
    float singularity = 0.35;

    // Generate fiber geometry
    int idx = 0;
    for (int shellIdx = 0; shellIdx < 4; shellIdx++) {
        for (int rotIdx = 0; rotIdx < 2; rotIdx++) {
            float phi = shells[shellIdx];
            float rotation = rotations[rotIdx];
            float cosPhi2 = cos(phi * 0.5);
            float sinPhi2 = sin(phi * 0.5);

            for (int seg = 0; seg < 40; seg++) {
                float theta = rotation + float(seg) / 40.0 * 6.28318531;
                float cosTheta = cos(theta);
                float sinTheta = sin(theta);

                // Correct Hopf quaternion
                vec4 q = vec4(
                    cosPhi2 * cosTheta,
                    cosPhi2 * sinTheta,
                    sinPhi2 * cosTheta,
                    sinPhi2 * sinTheta
                );

                // Stereographic projection with singularity protection
                vec3 p = vec3(2.0 * q.x, 2.0 * q.y, 2.0 * q.z) / (1.0 - q.w + singularity);
                p *= postScale;

                fiberData[idx++] = p.x;
                fiberData[idx++] = p.y;
                fiberData[idx++] = p.z;
            }
        }
    }

    // Camera setup - Y-offset orbit (NOT spherical elevation angle)
    float angle = u_time * 0.25;
    float camDist = 4.5;
    float camY = 1.5; // This is a POSITION, not an angle
    vec3 camPos = vec3(camDist * cos(angle), camY, camDist * sin(angle));
    vec3 camTarget = vec3(0.0);

    // Camera basis
    vec3 camForward = normalize(camTarget - camPos);
    vec3 camRight = normalize(cross(camForward, vec3(0.0, 1.0, 0.0)));
    vec3 camUp = cross(camRight, camForward);

    // Ray setup
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;
    vec3 rayDir = normalize(camForward + uv.x * camRight + uv.y * camUp);
    vec3 rayPos = camPos;

    // Ray marching
    float maxDist = 12.0;
    float stepSize = 0.15;
    int maxSteps = 64;

    vec3 finalColor = vec3(0.0);
    float finalAlpha = 0.0;

    for (int step = 0; step < 64; step++) {
        if (step >= maxSteps || finalAlpha > 0.98) break;

        // Find minimum distance to all fiber segments
        float minDist = 1000.0;
        int closestFiber = 0;

        for (int fiber = 0; fiber < 8; fiber++) {
            for (int seg = 0; seg < 40; seg++) {
                int baseIdx = (fiber * 40 + seg) * 3;
                int nextSeg = (seg + 1) % 40;
                int nextIdx = (fiber * 40 + nextSeg) * 3;

                vec3 a = vec3(fiberData[baseIdx], fiberData[baseIdx + 1], fiberData[baseIdx + 2]);
                vec3 b = vec3(fiberData[nextIdx], fiberData[nextIdx + 1], fiberData[nextIdx + 2]);

                float dist = distanceToSegment(rayPos, a, b);
                if (dist < minDist) {
                    minDist = dist;
                    closestFiber = fiber;
                }
            }
        }

        // Tube SDF - convert to unsigned distance
        float sdf = abs(minDist - tubeRadius);

        // Volumetric rendering
        float density = sdf * sdf; // Quadratic falloff
        float alpha = 1.0 - exp(-density * 4.5); // Exponential accumulation
        alpha *= 0.85; // Transparency for fiber overlap

        // Color from fiber ID
        vec3 fiberColor = hsv2rgb(vec3(float(closestFiber) / 8.0, 0.95, 0.95));

        // Add glow halo at 1.5x tube radius
        float glowDist = max(0.0, minDist - tubeRadius * 1.5);
        float glow = exp(-glowDist * 5.0) * 0.08;

        // Accumulate color
        float weight = alpha * (1.0 - finalAlpha);
        finalColor += fiberColor * weight;
        finalColor += fiberColor * glow * (1.0 - finalAlpha);
        finalAlpha += weight;

        // Advance ray - AFTER checking distance
        rayPos += rayDir * stepSize;
        if (length(rayPos - camPos) > maxDist) break;
    }

    // Dark background for contrast
    vec3 backgroundColor = vec3(0.02);
    finalColor = mix(backgroundColor, finalColor, finalAlpha);

    gl_FragColor = vec4(finalColor, 1.0);
}
