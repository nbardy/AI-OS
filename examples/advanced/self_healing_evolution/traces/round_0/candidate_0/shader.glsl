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
    vec2 uv = (gl_FragCoord.xy / u_resolution.xy) * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    // Camera setup - orbital with elevation
    float camAngle = u_time * 0.25;
    float camDist = 4.5;
    float camElev = 1.5;
    vec3 camPos = vec3(
        camDist * cos(camAngle),
        camElev,
        camDist * sin(camAngle)
    );

    vec3 target = vec3(0.0, 0.0, 0.0);
    vec3 forward = normalize(target - camPos);
    vec3 worldUp = vec3(0.0, 1.0, 0.0);
    vec3 right = normalize(cross(forward, worldUp));
    vec3 up = cross(right, forward);

    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);
    vec3 rayPos = camPos;

    // Ray marching parameters
    float stepSize = 0.09;
    int maxSteps = 100;
    float tubeRadius = 0.13;

    vec3 color = vec3(0.02);
    float opacity = 0.0;

    // Generate 6 fibers: 3 shells × 2 rotations
    // 40 segments each = 6 * 40 * 3 = 720 floats
    float fiberData[720];

    int idx = 0;
    float shellAngles[3];
    shellAngles[0] = 0.523599;  // π/6
    shellAngles[1] = 1.047198;  // π/3
    shellAngles[2] = 1.570796;  // π/2

    float rotations[2];
    rotations[0] = 0.0;
    rotations[1] = 3.141593;  // π

    // Pre-compute all fiber points
    for (int s = 0; s < 3; s++) {
        float phi = shellAngles[s];
        float cosHalfPhi = cos(phi * 0.5);
        float sinHalfPhi = sin(phi * 0.5);

        for (int r = 0; r < 2; r++) {
            float rotOffset = rotations[r];

            for (int i = 0; i < 40; i++) {
                float t = float(i) / 40.0;
                float theta = t * 6.283185 + rotOffset;

                // Hopf fibration quaternion (TIER 1 MANDATORY FORM)
                vec4 q = vec4(
                    cosHalfPhi * cos(theta),
                    cosHalfPhi * sin(theta),
                    sinHalfPhi * cos(theta),
                    sinHalfPhi * sin(theta)
                );

                // Stereographic projection with singularity protection
                float denom = 1.0 / (1.0 - q.w + 0.35);
                vec3 p = vec3(q.x, q.y, q.z) * denom;

                // Post-projection scale (TIER 1)
                p *= 0.85;

                fiberData[idx] = p.x;
                fiberData[idx + 1] = p.y;
                fiberData[idx + 2] = p.z;
                idx += 3;
            }
        }
    }

    // Ray march
    for (int step = 0; step < 100; step++) {
        if (step >= maxSteps) break;
        if (opacity > 0.99) break;

        // Check all 6 fibers
        float minDist = 999.0;
        int hitFiber = -1;

        for (int f = 0; f < 6; f++) {
            int baseIdx = f * 120;  // 40 segments × 3 coords

            // Check all 40 segments
            for (int i = 0; i < 40; i++) {
                int i0 = baseIdx + i * 3;
                int i1 = baseIdx + ((i + 1) % 40) * 3;

                vec3 p0 = vec3(fiberData[i0], fiberData[i0 + 1], fiberData[i0 + 2]);
                vec3 p1 = vec3(fiberData[i1], fiberData[i1 + 1], fiberData[i1 + 2]);

                float dist = distanceToSegment(rayPos, p0, p1);

                if (dist < minDist) {
                    minDist = dist;
                    hitFiber = f;
                }
            }
        }

        // Render tube
        if (minDist < tubeRadius) {
            float normalizedDist = minDist / tubeRadius;
            float d = 1.0 - normalizedDist;
            float density = d * d;
            float alpha = 1.0 - exp(-density * 4.5);
            alpha *= 0.85;  // TIER 2: transparency for layering

            // Color with flow animation (TIER 3 experiment)
            float baseHue = float(hitFiber) / 6.0;
            float hue = fract(baseHue + u_time * 0.1);
            vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95));

            color = mix(color, fiberColor, alpha * (1.0 - opacity));
            opacity += alpha * (1.0 - opacity);
        }
        else if (minDist < tubeRadius * 1.5) {
            // TIER 2: Glow halo effect
            float glowDist = (minDist - tubeRadius) / (tubeRadius * 0.5);
            float baseHue = float(hitFiber) / 6.0;
            float hue = fract(baseHue + u_time * 0.1);
            vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95));

            float glowAlpha = exp(-glowDist * 5.0) * 0.08;
            color += fiberColor * glowAlpha * (1.0 - opacity);
        }

        // TIER 1: Step AFTER checking (Candidate 1 pattern)
        rayPos += rayDir * stepSize;
    }

    gl_FragColor = vec4(color, 1.0);
}
