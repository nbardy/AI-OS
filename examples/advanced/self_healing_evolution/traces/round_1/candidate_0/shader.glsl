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
                float t = float(seg) / 40.0;
                float theta = t * 2.0 * 3.14159265 + rotation;

                // Hopf quaternion (MANDATORY correct form)
                float cph = cos(phi / 2.0);
                float sph = sin(phi / 2.0);
                float cth = cos(theta);
                float sth = sin(theta);
                vec4 q = vec4(cph * cth, cph * sth, sph * cth, sph * sth);

                // Stereographic projection with singularity protection
                float denom = 1.0 / (1.0 - q.w + 0.35);
                vec3 p = vec3(q.x, q.y, q.z) * denom;

                // Post-projection scale
                p *= 0.85;

                int baseIdx = (fiberIdx * 40 + seg) * 3;
                fiberData[baseIdx] = p.x;
                fiberData[baseIdx + 1] = p.y;
                fiberData[baseIdx + 2] = p.z;
            }
            fiberIdx++;
        }
    }

    // Camera setup (Y-offset orbit, NOT spherical)
    float camDist = 4.5;
    float camAngle = u_time * 0.3; // TWEAK 1: slightly faster rotation
    vec3 camPos = vec3(camDist * cos(camAngle), 1.6, camDist * sin(camAngle)); // TWEAK 1: Y=1.6 instead of 1.5

    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;
    vec3 rayDir = normalize(vec3(uv, -1.5));

    // Simple camera rotation to look at origin
    vec3 forward = normalize(-camPos);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
    vec3 up = cross(forward, right);
    rayDir = normalize(rayDir.x * right + rayDir.y * up + rayDir.z * forward);

    // Ray marching
    vec3 rayPos = camPos;
    vec3 color = vec3(0.02); // Dark background
    float totalAlpha = 0.0;

    for (int step = 0; step < 80; step++) {
        float minDist = 1e10;
        int closestFiber = -1;

        // Check distances BEFORE stepping (MANDATORY order)
        for (int fib = 0; fib < 8; fib++) {
            for (int seg = 0; seg < 40; seg++) {
                int nextSeg = (seg + 1) % 40;
                int baseIdx = (fib * 40 + seg) * 3;
                int nextIdx = (fib * 40 + nextSeg) * 3;

                vec3 p0 = vec3(fiberData[baseIdx], fiberData[baseIdx + 1], fiberData[baseIdx + 2]);
                vec3 p1 = vec3(fiberData[nextIdx], fiberData[nextIdx + 1], fiberData[nextIdx + 2]);

                float dist = distanceToSegment(rayPos, p0, p1);
                if (dist < minDist) {
                    minDist = dist;
                    closestFiber = fib;
                }
            }
        }

        // Unsigned distance only
        minDist = abs(minDist);

        // Tube rendering
        float tubeRadius = 0.11;
        if (minDist < tubeRadius) {
            float density = (tubeRadius - minDist) / tubeRadius;
            density = density * density; // Quadratic
            float alpha = 1.0 - exp(-density * 4.5); // Exponential
            alpha *= 0.85; // Transparency

            // TWEAK 2: Warmer color palette (hue shift +0.05)
            float hue = fract(float(closestFiber) / 8.0 + 0.05);
            vec3 fiberColor = hsv2rgb(hue, 0.95, 0.95);

            color = mix(color, fiberColor, alpha * (1.0 - totalAlpha));
            totalAlpha += alpha * (1.0 - totalAlpha);

            if (totalAlpha > 0.99) break;
        }

        // Glow halo
        float glowRadius = tubeRadius * 1.5;
        if (minDist < glowRadius) {
            float glowDist = minDist - tubeRadius;
            float glow = exp(-glowDist * 5.0) * 0.08;
            float hue = fract(float(closestFiber) / 8.0 + 0.05);
            vec3 glowColor = hsv2rgb(hue, 0.95, 0.95);
            color += glowColor * glow * (1.0 - totalAlpha);
        }

        rayPos += rayDir * 0.08;

        if (length(rayPos - camPos) > 15.0) break;
    }

    gl_FragColor = vec4(color, 1.0);
}
