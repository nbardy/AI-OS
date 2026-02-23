#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

// Distance from point p to line segment (a,b)
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    vec3 ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    vec3 closest = a + t * ab;
    return length(p - closest);
}

// HSV to RGB conversion
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    // Aspect-correct UV
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;

    // Camera setup: orbital at distance 4.5, Y-offset 1.2
    float camAngle = u_time * 0.25;
    float camDist = 4.5;
    vec3 camPos = vec3(camDist * cos(camAngle), 1.2, camDist * sin(camAngle));
    vec3 target = vec3(0.0, 0.0, 0.0);
    vec3 camForward = normalize(target - camPos);
    vec3 camRight = normalize(cross(vec3(0.0, 1.0, 0.0), camForward));
    vec3 camUp = cross(camForward, camRight);

    // Ray direction
    vec3 rayDir = normalize(camForward + uv.x * camRight + uv.y * camUp);
    vec3 rayPos = camPos;

    // Generate 4 fibers on single Clifford torus (eta = pi/4)
    // 4 fibers × 40 segments × 3 components = 480 floats
    float fiberPos[480];

    float eta = 3.14159265 / 4.0;  // Single shell angle
    int numFibers = 4;
    int segsPerFiber = 40;

    for(int f = 0; f < 4; f++) {
        // Base theta offset to separate fibers around the torus
        float thetaBase = float(f) * 3.14159265 * 0.5;

        for(int s = 0; s < 40; s++) {
            float t = float(s) / 40.0;
            float theta = thetaBase + t * 2.0 * 3.14159265;

            // Phase animation: add time-varying offset
            float xi = theta + u_time * 0.3;

            // Hopf quaternion parameterization
            float phi = eta;
            float qw = cos(phi * 0.5) * cos(xi);
            float qx = cos(phi * 0.5) * sin(xi);
            float qy = sin(phi * 0.5) * cos(xi);
            float qz = sin(phi * 0.5) * sin(xi);

            // Direct S³→R³ stereographic projection
            float denom = 1.0 - qw + 0.35;
            vec3 p3d = vec3(qx, qy, qz) / denom;
            p3d *= 0.85;  // Post-projection scale

            // Store in flat array
            int idx = f * 120 + s * 3;
            fiberPos[idx + 0] = p3d.x;
            fiberPos[idx + 1] = p3d.y;
            fiberPos[idx + 2] = p3d.z;
        }
    }

    // Ray marching with crossing detection
    vec3 color = vec3(0.02);  // Dark background
    float tubeRadius = 0.11;
    float stepSize = 0.1;
    int numSteps = 48;

    for(int step = 0; step < 48; step++) {
        // Check distances at current position BEFORE advancing
        float minDist[4];
        minDist[0] = 1e10;
        minDist[1] = 1e10;
        minDist[2] = 1e10;
        minDist[3] = 1e10;

        // Compute minimum distance to each fiber
        for(int f = 0; f < 4; f++) {
            for(int s = 0; s < 40; s++) {
                int idx = f * 120 + s * 3;
                vec3 segA = vec3(fiberPos[idx], fiberPos[idx+1], fiberPos[idx+2]);

                int nextS = s + 1;
                if(nextS >= 40) nextS = 0;
                int nextIdx = f * 120 + nextS * 3;
                vec3 segB = vec3(fiberPos[nextIdx], fiberPos[nextIdx+1], fiberPos[nextIdx+2]);

                float dist = distanceToSegment(rayPos, segA, segB);
                if(dist < minDist[f]) {
                    minDist[f] = dist;
                }
            }
        }

        // Detect crossing points: count fibers that are "near"
        int crossCount = 0;
        for(int f = 0; f < 4; f++) {
            if(minDist[f] < tubeRadius * 2.5) {
                crossCount++;
            }
        }
        bool isCrossing = (crossCount >= 2);

        // Find winning fiber (smallest distance overall)
        float winningDist = minDist[0];
        int winningFiber = 0;
        for(int f = 1; f < 4; f++) {
            if(minDist[f] < winningDist) {
                winningDist = minDist[f];
                winningFiber = f;
            }
        }

        // Solid tube density (only for winning fiber)
        if(winningDist < tubeRadius) {
            float density = (tubeRadius - winningDist) / tubeRadius;
            density = density * density;  // Quadratic

            // Apply crossing brightness boost
            if(isCrossing) {
                density *= 1.5;
            }

            // Fiber color based on latitude gradient
            float hue = 0.0;
            if(winningFiber == 0) hue = 0.0;        // Deep red
            else if(winningFiber == 1) hue = 30.0/360.0;  // Amber
            else if(winningFiber == 2) hue = 180.0/360.0; // Teal
            else hue = 260.0/360.0;                 // Indigo

            vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95));

            // Apply white shift at crossings
            if(isCrossing) {
                fiberColor = mix(fiberColor, vec3(1.0), 0.3);
            }

            float alpha = 1.0 - exp(-density * 4.5);
            alpha *= 0.85;  // Transparency for overlap
            color = mix(color, fiberColor, alpha);
        }

        // Glow halo at 1.5x tube radius
        float glowRadius = tubeRadius * 1.5;
        if(winningDist < glowRadius) {
            float glowDist = winningDist - tubeRadius;
            if(glowDist > 0.0) {
                float hue = 0.0;
                if(winningFiber == 0) hue = 0.0;
                else if(winningFiber == 1) hue = 30.0/360.0;
                else if(winningFiber == 2) hue = 180.0/360.0;
                else hue = 260.0/360.0;

                vec3 glowColor = hsv2rgb(vec3(hue, 0.95, 0.95));
                float glowIntensity = exp(-glowDist * 5.0) * 0.08;
                color += glowColor * glowIntensity;
            }
        }

        // Advance ray
        rayPos += rayDir * stepSize;
    }

    gl_FragColor = vec4(color, 1.0);
}
