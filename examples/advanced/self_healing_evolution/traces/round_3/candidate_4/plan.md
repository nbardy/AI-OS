# Dual-Scale Villarceau Circles with Complementary Warm/Cool Split

## Mathematical Foundation

### Hopf Fibration Parameterization
- **S³ quaternion**: `q = (cos(η/2)cos(ξ₁), cos(η/2)sin(ξ₁), sin(η/2)cos(ξ₁+ξ₂), sin(η/2)sin(ξ₁+ξ₂))`
  - η (eta/phi) = shell angle, controls the torus size in S³
  - ξ₁ (xi1/theta) = rotation parameter [0, 2π), parameterizes the circle
  - ξ₂ (xi2/rotation) = fiber offset, determines which Hopf fiber

- **Stereographic projection S³→R³**: `(x,y,z) = q.xyz / (1 - q.w + ε) × scale`
  - ε = 0.15 (singularity protection, proven in tiered guidance)
  - scale = 1.5 (post-projection scale, proven optimal)

### Two Fiber Families
**Family A (Inner, Warm)**: 4 fibers on Clifford torus
- Shell: η = π/4 ≈ 0.7854 (projects to smaller radius)
- Rotations: ξ₂ ∈ {0, π/2, π, 3π/2}
- Colors: Ruby-coral (HSV hue 0.02, 0.05, 0.08, 0.11) with sat=0.95, val=0.95

**Family B (Outer, Cool)**: 4 fibers on larger torus
- Shell: η = π/6 ≈ 0.5236 (projects to larger radius)
- Rotations: ξ₂ ∈ {π/4, 3π/4, 5π/4, 7π/4} (45° offset from Family A)
- Colors: Teal-sapphire (HSV hue 0.52, 0.55, 0.58, 0.61) with sat=0.95, val=0.95

### Linking Structure
- Each fiber forms a closed circle (Villarceau circle on the torus)
- Linking number = 1 between any fiber from Family A and any from Family B
- The 45° rotation offset maximizes spatial separation in R³
- Inner family threads through outer family → visible interlocking

## Implementation Plan

### 1. Setup and Initialization (lines 1-50)
- Define HSV→RGB converter
- Calculate aspect-corrected UV from gl_FragCoord
- Set up camera: orbital position at distance 3.0, Y-offset 1.2, rotation 0.25 rad/s
- Build camera ray from eye through pixel
- Initialize dark background vec3(0.02)

### 2. Generate 8 Fiber Geometries (lines 51-150)
- Allocate 8 flat float arrays inside main(): `float f0[120], f1[120], ..., f7[120]`
  - Each fiber: 40 segments × 3 coords = 120 floats
  - Total: 960 floats (at MANDATORY limit)
- Loop over 8 fibers:
  - fibers 0-3: shell = π/4, rotations = {0, π/2, π, 3π/2}
  - fibers 4-7: shell = π/6, rotations = {π/4, 3π/4, 5π/4, 7π/4}
- For each fiber, generate 40 points along ξ₁ ∈ [0, 2π):
  - Compute quaternion q at (shell, ξ₁, rotation)
  - Project: `vec3 p = q.xyz / (1.0 - q.w + 0.15) * 1.5`
  - Store (p.x, p.y, p.z) in flat array at index [seg*3, seg*3+1, seg*3+2]

### 3. Ray March Loop (lines 151-220)
- 46 ray march steps, step size 0.10
  - Budget: 46 × 8 × 40 = 14,720 iterations/pixel (< 15,000 limit)
- **Before each step**: check distances at current rayPos
  - For each of 8 fibers:
    - For each of 40 segments: distanceToSegment(rayPos, seg[i], seg[(i+1)%40])
    - Track minimum distance across all segments of this fiber
  - Find global minimum across all 8 fibers, record (minDist, fiberIdx, depth)
- If minDist < tubeRadius (0.05):
  - **Solid tube density**: `d = max(0.0, (0.05 - minDist) / 0.05)`
  - Quadratic: `d = d * d`
  - Color based on fiberIdx:
    - 0-3: `hsv2rgb(vec3(0.02 + fiberIdx*0.03, 0.95, 0.95))` (warm)
    - 4-7: `hsv2rgb(vec3(0.52 + (fiberIdx-4)*0.03, 0.95, 0.95))` (cool)
  - Gentle depth brightness: `color *= mix(0.85, 1.0, exp(-0.03*depth))`
  - Exponential alpha: `alpha = 1.0 - exp(-d * 4.5)`
  - Accumulate with transparency: `finalColor += color * alpha * (1.0 - finalAlpha)`
  - Update finalAlpha: `finalAlpha += alpha * (1.0 - finalAlpha) * 0.85`
- **Then advance**: `rayPos += rayDir * 0.10`
- Exit early if finalAlpha > 0.98

### 4. Glow Halo (lines 221-240)
- For each fiber, check if minimum distance in range [0.05, 0.075] (1.5× tube radius)
- If yes: `glow = exp(-(minDist - 0.05) * 5.0) * 0.08 * fiberColor`
- Accumulate glow contribution

### 5. Final Composite (lines 241-250)
- Blend accumulated fiber color over dark background
- Add glow halo
- Output to gl_FragColor

## Anticipated Challenges

### Challenge 1: Array Size Limit
- **Problem**: 8 fibers × 40 segments × 3 coords = 960 floats exactly at limit
- **Solution**: Use 40 segments (not 45), stay precisely at limit
- **Verification**: Count declarations: 8 arrays of 120 floats = 960

### Challenge 2: GPU Iteration Budget
- **Problem**: Ray march must not exceed ~15,000 iterations/pixel
- **Solution**: 46 steps × 8 fibers × 40 segments = 14,720 (safe margin)
- **Fallback**: Reduce to 45 steps if needed (14,400 iterations)

### Challenge 3: Fiber Visibility at Scale 1.5
- **Problem**: Previous scale 0.85 → merged blob
- **Solution**: Scale 1.5 spreads geometry; camera at distance 3.0 keeps in frame
- **Verification**: Inner shell at η=π/4 projects to ~1.0 radius, outer at η=π/6 to ~1.7 radius

### Challenge 4: Color Distinguishability
- **Problem**: Need to instantly identify which family each fiber belongs to
- **Solution**: Warm (hue 0.0-0.12) vs Cool (hue 0.50-0.62) with high saturation
- **Benefit**: Complementary colors maximally distinct, proven in prior 7/10 candidate

### Challenge 5: Threading Visibility
- **Problem**: Must show interlocking structure in still frame
- **Solution**:
  - 45° rotation offset maximizes separation when viewed from angle
  - Y-offset 1.2 tilts view to reveal depth layering
  - Slow orbital rotation (0.25 rad/s) captures good angle even at t=0

## Visual Prediction

### Expected Appearance
- **Foreground**: Two interleaved sets of thin luminous rings
  - 4 smaller ruby-coral rings (inner family, tight circle)
  - 4 larger teal-sapphire rings (outer family, wider circle)
- **Structure**: Chain-mail weave pattern
  - Warm rings thread through gaps between cool rings
  - Cool rings thread through gaps between warm rings
  - Visible crossing points where one ring passes over/under another
- **Depth**: Gentle brightness gradient reveals 3D layering
  - Rings closer to camera slightly brighter
  - Rings farther away slightly dimmer (not invisible)
- **Background**: Deep black (vec3(0.02)) for maximum contrast
- **Glow**: Subtle luminous halos around each fiber (1.5× radius)

### Key Visual Features to Verify

1. **Eight distinct rings visible**: Not merged into blob
2. **Two clear families**: Warm vs cool colors immediately distinguishable
3. **Size contrast**: Inner rings noticeably smaller/tighter than outer rings
4. **Threading/linking**: At least 2-3 crossing points visible where rings interweave
5. **Tube continuity**: Each ring is a smooth, closed curve (no breaks)
6. **Aspect-correct geometry**: Rings are circular, not elliptical (proper UV scaling)
7. **Adequate brightness**: All 8 rings visible, none lost in darkness or blown out
8. **Spatial separation**: 45° offset means rings from different families don't overlap perfectly

### Success Criteria
- Immediate "wow" reaction: "I see two sets of interlocked rings"
- Color coding works: "The warm/cool split makes the structure obvious"
- Geometric precision: "Each ring is clearly defined, not fuzzy or merged"
- 3D depth: "I can tell which rings are in front and which are behind"
- Mathematical correctness: "This is clearly a Hopf fibration, not an approximation"

### Expected Score Range
- **Target**: 8-9/10 (exceeding prior best of 7/10)
- **Rationale**:
  - Builds on proven 7/10 Villarceau approach
  - Fixes ALL R2 geometry failures (scale, epsilon, tube radius)
  - Adds scale contrast (inner/outer families) per feedback
  - Uses proven color split (ruby/cyan from 7/10 entry)
  - Maximizes spatial separation (45° offset geometric improvement)
  - No wasted features (no animation for still evaluation)
