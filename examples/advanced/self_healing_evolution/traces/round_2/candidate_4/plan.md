# Phase-Animated Hopf Fibers with Crossing Brightness

## Mathematical Foundation

### Hopf Fibration with Phase Rotation
Starting from the standard Hopf quaternion parameterization on a Clifford torus:
```
q(φ, θ) = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ), sin(φ/2)sin(θ))
```

Apply phase rotation by replacing θ with `θ + u_time * 0.3`:
```
ξ₁ = θ + u_time * 0.3
q(φ, ξ₁) = (cos(φ/2)cos(ξ₁), cos(φ/2)sin(ξ₁), sin(φ/2)cos(ξ₁), sin(φ/2)sin(ξ₁))
```

This creates a rigid rotation of all fibers in S³ space, preserving the linking structure exactly while creating smooth animation.

### Stereographic Projection
Direct S³→R³ projection (mandatory):
```
p₃ᴅ = q.xyz / (1.0 - q.w + 0.35)
```
Post-projection scale: `p₃ᴅ *= 0.85`

### Crossing Detection Algorithm
At each ray march step, maintain 4 minimum distances (one per fiber):
```
float minDist[4] = {1e10, 1e10, 1e10, 1e10};
```

After computing all fiber-to-ray distances:
1. Count fibers with `minDist[i] < tubeRadius * 2.5` → crossings occur when fibers are "near" but not quite touching
2. If 2+ fibers are near simultaneously → crossing point
3. Apply brightness multiplier 1.5× and white shift to winning fiber

This implements "visible linking at crossing points" by detecting where fibers pass close to each other in 3D.

### Color Gradient
4 fibers on single Clifford torus (η = π/4), colored by latitude:
- Fiber 0: Deep red (HSV: 0°)
- Fiber 1: Amber (HSV: 30°)
- Fiber 2: Teal (HSV: 180°)
- Fiber 3: Indigo (HSV: 260°)

Evenly spaced warm→cool gradient to maximize visual separation.

## Implementation Plan

### Step 1: Setup and Camera (lines 1-30)
- Standard aspect-correct UV calculation
- Orbital camera at distance 4.5, Y-offset 1.2
- Camera orbits at `u_time * 0.25` (different from fiber phase rate)
- Ray direction from camera through UV pixel

### Step 2: Fiber Geometry Generation (lines 31-80)
- 4 fibers at shell angle η = π/4 (single Clifford torus)
- Rotation offset 0 for all (they're distinguished by θ₀, not shell rotation)
- Each fiber: θ ranges 0→2π in 40 segments
- Apply phase animation: `theta = theta_base + u_time * 0.3`
- Store 160 vec3 positions (4 fibers × 40 segments) in flat array inside main()
- Project each quaternion point using direct S³ stereographic
- Post-multiply by 0.85 scale

### Step 3: Ray Marching with Crossing Detection (lines 81-180)
For each of 48 steps:
1. Initialize `float minDist[4]` to large values
2. For each of 4 fibers:
   - For each of 40 segments:
     - Compute `distanceToSegment(rayPos, seg[i], seg[i+1])`
     - Update `minDist[fiberIndex]` if smaller
3. After all fibers checked, detect crossings:
   - Count fibers with `minDist[i] < tubeRadius * 2.5`
   - If count >= 2, mark as crossing point
4. Find winning fiber (smallest minDist overall)
5. If crossing: multiply density by 1.5, shift color toward white
6. Accumulate density using solid tube formula: `max(0, (tubeRadius - minDist) / tubeRadius)`
7. Composite using quadratic density + exponential alpha with transparency 0.85
8. Add glow halo at 1.5× tube radius

### Step 4: Output (lines 181-185)
- Apply dark background vec3(0.02)
- Output final composited color

## Anticipated Challenges

### Challenge 1: Array Size Management
- 4 fibers × 40 segments = 160 vec3 = 480 floats (within 960 limit)
- Must use flat array `float pos[480]` and manual indexing
- Access pattern: `pos[fiberIdx*120 + segIdx*3 + component]`

### Challenge 2: Crossing Detection False Positives
- Threshold of `2.5 * tubeRadius` chosen empirically
- Too small: miss crossings that appear visually close
- Too large: trigger crossing boost everywhere
- 2.5× gives ~0.275 units of "near but not touching" detection range

### Challenge 3: GPU Performance
- 48 steps × 4 fibers × 40 segments = 7,680 iterations per pixel
- Well under 15,000 limit but still substantial
- Reduced from proven 80 steps to 48 to keep budget
- Step size increased to 0.1 (vs 0.08) to compensate

### Challenge 4: Phase Rate Tuning
- Fiber phase: `u_time * 0.3` → 0.3 rad/s
- Camera orbit: `u_time * 0.25` → 0.25 rad/s
- Different rates prevent camera from "locking" to fiber rotation
- Creates evolving viewpoints as relative angles shift

## Visual Prediction

### Expected Output
Four luminous fibers forming an interlocked ring system, slowly rotating as a unit. The fibers follow a gradient from deep red (bottom) through amber and teal to indigo (top). Where fibers cross in 3D space, bright white-hot nodes appear, creating pulsing accents as the rotation brings different pairs into alignment.

### Key Visual Features
1. **Fiber Definition**: Each fiber should be a clear, smooth tube against dark background
2. **Color Gradient**: Warm red/amber at bottom transitioning to cool teal/indigo at top
3. **Crossing Points**: 8-12 bright white nodes visible at any time where fibers pass near each other
4. **Animation**: Gentle rotation (full cycle ~21 seconds) with crossings drifting along curves
5. **Linking Structure**: Visual sense of "braiding" or "knotting" from the crossing highlights
6. **Depth**: Slight brightness variation as fibers recede (from glow and transparency)

### Success Criteria
- All 4 fibers clearly visible and distinguishable
- Crossing detection produces obvious brightness spikes (not uniform)
- Animation is smooth and continuous (no judder)
- No black screens, no runaway brightness, no degenerate geometry
- Topology appears "linked" (fibers weave through each other)

### How This Targets 8+ Score
This implementation directly addresses the three improvement paths from the 7.5/10 analysis:
1. **Sharper fiber definition**: Nearest-segment-only density (already in 7.5 template)
2. **Visible linking at crossings**: NEW - crossing brightness boost
3. **Subtle animation**: NEW - phase rotation in S³

By keeping everything else identical to the proven template (4 fibers, 40 segments, single torus, standard projection), this is the most conservative possible path to 8+. The only additions are crossing detection (comparing 4 stored distances) and phase animation (adding u_time to theta) — both minimal computational overhead and mathematically sound.
