# Preservation Plan: Minimal Tweaks to Best Shader

## Goal
Preserve the 7.5/10 shader structure with 1-2 small adjustments to potentially improve visual appeal without risking the proven formula.

## Mathematical Foundation
- **Hopf fibration**: Same proven quaternion form `q = (cos(phi/2)*cos(theta), cos(phi/2)*sin(theta), sin(phi/2)*cos(theta), sin(phi/2)*sin(theta))`
- **Stereographic projection**: `(x/(1-w+0.35), y/(1-w+0.35), z/(1-w+0.35))` with singularity protection
- **8 fibers**: 4 shells (π/8, π/4, 3π/8, π/2) × 2 rotations (0, π/2)
- **40 segments per fiber**: Dense parametric sampling

## Minimal Changes (Only 2 Tweaks)

### Tweak 1: Slightly Adjusted Camera Angle
- **Original**: Orbital rotation at `u_time * 0.25` with Y-offset 1.5
- **New**: Rotate at `u_time * 0.3` (slightly faster reveal) with Y-offset 1.6 (slightly higher viewpoint)
- **Risk**: Very low - still using Y-offset orbit, not spherical coordinates
- **Expected benefit**: Fresh angle without changing proven camera system

### Tweak 2: Warmer Color Palette Shift
- **Original**: Rainbow HSV with `h = fiberIdx/8.0`
- **New**: Shift hue base by +0.05 to emphasize warm golds/oranges instead of starting at pure red
- **Risk**: Very low - same HSV system, just offset
- **Expected benefit**: More visually distinctive warm palette vs generic rainbow

## What I'm NOT Changing
- ✓ Hopf quaternion math (MANDATORY correct form)
- ✓ 8 fibers, 40 segments, 960 float array
- ✓ Camera distance 4.5
- ✓ Post-projection scale 0.85
- ✓ Ray march: check-before-step order
- ✓ Segment-based distance calculation
- ✓ Tube radius 0.11
- ✓ Quadratic density + exponential alpha
- ✓ Transparency factor 0.85
- ✓ Glow halo
- ✓ Dark background vec3(0.02)

## Implementation Steps
1. Copy the best shader structure exactly
2. Modify camera Y-offset: 1.5 → 1.6
3. Modify camera rotation speed: 0.25 → 0.3
4. Modify HSV hue calculation: `fiberIdx/8.0` → `fract(fiberIdx/8.0 + 0.05)`
5. Verify all MANDATORY rules are preserved

## Anticipated Challenges
- **Challenge**: Any change risks breaking what works
- **Mitigation**: Changes are purely cosmetic (camera position, color offset), not structural

## Visual Prediction
- Same beautiful interlocking Hopf fibration structure as 7.5/10 shader
- Slightly elevated viewpoint may show more fiber separation
- Warmer gold/orange palette instead of red-start rainbow
- Smooth orbital rotation revealing 3D structure
- Glowing tubes with transparency showing depth
