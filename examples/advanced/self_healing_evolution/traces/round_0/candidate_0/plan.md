# Synthesis Plan: Best of Round 4 + Tier 3 Improvements

## Mathematical Foundation

### Hopf Fibration Parametrization
Using the proven quaternion form from Candidates 0/1:
```
q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ), sin(φ/2)sin(θ))
```
Where:
- φ = shell angle (constant per fiber): π/8, π/4, 3π/8, π/2
- θ = fiber parameter: sweeps 0→2π in 40 segments
- rotOffset = fiber rotation: 0, π/2, π, 3π/2

### Stereographic Projection
```
p = (q.x, q.y, q.z) / (1 - q.w + 0.35)
```
Post-projection scale: 0.85 (proven in Candidate 1)

### Distance Calculation
Segment-based distance for smooth curves:
```
distanceToSegment(rayPos, pointA, pointB)
```

### Density and Opacity
Quadratic density with exponential decay (Candidate 1 pattern):
```
d = (tubeRadius - dist) / tubeRadius  // normalized [0,1]
density = d * d
alpha = 1.0 - exp(-density * 4.5)
alpha *= 0.85  // transparency for layering
```

## Implementation Plan

### 1. Fiber Configuration (Tier 2 Proven + Tier 3 Experiment)
**Change from Candidate 1**: Reduce from 8 to 6 fibers (3 shells × 2 circles) per judge suggestion "fewer loops with more spacing."

- 3 shells at φ = π/6, π/3, π/2 (spread across 0→π/2)
- 2 rotations at 0, π (opposing circles)
- 40 segments per fiber
- Total: 6 fibers × 40 segments × 3 coords = 720 floats (well under 960 limit)

### 2. Tube Radius (Tier 3 Experiment)
**Change from Candidate 1**: Increase from 0.11 to 0.13 to compensate for fewer fibers and show structure better.

### 3. Glow Effect (Tier 2 Proven)
Keep Candidate 1's successful glow halo:
```glsl
if (dist < tubeRadius * 1.5) {
    float glowDist = (dist - tubeRadius) / (tubeRadius * 0.5);
    color += fiberColor * exp(-glowDist * 5.0) * 0.08;
}
```

### 4. Color Flow Animation (Tier 3 Experiment)
Add time-based hue shift along fibers:
```glsl
float hue = fract(baseHue + u_time * 0.1);
```
This makes color appear to flow along the fibers, addressing judge's suggestion for animation showing "iteration process."

### 5. Ray March Pattern (Tier 1 Mandatory)
Use Candidate 1's proven order:
1. Check fiber distances at current rayPos
2. Accumulate color/opacity
3. THEN advance rayPos += rayDir * stepSize

### 6. Camera Setup (Tier 2 Proven)
- Distance: 4.5 (proven in Candidate 1)
- Elevation: 1.5 (proven in Candidate 1)
- Orbital speed: 0.25 rad/s (proven in Candidate 1)

### 7. Array Declaration (Tier 1 Mandatory)
Declare `float fiberData[720];` inside main() function.

## Anticipated Challenges

### Challenge 1: Fewer Fibers May Look Sparse
**Mitigation**: Increased tube radius (0.13) and glow effect will maintain visual presence. The spacing should actually improve structure clarity per judge feedback.

### Challenge 2: Color Flow Animation Timing
**Risk**: Too fast = dizzying, too slow = imperceptible.
**Solution**: Use 0.1 cycles/second (10-second period). At single-frame render, will show slight offset but not disrupt static appearance.

### Challenge 3: Shell Angle Selection
**Decision**: Changed from π/8, π/4, 3π/8, π/2 to π/6, π/3, π/2 for better spacing with 3 shells instead of 4.

### Challenge 4: Maintaining 7.5/10 Score
**Strategy**: Keep ALL Tier 1 + Tier 2 proven patterns from Candidate 1, only modify:
- Fiber count (8→6) per judge suggestion
- Tube radius (0.11→0.13) to compensate
- Add color flow (judge suggestion)

## Visual Prediction

### Expected Output
**Core structure**: 6 interlocking circular fibers forming Hopf fibration topology
- 3 shells visible at different depths
- 2 opposing circles per shell clearly distinguishable
- Thicker tubes (0.13) reveal individual paths better than Candidate 1

**Color**:
- Rainbow palette (6 fibers = 6 distinct hues spaced 60° apart)
- High saturation (0.95) against dark background (0.02)
- Subtle color flow from time-based offset
- Glow halos around each fiber for atmosphere

**Depth and layering**:
- 85% transparency allows overlapping fibers to show through
- Glow effect adds perceived thickness
- Orbital camera reveals 3D structure

### Key Visual Features to Verify

1. **Hopf topology visible**: Fibers should appear as interlocking circles, not a blob or torus
2. **Individual fiber traceability**: With only 6 fibers, viewer should be able to follow a single loop
3. **Good frame composition**: Post-scale 0.85 should fill viewport without clipping
4. **Smooth curves**: 40 segments should produce no visible faceting
5. **Color distinction**: 6 colors should be clearly separable

### Success Criteria
- **Target score**: 7.5-8.5/10
- **Judge should note**: "improved clarity," "easier to trace individual fibers," "retains complexity"
- **Main goal alignment**: 8-9/10 (clearer Hopf structure than Candidate 1)
- **Visual appeal**: 7-8/10 (proven patterns + refinement)
- **Composition**: 7-8/10 (better spacing than Candidate 1)
