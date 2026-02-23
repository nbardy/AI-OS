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

// Distance from point p to line segment between a and b
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    vec3 ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    vec3 closest = a + t * ab;
    return length(p - closest);
}

void main() {
    // Fiber storage: 4 fibers × 40 segments × 3 coords = 480 floats
    float fiberData[480];

    // Generate 4 fibers (2 tori × 2 fibers each)
    // Torus 1 (gold): phi = π/6, rotations at 0 and π
    // Torus 2 (blue): phi = π/3, rotations at π/2 and 3π/2
    float phiAngles[4];
    phiAngles[0] = 3.14159265 / 6.0;  // π/6 for fiber 0
    phiAngles[1] = 3.14159265 / 6.0;  // π/6 for fiber 1
    phiAngles[2] = 3.14159265 / 3.0;  // π/3 for fiber 2
    phiAngles[3] = 3.14159265 / 3.0;  // π/3 for fiber 3

    float rotations[4];
    rotations[0] = 0.0;
    rotations[1] = 3.14159265;
    rotations[2] = 3.14159265 / 2.0;
    rotations[3] = 3.14159265 * 1.5;

    int numSegments = 40;
    float scale = 0.85;

    // Build all fiber segments
    for (int fiberIdx = 0; fiberIdx < 4; fiberIdx++) {
        float phi = phiAngles[fiberIdx];
        float rotation = rotations[fiberIdx];
        float cosHalfPhi = cos(phi * 0.5);
        float sinHalfPhi = sin(phi * 0.5);

        for (int segIdx = 0; segIdx < 40; segIdx++) {
            float theta = 6.28318530 * float(segIdx) / 40.0 + rotation;
            float cosTheta = cos(theta);
            float sinTheta = sin(theta);

            // Hopf quaternion form: q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ), sin(φ/2)sin(θ))
            vec4 q = vec4(
                cosHalfPhi * cosTheta,
                cosHalfPhi * sinTheta,
                sinHalfPhi * cosTheta,
                sinHalfPhi * sinTheta
            );

            // Stereographic projection: (x,y,z,w) -> (x,y,z)/(1-w+0.35)
            float denom = 1.0 / (1.0 - q.w + 0.35);
            vec3 p = vec3(q.x, q.y, q.z) * denom * scale;

            // Store in flat array
            int baseIdx = fiberIdx * 120 + segIdx * 3;
            fiberData[baseIdx + 0] = p.x;
            fiberData[baseIdx + 1] = p.y;
            fiberData[baseIdx + 2] = p.z;
        }
    }

    // Camera setup
    float camDist = 4.5;
    float camAngle = u_time * 0.25;
    float camElevation = 1.5;
    vec3 camPos = vec3(
        camDist * cos(camAngle) * cos(camElevation),
        camDist * sin(camElevation),
        camDist * sin(camAngle) * cos(camElevation)
    );

    vec3 target = vec3(0.0, 0.0, 0.0);
    vec3 forward = normalize(target - camPos);
    vec3 worldUp = vec3(0.0, 1.0, 0.0);
    vec3 right = normalize(cross(forward, worldUp));
    vec3 up = cross(right, forward);

    // Ray setup
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;
    float fov = 0.785398; // 45 degrees
    vec3 rayDir = normalize(forward + uv.x * right * tan(fov) + uv.y * up * tan(fov));
    vec3 rayPos = camPos;

    // Ray marching with depth tracking
    float stepSize = 0.09;
    int maxSteps = 100;
    float tubeRadius = 0.11;

    vec3 color = vec3(0.0);
    float opacity = 0.0;
    vec3 background = vec3(0.01, 0.01, 0.02);

    for (int step = 0; step < 100; step++) {
        if (opacity > 0.99) break;

        // Find closest fiber at current ray position
        float minDist = 1000.0;
        int closestFiber = -1;
        float rayDepth = length(rayPos - camPos);

        for (int fiberIdx = 0; fiberIdx < 4; fiberIdx++) {
            for (int segIdx = 0; segIdx < 40; segIdx++) {
                int baseIdx = fiberIdx * 120 + segIdx * 3;
                vec3 segStart = vec3(
                    fiberData[baseIdx + 0],
                    fiberData[baseIdx + 1],
                    fiberData[baseIdx + 2]
                );

                // Get next segment (wrap around)
                int nextSegIdx = segIdx + 1;
                if (nextSegIdx >= 40) nextSegIdx = 0;
                int nextBaseIdx = fiberIdx * 120 + nextSegIdx * 3;
                vec3 segEnd = vec3(
                    fiberData[nextBaseIdx + 0],
                    fiberData[nextBaseIdx + 1],
                    fiberData[nextBaseIdx + 2]
                );

                float dist = distanceToSegment(rayPos, segStart, segEnd);
                if (dist < minDist) {
                    minDist = dist;
                    closestFiber = fiberIdx;
                }
            }
        }

        // Render tube and glow
        if (minDist < tubeRadius) {
            // Determine torus color: fibers 0-1 are gold (hue 0.08), fibers 2-3 are blue (hue 0.6)
            float hue = (closestFiber < 2) ? 0.08 : 0.6;

            // Depth-aware brightness modulation
            float depthBrightness = exp(-0.5 * rayDepth);

            // Base color with depth modulation
            vec3 baseColor = hsv2rgb(vec3(hue, 0.95, 0.95 * depthBrightness));

            // Density calculation (proven quadratic formula)
            float normalizedDist = (tubeRadius - minDist) / tubeRadius;
            float density = normalizedDist * normalizedDist;
            float alpha = 1.0 - exp(-density * 4.5);
            alpha *= 0.85; // Transparency factor

            // Composite
            color = mix(color, baseColor, alpha * (1.0 - opacity));
            opacity += alpha * (1.0 - opacity);
        }
        else if (minDist < tubeRadius * 1.5) {
            // Subtle glow halo
            float glowDist = (minDist - tubeRadius) / (tubeRadius * 0.5);
            float hue = (closestFiber < 2) ? 0.08 : 0.6;
            float depthBrightness = exp(-0.5 * rayDepth);
            vec3 glowColor = hsv2rgb(vec3(hue, 0.95, 0.95 * depthBrightness));
            float glowAlpha = exp(-glowDist * 5.0) * 0.08;

            color = mix(color, glowColor, glowAlpha * (1.0 - opacity));
            opacity += glowAlpha * (1.0 - opacity);
        }

        // Advance ray (AFTER checking geometry)
        rayPos += rayDir * stepSize;
    }

    // Final composite with background
    vec3 finalColor = mix(background, color, opacity);
    gl_FragColor = vec4(finalColor, 1.0);
}
