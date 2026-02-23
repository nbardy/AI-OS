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

// Compute Hopf point in S³
vec4 hopfPoint(float phi, float theta, float rot) {
    float cp2 = cos(phi * 0.5);
    float sp2 = sin(phi * 0.5);
    return vec4(
        cp2 * cos(theta),
        cp2 * sin(theta),
        sp2 * cos(theta + rot),
        sp2 * sin(theta + rot)
    );
}

// Distance from point p to line segment (a, b)
float distToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    vec3 ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    vec3 closest = a + t * ab;
    return length(p - closest);
}

void main() {
    // Standard UV formula (aspect-corrected)
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Orbital camera with Y offset
    float angle = u_time * 0.25;
    float dist = 3.0;
    float yOffset = 1.4;
    vec3 camera = vec3(dist * cos(angle), yOffset, dist * sin(angle));
    vec3 lookAt = vec3(0.0, 0.0, 0.0);

    // Camera basis vectors
    vec3 forward = normalize(lookAt - camera);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
    vec3 up = cross(forward, right);

    // Ray direction
    vec3 rayDir = normalize(forward + right * uv.x + up * uv.y);
    vec3 rayOrigin = camera;

    // Fiber configuration (6 fibers x 4 params = 24 floats)
    // Format: [phi, rotation, hue, saturation]
    float fibers[24];

    // Shell 1 (phi = π/6): Warm reds/oranges
    fibers[0] = PI/6.0; fibers[1] = 0.0; fibers[2] = 0.05; fibers[3] = 0.95;
    fibers[4] = PI/6.0; fibers[5] = PI;  fibers[6] = 0.15; fibers[7] = 0.95;

    // Shell 2 (phi = π/3): Warm yellows/oranges
    fibers[8]  = PI/3.0; fibers[9]  = 0.0; fibers[10] = 0.10; fibers[11] = 0.95;
    fibers[12] = PI/3.0; fibers[13] = PI;  fibers[14] = 0.08; fibers[15] = 0.95;

    // Shell 3 (phi = π/2): Cool cyans/blues
    fibers[16] = PI/2.0; fibers[17] = 0.0; fibers[18] = 0.55; fibers[19] = 0.95;
    fibers[20] = PI/2.0; fibers[21] = PI;  fibers[22] = 0.65; fibers[23] = 0.95;

    // Ray marching
    float t = 0.0;
    float stepSize = 0.10;
    int maxSteps = 60;

    vec3 color = vec3(0.0);
    float accumulated = 0.0;

    float tubeRadius = 0.07;
    float glowRadius = tubeRadius * 1.5;
    float epsilon = 0.15;
    float scale = 1.5;

    for (int step = 0; step < 60; step++) {
        if (step >= maxSteps) break;

        vec3 p = rayOrigin + rayDir * t;

        float minDist = 1e10;
        vec3 closestColor = vec3(0.0);

        // Check all 6 fibers
        for (int f = 0; f < 6; f++) {
            float phi = fibers[f * 4];
            float rot = fibers[f * 4 + 1];
            float hue = fibers[f * 4 + 2];
            float sat = fibers[f * 4 + 3];

            // Check all 40 segments
            for (int seg = 0; seg < 40; seg++) {
                float theta0 = float(seg) * TWO_PI / 40.0;
                float theta1 = float(seg + 1) * TWO_PI / 40.0;

                // Wrap last segment
                if (seg == 39) {
                    theta1 = 0.0;
                }

                // Compute S³ points
                vec4 q0 = hopfPoint(phi, theta0, rot);
                vec4 q1 = hopfPoint(phi, theta1, rot);

                // Stereographic projection to R³
                vec3 p0 = q0.xyz / (1.0 - q0.w + epsilon) * scale;
                vec3 p1 = q1.xyz / (1.0 - q1.w + epsilon) * scale;

                // Distance to segment
                float segDist = distToSegment(p, p0, p1);

                if (segDist < minDist) {
                    minDist = segDist;
                    closestColor = hsv2rgb(vec3(hue, sat, 0.95));
                }
            }
        }

        // Density and alpha for closest fiber only
        if (minDist < glowRadius) {
            float coreDensity = 0.0;

            if (minDist < tubeRadius) {
                coreDensity = (tubeRadius - minDist) / tubeRadius;
                coreDensity = coreDensity * coreDensity;  // Quadratic
            }

            // Glow halo
            float glowDist = max(0.0, minDist - tubeRadius);
            float glowDensity = exp(-glowDist * 5.0) * 0.08;

            float totalDensity = coreDensity + glowDensity;
            float alpha = (1.0 - exp(-totalDensity * 4.5)) * 0.85;

            // Front-to-back accumulation
            color += closestColor * alpha * (1.0 - accumulated);
            accumulated += alpha * (1.0 - accumulated);

            if (accumulated > 0.95) break;
        }

        t += stepSize;
        if (t > 10.0) break;
    }

    // Dark background
    color += vec3(0.02) * (1.0 - accumulated);

    gl_FragColor = vec4(color, 1.0);
}
