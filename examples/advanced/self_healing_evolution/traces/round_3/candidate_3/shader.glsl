#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

// Constants
#define PI 3.14159265359
#define TUBE_RADIUS 0.06
#define SCALE 1.5
#define EPSILON 0.15
#define CAM_DIST 3.0
#define Y_OFFSET 1.5
#define NUM_STEPS 48
#define STEP_SIZE 0.10

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
    // Aspect-correct UV
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Generate 6 fibers (3 shells × 2 rotations)
    // Each fiber: 40 segments × 3 floats = 120 floats
    float f0[120]; // Shell π/6, rotation 0
    float f1[120]; // Shell π/6, rotation π/2
    float f2[120]; // Shell π/3, rotation 0
    float f3[120]; // Shell π/3, rotation π/2
    float f4[120]; // Shell π/2, rotation 0
    float f5[120]; // Shell π/2, rotation π/2

    // Shell angles
    float shells[3];
    shells[0] = PI / 6.0;
    shells[1] = PI / 3.0;
    shells[2] = PI / 2.0;

    // Rotations
    float rotations[2];
    rotations[0] = 0.0;
    rotations[1] = PI / 2.0;

    // Generate fiber geometry
    int fiberIdx = 0;
    for (int shell = 0; shell < 3; shell++) {
        float phi = shells[shell];
        for (int rot = 0; rot < 2; rot++) {
            float xi = rotations[rot];

            for (int seg = 0; seg < 40; seg++) {
                float theta = float(seg) * 2.0 * PI / 40.0;

                // Hopf quaternion
                vec4 q;
                q.x = cos(phi * 0.5) * cos(theta);
                q.y = cos(phi * 0.5) * sin(theta);
                q.z = sin(phi * 0.5) * cos(theta + xi);
                q.w = sin(phi * 0.5) * sin(theta + xi);

                // Stereographic projection S³ → R³
                vec3 proj = q.xyz / (1.0 - q.w + EPSILON) * SCALE;

                // Store in appropriate fiber array
                int idx = seg * 3;
                if (fiberIdx == 0) {
                    f0[idx] = proj.x;
                    f0[idx + 1] = proj.y;
                    f0[idx + 2] = proj.z;
                } else if (fiberIdx == 1) {
                    f1[idx] = proj.x;
                    f1[idx + 1] = proj.y;
                    f1[idx + 2] = proj.z;
                } else if (fiberIdx == 2) {
                    f2[idx] = proj.x;
                    f2[idx + 1] = proj.y;
                    f2[idx + 2] = proj.z;
                } else if (fiberIdx == 3) {
                    f3[idx] = proj.x;
                    f3[idx + 1] = proj.y;
                    f3[idx + 2] = proj.z;
                } else if (fiberIdx == 4) {
                    f4[idx] = proj.x;
                    f4[idx + 1] = proj.y;
                    f4[idx + 2] = proj.z;
                } else if (fiberIdx == 5) {
                    f5[idx] = proj.x;
                    f5[idx + 1] = proj.y;
                    f5[idx + 2] = proj.z;
                }
            }
            fiberIdx++;
        }
    }

    // Camera setup
    float angle = 0.25 * u_time;
    vec3 camPos = vec3(CAM_DIST * cos(angle), Y_OFFSET, CAM_DIST * sin(angle));
    vec3 lookAt = vec3(0.0);
    vec3 forward = normalize(lookAt - camPos);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
    vec3 up = cross(forward, right);

    // Ray direction
    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);
    vec3 rayPos = camPos;

    // Ray march
    vec3 color = vec3(0.0);
    float alpha = 0.0;

    for (int step = 0; step < NUM_STEPS; step++) {
        if (alpha > 0.99) break;

        // Find minimum distance to all fiber segments
        float minDist = 1000.0;
        int nearestShell = 0;

        // Check all 6 fibers
        for (int fiber = 0; fiber < 6; fiber++) {
            int shellIdx = fiber / 2;

            for (int seg = 0; seg < 40; seg++) {
                int idx = seg * 3;
                int nextIdx = ((seg + 1) % 40) * 3;

                vec3 a, b;

                // Read segment endpoints from appropriate fiber
                if (fiber == 0) {
                    a = vec3(f0[idx], f0[idx + 1], f0[idx + 2]);
                    b = vec3(f0[nextIdx], f0[nextIdx + 1], f0[nextIdx + 2]);
                } else if (fiber == 1) {
                    a = vec3(f1[idx], f1[idx + 1], f1[idx + 2]);
                    b = vec3(f1[nextIdx], f1[nextIdx + 1], f1[nextIdx + 2]);
                } else if (fiber == 2) {
                    a = vec3(f2[idx], f2[idx + 1], f2[idx + 2]);
                    b = vec3(f2[nextIdx], f2[nextIdx + 1], f2[nextIdx + 2]);
                } else if (fiber == 3) {
                    a = vec3(f3[idx], f3[idx + 1], f3[idx + 2]);
                    b = vec3(f3[nextIdx], f3[nextIdx + 1], f3[nextIdx + 2]);
                } else if (fiber == 4) {
                    a = vec3(f4[idx], f4[idx + 1], f4[idx + 2]);
                    b = vec3(f4[nextIdx], f4[nextIdx + 1], f4[nextIdx + 2]);
                } else {
                    a = vec3(f5[idx], f5[idx + 1], f5[idx + 2]);
                    b = vec3(f5[nextIdx], f5[nextIdx + 1], f5[nextIdx + 2]);
                }

                float dist = distanceToSegment(rayPos, a, b);
                if (dist < minDist) {
                    minDist = dist;
                    nearestShell = shellIdx;
                }
            }
        }

        // Compute density (solid tube, only nearest segment)
        float density = max(0.0, (TUBE_RADIUS - minDist) / TUBE_RADIUS);
        density = density * density; // Quadratic

        if (density > 0.0) {
            // Color from shell index (latitude gradient)
            float shellAngle = shells[nearestShell];
            float hue = mix(0.0, 0.55, (shellAngle - PI/6.0) / (PI/2.0 - PI/6.0));
            vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95));

            // Gentle depth brightness falloff
            float rayDepth = length(rayPos - camPos);
            float brightness = mix(0.85, 1.0, exp(-0.03 * rayDepth));
            fiberColor *= brightness;

            // Alpha accumulation
            float stepAlpha = 1.0 - exp(-density * 4.5);
            color += (1.0 - alpha) * stepAlpha * fiberColor;
            alpha += (1.0 - alpha) * stepAlpha;
        }

        // Advance ray
        rayPos += rayDir * STEP_SIZE;
    }

    // Blend with dark background
    vec3 background = vec3(0.02);
    vec3 finalColor = mix(background, color, alpha);

    gl_FragColor = vec4(finalColor, 1.0);
}
