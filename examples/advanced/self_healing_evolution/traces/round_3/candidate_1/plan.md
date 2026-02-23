# Implementation Plan: Synthesized Hopf Fibration

## Mathematical Foundation

### Core Hopf Fibration Math
- **S³ parametrization**: `q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ), sin(φ/2)sin(θ))`
  - φ (phi) = shell angle (controls which fiber circle)
  - θ (theta) = parameter around the fiber [0, 2π]
- **Stereographic projection S³→R³**: `p = q.xyz / (1 - q.w + ε)`
  - Using ε = 0.15 for moderate singularity protection (PROVEN)
  - Direct projection, NO intermediate S² step

### Fiber Configuration
- **6 fibers total**: 3 shells × 2 rotations
  - Shells: φ = π/6, π/3, π/2 (wide spacing for distinct radii)
  - Rotations: 0, π/2 (orthogonal to prevent overlap)
- **40 segments per fiber** with wraparound indexing
- **Color coding**: HSV per fiber with H = shellIndex/3 + rotationIndex/6

### Visualization Geometry
- **Camera**: Y-offset orbit (NOT spherical angles)
  - Position: `(3.0*cos(t*0.25), 1.5, 3.0*sin(t*0.25))`
  - Distance: 3.0 (mid-range for 1.5× scale)
  - Y-offset: 1.5 (proven sweet spot)
- **Post-projection scale**: 1.5× (avoid 0.85 blob compression)
- **Tube radius**: 0.06 (thin enough to stay distinct, thick enough to see)

### Rendering Strategy
- **Ray marching**: 48 steps × 0.10 step size = 4.8 units max depth
- **Density calculation**: Only nearest segment contributes (no accumulation)
  - Solid tube: `density = (tubeRadius - minDist) / tubeRadius` when minDist < tubeRadius
- **Alpha blending**: Quadratic density → exponential alpha with 0.85 transparency
- **Glow halo**: At 1.5× tube radius for depth perception

## Implementation Plan

### Step 1: Setup and Utilities
1. Define constants (tube radius, singularity epsilon, scale factor)
2. Implement HSV→RGB conversion
3. Implement segment distance function

### Step 2: Generate Fiber Data
1. Allocate flat float array `fiberData[960]` inside main() (6 fibers × 40 segments × 4 floats)
2. Loop through 3 shells × 2 rotations
3. For each fiber, compute 40 segments:
   - Calculate Hopf coordinates in S³
   - Apply stereographic projection
   - Scale by 1.5
   - Store x,y,z,colorHue in flat array

### Step 3: Camera and Ray Setup
1. Compute orbital camera position with Y-offset
2. Calculate view matrix (lookAt)
3. Compute UV with aspect correction: `(fragCoord - 0.5*resolution) / resolution.y`
4. Generate ray direction from camera through UV

### Step 4: Ray Marching
1. For each of 48 steps:
   - Compute current ray position
   - Find minimum distance to all fiber segments
   - If distance < tube radius:
     - Calculate solid tube density
     - Accumulate color with transparency blending
     - Add glow halo contribution
   - Advance ray by 0.10

### Step 5: Final Compositing
1. Blend accumulated color over dark background (0.02)
2. Output to gl_FragColor

## Anticipated Challenges

### Challenge 1: Array Size Management
- **Risk**: 960 floats is close to limit
- **Mitigation**: Stay at exactly 6 fibers × 40 segments, no expansion
- **Verification**: Shader compiles without errors

### Challenge 2: Geometric Spread vs. Screen Fill
- **Risk**: 1.5× scale might push fibers outside frustum
- **Mitigation**: Camera distance 3.0 balances proximity and field of view
- **Fallback**: Scale is proven safe at 1.2-2.0 range

### Challenge 3: Fiber Merging
- **Risk**: Projected fibers might overlap despite wide shell spacing
- **Mitigation**:
  - Tube radius 0.06 (thin)
  - Shell angles π/6, π/3, π/2 (wide spacing)
  - Singularity ε = 0.15 (moderate compression)
- **Verification**: Each fiber should be individually visible

### Challenge 4: GPU Performance
- **Total iterations**: 48 steps × 6 fibers × 40 segments = 11,520 (under 15k limit)
- **Mitigation**: Already optimized, no additional measures needed

## Visual Prediction

### Expected Output
- **Structure**: 6 distinct circular fiber loops linking through 3D space
- **Topology**: Nested/interlocking pattern showing Hopf fibration linking
- **Color**: Rainbow gradient across fibers (reds/oranges for outer shells, blues/purples for inner)
- **Depth**: Glow halos and transparency create 3D perception
- **Scale**: Fibers fill ~60-80% of frame, clearly separated from each other

### Key Visual Verification Points
1. **Separation**: Each of 6 fibers visible as individual tubes (NOT merged blob)
2. **Circularity**: Fibers appear as smooth circles/ellipses (NOT jagged or broken)
3. **Linking**: Visual evidence of topological linking (fibers pass through each other's centers)
4. **Color variation**: Distinct hues for each fiber
5. **No degeneration**: No point collapse, no extreme stretching

### Success Criteria
- Visually distinct from "kidney bean blob" (R2 failure mode)
- Shows more geometric complexity than "tiny ribbon" (R1/R2 3/10 candidates)
- Maintains mathematical structure (not "distorted blob" like R0 3/10)
- Target: 6-8/10 range by combining proven patterns
