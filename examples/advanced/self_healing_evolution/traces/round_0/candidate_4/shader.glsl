#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

#define PI 3.14159265359
#define TWO_PI 6.28318530718

// HSV to RGB conversion
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// Distance to line segment
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    float t = clamp(dot(p - a, ab) / dot(ab, ab), 0.0, 1.0);
    vec3 closest = a + t * ab;
    return length(p - closest);
}

void main() {
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Camera setup - orbital at distance 4.5
    float camAngle = u_time * 0.25;
    float camDist = 4.5;
    float camElevation = 1.5;
    vec3 camPos = vec3(
        camDist * cos(camAngle),
        camElevation,
        camDist * sin(camAngle)
    );

    vec3 forward = normalize(-camPos);
    vec3 right = normalize(cross(forward, vec3(0, 1, 0)));
    vec3 up = cross(right, forward);

    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);
    vec3 rayPos = camPos;

    // Generate fiber data: 4 fibers × 40 segments × 6 floats (pos + normal) = 960 floats
    float fiberData[960];

    float phi = PI * 0.25; // Clifford torus equator
    float cosHalfPhi = cos(phi * 0.5);
    float sinHalfPhi = sin(phi * 0.5);

    for (int fiberIdx = 0; fiberIdx < 4; fiberIdx++) {
        float xi1 = float(fiberIdx) * PI * 0.5; // rotation offset: 0, π/2, π, 3π/2

        for (int segIdx = 0; segIdx < 40; segIdx++) {
            float theta = float(segIdx) * TWO_PI / 40.0 + xi1;

            // Hopf quaternion parametrization
            vec4 q = vec4(
                cosHalfPhi * cos(theta),
                cosHalfPhi * sin(theta),
                sinHalfPhi * cos(theta),
                sinHalfPhi * sin(theta)
            );

            // Stereographic projection
            float denom = 1.0 / (1.0 - q.w + 0.35);
            vec3 p = vec3(q.x, q.y, q.z) * denom;
            p *= 0.85; // post-projection scale

            // Compute tangent for ribbon normal (using next point)
            float thetaNext = float((segIdx + 1) % 40) * TWO_PI / 40.0 + xi1;
            vec4 qNext = vec4(
                cosHalfPhi * cos(thetaNext),
                cosHalfPhi * sin(thetaNext),
                sinHalfPhi * cos(thetaNext),
                sinHalfPhi * sin(thetaNext)
            );
            vec3 pNext = vec3(qNext.x, qNext.y, qNext.z) / (1.0 - qNext.w + 0.35) * 0.85;

            vec3 tangent = normalize(pNext - p);
            vec3 ribbonNormal = normalize(cross(tangent, vec3(0, 1, 0)));

            // Fallback if tangent is nearly vertical
            if (length(ribbonNormal) < 0.1) {
                ribbonNormal = normalize(cross(tangent, vec3(1, 0, 0)));
            }

            // Store position and normal
            int baseIdx = (fiberIdx * 40 + segIdx) * 6;
            fiberData[baseIdx + 0] = p.x;
            fiberData[baseIdx + 1] = p.y;
            fiberData[baseIdx + 2] = p.z;
            fiberData[baseIdx + 3] = ribbonNormal.x;
            fiberData[baseIdx + 4] = ribbonNormal.y;
            fiberData[baseIdx + 5] = ribbonNormal.z;
        }
    }

    // Ray march
    vec3 color = vec3(0.02, 0.02, 0.03); // deep charcoal-navy background
    float opacity = 0.0;

    for (int step = 0; step < 100; step++) {
        float minDist = 1e10;
        vec3 closestNormal = vec3(0, 1, 0);
        int closestFiber = 0;
        float closestT = 0.0;

        // Check all ribbon segments
        for (int fiberIdx = 0; fiberIdx < 4; fiberIdx++) {
            for (int segIdx = 0; segIdx < 40; segIdx++) {
                int nextIdx = (segIdx + 1) % 40;

                // Load segment data
                int baseIdx = (fiberIdx * 40 + segIdx) * 6;
                vec3 a = vec3(
                    fiberData[baseIdx + 0],
                    fiberData[baseIdx + 1],
                    fiberData[baseIdx + 2]
                );
                vec3 na = vec3(
                    fiberData[baseIdx + 3],
                    fiberData[baseIdx + 4],
                    fiberData[baseIdx + 5]
                );

                int nextBaseIdx = (fiberIdx * 40 + nextIdx) * 6;
                vec3 b = vec3(
                    fiberData[nextBaseIdx + 0],
                    fiberData[nextBaseIdx + 1],
                    fiberData[nextBaseIdx + 2]
                );
                vec3 nb = vec3(
                    fiberData[nextBaseIdx + 3],
                    fiberData[nextBaseIdx + 4],
                    fiberData[nextBaseIdx + 5]
                );

                // Distance to segment centerline
                vec3 ab = b - a;
                float t = clamp(dot(rayPos - a, ab) / dot(ab, ab), 0.0, 1.0);
                vec3 closest = a + t * ab;
                float dist = length(rayPos - closest);

                // Ribbon geometry: width 0.12, thickness 0.02
                vec3 interpNormal = normalize(mix(na, nb, t));
                vec3 residual = rayPos - closest;
                float normalDist = abs(dot(residual, interpNormal));

                // Approximate ribbon cross-section as box
                float ribbonDist = max(dist - 0.12, normalDist - 0.02);

                if (ribbonDist < minDist) {
                    minDist = ribbonDist;
                    closestNormal = interpNormal;
                    closestFiber = fiberIdx;
                    closestT = t;
                }
            }
        }

        // Accumulate color if near ribbon
        if (minDist < 0.12) {
            float density = (0.12 - minDist) / 0.12;
            density = density * density;

            // Orientation-dependent brightness (surface-like shading)
            float facing = abs(dot(closestNormal, normalize(rayDir)));
            float brightness = mix(0.5, 1.0, facing);

            // Warm color palette: red to gold
            float hue = float(closestFiber) * 0.03; // 0.0, 0.03, 0.06, 0.09
            vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95)) * brightness;

            float alpha = 1.0 - exp(-density * 4.5);
            alpha *= 0.85; // transparency

            color = color * (1.0 - alpha) + fiberColor * alpha;
            opacity += alpha * (1.0 - opacity);

            if (opacity > 0.99) break;
        }

        // Advance ray
        rayPos += rayDir * 0.09;
        if (length(rayPos) > 10.0) break;
    }

    gl_FragColor = vec4(color, 1.0);
}
