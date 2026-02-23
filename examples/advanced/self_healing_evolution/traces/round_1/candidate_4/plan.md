# Nested Villarceau Circles with Chromatic Depth Separation - Implementation Plan

## Mathematical Foundation

### Core Equations
1. **Hopf Fibration Quaternion** (MANDATORY form):
   ```
   q = (cos(phi/2)*cos(theta), cos(phi/2)*sin(theta), sin(phi/2)*cos(theta), sin(phi/2)*sin(theta))
   ```
   - phi = shell angle (latitude on S³)
   - theta = 0..2π (parameter along fiber)

2. **Stereographic Projection**:
   ```
   scale = 1.0 / (1.0 - q.w + 0.35)  // 0.35 singularity protection
   p3D = vec3(q.x, q.y, q.z) * scale * 0.85  // post-projection scale
   ```

3. **Villarceau Circle Configuration**:
   - **Torus 1** (Clifford torus): phi = π/4, rotations: 0, π/2, π, 3π/2
   - **Torus 2** (second shell): phi = π/3, rotations: π/4, 3π/4, 5π/4, 7π/4
   - Total: 8 fibers arranged as 2 nested torus families

4. **Chromatic Depth Mapping**:
   ```
   currentDepth = float(step) * stepSize
   depthHue = mix(0.05, 0.58, smoothstep(1.0, 5.0, currentDepth))
   // 0.05 = warm gold (near), 0.58 = cool teal (far)
   ```

### Coordinate Mapping
- Camera: Y-offset orbit `vec3(4.5*cos(angle), 1.5, 4.5*sin(angle))` where angle = u_time * 0.25
- Ray origin: camera position
- Ray direction: from camera through pixel (perspective projection)
- Distance field: minimum distance to all 40 segments of all 8 fibers
- Density accumulation: quadratic falloff `d*d`, exponential alpha `1-exp(-density*4.5)`

### Key Simplifications
- Pre-compute all 8 fibers × 40 segments = 320 points (960 floats) in flat array inside main()
- Use linear segment interpolation between discrete theta samples (no continuous evaluation)
- Single-pass ray march with depth tracking, no multi-pass rendering
- Depth-to-hue is the ONLY per-sample variation (no per-fiber hue assignment)

## Implementation Plan

### Step 1: Setup Camera and Ray Generation
- Orbital camera at distance 4.5, Y-offset 1.5, rotation 0.25 rad/s
- Aspect-correct UV coordinates
- Perspective ray direction with ~60° FOV

### Step 2: Generate 8 Fiber Geometries
- Loop over 2 tori (phi = π/4 and π/3)
- Loop over 4 rotations per torus (offset by π/4 between tori)
- For each fiber, loop theta = 0..2π in 40 steps
- Apply Hopf quaternion + stereographic projection + post-scale 0.85
- Store in flat float array `fiberData[960]` as [x0,y0,z0, x1,y1,z1, ...]

### Step 3: Ray March with Depth Tracking
- March from t=0 to t=8 in steps of 0.05 (160 steps)
- At each step:
  - Compute rayPos = rayOrigin + rayDir * t
  - Check distance to all 320 segments using distanceToSegment()
  - Convert to unsigned distance
  - Accumulate density with quadratic falloff
  - Track currentDepth = t

### Step 4: Chromatic Depth Compositing
- When fiber contributes density (distance < threshold):
  - Compute depthHue = mix(0.05, 0.58, smoothstep(1.0, 5.0, currentDepth))
  - Convert HSV(depthHue, 0.95, 0.95) to RGB
  - Apply transparency factor 0.85
  - Accumulate color with front-to-back blending
- Add subtle glow halo at 1.5× tube radius

### Step 5: Background and Output
- Dark navy background vec3(0.01, 0.01, 0.03)
- Blend accumulated fiber color over background
- Output to gl_FragColor

## Anticipated Challenges

### Challenge 1: Array Size at Limit
- 8 fibers × 40 segments × 3 coords = 960 floats (exactly at MANDATORY limit)
- **Solution**: Carefully verify loop bounds, no overflow, no extra data

### Challenge 2: Depth-to-Hue Mapping Range
- If depth range is wrong, all fibers appear same color
- **Solution**: Use smoothstep(1.0, 5.0, depth) — empirically tuned to camera distance 4.5 and march range 0-8

### Challenge 3: Maintaining Full Brightness
- Must avoid depth attenuation that killed R0 Candidate 3
- **Solution**: Depth affects ONLY hue, not value/saturation. HSV value stays at 0.95 always.

### Challenge 4: Torus Family Separation
- Two tori at different phi angles must remain visually distinct
- **Solution**: pi/4 vs pi/3 gives ~15° latitude difference; rotation offset π/4 ensures spatial interleaving

### Challenge 5: Segment Distance Edge Cases
- Degenerate segments (a ≈ b) from quantization
- **Solution**: 40 segments on smooth circle should avoid this; distanceToSegment handles it anyway

## Visual Prediction

### Expected Appearance at t=0
- **Foreground (warm zone)**: 3-4 luminous gold-amber rings threading through each other
- **Background (cool zone)**: 3-4 cyan-teal rings receding behind the warm rings
- **Spatial arrangement**: Two sets of 4 rings each, one nested inside the other, rotated 45° relative
- **Color gradient**: Smooth warm-to-cool transition as rings pass from near to far along the ray depth
- **Background**: Deep navy-black providing maximum contrast
- **Motion** (over time): As camera orbits, rings exchange warm/cool tones — a ring that was gold in front becomes teal as it rotates behind

### Key Visual Features to Verify
1. **8 distinct fiber loops** visible (not blurred into a single blob)
2. **Depth-driven color variation**: Clear warm tones in foreground, cool tones in background
3. **No dimming/fading**: All fibers at full brightness regardless of depth
4. **Interleaving geometry**: Inner and outer torus families threading through each other's gaps
5. **3D readability**: Orbital camera reveals depth structure, crossings show clear over/under relationships
6. **Smooth color transitions**: No banding or discontinuities in the warm→cool gradient

### Success Criteria
- Score >7.5/10 requires: all 8 fibers visible, clear depth perception, novel color treatment, no technical errors
- The chromatic depth separation is the innovation — it must be visually obvious and enhance (not confuse) 3D structure
- Breaking 7.5→8+ requires this to be MORE compelling than per-fiber rainbow hue, which the judge found generic
