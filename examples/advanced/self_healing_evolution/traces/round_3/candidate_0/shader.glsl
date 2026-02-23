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
                float theta = float(seg) / 40.0 * 2.0 * 3.14159265 + rotation;

                // Hopf quaternion on S3
                float cp2 = cos(phi / 2.0);
                float sp2 = sin(phi / 2.0);
                vec4 q = vec4(
                    cp2 * cos(theta),
                    cp2 * sin(theta),
                    sp2 * cos(theta),
                    sp2 * sin(theta)
                );

                // Stereographic projection S3 -> R3
                vec3 projected = q.xyz / (1.0 - q.w + 0.15);

                // TWEAK 1: Scale up from 1.0 to 1.5 for larger, better-framed fibers
                projected *= 1.5;

                int baseIdx = fiberIdx * 120 + seg * 3;
                fiberData[baseIdx + 0] = projected.x;
                fiberData[baseIdx + 1] = projected.y;
                fiberData[baseIdx + 2] = projected.z;
            }
            fiberIdx++;
        }
    }

    // Camera setup
    // TWEAK 2: Adjust camera distance from ~4.5 to 3.0 to match 1.5 scale
    float camAngle = u_time * 0.25;
    float camDist = 3.0;
    vec3 camPos = vec3(camDist * cos(camAngle), 1.5, camDist * sin(camAngle));
    vec3 target = vec3(0.0, 0.0, 0.0);
    vec3 camForward = normalize(target - camPos);
    vec3 camRight = normalize(cross(vec3(0.0, 1.0, 0.0), camForward));
    vec3 camUp = cross(camForward, camRight);

    // UV coordinates (aspect-corrected)
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Ray setup
    vec3 rayDir = normalize(camForward + uv.x * camRight + uv.y * camUp);
    vec3 rayPos = camPos;

    // Ray marching
    vec3 color = vec3(0.02);
    float alpha = 0.0;
    float tubeRadius = 0.06;

    for (int step = 0; step < 48; step++) {
        float minDist = 1000.0;
        int closestFiber = -1;

        // Check distance to all fibers
        for (int fiber = 0; fiber < 8; fiber++) {
            for (int seg = 0; seg < 40; seg++) {
                int baseIdx = fiber * 120 + seg * 3;
                vec3 p0 = vec3(
                    fiberData[baseIdx + 0],
                    fiberData[baseIdx + 1],
                    fiberData[baseIdx + 2]
                );

                int nextSeg = seg + 1;
                if (nextSeg >= 40) nextSeg = 0;
                int nextIdx = fiber * 120 + nextSeg * 3;
                vec3 p1 = vec3(
                    fiberData[nextIdx + 0],
                    fiberData[nextIdx + 1],
                    fiberData[nextIdx + 2]
                );

                float dist = distanceToSegment(rayPos, p0, p1);
                if (dist < minDist) {
                    minDist = dist;
                    closestFiber = fiber;
                }
            }
        }

        // Density and color contribution
        if (minDist < tubeRadius * 1.5) {
            float density = clamp((tubeRadius - minDist) / tubeRadius, 0.0, 1.0);
            density = density * density;

            float fiberHue = float(closestFiber) / 8.0;
            vec3 fiberColor = hsv2rgb(fiberHue, 0.95, 0.95);

            float thisAlpha = (1.0 - exp(-density * 4.5)) * 0.85;
            color = mix(color, fiberColor, thisAlpha * (1.0 - alpha));
            alpha = alpha + thisAlpha * (1.0 - alpha);

            // Glow halo
            if (minDist > tubeRadius) {
                float glowDist = minDist - tubeRadius;
                float glow = exp(-glowDist * 5.0) * 0.08;
                color += fiberColor * glow * (1.0 - alpha);
            }
        }

        if (alpha > 0.98) break;

        rayPos += rayDir * 0.1;
        if (length(rayPos - camPos) > 15.0) break;
    }

    gl_FragColor = vec4(color, 1.0);
}
