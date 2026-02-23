# Implementation Plan: Hopf Fibers as Luminous Moebius Ribbons

## Mathematical Foundation

### Hopf Fibration Parametrization
Each fiber is a great circle in S³ parameterized as:
```
q(θ) = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ), sin(φ/2)sin(θ))
```
where:
- φ = latitude parameter (constant per fiber, determines which fiber on the Clifford torus)
- θ ∈ [0, 2π] = fiber parameter (traces the circle)

### Stereographic Projection to R³
```
p = (q.x, q.y, q.z) / (1 - q.w + 0.35)
```
The 0.35 offset prevents singularity at the south pole.

### Clifford Torus Equator
Using φ = π/4 places all fibers on the equator of the Clifford torus, the most visually stable configuration. Four fibers with rotation offsets ξ₁ ∈ {0, π/2, π, 3π/2} provide even angular spacing.

### Ribbon Geometry
Instead of round tubes (circular cross-section), ribbons have a **rectangular cross-section**:
- **Width**: 0.12 (perpendicular to tangent, in the ribbon plane)
- **Thickness**: 0.02 (perpendicular to ribbon plane)

For each segment from point A to point B:
1. Compute tangent: `T = normalize(B - A)`
2. Compute ribbon normal (perpendicular to tangent): `N = normalize(cross(T, vec3(0,1,0)))`
   - Fallback if T nearly vertical: `N = normalize(cross(T, vec3(1,0,0)))`
3. Ribbon surface is swept along the curve at distance ±0.06 from centerline in N direction

### Ribbon SDF
Given ray point P and segment [A, B] with normals [N_A, N_B]:
1. Find closest point Q on line segment AB (standard `distanceToSegment` logic)
2. Compute t = parameter along segment where Q lies
3. Interpolate ribbon normal: `N_interp = normalize(mix(N_A, N_B, t))`
4. Decompose residual vector `R = P - Q` into:
   - `tangentComponent = dot(R, T)` (along fiber direction - should be ~0 if Q is truly closest)
   - `ribbonPlaneComponent = dot(R, N_interp)` (perpendicular to ribbon, in its plane)
   - `ribbonNormalComponent = length(R - ribbonPlaneComponent * N_interp)` (out of plane)
5. Distance is box SDF in 2D cross-section:
   ```
   dist = max(abs(ribbonPlaneComponent) - 0.12, abs(ribbonNormalComponent) - 0.02)
   ```

**Simplification for implementation**: Since computing the full decomposition is complex, I'll use a hybrid approach:
- Compute closest point on segment (distance d_line)
- Project residual onto interpolated normal to get "flatness" factor
- Distance ≈ `max(d_line - width, abs(normalDistance) - thickness)`

This approximates ribbon behavior while staying within proven segment-distance patterns.

### Orientation-Dependent Brightness
To add depth cues via surface orientation:
```
ribbonFacing = abs(dot(N_interp, normalize(rayDir)))
brightness = mix(0.5, 1.0, ribbonFacing)
```
Ribbon faces perpendicular to view direction appear brighter, creating a sense of material surface.

## Implementation Plan

### Step 1: Define Fiber Configuration
- 4 fibers at φ = π/4 (Clifford torus equator)
- Rotation offsets: 0, π/2, π, 3π/2
- 40 segments per fiber
- Each segment stores: position (vec3) + ribbon normal (vec3) = 6 floats
- Total: 4 × 40 × 6 = 960 floats (exactly at limit)

### Step 2: Generate Fiber Data Inside main()
```glsl
float fiberData[960];
for (int fiberIdx = 0; fiberIdx < 4; fiberIdx++) {
    float xi1 = float(fiberIdx) * PI * 0.5;  // rotation offset
    float phi = PI * 0.25;  // equator

    for (int segIdx = 0; segIdx < 40; segIdx++) {
        float theta = float(segIdx) * TWO_PI / 40.0 + xi1;

        // Hopf quaternion
        vec4 q = vec4(
            cos(phi*0.5) * cos(theta),
            cos(phi*0.5) * sin(theta),
            sin(phi*0.5) * cos(theta),
            sin(phi*0.5) * sin(theta)
        );

        // Stereographic projection
        vec3 p = vec3(q.xyz) / (1.0 - q.w + 0.35);
        p *= 0.85;  // post-projection scale

        // Compute tangent for ribbon normal
        float thetaNext = float(segIdx + 1) * TWO_PI / 40.0 + xi1;
        vec4 qNext = vec4(
            cos(phi*0.5) * cos(thetaNext),
            cos(phi*0.5) * sin(thetaNext),
            sin(phi*0.5) * cos(thetaNext),
            sin(phi*0.5) * sin(thetaNext)
        );
        vec3 pNext = vec3(qNext.xyz) / (1.0 - qNext.w + 0.35) * 0.85;

        vec3 tangent = normalize(pNext - p);
        vec3 ribbonNormal = normalize(cross(tangent, vec3(0,1,0)));
        if (length(ribbonNormal) < 0.1) {
            ribbonNormal = normalize(cross(tangent, vec3(1,0,0)));
        }

        // Store position + normal
        int baseIdx = (fiberIdx * 40 + segIdx) * 6;
        fiberData[baseIdx + 0] = p.x;
        fiberData[baseIdx + 1] = p.y;
        fiberData[baseIdx + 2] = p.z;
        fiberData[baseIdx + 3] = ribbonNormal.x;
        fiberData[baseIdx + 4] = ribbonNormal.y;
        fiberData[baseIdx + 5] = ribbonNormal.z;
    }
}
```

### Step 3: Camera Setup
- Position: orbital at radius 4.5, elevation 1.5, rotation 0.25 rad/s
- Look at origin
- Build camera basis (forward, right, up)
- Ray direction from UV

### Step 4: Ray March Loop
```glsl
for (int step = 0; step < 100; step++) {
    // Check distance to all ribbon segments
    float minDist = 1e10;
    vec3 closestNormal = vec3(0,1,0);
    int closestFiber = 0;

    for (int fiberIdx = 0; fiberIdx < 4; fiberIdx++) {
        for (int segIdx = 0; segIdx < 40; segIdx++) {
            int nextIdx = (segIdx + 1) % 40;

            // Load segment endpoints and normals
            vec3 a = loadPos(fiberData, fiberIdx, segIdx);
            vec3 b = loadPos(fiberData, fiberIdx, nextIdx);
            vec3 na = loadNormal(fiberData, fiberIdx, segIdx);
            vec3 nb = loadNormal(fiberData, fiberIdx, nextIdx);

            // Distance to segment (standard proven approach)
            float t = clamp(dot(rayPos - a, b - a) / dot(b - a, b - a), 0.0, 1.0);
            vec3 closest = a + t * (b - a);
            float dist = length(rayPos - closest);

            // Ribbon cross-section: flat instead of round
            vec3 interpNormal = normalize(mix(na, nb, t));
            vec3 residual = rayPos - closest;
            float normalDist = abs(dot(residual, interpNormal));

            // Box cross-section: width in ribbon plane, thickness perpendicular
            float ribbonDist = max(dist - 0.12, normalDist - 0.02);

            if (ribbonDist < minDist) {
                minDist = ribbonDist;
                closestNormal = interpNormal;
                closestFiber = fiberIdx;
            }
        }
    }

    // Accumulate color if inside ribbon
    if (minDist < 0.0) {
        // Inside ribbon
        float density = (0.12 - abs(minDist)) / 0.12;
        density = density * density;

        // Orientation-dependent brightness
        float facing = abs(dot(closestNormal, normalize(rayDir)));
        float brightness = mix(0.6, 1.0, facing);

        // Warm color palette: red to gold
        float hue = float(closestFiber) * 0.03;  // 0.0, 0.03, 0.06, 0.09
        vec3 fiberColor = hsv2rgb(vec3(hue, 0.95, 0.95)) * brightness;

        float alpha = 1.0 - exp(-density * 4.5);
        alpha *= 0.85;  // transparency

        color = color * (1.0 - alpha) + fiberColor * alpha;
        opacity += alpha * (1.0 - opacity);

        if (opacity > 0.99) break;
    }

    // Step forward
    rayPos += rayDir * 0.09;
    if (length(rayPos) > 10.0) break;
}
```

### Step 5: Color Palette
- Fiber 0: hue 0.00 (deep red)
- Fiber 1: hue 0.03 (red-orange)
- Fiber 2: hue 0.06 (orange)
- Fiber 3: hue 0.09 (gold)
- Saturation 0.95, Value 0.95
- Background: vec3(0.02, 0.02, 0.03) (deep charcoal-navy)

## Anticipated Challenges

### Challenge 1: Ribbon Normal Stability
When tangent is near vertical, `cross(tangent, vec3(0,1,0))` becomes unstable.
**Solution**: Check if `length(ribbonNormal) < 0.1`, use fallback `cross(tangent, vec3(1,0,0))`.

### Challenge 2: Ribbon SDF Complexity
Full ribbon SDF requires decomposing residual into three orthogonal components.
**Solution**: Approximate with hybrid approach: segment distance for width, normal projection for thickness.

### Challenge 3: 960 Float Limit
4 fibers × 40 segments × 6 floats = exactly 960.
**Solution**: No margin for error. If compilation fails, reduce to 3 fibers (720 floats) or 35 segments (840 floats).

### Challenge 4: Orientation Brightness May Be Too Subtle
If `abs(dot(normal, rayDir))` variation is small, the surface effect won't be visible.
**Solution**: Use stronger mix range: `mix(0.5, 1.0, facing)` instead of `mix(0.8, 1.0, facing)`.

### Challenge 5: Thin Ribbons May Disappear at Distance
Thickness 0.02 is very thin; may not be hit by rays.
**Solution**: The width 0.12 is the primary dimension; thickness just affects perpendicular profile. If invisible, increase thickness to 0.04.

## Visual Prediction

### Expected Appearance
- Four luminous bands weaving around a torus-like shape
- Each band appears as a **flat ribbon** (not round tube) with visible width
- Ribbons catch light differently based on orientation:
  - Faces perpendicular to camera: bright, reflective appearance
  - Faces parallel to camera: dimmer, edge-on appearance
- Color gradient: warm spectrum from deep red through orange to gold
- Background: deep charcoal-navy (almost black)
- Overall composition: architectural, structured, with clear surface quality

### Key Visual Features to Verify
1. **Ribbon flatness**: Unlike previous round tubes, these should appear as strips/bands with visible width
2. **Orientation brightness**: As camera orbits, brightness should vary along each ribbon depending on which face is visible
3. **Four distinct fibers**: Each with consistent color throughout its loop
4. **Interlocking structure**: Ribbons should weave through each other on the Clifford torus surface
5. **Sharp edges**: Ribbons have defined boundaries (box cross-section) rather than soft falloff of round tubes
6. **Material quality**: Should feel like polished metal or glass ribbons, not glowing tubes

### Success Criteria
- Judge recognizes Hopf fibration structure (interlocking circles)
- Visual novelty: clearly different from round tube approach
- Depth cues: orientation-dependent brightness conveys 3D structure
- Color harmony: warm palette reads as cohesive
- Target score: 8+/10 (improvement over 7.5/10 baseline via sharper definition and surface-like quality)
