# Synthesis Plan: Hopf Fibration with Proven Patterns

## Mathematical Foundation

### Core Equations
1. **Hopf Map (S³ → S²)**: For each fiber, parameterized by base circle angle `phi`:
   ```
   theta ∈ [0, 2π] (circle parameter)
   q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ+rot), sin(φ/2)sin(θ+rot))
   ```

2. **Stereographic Projection (S³ → R³)**:
   ```
   p = q.xyz / (1 - q.w + ε)
   ε = 0.15 (proven singularity protection)
   ```

3. **Post-Projection Scaling**:
   ```
   p *= 1.5 (proven scale factor)
   ```

### Fiber Configuration
- **6 fibers total** (proven high-scorer configuration)
- **3 shell angles**: π/6, π/3, π/2 (widely spaced for distinct radii)
- **2 rotations per shell**: 0, π (minimizes overlap, maximizes clarity)
- **Warm/Cool color split**:
  - Shells 1,2 (φ = π/6, π/3): Warm hues (red-orange-yellow)
  - Shell 3 (φ = π/2): Cool hues (cyan-blue)

### Segment Discretization
- 40 segments per fiber with wraparound
- Segment endpoints: `theta_i = i * 2π / 40`

## Implementation Plan

### Step 1: Camera Setup
```
angle = u_time * 0.25 (proven rotation speed)
dist = 3.0 (proven distance)
Y_OFFSET = 1.4 (proven orbital height)
camera = vec3(dist*cos(angle), Y_OFFSET, dist*sin(angle))
lookAt = vec3(0, 0, 0)
```

### Step 2: Ray Marching Setup
```
uv = (gl_FragCoord.xy - 0.5*u_resolution.xy) / u_resolution.y (standard formula)
rayDir = normalize(lookAt + right*uv.x + up*uv.y - camera)
rayOrigin = camera
stepSize = 0.10 (proven)
maxSteps = 60 (60*6*40 = 14,400 iterations, under budget)
```

### Step 3: Fiber Data in main()
```glsl
// Build fiber array inline (6 fibers x 4 floats = 24 floats)
// Format: [phi, rotation, hue, saturation]
float fibers[24];
int idx = 0;

// Shell 1 (phi = π/6): Warm
fibers[idx++] = PI/6.0; fibers[idx++] = 0.0; fibers[idx++] = 0.05; fibers[idx++] = 0.95;  // Red
fibers[idx++] = PI/6.0; fibers[idx++] = PI;  fibers[idx++] = 0.15; fibers[idx++] = 0.95;  // Orange

// Shell 2 (phi = π/3): Warm
fibers[idx++] = PI/3.0; fibers[idx++] = 0.0; fibers[idx++] = 0.10; fibers[idx++] = 0.95;  // Yellow
fibers[idx++] = PI/3.0; fibers[idx++] = PI;  fibers[idx++] = 0.08; fibers[idx++] = 0.95;  // Orange-Yellow

// Shell 3 (phi = π/2): Cool
fibers[idx++] = PI/2.0; fibers[idx++] = 0.0; fibers[idx++] = 0.55; fibers[idx++] = 0.95;  // Cyan
fibers[idx++] = PI/2.0; fibers[idx++] = PI;  fibers[idx++] = 0.65; fibers[idx++] = 0.95;  // Blue
```

### Step 4: Ray March Loop
```glsl
for (int step = 0; step < 60; step++) {
    vec3 p = rayOrigin + rayDir * t;

    float minDist = 1e10;
    vec3 closestColor = vec3(0);

    // Check all 6 fibers
    for (int f = 0; f < 6; f++) {
        float phi = fibers[f*4];
        float rot = fibers[f*4+1];
        float hue = fibers[f*4+2];
        float sat = fibers[f*4+3];

        // Check all 40 segments
        for (int seg = 0; seg < 40; seg++) {
            float theta0 = float(seg) * TWO_PI / 40.0;
            float theta1 = float((seg+1)%40) * TWO_PI / 40.0;

            // Compute S³ points
            vec4 q0 = hopfPoint(phi, theta0, rot);
            vec4 q1 = hopfPoint(phi, theta1, rot);

            // Stereographic projection
            vec3 p0 = q0.xyz / (1.0 - q0.w + 0.15) * 1.5;
            vec3 p1 = q1.xyz / (1.0 - q1.w + 0.15) * 1.5;

            // Distance to segment
            float segDist = distToSegment(p, p0, p1);

            if (segDist < minDist) {
                minDist = segDist;
                closestColor = hsv2rgb(vec3(hue, sat, 0.95));
            }
        }
    }

    // Tube density (only for closest fiber)
    float tubeRadius = 0.07;
    float glowRadius = tubeRadius * 1.5;

    if (minDist < glowRadius) {
        float coreDensity = 0.0;
        float glowDensity = 0.0;

        if (minDist < tubeRadius) {
            coreDensity = (tubeRadius - minDist) / tubeRadius;
            coreDensity = coreDensity * coreDensity;  // Quadratic
        }

        float glowDist = max(0.0, minDist - tubeRadius);
        glowDensity = exp(-glowDist * 5.0) * 0.08;

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
```

### Step 5: Background & Output
```glsl
color += vec3(0.02) * (1.0 - accumulated);  // Dark background
gl_FragColor = vec4(color, 1.0);
```

## Anticipated Challenges

### Challenge 1: Fiber Overlap at Same Shell
With 2 rotations per shell spaced π apart, fibers may visually merge after projection.
**Solution**: Wide shell spacing (π/6, π/3, π/2) ensures distinct projected radii even if rotations overlap.

### Challenge 2: Dashed/Segmented Appearance
40 segments with 0.10 step size may miss geometry between segments.
**Solution**: Glow halo at 1.5x tube radius (proven critical by R3C3 vs R3C1).

### Challenge 3: GPU Budget
60 steps × 6 fibers × 40 segments = 14,400 iterations.
**Mitigation**: Early exit on accumulated > 0.95; rays pointing away from geometry exit quickly.

### Challenge 4: Color Distinguishability
6 fibers need distinct colors while maintaining warm/cool structure.
**Solution**: Vary hue within warm (0.05-0.15) and cool (0.55-0.65) ranges; high saturation (0.95) ensures separation.

## Visual Prediction

### Expected Output
- **Geometric Structure**: 3 concentric "layers" of linked circles, each layer containing 2 interwoven fibers
  - Innermost layer (π/6): Tightest circles, warmest colors (red/orange)
  - Middle layer (π/3): Medium circles, warm colors (yellow/orange)
  - Outer layer (π/2): Largest circles, cool colors (cyan/blue)

- **Color Palette**: Smooth transition from warm reds/oranges/yellows in inner shells to cool cyans/blues in outer shell, encoding mathematical structure

- **Lighting/Depth**: Soft glow halos around each fiber tube; front fibers brighter due to alpha accumulation; depth visible through occlusion

- **Camera View**: Gentle orbital rotation reveals 3D topology; Y-offset of 1.4 provides oblique view showing linking without overhead collapse

### Verification Checks
1. **Distinct fibers**: Should see 6 separate colored ribbons, not merged blobs
2. **Circular forms**: Each fiber projects as a circle (or ellipse from oblique view)
3. **Linking structure**: Fibers pass through each other demonstrating Hopf linking
4. **Smooth tubes**: No dashed/grainy artifacts (glow should fill gaps)
5. **Color encoding**: Warm inner, cool outer shells immediately visible

### Success Criteria
- Visually matches "colorful interlocking circles" description from top performers
- Mathematical structure evident (not abstract art)
- Clean, smooth rendering (no artifacts)
- Distinct from merged blob or sparse/invisible extremes
