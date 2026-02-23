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
    // Standard UV setup (MANDATORY formula)
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Y-offset orbit camera (MANDATORY: NOT spherical)
    float cameraAngle = u_time * 0.25;
    float cameraDist = 3.0; // Closer than 4.5 to match larger scale
    vec3 cameraPos = vec3(cameraDist * cos(cameraAngle), 1.5, cameraDist * sin(cameraAngle));
    vec3 target = vec3(0.0, 0.0, 0.0);

    vec3 forward = normalize(target - cameraPos);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
    vec3 up = cross(forward, right);

    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);

    // Generate fiber data (MANDATORY: flat array inside main)
    float fiberData[960]; // 6 fibers × 40 segments × 4 floats (x,y,z,hue)

    float shellAngles[3];
    shellAngles[0] = 0.523599; // π/6
    shellAngles[1] = 1.047198; // π/3
    shellAngles[2] = 1.570796; // π/2

    float rotations[2];
    rotations[0] = 0.0;
    rotations[1] = 1.570796; // π/2

    int dataIdx = 0;

    for (int shellIdx = 0; shellIdx < 3; shellIdx++) {
        float phi = shellAngles[shellIdx];
        float cosPhi2 = cos(phi * 0.5);
        float sinPhi2 = sin(phi * 0.5);

        for (int rotIdx = 0; rotIdx < 2; rotIdx++) {
            float rotation = rotations[rotIdx];
            float fiberHue = float(shellIdx * 2 + rotIdx) / 6.0;

            for (int seg = 0; seg < 40; seg++) {
                float t = float(seg) / 40.0;
                float theta = t * 6.283185 + rotation; // 2π

                // MANDATORY: Correct Hopf quaternion
                float cosTheta = cos(theta);
                float sinTheta = sin(theta);
                vec4 q = vec4(
                    cosPhi2 * cosTheta,
                    cosPhi2 * sinTheta,
                    sinPhi2 * cosTheta,
                    sinPhi2 * sinTheta
                );

                // MANDATORY: Direct S3 stereographic projection with low epsilon
                float epsilon = 0.12;
                vec3 projected = q.xyz / (1.0 - q.w + epsilon);

                // MANDATORY: Post-projection scale 1.8 (NOT 0.85)
                projected *= 1.8;

                fiberData[dataIdx++] = projected.x;
                fiberData[dataIdx++] = projected.y;
                fiberData[dataIdx++] = projected.z;
                fiberData[dataIdx++] = fiberHue;
            }
        }
    }

    // Ray marching
    vec3 rayPos = cameraPos;
    float stepSize = 0.10;
    int maxSteps = 48;
    float tubeRadius = 0.05; // Thin tubes

    float totalDensity = 0.0;
    vec3 accumulatedColor = vec3(0.0);
    vec3 glowColor = vec3(0.0);

    for (int step = 0; step < 48; step++) {
        if (step >= maxSteps) break;

        float minDist = 1000.0;
        float nearestHue = 0.0;

        // Check all fibers
        for (int fiber = 0; fiber < 6; fiber++) {
            int baseIdx = fiber * 160; // 40 segments × 4 floats

            // Check all segments in this fiber
            for (int seg = 0; seg < 40; seg++) {
                int idx = baseIdx + seg * 4;
                int nextIdx = baseIdx + ((seg + 1) % 40) * 4; // Wraparound

                vec3 a = vec3(fiberData[idx], fiberData[idx+1], fiberData[idx+2]);
                vec3 b = vec3(fiberData[nextIdx], fiberData[nextIdx+1], fiberData[nextIdx+2]);

                float dist = distanceToSegment(rayPos, a, b);

                if (dist < minDist) {
                    minDist = dist;
                    nearestHue = fiberData[idx+3];
                }
            }
        }

        // MANDATORY: Solid tube density (NOT hollow shell)
        if (minDist < tubeRadius) {
            float density = (tubeRadius - minDist) / tubeRadius;
            density = density * density; // Quadratic

            vec3 fiberColor = hsv2rgb(vec3(nearestHue, 0.95, 0.95));
            accumulatedColor += fiberColor * density * stepSize;
            totalDensity += density * stepSize;
        }

        // Glow halo at 1.5x radius
        if (minDist < tubeRadius * 1.5) {
            float glowDist = minDist - tubeRadius;
            float glowIntensity = exp(-glowDist * 5.0) * 0.08;
            vec3 fiberColor = hsv2rgb(vec3(nearestHue, 0.95, 0.95));
            glowColor += fiberColor * glowIntensity * stepSize;
        }

        rayPos += rayDir * stepSize;
    }

    // PROVEN: Exponential alpha with transparency
    float alpha = 1.0 - exp(-totalDensity * 4.5);
    alpha *= 0.85; // Transparency factor

    vec3 finalColor = vec3(0.02); // Dark background

    if (totalDensity > 0.0) {
        finalColor = mix(finalColor, accumulatedColor / max(totalDensity, 0.001), alpha);
    }

    finalColor += glowColor;

    gl_FragColor = vec4(finalColor, 1.0);
}
