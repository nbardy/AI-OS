# Preservation Plan: Minimal Tweaks to Best Shader

## Mathematical Foundation
The best shader already implements:
- **Hopf fibration**: `q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ), sin(φ/2)sin(θ))`
- **Stereographic projection**: `q.xyz / (1 - q.w + 0.15)`
- **Distance to segment**: Point-to-line-segment distance for curves
- **Solid tube density**: `(tubeRadius - minDist) / tubeRadius`

**NO changes to math** - it's already correct.

## Implementation Plan

### What I'm PRESERVING (not changing):
1. ✓ 8 fibers (4 shells × 2 rotations)
2. ✓ Shell angles: π/8, π/4, 3π/8, π/2
3. ✓ Rotations: 0 and π/2
4. ✓ 40 segments per fiber
5. ✓ Stereographic projection with 0.15 epsilon
6. ✓ Post-projection scale (appears to be default 1.0)
7. ✓ Camera orbit with Y-offset
8. ✓ Distance-to-segment ray marching
9. ✓ HSV color per fiber
10. ✓ Quadratic density + exponential alpha
11. ✓ Glow halo
12. ✓ Dark background

### What I'm TWEAKING (1-2 small changes):

**Tweak 1: Increase post-projection scale from 1.0 to 1.5**
- Rationale: The shader appears to be cut off. From TIER 1 MANDATORY rules, scale should be 1.2-2.0, and current appears to be 1.0
- Location: After stereographic projection, multiply `projected *= 1.5;`
- Impact: Larger, more visible fibers that fill the frame better

**Tweak 2: Adjust camera distance from (appears too far) to 3.0**
- Rationale: TIER 1 MANDATORY says "4.5 proven with 0.85 scale, use 3.0 with 1.5 scale"
- Since we're setting scale to 1.5, camera should be 3.0
- Impact: Brings fibers closer to match the larger scale

## Anticipated Challenges

None expected - we're making minimal numerical adjustments to proven code.

Edge cases already handled:
- Stereographic singularity (0.15 epsilon)
- Segment wrapping (modulo 40)
- UV aspect correction
- Ray march bounds

## Visual Prediction

Expected output:
- **Same structure** as current best shader but **larger and better framed**
- 8 interlinked Hopf fiber rings in distinct colors
- Fibers fill more of the screen (not cut off at edges)
- Smooth tubes with glow halos
- Dark background for contrast
- Slow orbital camera rotation revealing 3D linking structure
- Transparent overlaps showing depth

Key verification:
- Fibers should be larger than current best
- Should fill frame without being cut off
- Same beautiful rainbow coloring and linking topology
- No performance issues (same GPU budget)
