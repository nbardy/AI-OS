#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

const float PI = 3.14159265359;
const int NUM_FIBERS = 8;
const int SAMPLES_PER_FIBER = 40;
const int FLOATS_PER_FIBER = 120; // 40 samples * 3 coords

// Distance from point to line segment
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    vec3 ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    vec3 closest = a + t * ab;
    return length(p - closest);
}

// HSV to RGB conversion
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    // Declare fiber data array inside main (MANDATORY for GLSL ES)
    float fiberData[960];

    // Generate 8 fibers: 4 shells × 2 rotations
    float shells[4];
    shells[0] = PI / 8.0;
    shells[1] = PI / 4.0;
    shells[2] = 3.0 * PI / 8.0;
    shells[3] = PI / 2.0;

    float rotations[2];
    rotations[0] = 0.0;
    rotations[1] = PI / 2.0;

    int dataIdx = 0;

    // Generate all fiber data
    for (int fiberIdx = 0; fiberIdx < NUM_FIBERS; fiberIdx++) {
        int shellIdx = fiberIdx / 2;
        int rotIdx = fiberIdx - shellIdx * 2;

        float phi = shells[shellIdx];
        float rotation = rotations[rotIdx];

        for (int i = 0; i < SAMPLES_PER_FIBER; i++) {
            float t = float(i) / float(SAMPLES_PER_FIBER);
            float theta = t * 2.0 * PI + rotation;

            // Correct Hopf quaternion (MANDATORY)
            float cp2 = cos(phi * 0.5);
            float sp2 = sin(phi * 0.5);
            float ct = cos(theta);
            float st = sin(theta);

            vec4 q = vec4(cp2 * ct, cp2 * st, sp2 * ct, sp2 * st);

            // Hopf map: S³ → S²
            float X = 2.0 * (q.x * q.y + q.z * q.w);
            float Y = 2.0 * (q.y * q.z - q.x * q.w);
            float Z = q.x * q.x - q.y * q.y - q.z * q.z + q.w * q.w;

            // Stereographic projection with singularity protection (MANDATORY)
            float denom = 1.0 - Z + 0.35;
            vec3 p3d = vec3(2.0 * X / denom, 2.0 * Y / denom, (1.0 + Z) / denom);

            // Post-projection scale (MANDATORY)
            p3d *= 0.85;

            // Store in array
            fiberData[dataIdx] = p3d.x;
            fiberData[dataIdx + 1] = p3d.y;
            fiberData[dataIdx + 2] = p3d.z;
            dataIdx += 3;
        }
    }

    // Setup camera (Y-offset orbit, NOT spherical - MANDATORY)
    float camAngle = u_time * 0.25;
    float camDist = 4.5;
    vec3 camPos = vec3(camDist * cos(camAngle), 1.5, camDist * sin(camAngle));

    // Ray setup
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;
    vec3 target = vec3(0.0, 0.0, 0.0);
    vec3 forward = normalize(target - camPos);
    vec3 right = normalize(cross(forward, vec3(0.0, 1.0, 0.0)));
    vec3 up = cross(right, forward);
    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);

    // Ray marching with accumulation
    vec3 color = vec3(0.0);
    float totalAlpha = 0.0;

    float tubeRadius = 0.11;
    float glowRadius = tubeRadius * 1.5;

    for (float depth = 0.0; depth < 12.0; depth += 0.15) {
        if (totalAlpha > 0.99) break;

        vec3 rayPos = camPos + rayDir * depth;

        float minDist = 1000.0;
        int closestFiber = -1;

        // Check all fibers (CHECK BEFORE STEP - MANDATORY)
        for (int fiberIdx = 0; fiberIdx < NUM_FIBERS; fiberIdx++) {
            int baseIdx = fiberIdx * FLOATS_PER_FIBER;

            // Check all 40 segments in this fiber
            for (int segIdx = 0; segIdx < SAMPLES_PER_FIBER; segIdx++) {
                int idx1 = baseIdx + segIdx * 3;
                int idx2 = baseIdx + ((segIdx + 1) % SAMPLES_PER_FIBER) * 3;

                vec3 p1 = vec3(fiberData[idx1], fiberData[idx1 + 1], fiberData[idx1 + 2]);
                vec3 p2 = vec3(fiberData[idx2], fiberData[idx2 + 1], fiberData[idx2 + 2]);

                float d = distanceToSegment(rayPos, p1, p2);

                if (d < minDist) {
                    minDist = d;
                    closestFiber = fiberIdx;
                }
            }
        }

        // Convert to unsigned distance (MANDATORY)
        float unsignedDist = abs(minDist - tubeRadius);

        // Quadratic density (PROVEN)
        float density = unsignedDist * unsignedDist;

        // Add glow halo (PROVEN)
        float glowDist = abs(minDist - glowRadius);
        density += exp(-glowDist * 5.0) * 0.08;

        // Exponential alpha (PROVEN)
        float alpha = 1.0 - exp(-density * 4.5);
        alpha *= 0.85; // Transparency factor (PROVEN)
        alpha *= (1.0 - totalAlpha); // Proper alpha blending

        if (closestFiber >= 0 && alpha > 0.01) {
            // Color per fiber (PROVEN)
            float hue = float(closestFiber) / float(NUM_FIBERS);
            vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95));

            color += fiberColor * alpha;
            totalAlpha += alpha;
        }
    }

    // Composite over dark background (PROVEN)
    vec3 bgColor = vec3(0.02);
    color = mix(bgColor, color, totalAlpha);

    gl_FragColor = vec4(color, 1.0);
}
