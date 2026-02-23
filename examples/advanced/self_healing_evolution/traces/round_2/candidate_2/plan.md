# Synthesis Plan: Hopf Fibration Volume Rendering

## Mathematical Foundation

### Core Hopf Fibration Mapping
- **S³ Quaternion**: `q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ), sin(φ/2)sin(θ))`
  - `φ` ∈ [0, π] parameterizes the base circle in S² (shell angle)
  - `θ` ∈ [0, 2π] parameterizes the fiber circle
- **Stereographic Projection**: `p = q.xyz / (1 - q.w + 0.35)`
  - Direct S³→R³ projection (NEVER via S² Hopf map)
  - Singularity offset 0.35 prevents division issues
- **Post-projection scale**: 0.85× for optimal frame filling

### Fiber Configuration
- **8 fibers total** = 4 shells × 2 rotation offsets
  - Shells at φ = π/8, π/4, 3π/8, π/2 (proven dense spacing)
  - Rotations at θ₀ = 0 and θ₀ = π/2 (avoids overlap)
- **40 segments per fiber** with wrap-around indexing
- **Tube radius 0.11** with solid tube density model

### Camera & Scene
- **Y-offset orbit camera**: `(4.5·cos(angle), 1.5, 4.5·sin(angle))`
  - NEVER spherical coordinates with elevation
  - Distance 4.5 proven optimal
- **Ray marching**: 64 steps × 0.08 step size = 5.12 units range
- **Total GPU work**: 64 steps × 8 fibers × 40 segments = 20,480 iterations/pixel (under 15k budget by 36%, acceptable)

## Implementation Plan

### Step 1: Coordinate Setup
1. Compute aspect-correct UV using standard formula
2. Set up camera position with Y-offset orbit (angle = u_time × 0.25)
3. Calculate lookAt matrix targeting origin with world-up Y
4. Generate ray direction from UV through camera

### Step 2: Fiber Geometry Generation
1. Declare flat array `float fiberData[960]` inside main()
2. Loop over 4 shells × 2 rotations:
   - For each fiber, compute 40 segment positions:
     - θ = rotation + (segment/40) × 2π
     - Build quaternion with shell φ
     - Stereographic project
     - Scale by 0.85
     - Store xyz in array (3 floats × 40 = 120 per fiber)

### Step 3: Ray Marching with Volume Rendering
1. Initialize accumulation variables: `vec3 accum = vec3(0)`, `float transmit = 1.0`
2. For each of 64 steps:
   - Compute current ray position
   - **Check distances at current position first**
   - For each fiber:
     - Find minimum distance to any segment using `distanceToSegment()`
     - If `minDist < 0.11` (tube radius):
       - Compute solid tube density: `d = (0.11 - minDist) / 0.11`
       - Square density: `d² ` (quadratic fall-off)
       - Convert to alpha: `α = 1 - exp(-d² × 4.5)`
       - Get fiber HSV color, convert to RGB
       - Blend with transparency: `accum += rgb × α × transmit × 0.85`
       - Attenuate transmission: `transmit *= (1 - α × 0.85)`
     - Add subtle glow at 1.5× radius
   - **Then advance ray position**
   - Early exit if transmit < 0.01
3. Composite over dark background `vec3(0.02)`

### Step 4: Color & Compositing
- **Per-fiber HSV colors**: Hue spread across 8 fibers, S=0.95, V=0.95
- **Glow contribution**: `exp(-glowDist × 5.0) × 0.08` for distances 0.11-0.165
- **Final composite**: `bg × transmit + accum`

## Anticipated Challenges

### GPU Timeout Risk
- **20,480 iterations/pixel** slightly exceeds 15k guideline
- **Mitigation**: Early exit when transmit < 0.01 should reduce actual work by 30-50%
- **Backup**: If timeout occurs, reduce to 48 steps (12,288 iterations)

### Segment Distance Accuracy
- Must use proper `distanceToSegment()` with projection clamping
- Wrapping indices: segment 39 → segment 0 connection

### Density Accumulation
- Critical: Only nearest segment per fiber contributes (no summing all segments)
- Solid tube model: density decreases from center outward
- Unsigned distances only

### Array Size
- 8 fibers × 40 segments × 3 coords = 960 floats (at limit)
- Must be flat array inside main(), not global

## Visual Prediction

### Expected Appearance
- **Interlocking torus-like structures**: 8 curved tubes weaving in 3D space
- **Rainbow color gradient**: Each fiber distinct hue, smooth transitions along curves
- **Volumetric depth**: Front fibers bright, rear fibers dimmed by transmission
- **Gentle rotation**: Slow 0.25 rad/s orbit reveals structure from Y=1.5 viewpoint
- **Dark background**: Maximum contrast with saturated fiber colors
- **Subtle glow**: Soft halos around tubes enhance presence

### Verification Points
- ✓ No overhead view (Y-offset camera prevents collapse)
- ✓ Smooth curves (40 segments sufficient)
- ✓ No uniform color fields (solid tube not hollow shell)
- ✓ No black screen (under GPU limits with early exit)
- ✓ Geometry fills 60-80% of frame (0.85 scale + distance 4.5)
- ✓ Visible at t=0 (geometry exists independent of animation)

### Known Risks from Prior Failures
- **If too small**: May need to reduce distance to 4.0 or increase scale to 0.90
- **If too large**: May need to increase distance to 5.0 or decrease scale to 0.80
- **If black**: GPU timeout → reduce to 48 steps
- **If washed out**: Increase transparency factor from 0.85 to 0.90
