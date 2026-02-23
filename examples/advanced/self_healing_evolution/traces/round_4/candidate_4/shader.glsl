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
    // Standard aspect-corrected UV
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Orbital camera: distance 3.0, Y-offset 1.2, slow rotation
    float angle = u_time * 0.25;
    vec3 camPos = vec3(3.0 * cos(angle), 1.2, 3.0 * sin(angle));
    vec3 camTarget = vec3(0.0, 0.0, 0.0);

    // Camera basis vectors
    vec3 forward = normalize(camTarget - camPos);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
    vec3 up = cross(forward, right);

    // Ray direction
    vec3 rayDir = normalize(forward + uv.x * right + uv.y * up);
    vec3 rayPos = camPos;

    // Fiber configuration: 4 fibers in 2 families
    // Family A (inner, warm): η=π/6, rotations 0 and π
    // Family B (outer, cool): η=π/3, rotations π/4 and 5π/4
    float phi_values[4];
    phi_values[0] = 3.14159265 / 6.0;  // π/6
    phi_values[1] = 3.14159265 / 6.0;  // π/6
    phi_values[2] = 3.14159265 / 3.0;  // π/3
    phi_values[3] = 3.14159265 / 3.0;  // π/3

    float rot_values[4];
    rot_values[0] = 0.0;
    rot_values[1] = 3.14159265;        // π
    rot_values[2] = 3.14159265 / 4.0;  // π/4
    rot_values[3] = 5.0 * 3.14159265 / 4.0;  // 5π/4

    float hue_values[4];
    hue_values[0] = 0.08;  // gold
    hue_values[1] = 0.05;  // copper
    hue_values[2] = 0.52;  // cyan
    hue_values[3] = 0.55;  // silver-blue

    float sat_values[4];
    sat_values[0] = 0.9;
    sat_values[1] = 0.85;
    sat_values[2] = 0.9;
    sat_values[3] = 0.7;

    float val_values[4];
    val_values[0] = 1.0;
    val_values[1] = 0.9;
    val_values[2] = 1.0;
    val_values[3] = 0.85;

    // Rendering parameters
    float tubeRadius = 0.06;
    float glowRadius = tubeRadius * 1.5;
    float stepSize = 0.10;
    int numSteps = 64;
    int numSegments = 40;
    float epsilon = 0.15;
    float scale = 1.5;

    // Accumulation variables
    vec3 accumColor = vec3(0.0);
    float accumAlpha = 0.0;

    // Ray march
    for (int step = 0; step < 64; step++) {
        if (step >= numSteps) break;

        float t = float(step) * stepSize;
        vec3 p = rayPos + rayDir * t;

        float minDist = 1000.0;
        int closestFiber = -1;

        // Check distance to all fiber segments
        for (int fiberIdx = 0; fiberIdx < 4; fiberIdx++) {
            float phi = phi_values[fiberIdx];
            float rot = rot_values[fiberIdx];

            float cosPhi2 = cos(phi * 0.5);
            float sinPhi2 = sin(phi * 0.5);

            // Generate segments for this fiber
            for (int seg = 0; seg < 40; seg++) {
                if (seg >= numSegments) break;

                float theta0 = 2.0 * 3.14159265 * float(seg) / float(numSegments);
                float theta1 = 2.0 * 3.14159265 * float((seg + 1) % numSegments) / float(numSegments);

                // Segment start
                vec4 q0;
                q0.x = cosPhi2 * cos(theta0);
                q0.y = cosPhi2 * sin(theta0);
                q0.z = sinPhi2 * cos(theta0 + rot);
                q0.w = sinPhi2 * sin(theta0 + rot);

                vec3 p0 = q0.xyz / (1.0 - q0.w + epsilon);
                p0 *= scale;

                // Segment end
                vec4 q1;
                q1.x = cosPhi2 * cos(theta1);
                q1.y = cosPhi2 * sin(theta1);
                q1.z = sinPhi2 * cos(theta1 + rot);
                q1.w = sinPhi2 * sin(theta1 + rot);

                vec3 p1 = q1.xyz / (1.0 - q1.w + epsilon);
                p1 *= scale;

                // Distance to line segment
                vec3 v = p1 - p0;
                vec3 w = p - p0;
                float c1 = dot(w, v);
                float c2 = dot(v, v);
                float b = clamp(c1 / c2, 0.0, 1.0);
                vec3 closest = p0 + b * v;
                float dist = length(p - closest);

                if (dist < minDist) {
                    minDist = dist;
                    closestFiber = fiberIdx;
                }
            }
        }

        // Render closest fiber segment
        if (closestFiber >= 0 && minDist < glowRadius) {
            vec3 fiberColor = hsv2rgb(vec3(
                hue_values[closestFiber],
                sat_values[closestFiber],
                val_values[closestFiber]
            ));

            float alpha = 0.0;

            // Core tube
            if (minDist < tubeRadius) {
                float density = (tubeRadius - minDist) / tubeRadius;
                density = density * density;  // Quadratic
                alpha = (1.0 - exp(-density * 4.5)) * 0.85;
            }

            // Glow halo
            float glowDist = max(0.0, minDist - tubeRadius);
            float glowAlpha = exp(-glowDist * 5.0) * 0.08;
            alpha += glowAlpha;

            // Apply depth fog
            float fogFactor = exp(-t * 0.3);
            vec3 fogged = fiberColor * fogFactor;

            // Front-to-back alpha compositing
            accumColor += fogged * alpha * (1.0 - accumAlpha);
            accumAlpha += alpha * (1.0 - accumAlpha);

            if (accumAlpha > 0.95) break;
        }
    }

    // Background
    vec3 backgroundColor = vec3(0.02);
    vec3 finalColor = accumColor + backgroundColor * (1.0 - accumAlpha);

    gl_FragColor = vec4(finalColor, 1.0);
}
