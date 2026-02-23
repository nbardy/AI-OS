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

            for (int seg = 0; seg < 40; seg++) {
                float theta = float(seg) * 2.0 * 3.14159265 / 40.0 + rotation;

                // Hopf fibration quaternion
                float cosPhi2 = cos(phi / 2.0);
                float sinPhi2 = sin(phi / 2.0);
                float cosTheta = cos(theta);
                float sinTheta = sin(theta);

                vec4 q = vec4(
                    cosPhi2 * cosTheta,
                    cosPhi2 * sinTheta,
                    sinPhi2 * cosTheta,
                    sinPhi2 * sinTheta
                );

                // Direct S³ stereographic projection
                vec3 p3d = q.xyz / (1.0 - q.w + 0.35);
                p3d *= 0.85; // Post-projection scale

                int idx = (fiberIdx * 40 + seg) * 3;
                fiberData[idx] = p3d.x;
                fiberData[idx + 1] = p3d.y;
                fiberData[idx + 2] = p3d.z;
            }
            fiberIdx++;
        }
    }

    // Setup camera and ray
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    float cameraAngle = u_time * 0.25;
    float cameraDist = 4.5;
    vec3 cameraPos = vec3(
        cameraDist * cos(cameraAngle),
        1.5,
        cameraDist * sin(cameraAngle)
    );

    vec3 target = vec3(0.0, 0.0, 0.0);
    vec3 forward = normalize(target - cameraPos);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
    vec3 up = cross(forward, right);

    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);
    vec3 rayPos = cameraPos;

    // Ray marching
    vec3 color = vec3(0.02); // Dark background
    float tubeRadius = 0.11;
    float glowRadius = tubeRadius * 1.5;
    float stepSize = 0.08;

    for (int step = 0; step < 64; step++) {
        float minDist = 1000.0;
        int closestFiber = -1;

        // Find nearest fiber segment
        for (int fiber = 0; fiber < 8; fiber++) {
            for (int seg = 0; seg < 40; seg++) {
                int idx = (fiber * 40 + seg) * 3;
                vec3 p1 = vec3(fiberData[idx], fiberData[idx + 1], fiberData[idx + 2]);

                int nextSeg = seg + 1;
                if (nextSeg >= 40) nextSeg = 0;
                int nextIdx = (fiber * 40 + nextSeg) * 3;
                vec3 p2 = vec3(fiberData[nextIdx], fiberData[nextIdx + 1], fiberData[nextIdx + 2]);

                float dist = distanceToSegment(rayPos, p1, p2);
                if (dist < minDist) {
                    minDist = dist;
                    closestFiber = fiber;
                }
            }
        }

        // Solid tube density (nearest segment only)
        if (minDist < tubeRadius && closestFiber >= 0) {
            float density = (tubeRadius - minDist) / tubeRadius;
            density = density * density; // Quadratic falloff

            // Triadic color scheme (warm/cool/neutral families)
            float hue;
            if (closestFiber == 0 || closestFiber == 3 || closestFiber == 6) {
                // Warm: gold/orange family
                hue = 0.08 + float(closestFiber) * 0.02;
            } else if (closestFiber == 1 || closestFiber == 4 || closestFiber == 7) {
                // Cool: sapphire/cyan family
                hue = 0.52 + float(closestFiber) * 0.02;
            } else {
                // Neutral: magenta/purple family (fibers 2, 5)
                hue = 0.80 + float(closestFiber) * 0.02;
            }

            vec3 fiberColor = hsv2rgb(hue, 0.95, 0.95);

            float alpha = 1.0 - exp(-density * 4.5);
            color = mix(color, fiberColor, alpha * 0.85);
        }

        // Glow halo
        if (minDist < glowRadius && closestFiber >= 0) {
            float glowDist = minDist - tubeRadius;
            if (glowDist > 0.0) {
                float hue;
                if (closestFiber == 0 || closestFiber == 3 || closestFiber == 6) {
                    hue = 0.08 + float(closestFiber) * 0.02;
                } else if (closestFiber == 1 || closestFiber == 4 || closestFiber == 7) {
                    hue = 0.52 + float(closestFiber) * 0.02;
                } else {
                    hue = 0.80 + float(closestFiber) * 0.02;
                }

                vec3 glowColor = hsv2rgb(hue, 0.95, 0.95);
                float glowIntensity = exp(-glowDist * 5.0) * 0.08;
                color += glowColor * glowIntensity;
            }
        }

        rayPos += rayDir * stepSize;
    }

    gl_FragColor = vec4(color, 1.0);
}
