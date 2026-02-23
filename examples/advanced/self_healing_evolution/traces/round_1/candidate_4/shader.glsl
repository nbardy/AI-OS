#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

const float PI = 3.14159265359;

// HSV to RGB conversion
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// Distance from point p to line segment a-b
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 pa = p - a;
    vec3 ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h);
}

// Hopf fibration with stereographic projection
vec3 hopfFiber(float phi, float theta, float rotation) {
    // Apply rotation offset to theta
    float t = theta + rotation;

    // MANDATORY quaternion form
    float cp2 = cos(phi * 0.5);
    float sp2 = sin(phi * 0.5);
    float ct = cos(t);
    float st = sin(t);

    vec4 q = vec4(
        cp2 * ct,
        cp2 * st,
        sp2 * ct,
        sp2 * st
    );

    // Stereographic projection with singularity protection
    float scale = 1.0 / (1.0 - q.w + 0.35);
    vec3 p3d = vec3(q.x, q.y, q.z) * scale;

    // Post-projection scale
    return p3d * 0.85;
}

void main() {
    vec2 uv = (gl_FragCoord.xy * 2.0 - u_resolution.xy) / u_resolution.y;

    // Camera setup: Y-offset orbit (MANDATORY form)
    float camAngle = u_time * 0.25;
    float camDist = 4.5;
    float camY = 1.5;
    vec3 camPos = vec3(camDist * cos(camAngle), camY, camDist * sin(camAngle));

    // Ray setup
    vec3 rayOrigin = camPos;
    vec3 forward = normalize(-camPos);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
    vec3 up = cross(forward, right);
    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);

    // Generate 8 fibers (2 tori × 4 rotations) with 40 segments each
    // Total: 8 × 40 × 3 = 960 floats (exactly at limit)
    float fiberData[960];

    int idx = 0;

    // Torus 1: phi = π/4, rotations 0, π/2, π, 3π/2
    float phi1 = PI * 0.25;
    float rotations1[4];
    rotations1[0] = 0.0;
    rotations1[1] = PI * 0.5;
    rotations1[2] = PI;
    rotations1[3] = PI * 1.5;

    for (int fib = 0; fib < 4; fib++) {
        for (int seg = 0; seg < 40; seg++) {
            float theta = float(seg) * 2.0 * PI / 40.0;
            vec3 p = hopfFiber(phi1, theta, rotations1[fib]);
            fiberData[idx++] = p.x;
            fiberData[idx++] = p.y;
            fiberData[idx++] = p.z;
        }
    }

    // Torus 2: phi = π/3, rotations π/4, 3π/4, 5π/4, 7π/4
    float phi2 = PI / 3.0;
    float rotations2[4];
    rotations2[0] = PI * 0.25;
    rotations2[1] = PI * 0.75;
    rotations2[2] = PI * 1.25;
    rotations2[3] = PI * 1.75;

    for (int fib = 0; fib < 4; fib++) {
        for (int seg = 0; seg < 40; seg++) {
            float theta = float(seg) * 2.0 * PI / 40.0;
            vec3 p = hopfFiber(phi2, theta, rotations2[fib]);
            fiberData[idx++] = p.x;
            fiberData[idx++] = p.y;
            fiberData[idx++] = p.z;
        }
    }

    // Ray march with depth tracking
    vec3 color = vec3(0.0);
    float alpha = 0.0;
    float tubeRadius = 0.11;
    float glowRadius = tubeRadius * 1.5;

    for (int step = 0; step < 160; step++) {
        float t = float(step) * 0.05;
        vec3 rayPos = rayOrigin + rayDir * t;
        float currentDepth = t;

        // Check BEFORE step (MANDATORY)
        float minDist = 1000.0;

        // Check all 8 fibers × 40 segments
        for (int fiber = 0; fiber < 8; fiber++) {
            int baseIdx = fiber * 120; // 40 segments × 3 coords

            for (int seg = 0; seg < 40; seg++) {
                int i0 = baseIdx + seg * 3;
                int i1 = baseIdx + ((seg + 1) % 40) * 3;

                vec3 p0 = vec3(fiberData[i0], fiberData[i0 + 1], fiberData[i0 + 2]);
                vec3 p1 = vec3(fiberData[i1], fiberData[i1 + 1], fiberData[i1 + 2]);

                float dist = distanceToSegment(rayPos, p0, p1);
                minDist = min(minDist, dist);
            }
        }

        // Convert to unsigned (MANDATORY)
        minDist = abs(minDist);

        // Chromatic depth separation: map depth to hue
        float depthHue = mix(0.05, 0.58, smoothstep(1.0, 5.0, currentDepth));
        vec3 fiberColor = hsv2rgb(vec3(depthHue, 0.95, 0.95));

        // Core fiber density
        if (minDist < tubeRadius) {
            float d = 1.0 - minDist / tubeRadius;
            float density = d * d; // quadratic falloff
            float localAlpha = (1.0 - exp(-density * 4.5)) * 0.85; // transparency factor

            color += fiberColor * localAlpha * (1.0 - alpha);
            alpha += localAlpha * (1.0 - alpha);
        }

        // Glow halo
        if (minDist < glowRadius && minDist >= tubeRadius) {
            float glowDist = minDist - tubeRadius;
            float glowIntensity = exp(-glowDist * 5.0) * 0.08;

            color += fiberColor * glowIntensity * (1.0 - alpha);
            alpha += glowIntensity * (1.0 - alpha);
        }

        if (alpha > 0.99) break;
    }

    // Dark navy background
    vec3 backgroundColor = vec3(0.01, 0.01, 0.03);
    color = color + backgroundColor * (1.0 - alpha);

    gl_FragColor = vec4(color, 1.0);
}
