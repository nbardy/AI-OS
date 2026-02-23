# Implementation Plan: Hopf Fibration Shader (Round 1, Candidate 2)

## Mathematical Foundation

### Hopf Map (S³ → S²)
Using the proven quaternion parameterization:
```
q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ), sin(φ/2)sin(θ))
where φ = shell angle (fiber parameter)
      θ = 0..2π (parameter along fiber)
```

### Stereographic Projection (S² → R³)
```
(x, y, z) = (2*q.x, 2*q.y, 2*q.z) / (1 - q.w + 0.35)
```
- Singularity protection: 0.35 prevents division by zero
- Post-projection scale: 0.85 for optimal framing

### Camera Setup
- **Position**: `vec3(4.5*cos(angle), 1.5, 4.5*sin(angle))`
  - Y-offset = 1.5 (position, NOT spherical elevation angle)
  - Distance = 4.5 (proven optimal)
  - Orbital angle = u_time * 0.25 (slow reveal)
- **Target**: Origin (0, 0, 0)

### Fiber Configuration
- **8 fibers total**: 4 shells × 2 rotations
- **Shell angles**: π/8, π/4, 3π/8, π/2 (dense spacing)
- **Rotations**: 0, π/2 (avoids diametric overlap)
- **40 segments per fiber**: Smooth curves
- **Tube radius**: 0.11 (proven visibility)

## Implementation Plan

### Step 1: Data Structure (Inside main())
```glsl
float fiberData[960]; // 8 fibers × 40 points × 3 coords = 960 floats
```
- MANDATORY: Declared inside main() (global arrays fail in GLSL ES)
- Layout: [fiber0_point0_xyz, fiber0_point1_xyz, ..., fiber7_point39_xyz]

### Step 2: Fiber Generation
For each fiber (shell_idx, rotation_idx):
1. Calculate shell angle: `shells[shell_idx]`
2. Calculate rotation offset: `rotations[rotation_idx]`
3. For each of 40 segments:
   - `θ = rotation + segment/40 * 2π`
   - Compute quaternion q(shell_angle, θ)
   - Stereographic project → 3D point
   - Scale by 0.85
   - Store in fiberData array

### Step 3: Ray Marching Setup
- Ray origin: camera position
- Ray direction: perspective projection from UV
- 64 steps, max distance 12.0
- Step size: 0.15 (aggressive for solid shape)

### Step 4: Distance Field Evaluation
For each ray sample:
1. Find minimum distance to ALL fiber segments (320 segments total)
2. Use `distanceToSegment(p, a, b)` for curve accuracy
3. Tube SDF: `dist - 0.11`
4. Convert to unsigned: `abs(sdf)`

### Step 5: Volumetric Rendering
- **Density**: `quadratic(unsigned_dist)` → smooth falloff
- **Alpha**: `1 - exp(-density * 4.5)` → exponential accumulation
- **Transparency**: `alpha *= 0.85` per sample (fiber overlap)
- **Glow halo**: `exp(-dist * 5.0) * 0.08` at 1.5× tube radius

### Step 6: Color Assignment
- Per-fiber HSV color: `hsv2rgb(vec3(fiberID / 8.0, 0.95, 0.95))`
- Rainbow spectrum across 8 fibers
- High saturation (0.95) against dark background (0.02)

## Anticipated Challenges

### Challenge 1: Array Size Limit
- **Issue**: 8 fibers × 40 points × 3 coords = 960 floats (at limit)
- **Mitigation**: Can't add more fibers without reducing segments
- **Fallback**: If compilation fails, reduce to 6 fibers (720 floats)

### Challenge 2: Performance
- **Issue**: 64 ray steps × 320 segments = 20,480 distance checks
- **Optimization**: Early exit when accumulated alpha > 0.98
- **Expected**: Should run at interactive framerates on modern GPUs

### Challenge 3: Depth Perception
- **Issue**: Overlapping transparent fibers can appear flat
- **Solution**: Orbital camera animation reveals 3D structure
- **Verification**: Check that different fibers are distinguishable

### Challenge 4: Quaternion Correctness
- **Issue**: Easy to mix up angle parameters
- **Mitigation**: Use EXACT proven form, test at t=0 for immediate feedback
- **Verification**: Fibers should form circular loops, not blobs

## Visual Prediction

### Expected Output
1. **Structure**: 8 interlocking circular loops forming a torus-like arrangement
2. **Colors**: Rainbow gradient (red → orange → yellow → green → cyan → blue → purple → magenta)
3. **Motion**: Slow orbital rotation reveals 3D depth
4. **Transparency**: Fibers visibly overlap, showing through each other
5. **Glow**: Soft halos around each fiber against dark background

### Key Visual Features (Verification)
- ✓ Circular loops (not blobs or ribbons)
- ✓ 8 distinct colored fibers
- ✓ Smooth tube geometry (no faceting)
- ✓ Depth revealed by orbital motion
- ✓ High contrast against dark background
- ✓ Centered in frame (not clipped)

### At t=0
- Camera at angle=0 → positioned at (4.5, 1.5, 0)
- Looking at origin from the side with slight elevation
- Should see interlocking loops from oblique angle
- Some fibers in front, some behind (depth cues)

## Why This Should Score Higher

### Combines Proven Elements
- Correct quaternion math (mandatory)
- Y-offset camera, not spherical elevation (mandatory)
- Optimal rendering parameters from 7.5/10 shader
- 8 fibers with proven shell/rotation spacing

### Avoids Known Failures
- No spherical elevation angle (caused 1-5/10 scores)
- No aggressive depth attenuation (caused invisible geometry)
- No ribbon SDF (caused degenerate normals)
- No diametric rotations (caused overlaps)

### Expected Score: 7-8/10
- Should match or exceed prior 7.5/10 baseline
- Solid mathematical foundation + proven rendering
- May not reach 9-10 without experimental innovations
