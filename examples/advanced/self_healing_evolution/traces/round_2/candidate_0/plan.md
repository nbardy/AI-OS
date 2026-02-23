# Preservation Plan: Minimal Refinement of Best Shader

## Goal
Preserve the 7.5/10 shader structure with minimal changes. Only adjust color palette to enhance visual distinction between fibers.

## Mathematical Foundation
**No changes to geometry or projection:**
- Hopf fibration: `q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ), sin(φ/2)sin(θ))`
- Direct S³ stereographic: `q.xyz / (1 - q.w + 0.35)`
- Post-projection scale: `0.85`
- 8 fibers: 4 shells (π/8, π/4, 3π/8, π/2) × 2 rotations (0, π/2)
- 40 segments per fiber with wraparound

## Implementation Plan

### What I'm Preserving (100% unchanged):
1. ✓ Correct Hopf quaternion construction
2. ✓ Direct S³→R³ stereographic projection
3. ✓ Y-offset orbital camera (4.5 dist, Y=1.5, 0.25 rad/s)
4. ✓ Flat array `fiberData[960]` inside main()
5. ✓ Segment-based distance function
6. ✓ Solid tube density `(tubeRadius - minDist) / tubeRadius`
7. ✓ Nearest-segment-only accumulation
8. ✓ 64 ray march steps (safe GPU budget)
9. ✓ Tube radius 0.11
10. ✓ Ray step size 0.08
11. ✓ Quadratic density + exponential alpha
12. ✓ Glow halo at 1.5x tube radius

### What I'm Changing (minimal):
**Single change: Enhanced color palette**
- Replace HSV(fiberIdx/8.0, 0.95, 0.95) with triadic color scheme
- 3 color families (warm, cool, neutral) to better distinguish fibers
- Gold/orange (warm): fibers 0, 3, 6
- Sapphire/cyan (cool): fibers 1, 4, 7
- Magenta/purple (neutral): fibers 2, 5
- Still using HSV→RGB with high saturation (0.95) and value (0.95)

**Rationale:** The original linear hue progression may cause adjacent fibers to blend visually. Triadic spacing provides maximum perceptual separation while maintaining the proven rendering pipeline.

## Anticipated Challenges
**None expected** - this is a cosmetic-only change:
- Color calculation happens after all geometry/density work
- No impact on GPU budget or ray marching logic
- Falls back to original behavior if triadic scheme fails (unlikely)

## Visual Prediction
**Expected output:**
- Same interlocking Hopf fiber structure as 7.5/10 shader
- Same smooth 3D curves with depth and transparency
- Enhanced: Fibers now clearly grouped by color temperature
- Warm fibers (gold/orange) pop against cool background
- Cool fibers (sapphire/cyan) provide contrast
- Magenta fibers bridge the palette
- Should maintain or slightly improve visual clarity over 7.5/10

**Key visual features to verify:**
- 8 distinct fibers visible (not 7, not 9)
- Smooth circular paths (no faceting)
- Proper depth ordering (transparency working)
- Glow halos around fibers
- Dark background (vec3(0.02))
- Orbital camera motion at 0.25 rad/s
