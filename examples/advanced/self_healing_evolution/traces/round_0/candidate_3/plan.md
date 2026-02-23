# Implementation Plan: Interlocked Clifford Tori with Depth-Aware Silhouettes

## Mathematical Foundation

### Hopf Fibration Quaternion Form
For a fiber at latitude φ on S², the Hopf quaternion is:
```
q(θ) = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ), sin(φ/2)sin(θ))
```
where θ ∈ [0, 2π] traces the fiber (a great circle in S³).

### Two Distinct Tori
- **Torus 1 (outer, warm gold)**: φ₁ = π/6, two fibers at rotations 0 and π
- **Torus 2 (inner, cool blue)**: φ₂ = π/3, two fibers at rotations π/2 and 3π/2

This gives 4 total fibers, each with different (φ, rotation) pairs, creating two distinct Clifford tori that are topologically linked.

### Stereographic Projection
Project from S³ to ℝ³:
```
(x, y, z, w) → (x, y, z) / (1 - w + 0.35)
```
The 0.35 offset prevents singularities at w=1.

### Depth-Aware Brightness
During ray marching, track depth `t` along the ray where each fiber is encountered. Modulate brightness by `exp(-0.5 * t)` so nearer fibers glow brighter, creating visual "over-under" weaving at crossings.

## Implementation Plan

### Step 1: Fiber Data Structure
- 4 fibers × 40 segments × 3 coordinates = 480 floats (well under 960 limit)
- Flat array `float fiberData[480]` declared inside `main()`
- Index scheme: `fiberData[fiberIdx * 120 + segIdx * 3 + component]`

### Step 2: Fiber Generation
For each of 4 fibers:
- Fiber 0: φ = π/6, rotation = 0 (outer torus, gold)
- Fiber 1: φ = π/6, rotation = π (outer torus, gold)
- Fiber 2: φ = π/3, rotation = π/2 (inner torus, blue)
- Fiber 3: φ = π/3, rotation = 3π/2 (inner torus, blue)

For each segment (40 per fiber):
- θ = 2π * segIdx / 40.0
- Compute quaternion q(θ) using the fiber's (φ, rotation)
- Apply stereographic projection
- Scale by 0.85 to fill frame
- Store xyz in fiberData array

### Step 3: Camera Setup
- Distance: 4.5 from origin
- Orbital motion: angle = u_time * 0.25
- Elevation: 1.5
- Look at origin with up vector (0, 1, 0)
- Perspective: 45° FOV

### Step 4: Ray Marching with Depth Tracking
For each pixel:
- Cast ray from camera through pixel
- March in steps of 0.09 for 100 iterations
- At each step:
  - Compute distance to ALL 4 fibers (using `distanceToSegment`)
  - Find closest fiber and its distance
  - Record depth `t` (distance along ray)
  - If distance < tubeRadius (0.11):
    - Determine which torus (fibers 0-1 = gold, fibers 2-3 = blue)
    - Compute base color from hue (0.08 for gold, 0.6 for blue)
    - Modulate brightness by `exp(-0.5 * t)` for depth cue
    - Compute density using proven quadratic formula
    - Accumulate color with transparency (alpha *= 0.85)
  - Add subtle glow halo for distances < tubeRadius * 1.5

### Step 5: Color Compositing
- Background: vec3(0.01, 0.01, 0.02) (near-black)
- Composite accumulated color over background
- Use proven opacity blend: `mix(background, fiberColor, opacity)`

## Anticipated Challenges

### Challenge 1: 480 Floats in Nested Loops
**Risk**: Initializing 480 array elements might hit shader compilation limits.
**Mitigation**: Use proven pattern from Candidate 1 (7.5/10) which successfully used 960 floats. 480 is well below that limit.

### Challenge 2: Depth Sort Complexity
**Risk**: Need to track which fiber is closest at each ray step without expensive sorting.
**Mitigation**: Simple linear search over 4 fibers per step. With only 4 fibers, this is ~40 segment checks per step, well within performance budget.

### Challenge 3: Color Separation at Crossings
**Risk**: If depth modulation is too subtle, the "over-under" weaving won't be visible.
**Mitigation**: Use `exp(-0.5 * t)` which gives 0.61× brightness at t=1.0, 0.37× at t=2.0 — perceptible but not extreme. If too subtle, can adjust coefficient.

### Challenge 4: Two Tori May Overlap Too Much
**Risk**: φ = π/6 and π/3 might create tori that obscure each other.
**Mitigation**: These angles were chosen to create distinct major/minor radius ratios while maintaining visual separation. The rotation offsets (0, π vs π/2, 3π/2) further separate the fibers spatially.

## Visual Prediction

### Overall Composition
Two nested ring structures against near-black background. The outer ring glows warm amber/gold, the inner ring glows cool sapphire blue. Camera orbits slowly, revealing the 3D interlocking.

### Key Visual Features

1. **Two Distinct Color Families**
   - No rainbow gradient — just gold and blue
   - High saturation (0.95) creates vibrant glow
   - Complementary warm/cool tension

2. **Depth Weaving Effect**
   - Where fibers cross in depth, nearer fiber is brighter
   - Creates visual "over-under" pattern like woven fabric
   - Makes topological linking tangible

3. **Smooth Closed Curves**
   - 40 segments per fiber ensures smooth appearance
   - No jagged edges or discontinuities

4. **Proper Frame Filling**
   - Post-projection scale 0.85 fills viewport well
   - Camera distance 4.5 provides good perspective
   - Not too small (unlike Round 4 Candidate 0)

5. **Subtle Atmospheric Glow**
   - Halo extends slightly beyond tube radius
   - Adds depth and prevents harsh edges
   - Low intensity (0.08) prevents washout

### Verification Checklist
- [ ] Two distinct toroidal structures visible
- [ ] Gold and blue colors clearly separated by torus
- [ ] Brightness variation at crossing points
- [ ] Smooth curves, no jagged segments
- [ ] Fills frame well, not too small
- [ ] Animation reveals 3D structure
- [ ] No render artifacts (split screen, saturation, etc.)
