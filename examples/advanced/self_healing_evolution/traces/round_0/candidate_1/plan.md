# Hopf Fibration Implementation Plan

## Mathematical Foundation

### Core Equations

**Hopf Map (S³ → S²):**
- Quaternion parametrization: `q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ), sin(φ/2)sin(θ))`
- Where φ = shell angle (constant per fiber), θ ∈ [0, 2π] (sweeps the fiber)
- Stereographic projection: `p = (q.x, q.y, q.z) / (1 - q.w + ε)`

**Key Parameters:**
- φ values: π/8, π/4, 3π/8, π/2 (4 shells spread across torus surface)
- Rotation offsets: 0, π/2 (2 circles per shell for 8 total fibers)
- 40 segments per fiber for smooth curves
- Total: 8 fibers × 40 segments × 3 coords = 960 floats

**Distance Metric:**
- Point-to-line-segment distance for each fiber segment
- `distanceToSegment(rayPos, segmentStart, segmentEnd)`

### Shader Coordinate Mapping

**Camera Setup:**
- Position: Orbital at radius 4.5, elevation 1.5, rotating at 0.25 rad/s
- Camera-to-world matrix: forward, right, up vectors
- Ray direction: `normalize(forward + uv.x * right + uv.y * up)`

**UV Coordinates:**
- Center origin: `uv = (gl_FragCoord.xy / u_resolution.xy) * 2.0 - 1.0`
- Aspect correction: Apply to right vector scaling

**Post-Projection Scale:**
- Multiply stereographic result by 0.85 to fill frame

## Implementation Plan

### 1. Helper Functions (Lines 1-30)
- `distanceToSegment(vec3 p, vec3 a, vec3 b)` - returns closest distance to line segment
- `hsv2rgb(vec3 hsv)` - color conversion for vibrant fiber colors

### 2. Fiber Data Generation (Lines 31-95)
- Declare `float fiberData[960];` inside main() (TIER 1 requirement)
- Nested loops:
  - 4 shell angles: shellEta = π/8, π/4, 3π/8, π/2
  - 2 rotations per shell: rotOffset = 0, π/2
  - 40 segments per fiber: phi sweeps 0 to 2π
- For each segment:
  - Compute theta = segment angle
  - Build quaternion: `vec4(cos(shellEta/2)*cos(theta), cos(shellEta/2)*sin(theta), sin(shellEta/2)*cos(theta), sin(shellEta/2)*sin(theta))`
  - Apply rotation offset to phi
  - Stereographic projection with singularity protection (ε = 0.35)
  - Scale by 0.85
  - Store x, y, z in fiberData[idx], fiberData[idx+1], fiberData[idx+2]

### 3. Camera Setup (Lines 96-110)
- Orbital camera at distance 4.5
- Rotation: angle = u_time * 0.25
- Position: `(4.5 * cos(angle), 1.5, 4.5 * sin(angle))`
- Look-at origin, compute forward, right (aspect-corrected), up vectors

### 4. Ray Marching (Lines 111-180)
- 100 steps, stepSize = 0.09 (budget: 100 × 0.09 = 9.0 > 2 × 4.7)
- Start rayPos at camera position
- Accumulate color and opacity:
  - For each fiber (8 total):
    - For each segment in fiber (40 segments, check indices 0-39):
      - Load segment start and end from fiberData
      - Compute `distanceToSegment(rayPos, segStart, segEnd)`
      - Track minimum distance
    - If minDist < tubeRadius (0.11):
      - Compute normalized distance: `d = (tubeRadius - minDist) / tubeRadius`
      - Density: `d * d` (quadratic for smooth falloff)
      - Alpha: `(1.0 - exp(-density * 4.5)) * 0.85` (transparency factor)
      - Color: HSV(fiberIndex / 8.0, 0.95, 0.95) converted to RGB
      - Composite: `color += alpha * (1.0 - opacity) * fiberColor`
      - Update: `opacity += alpha * (1.0 - opacity)`
    - Else if minDist < tubeRadius * 1.5 (glow halo):
      - Glow: `exp(-(minDist - tubeRadius) * 5.0) * 0.08`
      - Composite: `color += glow * (1.0 - opacity) * fiberColor`
  - **THEN** advance ray: `rayPos += rayDir * stepSize` (TIER 1: check before step)
  - Break if opacity > 0.99

### 5. Final Output (Lines 181-185)
- Blend accumulated color over dark background: `vec3(0.02)`
- Output: `gl_FragColor = vec4(color, 1.0)`

## Anticipated Challenges

### Array Size Limit
- 960 floats is at hardware limit for some drivers
- Mitigation: Keep shader simple, no additional complex functions
- Evidence: Candidates 0 and 1 succeeded with 960 floats when shader was otherwise minimal

### Stereographic Singularity
- When q.w → 1, denominator (1 - q.w) → 0
- Mitigation: Add ε = 0.35 protection term
- This shifts projection slightly but prevents infinities

### Fiber Visibility Balance
- Too few fibers: Won't show "interlocking" property
- Too many fibers: "Tangled structure makes it difficult to trace individual fibers" (judge feedback on 7.5/10 candidate)
- Solution: Use proven 8-fiber configuration (4 shells × 2 circles)

### Ray March Step Order
- Candidate 0 (6/10) stepped before checking → appeared small
- Candidate 1 (7.5/10) checked before stepping → filled frame properly
- Solution: Always check geometry at current rayPos, THEN advance

### Distance Calculation Efficiency
- Checking 8 fibers × 40 segments = 320 segment distances per ray step
- 100 steps × 320 checks = 32,000 distance calculations per pixel
- Mitigation: Simple distanceToSegment formula, no branching inside segment loop

## Visual Prediction

### Expected Output
- **Structure**: 8 colored fiber loops forming interlocking rings
- **Topology**: Hopf fibration — each fiber is a closed circle, all fibers link but don't intersect
- **Colors**: Rainbow spectrum (8 hues evenly distributed around color wheel)
- **Layering**: Fibers pass over/under each other with visible depth due to 85% transparency
- **Glow**: Subtle atmospheric halo around each fiber for "depth and layering" (judge's words)
- **Composition**: Structure fills ~70-80% of frame (post-projection scale 0.85)
- **Animation**: Gentle rotation reveals 3D structure as camera orbits

### Key Visual Features to Verify

1. **Closed loops**: Each fiber returns to its starting point (theta sweeps full 2π)
2. **No self-intersection**: Each individual fiber is a simple circle in 3D
3. **Interlocking**: Fibers weave through each other without breaking
4. **Smooth curves**: 40 segments per fiber should appear continuous
5. **Color distinction**: All 8 fibers visible with distinct hues
6. **Depth cues**: Transparency allows seeing which fiber is in front
7. **Proper scale**: Not too small (Candidate 0's issue) or too large

### Success Criteria
- Judge recognizes Hopf fibration topology immediately
- "Interlocking colored rings" clearly visible
- Main goal alignment: 8-10/10
- Composition: 7-10/10 (well-framed, good use of space)
- Visual impact: 7-10/10 (vibrant colors, clear depth)
