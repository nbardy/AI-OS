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

void main() {
    // Standard UV with aspect correction
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Orbital camera with Y offset
    float angle = u_time * 0.25;
    vec3 camPos = vec3(3.0 * cos(angle), 1.5, 3.0 * sin(angle));
    vec3 camTarget = vec3(0.0, 0.0, 0.0);
    vec3 camUp = vec3(0.0, 1.0, 0.0);

    // Camera basis vectors
    vec3 forward = normalize(camTarget - camPos);
    vec3 right = normalize(cross(forward, camUp));
    vec3 up = cross(right, forward);

    // Ray direction
    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);

    // Dark background
    vec3 color = vec3(0.01, 0.01, 0.02);

    // === GEOMETRY GENERATION ===
    // 4 fibers, 40 segments each, 3 floats per segment = 480 floats
    float segments[480];

    const float PI = 3.14159265359;
    const float phi = PI / 4.0; // Clifford torus
    const float epsilon = 0.15;
    const float scale = 1.5;

    // Generate 4 fibers with rotations 0, pi/2, pi, 3pi/2
    for (int fiberIdx = 0; fiberIdx < 4; fiberIdx++) {
        float rot = float(fiberIdx) * PI / 2.0;

        for (int seg = 0; seg < 40; seg++) {
            float theta = 2.0 * PI * float(seg) / 40.0;

            // Hopf quaternion: q = (cos(phi/2)*cos(theta), cos(phi/2)*sin(theta),
            //                       sin(phi/2)*cos(theta+rot), sin(phi/2)*sin(theta+rot))
            float half_phi = phi / 2.0;
            vec4 q = vec4(
                cos(half_phi) * cos(theta),
                cos(half_phi) * sin(theta),
                sin(half_phi) * cos(theta + rot),
                sin(half_phi) * sin(theta + rot)
            );

            // Stereographic projection: q.xyz / (1 - q.w + epsilon)
            vec3 p3d = q.xyz / (1.0 - q.w + epsilon);

            // Post-projection scale
            p3d *= scale;

            // Store in flat array
            int baseIdx = fiberIdx * 120 + seg * 3;
            segments[baseIdx] = p3d.x;
            segments[baseIdx + 1] = p3d.y;
            segments[baseIdx + 2] = p3d.z;
        }
    }

    // === RAY MARCHING ===
    const int MAX_STEPS = 60;
    const float STEP_SIZE = 0.10;
    const float MAX_DIST = 8.0;
    const float TUBE_RADIUS = 0.06;
    const float GLOW_RADIUS = 0.09; // 1.5x tube radius

    float totalAlpha = 0.0;
    vec3 rayPos = camPos;

    // Fiber colors (HSV to RGB)
    vec3 fiberColors[4];
    fiberColors[0] = hsv2rgb(vec3(0.0, 0.95, 0.95));   // Ruby
    fiberColors[1] = hsv2rgb(vec3(0.08, 0.95, 0.95));  // Amber
    fiberColors[2] = hsv2rgb(vec3(0.5, 0.95, 0.95));   // Teal
    fiberColors[3] = hsv2rgb(vec3(0.75, 0.95, 0.95));  // Violet

    for (int step = 0; step < MAX_STEPS; step++) {
        if (totalAlpha > 0.95) break;

        float stepAlpha = 0.0;
        vec3 stepColor = vec3(0.0);

        // Check each fiber
        for (int fiberIdx = 0; fiberIdx < 4; fiberIdx++) {
            float minDist = 1000.0;
            vec3 nearestA = vec3(0.0);
            vec3 nearestB = vec3(0.0);

            // Find nearest segment
            for (int seg = 0; seg < 40; seg++) {
                int baseIdx = fiberIdx * 120 + seg * 3;
                vec3 a = vec3(segments[baseIdx], segments[baseIdx + 1], segments[baseIdx + 2]);

                int nextSeg = (seg + 1) % 40;
                int nextIdx = fiberIdx * 120 + nextSeg * 3;
                vec3 b = vec3(segments[nextIdx], segments[nextIdx + 1], segments[nextIdx + 2]);

                // Distance to line segment
                vec3 ab = b - a;
                vec3 ap = rayPos - a;
                float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
                vec3 closest = a + t * ab;
                float dist = length(rayPos - closest);

                if (dist < minDist) {
                    minDist = dist;
                    nearestA = a;
                    nearestB = b;
                }
            }

            // Compute Fresnel edge term
            float edgeBoost = 1.0;
            vec3 tangent = nearestB - nearestA;
            float tangentLen = length(tangent);
            if (tangentLen > 0.001) {
                tangent = tangent / tangentLen; // normalize
                float viewAngle = abs(dot(rayDir, tangent));
                float fresnel = pow(1.0 - viewAngle, 2.0);
                edgeBoost = mix(1.0, 2.5, fresnel);
            }

            // Solid tube density
            if (minDist < TUBE_RADIUS) {
                float density = (TUBE_RADIUS - minDist) / TUBE_RADIUS;
                density = density * density; // quadratic
                float alpha = (1.0 - exp(-density * 4.5)) * 0.85;

                vec3 fiberColor = fiberColors[fiberIdx] * edgeBoost;
                stepColor += fiberColor * alpha * (1.0 - stepAlpha);
                stepAlpha += alpha * (1.0 - stepAlpha);
            }

            // Glow halo at 1.5x radius
            if (minDist < GLOW_RADIUS) {
                float glowDist = minDist - TUBE_RADIUS;
                if (glowDist > 0.0) {
                    float glowAlpha = exp(-glowDist * 5.0) * 0.08;
                    vec3 fiberColor = fiberColors[fiberIdx] * edgeBoost;
                    stepColor += fiberColor * glowAlpha * (1.0 - stepAlpha);
                    stepAlpha += glowAlpha * (1.0 - stepAlpha);
                }
            }
        }

        // Crossing brightness flare
        if (stepAlpha > 0.6) {
            stepColor += vec3(0.3) * (stepAlpha - 0.6);
        }

        // Front-to-back accumulation
        color += stepColor * (1.0 - totalAlpha);
        totalAlpha += stepAlpha * (1.0 - totalAlpha);

        // Advance ray
        rayPos += rayDir * STEP_SIZE;

        if (length(rayPos - camPos) > MAX_DIST) break;
    }

    gl_FragColor = vec4(color, 1.0);
}
