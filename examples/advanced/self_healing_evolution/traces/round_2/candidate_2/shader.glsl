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

// LookAt matrix
mat3 lookAt(vec3 eye, vec3 target, vec3 up) {
    vec3 z = normalize(target - eye);
    vec3 x = normalize(cross(z, up));
    vec3 y = cross(x, z);
    return mat3(x, y, z);
}

void main() {
    // Standard UV formula
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Y-offset orbit camera (NOT spherical coordinates)
    float angle = u_time * 0.25;
    float camDist = 4.5;
    vec3 eye = vec3(camDist * cos(angle), 1.5, camDist * sin(angle));
    vec3 target = vec3(0.0, 0.0, 0.0);

    mat3 cam = lookAt(eye, target, vec3(0.0, 1.0, 0.0));
    vec3 rayDir = normalize(cam * vec3(uv, 1.0));

    // Generate fiber geometry - flat array inside main()
    float fiberData[960]; // 8 fibers × 40 segments × 3 coords

    int idx = 0;
    float shells[4];
    shells[0] = 3.14159265 / 8.0;
    shells[1] = 3.14159265 / 4.0;
    shells[2] = 3.0 * 3.14159265 / 8.0;
    shells[3] = 3.14159265 / 2.0;

    float rotations[2];
    rotations[0] = 0.0;
    rotations[1] = 3.14159265 / 2.0;

    for (int shellIdx = 0; shellIdx < 4; shellIdx++) {
        for (int rotIdx = 0; rotIdx < 2; rotIdx++) {
            float phi = shells[shellIdx];
            float baseRot = rotations[rotIdx];

            for (int seg = 0; seg < 40; seg++) {
                float theta = baseRot + (float(seg) / 40.0) * 2.0 * 3.14159265;

                // Correct Hopf quaternion
                float cosPhi2 = cos(phi / 2.0);
                float sinPhi2 = sin(phi / 2.0);
                vec4 q = vec4(
                    cosPhi2 * cos(theta),
                    cosPhi2 * sin(theta),
                    sinPhi2 * cos(theta),
                    sinPhi2 * sin(theta)
                );

                // Direct S³ stereographic projection
                vec3 pos3d = q.xyz / (1.0 - q.w + 0.35);

                // Post-projection scale
                pos3d *= 0.85;

                fiberData[idx] = pos3d.x;
                fiberData[idx + 1] = pos3d.y;
                fiberData[idx + 2] = pos3d.z;
                idx += 3;
            }
        }
    }

    // Ray marching with volume rendering
    vec3 accum = vec3(0.0);
    float transmit = 1.0;
    vec3 rayPos = eye;
    float stepSize = 0.08;
    float tubeRadius = 0.11;

    for (int step = 0; step < 64; step++) {
        // Check distances at current position BEFORE advancing

        for (int fiber = 0; fiber < 8; fiber++) {
            int baseIdx = fiber * 120; // 40 segments × 3 coords

            float minDist = 1000.0;

            // Find closest segment in this fiber
            for (int seg = 0; seg < 40; seg++) {
                int i0 = baseIdx + seg * 3;
                int i1 = baseIdx + ((seg + 1) % 40) * 3;

                vec3 p0 = vec3(fiberData[i0], fiberData[i0 + 1], fiberData[i0 + 2]);
                vec3 p1 = vec3(fiberData[i1], fiberData[i1 + 1], fiberData[i1 + 2]);

                float d = distanceToSegment(rayPos, p0, p1);
                minDist = min(minDist, d);
            }

            // Solid tube density (NOT hollow shell)
            if (minDist < tubeRadius) {
                float density = (tubeRadius - minDist) / tubeRadius;
                density = density * density; // Quadratic
                float alpha = 1.0 - exp(-density * 4.5);

                // Per-fiber HSV color
                float hue = float(fiber) / 8.0;
                vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95));

                // Accumulate with transparency
                accum += fiberColor * alpha * transmit * 0.85;
                transmit *= (1.0 - alpha * 0.85);
            }

            // Glow at 1.5x radius
            float glowRadius = tubeRadius * 1.5;
            if (minDist >= tubeRadius && minDist < glowRadius) {
                float glowDist = minDist - tubeRadius;
                float glowAlpha = exp(-glowDist * 5.0) * 0.08;

                float hue = float(fiber) / 8.0;
                vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95));

                accum += fiberColor * glowAlpha * transmit;
                transmit *= (1.0 - glowAlpha);
            }
        }

        // Early exit
        if (transmit < 0.01) break;

        // THEN advance ray position
        rayPos += rayDir * stepSize;
    }

    // Composite over dark background
    vec3 background = vec3(0.02);
    vec3 finalColor = background * transmit + accum;

    gl_FragColor = vec4(finalColor, 1.0);
}
