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

// Distance from point p to line segment (a, b)
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    vec3 ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    vec3 closest = a + t * ab;
    return length(p - closest);
}

void main() {
    // Standard aspect-correct UV
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Camera: Y-offset orbit (NOT spherical angles)
    float cameraAngle = u_time * 0.25;
    float cameraDist = 4.5;
    vec3 cameraPos = vec3(cameraDist * cos(cameraAngle), 1.5, cameraDist * sin(cameraAngle));

    // Ray setup
    vec3 target = vec3(0.0, 0.0, 0.0);
    vec3 forward = normalize(target - cameraPos);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
    vec3 up = cross(forward, right);
    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);
    vec3 rayPos = cameraPos;

    // Generate fiber geometry (8 fibers × 40 segments × 3 coords = 960 floats)
    float fiberData[960];
    int dataIdx = 0;

    // Two torus shells: outer (eta=pi/4), inner (eta=pi/6)
    float etas[2];
    etas[0] = 3.14159265 / 4.0;  // pi/4 - outer torus
    etas[1] = 3.14159265 / 6.0;  // pi/6 - inner torus

    for (int shellIdx = 0; shellIdx < 2; shellIdx++) {
        float eta = etas[shellIdx];
        float cosEta = cos(eta);
        float sinEta = sin(eta);

        // 4 fibers per shell at different rotations
        float rotations[4];
        rotations[0] = 0.0;
        rotations[1] = 3.14159265 / 4.0;      // pi/4
        rotations[2] = 3.14159265 / 2.0;      // pi/2
        rotations[3] = 3.14159265 * 3.0 / 4.0; // 3pi/4

        for (int fiberIdx = 0; fiberIdx < 4; fiberIdx++) {
            float xi2 = rotations[fiberIdx];
            float cosXi2 = cos(xi2);
            float sinXi2 = sin(xi2);

            // Generate 40 points along fiber
            for (int segIdx = 0; segIdx < 40; segIdx++) {
                float xi1 = float(segIdx) * 2.0 * 3.14159265 / 40.0;
                float cosXi1 = cos(xi1);
                float sinXi1 = sin(xi1);

                // Hopf quaternion: (cos(eta)cos(xi1), cos(eta)sin(xi1), sin(eta)cos(xi2), sin(eta)sin(xi2))
                vec4 q = vec4(
                    cosEta * cosXi1,
                    cosEta * sinXi1,
                    sinEta * cosXi2,
                    sinEta * sinXi2
                );

                // Direct S³ stereographic projection
                vec3 p = q.xyz / (1.0 - q.w + 0.35) * 0.85;

                fiberData[dataIdx++] = p.x;
                fiberData[dataIdx++] = p.y;
                fiberData[dataIdx++] = p.z;
            }
        }
    }

    // Fiber colors
    vec3 fiberColors[8];
    // Outer fibers: warm (gold → coral)
    fiberColors[0] = hsv2rgb(vec3(30.0 / 360.0, 0.95, 0.95));
    fiberColors[1] = hsv2rgb(vec3(22.5 / 360.0, 0.95, 0.95));
    fiberColors[2] = hsv2rgb(vec3(15.0 / 360.0, 0.95, 0.95));
    fiberColors[3] = hsv2rgb(vec3(7.5 / 360.0, 0.95, 0.95));
    // Inner fibers: cool (cyan → violet)
    fiberColors[4] = hsv2rgb(vec3(180.0 / 360.0, 0.95, 0.95));
    fiberColors[5] = hsv2rgb(vec3(210.0 / 360.0, 0.95, 0.95));
    fiberColors[6] = hsv2rgb(vec3(240.0 / 360.0, 0.95, 0.95));
    fiberColors[7] = hsv2rgb(vec3(270.0 / 360.0, 0.95, 0.95));

    // Tube radii
    float tubeRadii[8];
    tubeRadii[0] = 0.11;
    tubeRadii[1] = 0.11;
    tubeRadii[2] = 0.11;
    tubeRadii[3] = 0.11;
    tubeRadii[4] = 0.08;
    tubeRadii[5] = 0.08;
    tubeRadii[6] = 0.08;
    tubeRadii[7] = 0.08;

    // Ray marching
    vec3 color = vec3(0.02, 0.02, 0.03);  // Dark background
    float stepSize = 0.10;

    for (int step = 0; step < 46; step++) {
        // Check distance BEFORE advancing ray
        float minDist = 1000.0;
        int nearestFiber = -1;
        int nearestSegment = -1;

        // Check all 8 fibers
        for (int fiberIdx = 0; fiberIdx < 8; fiberIdx++) {
            int baseIdx = fiberIdx * 40 * 3;

            // Check all 40 segments
            for (int segIdx = 0; segIdx < 40; segIdx++) {
                int idx = baseIdx + segIdx * 3;
                vec3 p1 = vec3(fiberData[idx], fiberData[idx + 1], fiberData[idx + 2]);

                // Next point (wrap around)
                int nextSegIdx = segIdx + 1;
                if (nextSegIdx >= 40) nextSegIdx = 0;
                int nextIdx = baseIdx + nextSegIdx * 3;
                vec3 p2 = vec3(fiberData[nextIdx], fiberData[nextIdx + 1], fiberData[nextIdx + 2]);

                float dist = distanceToSegment(rayPos, p1, p2);
                if (dist < minDist) {
                    minDist = dist;
                    nearestFiber = fiberIdx;
                    nearestSegment = segIdx;
                }
            }
        }

        // If within tube radius, accumulate color with Fresnel enhancement
        if (nearestFiber >= 0 && minDist < tubeRadii[nearestFiber]) {
            // Compute fiber tangent for Fresnel term
            int baseIdx = nearestFiber * 40 * 3;
            int idx = baseIdx + nearestSegment * 3;
            vec3 p1 = vec3(fiberData[idx], fiberData[idx + 1], fiberData[idx + 2]);

            int nextSegIdx = nearestSegment + 1;
            if (nextSegIdx >= 40) nextSegIdx = 0;
            int nextIdx = baseIdx + nextSegIdx * 3;
            vec3 p2 = vec3(fiberData[nextIdx], fiberData[nextIdx + 1], fiberData[nextIdx + 2]);

            vec3 tangent = normalize(p2 - p1);
            vec3 normalizedRayDir = normalize(rayDir);

            // Fresnel term: brightens edges
            float fresnelTerm = pow(1.0 - abs(dot(normalizedRayDir, tangent)), 3.0);
            fresnelTerm = clamp(fresnelTerm, 0.0, 1.0);

            // Solid tube density
            float baseDensity = (tubeRadii[nearestFiber] - minDist) / tubeRadii[nearestFiber];
            float density = baseDensity * mix(1.0, 2.0, fresnelTerm);

            // Quadratic falloff + exponential alpha
            float alpha = 1.0 - exp(-density * density * 4.5);
            alpha *= 0.85;  // Transparency factor

            // Blend nearest fiber color
            color = mix(color, fiberColors[nearestFiber], alpha);
        }

        // Advance ray
        rayPos += rayDir * stepSize;
    }

    gl_FragColor = vec4(color, 1.0);
}
