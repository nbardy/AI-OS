#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

// Distance from point p to line segment [a, b]
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    vec3 ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    vec3 closest = a + t * ab;
    return length(p - closest);
}

// HSV to RGB conversion
vec3 hsv2rgb(float h, float s, float v) {
    float c = v * s;
    float x = c * (1.0 - abs(mod(h * 6.0, 2.0) - 1.0));
    float m = v - c;
    vec3 rgb;
    if (h < 1.0/6.0) rgb = vec3(c, x, 0.0);
    else if (h < 2.0/6.0) rgb = vec3(x, c, 0.0);
    else if (h < 3.0/6.0) rgb = vec3(0.0, c, x);
    else if (h < 4.0/6.0) rgb = vec3(0.0, x, c);
    else if (h < 5.0/6.0) rgb = vec3(x, 0.0, c);
    else rgb = vec3(c, 0.0, x);
    return rgb + m;
}

void main() {
    // Fiber data: 8 fibers × 40 segments × 3 coords = 960 floats
    float fiberData[960];

    // Generate 8 Hopf fibers (4 shells × 2 rotations)
    float shellAngles[4];
    shellAngles[0] = 3.14159265 / 8.0;      // π/8
    shellAngles[1] = 3.14159265 / 4.0;      // π/4
    shellAngles[2] = 3.14159265 * 3.0 / 8.0; // 3π/8
    shellAngles[3] = 3.14159265 / 2.0;      // π/2

    float rotations[2];
    rotations[0] = 0.0;
    rotations[1] = 3.14159265 / 2.0; // π/2

    int fiberIdx = 0;
    for (int shell = 0; shell < 4; shell++) {
        for (int rot = 0; rot < 2; rot++) {
            float phi = shellAngles[shell];
            float rotation = rotations[rot];
            float cosHalfPhi = cos(phi * 0.5);
            float sinHalfPhi = sin(phi * 0.5);

            int baseIndex = fiberIdx * 120; // 40 segments × 3 coords

            for (int seg = 0; seg < 40; seg++) {
                float theta = 2.0 * 3.14159265 * float(seg) / 40.0 + rotation;
                float cosTheta = cos(theta);
                float sinTheta = sin(theta);

                // PROVEN quaternion form: all components use theta consistently
                vec4 q = vec4(
                    cosHalfPhi * cosTheta,  // x
                    cosHalfPhi * sinTheta,  // y
                    sinHalfPhi * cosTheta,  // z
                    sinHalfPhi * sinTheta   // w
                );

                // Stereographic projection with singularity protection
                float denom = 1.0 / (1.0 - q.w + 0.35);
                vec3 p = vec3(q.x, q.y, q.z) * denom;

                // Post-projection scale to fill frame
                p *= 0.85;

                // Store in array
                int idx = baseIndex + seg * 3;
                fiberData[idx] = p.x;
                fiberData[idx + 1] = p.y;
                fiberData[idx + 2] = p.z;
            }

            fiberIdx++;
        }
    }

    // Camera setup
    float angle = u_time * 0.25;
    float camDist = 4.5;
    float elevation = 1.5;
    vec3 camPos = vec3(
        camDist * cos(angle) * cos(elevation),
        camDist * sin(elevation),
        camDist * sin(angle) * cos(elevation)
    );

    vec3 forward = normalize(-camPos);
    vec3 right = normalize(cross(forward, vec3(0.0, 1.0, 0.0)));
    vec3 up = cross(right, forward);

    // Ray direction
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;
    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);

    // Ray marching
    vec3 rayPos = camPos;
    vec3 finalColor = vec3(0.0);
    float opacity = 0.0;
    float tubeRadius = 0.11;
    float stepSize = 0.09;

    for (int step = 0; step < 100; step++) {
        // CRITICAL: Check distances FIRST at current rayPos
        float minDist = 1000.0;
        int hitFiber = -1;

        for (int fiber = 0; fiber < 8; fiber++) {
            int baseIdx = fiber * 120;

            for (int seg = 0; seg < 40; seg++) {
                int idx = baseIdx + seg * 3;
                vec3 p0 = vec3(fiberData[idx], fiberData[idx + 1], fiberData[idx + 2]);

                // Get next segment (wrap around)
                int nextSeg = seg + 1;
                if (nextSeg >= 40) nextSeg = 0;
                int nextIdx = baseIdx + nextSeg * 3;
                vec3 p1 = vec3(fiberData[nextIdx], fiberData[nextIdx + 1], fiberData[nextIdx + 2]);

                float dist = distanceToSegment(rayPos, p0, p1);
                if (dist < minDist) {
                    minDist = dist;
                    hitFiber = fiber;
                }
            }
        }

        // Render tube
        if (minDist < tubeRadius) {
            float normalizedDist = (tubeRadius - minDist) / tubeRadius;
            float density = normalizedDist * normalizedDist;
            float alpha = 1.0 - exp(-density * 4.5);

            // TIER 2: Transparency factor
            alpha *= 0.85;

            // Color based on fiber index
            float hue = float(hitFiber) / 8.0;
            vec3 color = hsv2rgb(hue, 0.95, 0.95);

            // Composite
            finalColor += color * alpha * (1.0 - opacity);
            opacity += alpha * (1.0 - opacity);
        }

        // TIER 2: Subtle glow halo
        if (minDist < tubeRadius * 1.5 && minDist >= tubeRadius) {
            float glowDist = (minDist - tubeRadius) / (tubeRadius * 0.5);
            float glowIntensity = exp(-glowDist * 5.0) * 0.08;

            float hue = float(hitFiber) / 8.0;
            vec3 glowColor = hsv2rgb(hue, 0.95, 0.95);

            finalColor += glowColor * glowIntensity * (1.0 - opacity);
        }

        // Early exit
        if (opacity > 0.99) break;

        // THEN advance ray (CRITICAL ORDER)
        rayPos += rayDir * stepSize;
    }

    // Composite with dark background
    vec3 background = vec3(0.02);
    vec3 result = finalColor + background * (1.0 - opacity);

    gl_FragColor = vec4(result, 1.0);
}
